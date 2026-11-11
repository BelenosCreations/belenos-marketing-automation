"""Disabled-by-default BAM content attachment *metadata* preflight.

This does not upload files, supply signed URLs, scan bytes, grant permission
to publish, or mark attachments verified. Storage remains disconnected.
"""
import json
import re
import time

from content_upload_preflight import MAX_BYTES

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[a-f0-9]{32}\Z')
_SHA=re.compile(r'[a-f0-9]{64}\Z')
_PATH='/api/v1/content/upload-preflight'

def _object(pairs):
    values={}
    for key,value in pairs:
        if key in values:
            raise ValueError('Duplicate field')
        values[key]=value
    return values

class BAMUploadPreflightWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean enabled state required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response,status,result):
        raw=json.dumps(result,separators=(',',':')).encode('utf-8')
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
            raise ValueError('Strict JSON expected')
        length=environ.get('CONTENT_LENGTH')
        if (type(length) is not str or not length.isascii()
                or not length.isdecimal() or len(length)>4
                or not 1<=int(length)<=4096):
            raise ValueError('Invalid content length')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing stream')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete body')
        body=json.loads(raw.decode('utf-8'),object_pairs_hook=_object)
        if type(body) is not dict or set(body)!={
                'request_id','item','media_type','sha256','byte_count'}:
            raise ValueError('Unexpected attachment metadata')
        if type(body['request_id']) is not str or _ID.fullmatch(body['request_id']) is None:
            raise ValueError('Invalid request id')
        if (type(body['item']) is not str or not body['item'].strip()
                or body['item']!=body['item'].strip() or len(body['item'])>80):
            raise ValueError('Invalid checklist item')
        if type(body['media_type']) is not str or body['media_type'] not in MAX_BYTES:
            raise ValueError('Invalid media type')
        if type(body['sha256']) is not str or _SHA.fullmatch(body['sha256']) is None:
            raise ValueError('Invalid SHA256 hash')
        if (type(body['byte_count']) is not int or not 0<body['byte_count']
                <=MAX_BYTES[body['media_type']]):
            raise ValueError('Invalid media size')
        return body

    @staticmethod
    def _safe(result):
        if (type(result) is not dict or set(result)!={
                'tenant_id','request_id','item','attachment_id','status',
                'max_bytes','upload_url','publishing_enabled'}
                or type(result['tenant_id']) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or type(result['request_id']) is not str
                or _ID.fullmatch(result['request_id']) is None
                or type(result['item']) is not str or not result['item'].strip()
                or len(result['item'])>80
                or type(result['attachment_id']) is not str
                or _ID.fullmatch(result['attachment_id']) is None
                or result['status']!='pending'
                or result['upload_url'] is not None
                or result['publishing_enabled'] is not False
                or type(result['max_bytes']) is not int
                or not 0<result['max_bytes']<=250*1024*1024):
            raise RuntimeError('Invalid trusted pending attachment')
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
                         {'error':'Media preflight disabled'})
        try:
            bearer=environ.get('HTTP_AUTHORIZATION')
            if (type(bearer) is not str or not bearer.startswith('Bearer ')
                    or _TOKEN.fullmatch(bearer[7:]) is None):
                raise PermissionError('BAM session required')
            data=self._parse(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server time')
            result=self.api.begin_content_upload_preflight(
                session_token=bearer[7:],server_now=now,**data)
            safe=self._safe(result)
            if safe['request_id']!=data['request_id'] or safe['item']!=data['item']:
                raise RuntimeError('Untrusted attachment scope')
            return reply('202 Accepted',safe)
        except PermissionError:
            return reply('401 Unauthorized',
                         {'error':'Attachment access unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Content request unavailable'})
        except (ValueError,TypeError,UnicodeDecodeError,json.JSONDecodeError,
                AttributeError):
            return reply('400 Bad Request',{'error':'Invalid attachment metadata'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Media preflight unavailable'})
