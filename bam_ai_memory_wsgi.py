"""Authenticated, unpublished per-user AI writing preference update.

No OpenAI calls, keys, billing, owner facts or publishing. The caller may
replace only their own current-business memory after a strict optimistic
comparison with the exact preference dictionary last read from the server.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')

def _unique(pairs):
    value={}
    for key,entry in pairs:
        if key in value:
            raise ValueError('Duplicate request field')
        value[key]=entry
    return value

class BAMAIMemoryWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit boolean feature switch required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted server clock required')

    @staticmethod
    def _reply(start_response,status,data):
        raw=json.dumps(data,ensure_ascii=False,
                       separators=(',',':')).encode('utf-8')
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(raw))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    @staticmethod
    def _parse(environ):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('JSON required')
        length=environ.get('CONTENT_LENGTH')
        if (type(length) is not str or not length.isascii() or
                not length.isdecimal() or len(length)>5 or
                not 1<=int(length)<=40000):
            raise ValueError('Invalid request size')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing request')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete request')
        body=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
        if type(body) is not dict or set(body)!={'memory','expected_memory'}:
            raise ValueError('Unexpected AI memory fields')
        return body

    @staticmethod
    def _safe(result):
        if (type(result) is not dict or set(result)!={
                'tenant_id','memory','publishing_enabled'} or
                type(result['tenant_id']) is not str or
                not result['tenant_id'].strip() or
                len(result['tenant_id'])>128 or
                type(result['memory']) is not dict or
                len(result['memory'])>40 or
                any(type(k) is not str or not k.strip() or len(k)>80 or
                    type(v) is not str or not v.strip() or len(v)>2000
                    for k,v in result['memory'].items()) or
                result['publishing_enabled'] is not False):
            raise RuntimeError('Untrusted AI preference update')
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/ai-memory':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='PUT':
            return reply('405 Method Not Allowed',{'error':'PUT required'})
        if not self.enabled:
            return reply('503 Service Unavailable',
                         {'error':'AI memory editing disabled'})
        try:
            header=environ.get('HTTP_AUTHORIZATION')
            if (type(header) is not str or not header.startswith('Bearer ') or
                    _TOKEN.fullmatch(header[7:]) is None):
                raise PermissionError('BAM session required')
            body=self._parse(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server clock')
            result=self.api.edit_ai_memory(
                session_token=header[7:],server_now=now,**body)
            return reply('200 OK',self._safe(result))
        except PermissionError:
            return reply('401 Unauthorized',
                         {'error':'AI preferences unavailable'})
        except ValueError as error:
            if str(error)=='AI memory changed; refresh before saving':
                return reply('409 Conflict',
                             {'error':'Preferences changed; refresh required'})
            return reply('400 Bad Request',
                         {'error':'Invalid AI preferences'})
        except (TypeError,AttributeError,UnicodeError):
            return reply('400 Bad Request',
                         {'error':'Invalid AI preferences'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'AI preferences unavailable'})
