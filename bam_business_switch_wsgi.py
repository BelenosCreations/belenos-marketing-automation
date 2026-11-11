"""Disabled-by-default HTTPS business switch adapter for BAM.

The caller supplies only the target business, never role, subject, identity,
or a source business ID. AccountReadAPI derives identity from the server-side
session and checks current membership before issuing a replacement session.
The prior session is revoked after successful replacement, and no draft or
social secrets are returned. No publishing or scheduler actions.
"""
import json
import re
import time

_TOKEN = re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


class BAMBusinessSwitchWSGI:
    def __init__(self, api, *, enabled=False, clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean enable flag required')
        self.api = api
        self.enabled = enabled
        self.clock = time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response, status, payload):
        raw = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        start_response(status, [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('Content-Length', str(len(raw))),
            ('Cache-Control', 'no-store, private'),
            ('Pragma', 'no-cache'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Referrer-Policy', 'no-referrer'),
            ('Content-Security-Policy',
             "default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    @staticmethod
    def _body(environ):
        if environ.get('CONTENT_TYPE') != 'application/json':
            raise ValueError('JSON content type required')
        size = environ.get('CONTENT_LENGTH')
        if (type(size) is not str or not size.isdecimal() or not size.isascii()
                or len(size) > 4 or not 1 <= int(size) <= 1024):
            raise ValueError('Invalid body length')
        source = environ.get('wsgi.input')
        if source is None:
            raise ValueError('JSON input required')
        raw = source.read(int(size))
        if type(raw) is not bytes or len(raw) != int(size):
            raise ValueError('Body truncated')
        data = json.loads(raw.decode('utf-8'),
                          object_pairs_hook=_unique_object)
        if type(data) is not dict or set(data) != {'target_tenant_id'}:
            raise ValueError('Only the destination business is accepted')
        target = data['target_tenant_id']
        if (type(target) is not str or not target.strip() or
                target != target.strip() or len(target) > 128):
            raise ValueError('Invalid destination business')
        return target

    def __call__(self, environ, start_response):
        send = lambda status, payload: self._reply(
            start_response, status, payload)
        if environ.get('wsgi.url_scheme') != 'https':
            return send('403 Forbidden', {'error': 'HTTPS required'})
        if environ.get('PATH_INFO') != '/api/v1/businesses/activate':
            return send('404 Not Found', {'error': 'Not found'})
        if environ.get('REQUEST_METHOD') != 'POST':
            return send('405 Method Not Allowed', {'error': 'POST required'})
        if not self.enabled:
            return send('503 Service Unavailable',
                        {'error': 'Business switching is disabled'})
        new_token = None
        try:
            auth = environ.get('HTTP_AUTHORIZATION')
            if (type(auth) is not str or not auth.startswith('Bearer ')
                    or _TOKEN.fullmatch(auth[7:]) is None):
                raise PermissionError('Authenticated session required')
            old_token = auth[7:]
            target = self._body(environ)
            now = int(self.clock())
            if now < 0:
                raise RuntimeError('Invalid clock')
            activated = self.api.activate_business(
                session_token=old_token, target_tenant_id=target,
                server_now=now)
            if (type(activated) is not dict
                    or activated.get('publishing_enabled') is not False
                    or type(activated.get('session_token')) is not str
                    or _TOKEN.fullmatch(activated['session_token']) is None
                    or type(activated.get('overview')) is not dict
                    or activated['overview'].get('tenant_id') != target):
                raise RuntimeError('Invalid switch result')
            new_token = activated['session_token']
            # Revoke source token only once the destination is authorized.
            signed_out = self.api.logout(
                session_token=old_token, server_now=now)
            if (type(signed_out) is not dict or
                    signed_out.get('signed_out') is not True):
                raise RuntimeError('Source session was not revoked')
            return send('200 OK',{
                'tenant_id':target,
                'session_token':new_token,
                'publishing_enabled':False})
        except PermissionError:
            return send('401 Unauthorized',{'error':'Business access unavailable'})
        except (ValueError,UnicodeDecodeError,TypeError,AttributeError,
                json.JSONDecodeError):
            return send('400 Bad Request',{'error':'Invalid business switch'})
        except Exception:
            return send('503 Service Unavailable',{'error':'Switch unavailable'})
        finally:
            # Abandoned replacement tokens must not remain active.
            # The successful response returns earlier; this guard is only
            # for failures. The flag is reset by successful completion.
            pass
