"""Disabled-by-default HTTPS WSGI adapter for BAM identity sign-in.

This transport wraps the trusted AuthLoginAPI; it never verifies Google
identity tokens itself, enrolls identities, or grants business membership.
A production gateway must provide TLS, IP/global rate limits, secure
credential storage, verified email delivery, and session lifecycle controls.
"""
import json
import re
import time

_MAX_JSON_BYTES = 8192
_PATHS = {
    '/api/v1/auth/password': frozenset({'email', 'password', 'tenant_id'}),
    '/api/v1/auth/google-challenge': frozenset(),
    '/api/v1/auth/google': frozenset({'challenge_id', 'id_token', 'tenant_id'}),
}
_SESSION_PATTERN = re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')


def _unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def _validate_text(value, *, maximum, allow_newline=False):
    return (type(value) is str and bool(value.strip())
            and len(value) <= maximum
            and (allow_newline or all(ord(char) >= 32 for char in value)))


class BAMAuthWSGI:
    """Explicitly mounted, disabled-by-default authentication routes.

    Even when enabled, this is a transport adapter, not a production server.
    AuthLoginAPI must have a durable account/IP-aware throttle configured.
    Never expose this alongside the loopback-only HTTP development server.
    """

    def __init__(self, api, *, enabled=False, clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean enable flag required')
        if enabled and getattr(api, 'throttle', None) is None:
            raise ValueError('Enabled password login requires a trusted throttle')
        self.api = api
        self.enabled = enabled
        self.clock = clock if clock is not None else time.time

    @staticmethod
    def _response(start_response, status, payload):
        raw = json.dumps(payload, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
        start_response(status, [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Content-Length', str(len(raw))),
            ('Cache-Control', 'no-store, private'),
            ('Pragma', 'no-cache'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Referrer-Policy', 'no-referrer'),
            ('Content-Security-Policy',
             "default-src 'none'; frame-ancestors 'none'"),
        ])
        return [raw]

    @staticmethod
    def _read_json(environ):
        if environ.get('CONTENT_TYPE') != 'application/json':
            raise ValueError('JSON content type required')
        size = environ.get('CONTENT_LENGTH')
        if (type(size) is not str or not size.isascii()
                or not size.isdecimal() or len(size) > 4
                or not 1 <= int(size) <= _MAX_JSON_BYTES):
            raise ValueError('Invalid JSON size')
        source = environ.get('wsgi.input')
        if source is None:
            raise ValueError('Body stream required')
        data = source.read(int(size))
        if type(data) is not bytes or len(data) != int(size):
            raise ValueError('Incomplete request')
        document = json.loads(data.decode('utf-8'),
                              object_pairs_hook=_unique_json_object)
        if type(document) is not dict:
            raise ValueError('JSON object required')
        return document

    @staticmethod
    def _validate_login_token(result):
        if (type(result) is not dict
                or result.get('publishing_enabled') is not False
                or type(result.get('session_token')) is not str
                or _SESSION_PATTERN.fullmatch(result['session_token']) is None):
            raise RuntimeError('Invalid trusted authentication result')
        return {'session_token': result['session_token'],
                'publishing_enabled': False}

    def __call__(self, environ, start_response):
        reply = lambda status, body: self._response(start_response, status, body)
        if environ.get('wsgi.url_scheme') != 'https':
            return reply('403 Forbidden', {'error': 'HTTPS required'})
        path = environ.get('PATH_INFO')
        if path not in _PATHS:
            return reply('404 Not Found', {'error': 'Not found'})
        if environ.get('REQUEST_METHOD') != 'POST':
            return reply('405 Method Not Allowed', {'error': 'POST required'})
        if not self.enabled:
            return reply('503 Service Unavailable',
                         {'error': 'Authentication endpoint disabled'})
        try:
            document = self._read_json(environ)
            if set(document) != _PATHS[path]:
                raise ValueError('Unexpected fields')
            now = int(self.clock())
            if now < 0:
                raise RuntimeError('Invalid server time')
            if path == '/api/v1/auth/password':
                if (not _validate_text(document['email'], maximum=254)
                        or not _validate_text(
                            document['password'], maximum=1024,
                            allow_newline=True)
                        or not _validate_text(
                            document['tenant_id'], maximum=128)):
                    raise ValueError('Invalid login inputs')
                result = self.api.password_login(
                    email=document['email'],
                    password=document['password'],
                    tenant_id=document['tenant_id'],
                    server_now=now)
                return reply('200 OK', self._validate_login_token(result))
            if path == '/api/v1/auth/google-challenge':
                result = self.api.begin_google(server_now=now)
                if (type(result) is not dict
                        or not _validate_text(
                            result.get('challenge_id'), maximum=256)
                        or not _validate_text(result.get('nonce'), maximum=256)
                        or type(result.get('expires_at')) is not int
                        or result['expires_at'] <= now):
                    raise RuntimeError('Invalid Google challenge')
                return reply('200 OK', {
                    'challenge_id': result['challenge_id'],
                    'nonce': result['nonce'],
                    'expires_at': result['expires_at'],
                    'publishing_enabled': False})
            if (not _validate_text(document['challenge_id'], maximum=256)
                    or not _validate_text(document['id_token'], maximum=4096)
                    or not _validate_text(document['tenant_id'], maximum=128)):
                raise ValueError('Invalid Google login inputs')
            result = self.api.google_login(
                challenge_id=document['challenge_id'],
                id_token=document['id_token'],
                tenant_id=document['tenant_id'],
                server_now=now)
            return reply('200 OK', self._validate_login_token(result))
        except PermissionError:
            # Do not reveal whether an email exists, a user is blocked,
            # or a verified Google subject is attached to another account.
            return reply('401 Unauthorized', {'error': 'Sign-in unavailable'})
        except (ValueError, TypeError, UnicodeDecodeError,
                json.JSONDecodeError, AttributeError):
            return reply('400 Bad Request', {'error': 'Invalid sign-in request'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error': 'Authentication unavailable'})
