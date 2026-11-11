"""Zero-API-request product draft creation from owner-confirmed facts only.

Strict, disabled-by-default HTTPS transport. User opts in to each draft.
This endpoint never calls OpenAI, creates an image, approves or publishes.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[a-f0-9]{32}\Z')
_PLATFORMS=frozenset(('facebook','instagram','linkedin','pinterest','tiktok','youtube'))
_PATH='/api/v1/ai/local-product-draft'

def _object(pairs):
    value={}
    for key,item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key')
        value[key]=item
    return value

class BAMLocalProductDraftWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean enabled flag required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response,status,result):
        raw=json.dumps(result,separators=(',',':'),ensure_ascii=False).encode('utf-8')
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
        if (type(length) is not str or not length.isascii()
                or not length.isdecimal() or len(length)>3
                or not 1<=int(length)<=256):
            raise ValueError('Invalid JSON size')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing JSON input')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete JSON')
        data=json.loads(raw.decode('utf-8'),object_pairs_hook=_object)
        if (type(data) is not dict
                or set(data)!={'platform','include_image_prompt'}
                or type(data['platform']) is not str
                or data['platform'] not in _PLATFORMS
                or type(data['include_image_prompt']) is not bool):
            raise ValueError('Invalid local draft inputs')
        return data

    @staticmethod
    def _safe(result,*,platform,needs_media):
        if (type(result) is not dict
                or set(result)!={'tenant_id','draft_id','platform','post_text',
                                  'image_prompt','needs_media','media_attached',
                                  'status','revision','publishing_enabled',
                                  'generation_method','openai_requests'}
                or type(result['tenant_id']) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or type(result['draft_id']) is not str
                or _ID.fullmatch(result['draft_id']) is None
                or result['platform']!=platform
                or type(result['post_text']) is not str
                or not result['post_text'].strip()
                or len(result['post_text'])>4000
                or result['needs_media'] is not needs_media
                or result['media_attached'] is not False
                or result['revision']!=1
                or result['status']!=('needs_media' if needs_media
                                     else 'draft_pending_verification')
                or (needs_media and (type(result['image_prompt']) is not str
                    or not result['image_prompt'].strip()
                    or len(result['image_prompt'])>2000))
                or (not needs_media and result['image_prompt'] is not None)
                or result['publishing_enabled'] is not False
                or result['generation_method']!='local_template'
                or result['openai_requests']!=0):
            raise RuntimeError('Invalid zero-cost draft result')
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,body:self._reply(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!=_PATH:
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='POST':
            return reply('405 Method Not Allowed',{'error':'POST required'})
        if not self.enabled:
            return reply('503 Service Unavailable',
                         {'error':'Local draft writes disabled'})
        try:
            bearer=environ.get('HTTP_AUTHORIZATION')
            if (type(bearer) is not str or not bearer.startswith('Bearer ')
                    or _TOKEN.fullmatch(bearer[7:]) is None):
                raise PermissionError('BAM session required')
            data=self._parse(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid clock')
            result=self.api.create_local_product_draft(
                session_token=bearer[7:],server_now=now,**data)
            return reply('201 Created',self._safe(
                result,platform=data['platform'],
                needs_media=data['include_image_prompt']))
        except PermissionError:
            return reply('401 Unauthorized',
                         {'error':'Draft access unavailable'})
        except (ValueError,TypeError,UnicodeDecodeError,
                json.JSONDecodeError,AttributeError):
            return reply('400 Bad Request',
                         {'error':'Confirmed business name and product required'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Local draft unavailable'})
