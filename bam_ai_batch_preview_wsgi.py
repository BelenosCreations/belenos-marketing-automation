"""Read-only-in-effect, POST-shaped advance AI batch planning endpoint.

A signed-in creator may preview 1–14 planned request topics. There is no
provider, quota reservation, draft write, billing, scheduling or publishing.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_PLATFORMS=frozenset(('facebook','instagram','linkedin',
                     'pinterest','tiktok','youtube'))

def _unique(pairs):
    data={}
    for key,value in pairs:
        if key in data:
            raise ValueError('Duplicate request key')
        data[key]=value
    return data

class BAMAIBatchPreviewWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean opt-in required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

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
            raise ValueError('Strict JSON required')
        length=environ.get('CONTENT_LENGTH')
        if (type(length) is not str or not length.isascii() or
                not length.isdecimal() or len(length)>5
                or not 1<=int(length)<=8192):
            raise ValueError('Invalid request size')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Request body required')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete request')
        payload=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
        if (type(payload) is not dict or
                set(payload)!={'topics','platform','include_image_prompt'} or
                type(payload['topics']) is not list or
                not 1<=len(payload['topics'])<=14 or
                any(type(value) is not str or not value.strip()
                    or value!=value.strip() or len(value)>300
                    for value in payload['topics']) or
                len({value.casefold() for value in payload['topics']})!=
                   len(payload['topics']) or
                payload['platform'] not in _PLATFORMS or
                type(payload['include_image_prompt']) is not bool):
            raise ValueError('Invalid batch topics')
        return payload

    @staticmethod
    def _safe(result,body):
        if (type(result) is not dict or set(result)!={
                'tenant_id','mode','fact_revision','fact_provenance',
                'items','planned_individual_requests','provider_requests_made',
                'quota_reserved','actual_cost_known','drafts_created',
                'status','publishing_enabled'} or
                type(result['tenant_id']) is not str or
                not result['tenant_id'].strip() or
                len(result['tenant_id'])>128 or
                result['mode'] not in ('bam_sponsored','own_openai_key') or
                type(result['fact_revision']) is not int or
                result['fact_revision']<1 or
                result['fact_provenance']!='owner_confirmed' or
                type(result['items']) is not list or
                len(result['items'])!=len(body['topics']) or
                type(result['planned_individual_requests']) is not int or
                result['planned_individual_requests']!=len(body['topics']) or
                result['provider_requests_made']!=0 or
                result['quota_reserved'] is not False or
                result['actual_cost_known'] is not False or
                result['drafts_created']!=0 or
                result['status']!='planning_only' or
                result['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe batch plan')
        for expected,item in zip(body['topics'],result['items']):
            if (type(item) is not dict or
                    set(item)!={'topic','platform','image_prompt_planned'} or
                    item['topic']!=expected or
                    item['platform']!=body['platform'] or
                    item['image_prompt_planned'] is not body['include_image_prompt']):
                raise RuntimeError('Untrusted batch plan topic')
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,body:self._reply(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/ai/batch-preview':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='POST':
            return reply('405 Method Not Allowed',{'error':'POST required'})
        if not self.enabled:
            return reply('503 Service Unavailable',{'error':'AI plan preview disabled'})
        try:
            header=environ.get('HTTP_AUTHORIZATION')
            if (type(header) is not str or not header.startswith('Bearer ')
                    or _TOKEN.fullmatch(header[7:]) is None):
                raise PermissionError('BAM session required')
            if environ.get('QUERY_STRING'):
                raise ValueError('No query parameters allowed')
            data=self._parse(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid time')
            result=self.api.preview_ai_batch(
                session_token=header[7:],server_now=now,**data)
            return reply('200 OK',self._safe(result,data))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Preview unavailable'})
        except (ValueError,TypeError,UnicodeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid batch preview'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Batch planning unavailable'})
