"""Disabled-by-default HTTPS boundary for *held*, unpublished BAM drafts.

These endpoints cannot attach unverified media, approve a post, schedule a
post, publish, or accept a client tenant/role claim. The trusted AccountReadAPI
performs current membership checks; this adapter only validates transport.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[0-9a-f]{32}\Z')
_POSTS=frozenset(('/api/v1/content/drafts','/api/v1/content/hold'))


def _unique_object(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON field')
        obj[key]=value
    return obj


class BAMContentWriteWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean enabled state required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response,status,body):
        raw=json.dumps(body,separators=(',',':')).encode('utf-8')
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(raw))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',
             "default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    @staticmethod
    def _body(environ):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('JSON content type required')
        length=environ.get('CONTENT_LENGTH')
        if (type(length) is not str or not length.isascii()
                or not length.isdecimal() or len(length)>4
                or not 1<=int(length)<=8192):
            raise ValueError('Invalid content size')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing JSON stream')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete JSON body')
        body=json.loads(raw.decode('utf-8'),
                        object_pairs_hook=_unique_object)
        if type(body) is not dict:
            raise ValueError('JSONObject expected')
        return body

    @staticmethod
    def _safe_result(result,*,status):
        if (type(result) is not dict
                or type(result.get('tenant_id')) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or type(result.get('request_id')) is not str
                or _ID.fullmatch(result['request_id']) is None
                or result.get('publishing_enabled') is not False
                or result.get('status') not in (
                    'needs_content','postponed','unavailable')):
            raise RuntimeError('Invalid trusted content result')
        return {'tenant_id':result['tenant_id'],
                'request_id':result['request_id'],
                'status':result['status'],
                'publishing_enabled':False}

    def __call__(self,environ,start_response):
        reply=lambda status,body:self._reply(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        path=environ.get('PATH_INFO')
        if path not in _POSTS:
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='POST':
            return reply('405 Method Not Allowed',{'error':'POST required'})
        if not self.enabled:
            return reply('503 Service Unavailable',
                         {'error':'Content writes disabled'})
        try:
            header=environ.get('HTTP_AUTHORIZATION')
            if (type(header) is not str or not header.startswith('Bearer ')
                    or _TOKEN.fullmatch(header[7:]) is None):
                raise PermissionError('Valid BAM session required')
            token=header[7:]
            body=self._body(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server clock')
            if path=='/api/v1/content/drafts':
                required={'channel','draft_text','suggestion','required_items'}
                if not required.issubset(body) or set(body)-required-{'priority'}:
                    raise ValueError('Unexpected draft fields')
                result=self.api.create_held_draft(
                    session_token=token,server_now=now,
                    channel=body['channel'],draft_text=body['draft_text'],
                    suggestion=body['suggestion'],
                    required_items=body['required_items'],
                    priority=body.get('priority',0))
                return reply('201 Created',
                             self._safe_result(result,status='needs_content'))
            if set(body)!={'request_id','status'}:
                raise ValueError('Unexpected hold fields')
            if type(body['request_id']) is not str or (
                    _ID.fullmatch(body['request_id']) is None):
                raise ValueError('Invalid request ID')
            if body['status'] not in ('needs_content','postponed','unavailable'):
                raise ValueError('Invalid hold state')
            result=self.api.update_draft_hold(
                session_token=token,server_now=now,
                request_id=body['request_id'],status=body['status'])
            return reply('200 OK',
                         self._safe_result(result,status=body['status']))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Content access unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Draft unavailable'})
        except (ValueError,TypeError,UnicodeDecodeError,
                json.JSONDecodeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid draft request'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Content service unavailable'})
