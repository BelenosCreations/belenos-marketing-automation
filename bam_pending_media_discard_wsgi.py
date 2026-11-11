"""Explicitly discard one tenant-scoped pending image item; no media approval."""
import json
import re
import time

class BAMPendingMediaDiscardWSGI:
    def __init__(self,store=None,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit boolean switch required')
        self.store=store
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted server clock required')

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
    def _parse(environ):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('Strict JSON required')
        size=environ.get('CONTENT_LENGTH')
        if (type(size) is not str or not size.isascii()
                or not size.isdecimal() or len(size)>3
                or not 1<=int(size)<=512):
            raise ValueError('Invalid body size')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing body')
        raw=stream.read(int(size))
        if type(raw) is not bytes or len(raw)!=int(size):
            raise ValueError('Incomplete body')
        def unique(pairs):
            obj={}
            for k,v in pairs:
                if k in obj:raise ValueError('Duplicate field')
                obj[k]=v
            return obj
        data=json.loads(raw.decode('utf-8'),object_pairs_hook=unique)
        if type(data) is not dict or set(data)!={'request_id','item'}:
            raise ValueError('Unexpected discard fields')
        if (type(data['request_id']) is not str
                or re.fullmatch('[a-f0-9]{32}',data['request_id']) is None
                or type(data['item']) is not str
                or not data['item'].strip()
                or data['item']!=data['item'].strip()
                or len(data['item'])>80):
            raise ValueError('Invalid request/item')
        return data

    @staticmethod
    def _safe(result,data):
        if (type(result) is not dict or set(result)!={
                'tenant_id','request_id','item','removed',
                'media_verified','publishing_enabled'}
                or type(result['tenant_id']) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or result['request_id']!=data['request_id']
                or result['item']!=data['item']
                or type(result['removed']) is not int
                or not 0<=result['removed']<=200
                or result['media_verified'] is not False
                or result['publishing_enabled'] is not False):
            raise RuntimeError('Untrusted pending discard')
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/content/media-pending':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='DELETE':
            return reply('405 Method Not Allowed',{'error':'DELETE required'})
        if not self.enabled or self.store is None:
            return reply('503 Service Unavailable',{'error':'Media discard disabled'})
        try:
            bearer=environ.get('HTTP_AUTHORIZATION')
            if (type(bearer) is not str or not bearer.startswith('Bearer ')
                    or re.fullmatch('[A-Za-z0-9_-]{32,2048}',bearer[7:]) is None):
                raise PermissionError('BAM session required')
            data=self._parse(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid clock')
            result=self.store.discard(token=bearer[7:],now=now,**data)
            return reply('200 OK',self._safe(result,data))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Discard unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Request not found'})
        except (ValueError,TypeError,UnicodeDecodeError,json.JSONDecodeError,
                AttributeError):
            return reply('400 Bad Request',{'error':'Invalid discard request'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Discard unavailable'})
