"""Optional read-only status of private unverified media; no attachment IDs."""
import json
import re
import time

class BAMPendingMediaStatusWSGI:
    def __init__(self,store=None,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean enable switch required')
        self.store=store
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response,status,data):
        raw=json.dumps(data,separators=(',',':')).encode('utf-8')
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(raw))),
            ('Cache-Control','no-store, private'),('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    @staticmethod
    def _safe(data):
        if (type(data) is not dict or set(data)!={
                'tenant_id','items','media_verified','publishing_enabled'}
                or type(data['tenant_id']) is not str
                or not data['tenant_id'] or len(data['tenant_id'])>128
                or data['media_verified'] is not False
                or data['publishing_enabled'] is not False
                or type(data['items']) is not list or len(data['items'])>500):
            raise RuntimeError('Untrusted pending media status')
        for item in data['items']:
            if (type(item) is not dict or set(item)!={'request_id','item','status'}
                    or type(item['request_id']) is not str
                    or re.fullmatch('[a-f0-9]{32}',item['request_id']) is None
                    or type(item['item']) is not str
                    or not item['item'].strip() or len(item['item'])>80
                    or item['status'] not in ('awaiting_file','pending_scan')):
                raise RuntimeError('Untrusted pending media item')
        return data

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/content/media-status':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='GET':
            return reply('405 Method Not Allowed',{'error':'GET required'})
        if not self.enabled or self.store is None:
            return reply('503 Service Unavailable',{'error':'Status disabled'})
        try:
            header=environ.get('HTTP_AUTHORIZATION')
            if (type(header) is not str or not header.startswith('Bearer ')
                    or re.fullmatch('[A-Za-z0-9_-]{32,2048}',header[7:]) is None):
                raise PermissionError('Session required')
            if environ.get('QUERY_STRING',''):
                raise ValueError('Unexpected query')
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid clock')
            return reply('200 OK',self._safe(
                self.store.statuses(token=header[7:],now=now)))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Media status unavailable'})
        except (ValueError,TypeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid request'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Media status unavailable'})
