"""Disabled-by-default manual editing of one unpublished AI draft component.

No AI request, revision of the other component, model, publishing, approval
or attachment upload. Authenticated user/business scope is server-derived.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[a-f0-9]{32}\Z')
_CHANNELS=frozenset(('facebook','instagram','linkedin','pinterest','tiktok','youtube'))
_PATH='/api/v1/ai-drafts'

def _unique(pairs):
    output={}
    for key,value in pairs:
        if key in output:
            raise ValueError('Duplicate JSON field')
        output[key]=value
    return output

class BAMAIDraftEditWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit enabled state required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Server clock required')

    @staticmethod
    def _reply(start_response,status,body):
        raw=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode('utf-8')
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
                or not length.isdecimal() or len(length)>5
                or not 1<=int(length)<=20000):
            raise ValueError('Invalid content length')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('JSON input required')
        body=stream.read(int(length))
        if type(body) is not bytes or len(body)!=int(length):
            raise ValueError('Incomplete JSON request')
        data=json.loads(body.decode('utf-8'),object_pairs_hook=_unique)
        if type(data) is not dict or set(data)!={
                'draft_id','target','revised_text','expected_revision'}:
            raise ValueError('Unexpected draft edit fields')
        if (type(data['draft_id']) is not str
                or _ID.fullmatch(data['draft_id']) is None):
            raise ValueError('Invalid draft id')
        if data['target'] not in ('post_text','image_prompt'):
            raise ValueError('Invalid component target')
        text=data['revised_text']
        if (type(text) is not str or not text.strip()
                or len(text)>(4000 if data['target']=='post_text' else 2000)):
            raise ValueError('Invalid revised draft component')
        if (type(data['expected_revision']) is not int
                or data['expected_revision']<1):
            raise ValueError('Invalid draft revision')
        return data

    @staticmethod
    def _safe(body,data):
        if (type(body) is not dict
                or set(body)!={'tenant_id','draft_id','platform','post_text',
                                 'image_prompt','needs_media','media_attached',
                                 'status','revision','publishing_enabled'}
                or type(body['tenant_id']) is not str
                or not body['tenant_id'].strip()
                or len(body['tenant_id'])>128
                or body['draft_id']!=data['draft_id']
                or body['platform'] not in _CHANNELS
                or type(body['post_text']) is not str
                or not body['post_text'].strip()
                or len(body['post_text'])>4000
                or (body['image_prompt'] is not None and
                    (type(body['image_prompt']) is not str
                     or not body['image_prompt'].strip()
                     or len(body['image_prompt'])>2000))
                or type(body['needs_media']) is not bool
                or type(body['media_attached']) is not bool
                or (body['media_attached'] and not body['needs_media'])
                or body['revision']!=data['expected_revision']+1
                or body['publishing_enabled'] is not False
                or body['status']!=(
                    'needs_media' if body['needs_media'] and not body['media_attached']
                    else 'draft_pending_verification')
                or body[data['target']]!=data['revised_text']):
            raise RuntimeError('Unsafe edited draft response')
        return body

    def __call__(self,environ,start_response):
        reply=lambda status,body:self._reply(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!=_PATH:
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='PUT':
            return reply('405 Method Not Allowed',{'error':'PUT required'})
        if not self.enabled:
            return reply('503 Service Unavailable',
                         {'error':'Draft editing disabled'})
        try:
            auth=environ.get('HTTP_AUTHORIZATION')
            if (type(auth) is not str or not auth.startswith('Bearer ')
                    or _TOKEN.fullmatch(auth[7:]) is None):
                raise PermissionError('Valid BAM session required')
            data=self._parse(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid clock')
            revised=self.api.edit_ai_draft_component(
                session_token=auth[7:],server_now=now,**data)
            return reply('200 OK',self._safe(revised,data))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Draft editing unavailable'})
        except LookupError:
            return reply('404 Not Found',{'error':'Draft not found'})
        except (ValueError,TypeError,UnicodeDecodeError,
                json.JSONDecodeError,AttributeError):
            return reply('400 Bad Request',{'error':'Draft edit invalid or outdated'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Draft edit unavailable'})
