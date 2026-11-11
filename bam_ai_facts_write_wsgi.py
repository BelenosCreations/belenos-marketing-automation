"""Disabled-by-default owner-confirmed business fact write endpoint.

This is a separate authenticated HTTPS-only WSGI adapter. The authenticated
business and confirming user are derived from the session, never request JSON.
"""
import json
import time

class BAMAIFactsWriteWSGI:
    def __init__(self, *, registry,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit enable flag required')
        self.registry=registry
        self.enabled=enabled
        self.clock=clock if clock is not None else time.time

    @staticmethod
    def _response(start_response,status,body):
        data=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(data))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")])
        return [data]

    def __call__(self,environ,start_response):
        respond=lambda status,body:self._response(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return respond('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/ai-business-facts':
            return respond('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='PUT':
            return respond('405 Method Not Allowed',{'error':'PUT required'})
        if not self.enabled:
            return respond('503 Service Unavailable',
                           {'error':'Business fact editing not enabled'})
        auth=environ.get('HTTP_AUTHORIZATION','')
        if type(auth) is not str or not auth.startswith('Bearer ') or (
            len(auth)>2060 or not auth[7:].strip() or
            auth[7:]!=auth[7:].strip()):
            return respond('401 Unauthorized',{'error':'Authentication required'})
        if environ.get('CONTENT_TYPE')!='application/json':
            return respond('415 Unsupported Media Type',{'error':'JSON required'})
        length=environ.get('CONTENT_LENGTH','')
        if type(length) is not str or len(length)>5 or (
            not length.isascii() or not length.isdecimal() or
            not 1<=int(length)<=20000):
            return respond('413 Content Too Large',{'error':'Invalid request size'})
        stream=environ.get('wsgi.input')
        if stream is None:
            return respond('400 Bad Request',{'error':'Invalid request'})
        try:
            raw=stream.read(int(length))
            if len(raw)!=int(length):
                raise ValueError('Incomplete request')
            data=json.loads(raw.decode('utf-8'))
            if type(data) is not dict or set(data)!={
                'facts','expected_revision'} or (
                type(data['expected_revision']) is not int or
                data['expected_revision']<0):
                raise ValueError('Invalid fact confirmation')
        except (ValueError,TypeError,UnicodeDecodeError,AttributeError):
            return respond('400 Bad Request',{'error':'Invalid fact confirmation'})
        try:
            result=self.registry.confirm(token=auth[7:],
                now=int(self.clock()),facts=data['facts'],
                expected_revision=data['expected_revision'])
        except PermissionError:
            return respond('403 Forbidden',{'error':'Owner permission required'})
        except ValueError:
            return respond('409 Conflict',
                           {'error':'Facts invalid or changed; refresh first'})
        except Exception:
            return respond('503 Service Unavailable',
                           {'error':'Fact confirmation unavailable'})
        return respond('200 OK',result)
