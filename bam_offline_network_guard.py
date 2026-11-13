"""Additional isolation for BAM's test-only offline WSGI composition.

A direct-call test may omit network metadata. An actual WSGI request with
network metadata must be loopback, have a local Host and no proxy headers.
This is NOT permission to mount the offline gateway publicly. A reverse
proxy can rewrite or remove metadata; production needs a separate app.
"""
import re

_HOST=re.compile(r'(?:localhost|127\.0\.0\.1)(?::([0-9]{1,5}))?\Z',re.I)
_HOST_V6=re.compile(r'\[::1\](?::([0-9]{1,5}))?\Z')
_FORWARDING=frozenset((
    'HTTP_FORWARDED','HTTP_X_FORWARDED_FOR','HTTP_X_FORWARDED_HOST',
    'HTTP_X_FORWARDED_PROTO','HTTP_X_FORWARDED_PORT','HTTP_X_REAL_IP',
    'HTTP_X_ORIGINAL_HOST','HTTP_X_ORIGINAL_FORWARDED_FOR',
    'HTTP_X_FORWARDED_SERVER',
))

def _local_host(value,*,server_name=False):
    if type(value) is not str or not value:
        return False
    if server_name and value=='::1':
        return True
    match=_HOST.fullmatch(value) or _HOST_V6.fullmatch(value)
    if match is None:
        return False
    port=match.group(1)
    return port is None or 1<=int(port)<=65535

def offline_gateway_request_allowed(environ):
    """Block remote, proxy-tainted and ambiguous local-preview WSGI ingress."""
    if type(environ) is not dict:
        return False
    # Any forwarding/original URI variant is untrusted, not just known names.
    # Reject ambiguous body framing and method override before parsing secrets.
    forbidden=frozenset(('HTTP_TRANSFER_ENCODING','HTTP_CONTENT_LENGTH',
        'HTTP_X_HTTP_METHOD_OVERRIDE','HTTP_X_METHOD_OVERRIDE',
        'HTTP_PROXY','HTTP_PROXY_CONNECTION','HTTP_CF_CONNECTING_IP',
        'HTTP_TRUE_CLIENT_IP','HTTP_X_CLUSTER_CLIENT_IP'))
    if any(type(k) is not str or k in _FORWARDING or k in forbidden
           or k.startswith('HTTP_X_FORWARDED_')
           or k.startswith('HTTP_X_ORIGINAL_')
           for k in environ):
        return False
    address=environ.get('REMOTE_ADDR')
    if 'REMOTE_ADDR' in environ and (type(address) is not str or
            address not in ('127.0.0.1','::1')):
        return False
    for key in ('HTTP_HOST','SERVER_NAME'):
        if key in environ and not _local_host(environ[key],
                server_name=key=='SERVER_NAME'):
            return False
    return True
