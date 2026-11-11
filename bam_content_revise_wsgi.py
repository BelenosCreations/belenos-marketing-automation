"""Disabled-by-default HTTPS-only manual revision for unpublished held drafts.

Only draft copy or content guidance may change. Optimistic revision prevents
silent overwrites; no tenant, approval, schedule or publish fields accepted.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[a-f0-9]{32}\Z')

def _unique(pairs):
    data={}
    for key,value in pairs:
        if key in data:raise ValueError('Duplicate JSON field')
        data[key]=value
    return data

class BAMContentReviseWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:raise ValueError('Boolean enable required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response,status,data):
        raw=json.dumps(data,separators=(',',':')).encode()
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
            raise ValueError('Strict JSON required')
        n=environ.get('CONTENT_LENGTH')
        if (type(n) is not str or not n.isascii() or not n.isdecimal()
                or len(n)>4 or not 1<=int(n)<=8192):
            raise ValueError('Invalid content size')
        body=environ.get('wsgi.input')
        if body is None:raise ValueError('Missing body')
        raw=body.read(int(n))
        if type(raw) is not bytes or len(raw)!=int(n):
            raise ValueError('Invalid request length')
        data=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
        if type(data) is not dict or set(data)!={
                'request_id','target','revised_text','expected_revision'}:
            raise ValueError('Unexpected field')
        if (type(data['request_id']) is not str
                or _ID.fullmatch(data['request_id']) is None
                or data['target'] not in ('draft_text','suggestion')
                or type(data['revised_text']) is not str
                or not data['revised_text'].strip()
                or data['revised_text']!=data['revised_text'].strip()
                or len(data['revised_text'])>2000
                or type(data['expected_revision']) is not int
                or data['expected_revision']<1):
            raise ValueError('Invalid draft edit')
        return data

    @staticmethod
    def _safe(data,expected):
        if (type(data) is not dict or set(data)!={
                'tenant_id','request_id','status','revision',
                'publishing_enabled'} or type(data['tenant_id']) is not str
                or not data['tenant_id'].strip() or len(data['tenant_id'])>128
                or data['request_id']!=expected['request_id']
                or data['status'] not in ('needs_content','ready_for_review',
                                         'postponed','unavailable')
                or type(data['revision']) is not int
                or data['revision']!=expected['expected_revision']+1
                or data['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe draft revision response')
        return data

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/content/drafts':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='PUT':
            return reply('405 Method Not Allowed',{'error':'PUT required'})
        if not self.enabled:
            return reply('503 Service Unavailable',{'error':'Draft revisions disabled'})
        try:
            authorization=environ.get('HTTP_AUTHORIZATION')
            if (type(authorization) is not str
                    or not authorization.startswith('Bearer ')
                    or _TOKEN.fullmatch(authorization[7:]) is None):
                raise PermissionError('BAM session required')
            body=self._parse(environ)
            now=int(self.clock())
            if now<0:raise RuntimeError('Invalid time')
            result=self.api.revise_held_draft(
                session_token=authorization[7:],server_now=now,**body)
            return reply('200 OK',self._safe(result,body))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Draft edit unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Draft not found'})
        except ValueError as exc:
            if str(exc)=='Stale draft revision':
                return reply('409 Conflict',{'error':'Draft changed; refresh required'})
            return reply('400 Bad Request',{'error':'Invalid draft revision'})
        except (TypeError,UnicodeDecodeError,json.JSONDecodeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid draft revision'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Draft edit unavailable'})
