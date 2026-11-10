"""Loopback-only development HTTP transport for BAM account operations.

This is NOT a production server. It requires an already-issued BAM session
and cannot authenticate users, provision accounts, or publish posts.
Never bind to a public interface or expose this gateway to the Internet.
"""
import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

_MAX_BODY=4096

def make_handler(api, *, clock=None):
    """Return a handler bound to an injected trusted AccountReadAPI."""
    clock=clock or (lambda: int(datetime.now(timezone.utc).timestamp()))

    class Handler(BaseHTTPRequestHandler):
        server_version='BAMDev/0.1'
        sys_version=''

        def log_message(self, format, *args):
            # Do not log URLs, Authorization headers, session tokens, or bodies.
            return

        def _respond(self, status, payload):
            raw=json.dumps(payload,separators=(',',':')).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'none'")
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _local_request(self):
            # Reject browser-origin cross-site requests and DNS-rebinding hosts.
            host=self.headers.get('Host','').split(':',1)[0].lower()
            if host not in ('127.0.0.1','localhost','[::1]'):
                raise PermissionError('Local host required')
            if self.headers.get('Origin') is not None:
                raise PermissionError('Browser-origin requests disabled')

        def _session(self):
            header=self.headers.get('Authorization','')
            if not header.startswith('Bearer '):
                raise PermissionError('Bearer token required')
            return header[7:]

        def _body(self):
            size=self.headers.get('Content-Length')
            if size is None or not size.isascii() or not size.isdecimal():
                raise ValueError('JSON body required')
            n=int(size)
            if n<1 or n>_MAX_BODY:
                raise ValueError('Invalid request size')
            if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':
                raise ValueError('JSON content type required')
            body=json.loads(self.rfile.read(n))
            if not isinstance(body,dict):
                raise ValueError('JSON object required')
            return body

        def do_GET(self):
            path=urlsplit(self.path)
            if path.query or path.fragment or path.path!='/api/account/overview':
                self._respond(404,{'error':'not_found'})
                return
            try:
                self._local_request()
                result=api.get_overview(session_token=self._session(),server_now=clock())
                self._respond(200,result)
            except PermissionError:
                self._respond(403,{'error':'access_denied'})
            except (ValueError,TypeError):
                self._respond(400,{'error':'invalid_request'})

        def do_POST(self):
            path=urlsplit(self.path)
            if path.query or path.fragment or path.path not in (
                    '/api/account/activate','/api/account/logout',
                    '/api/account/logout-everywhere','/api/content/drafts',
                    '/api/content/hold'):
                self._respond(404,{'error':'not_found'})
                return
            try:
                self._local_request()
                token=self._session()
                body=self._body()
                if path.path=='/api/content/hold':
                    if set(body)!={'request_id','status'}:
                        raise ValueError('Invalid hold fields')
                    result=api.update_draft_hold(session_token=token,
                        server_now=clock(),request_id=body['request_id'],
                        status=body['status'])
                elif path.path=='/api/content/drafts':
                    required={'channel','draft_text','suggestion','required_items'}
                    if not required.issubset(body) or set(body)-required-{'priority'}:
                        raise ValueError('Invalid draft fields')
                    result=api.create_held_draft(session_token=token,
                        server_now=clock(),channel=body['channel'],
                        draft_text=body['draft_text'],suggestion=body['suggestion'],
                        required_items=body['required_items'],
                        priority=body.get('priority',0))
                elif path.path=='/api/account/activate':
                    if set(body)!={'target_tenant_id'}:
                        raise ValueError('Unexpected fields')
                    result=api.activate_business(session_token=token,
                        target_tenant_id=body['target_tenant_id'],server_now=clock())
                elif path.path=='/api/account/logout':
                    if body:
                        raise ValueError('Unexpected fields')
                    result=api.logout(session_token=token,server_now=clock())
                else:
                    if body:
                        raise ValueError('Unexpected fields')
                    result=api.logout_everywhere(session_token=token,server_now=clock())
                self._respond(200,result)
            except PermissionError:
                self._respond(403,{'error':'access_denied'})
            except (ValueError,TypeError,json.JSONDecodeError):
                self._respond(400,{'error':'invalid_request'})
            except KeyError:
                self._respond(404,{'error':'not_found'})
            except RuntimeError:
                self._respond(503,{'error':'service_unavailable'})

    return Handler

def create_loopback_server(api, *, host='127.0.0.1', port=0, clock=None):
    """Create a local test server; caller controls lifecycle."""
    if host not in ('127.0.0.1','::1','localhost'):
        raise ValueError('Only loopback binding is permitted')
    return ThreadingHTTPServer((host,port),make_handler(api,clock=clock))
