"""Strict, disabled-by-default HTTPS held-draft priority edit.

This is a metadata-only operation, not content approval, scheduling,
post execution, or social publishing.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[a-f0-9]{32}\Z')

def _object(pairs):
    data={}
    for key,value in pairs:
        if key in data:
            raise ValueError('Duplicate priority JSON field')
        data[key]=value
    return data

class BAMContentPriorityWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit priority-write gate required')
        self.api=api
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
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',
             "default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    @staticmethod
    def _parse(environ):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('JSON body required')
        length=environ.get('CONTENT_LENGTH')
        if (type(length) is not str or not length.isascii()
                or not length.isdecimal() or len(length)>4
                or not 1<=int(length)<=512):
            raise ValueError('Invalid priority request body length')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing priority request stream')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Truncated priority request')
        body=json.loads(raw.decode('utf-8'),object_pairs_hook=_object)
        if (type(body) is not dict
                or set(body)!={'request_id','priority',
                               'expected_priority_token'}
                or type(body['request_id']) is not str
                or _ID.fullmatch(body['request_id']) is None
                or type(body['priority']) is not int
                or not -10<=body['priority']<=10
                or type(body['expected_priority_token']) is not str
                or _ID.fullmatch(body['expected_priority_token']) is None):
            raise ValueError('Unsafe queue priority request')
        return body

    @staticmethod
    def _safe(result,requested):
        if (type(result) is not dict or set(result)!={
                'tenant_id','request_id','priority','priority_token',
                'revision','status','publishing_enabled'}
                or type(result['tenant_id']) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or result['request_id']!=requested['request_id']
                or type(result['priority']) is not int
                or result['priority']!=requested['priority']
                or type(result['priority_token']) is not str
                or _ID.fullmatch(result['priority_token']) is None
                or result['priority_token']==requested['expected_priority_token']
                or type(result['revision']) is not int
                or result['revision']<1
                or result['status']!='held_priority_only'
                or result['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe priority write response')
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/content/priority':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='PUT':
            return reply('405 Method Not Allowed',{'error':'PUT required'})
        if not self.enabled:
            return reply('503 Service Unavailable',
                         {'error':'Priority edits disabled'})
        try:
            bearer=environ.get('HTTP_AUTHORIZATION')
            if (type(bearer) is not str or not bearer.startswith('Bearer ')
                    or _TOKEN.fullmatch(bearer[7:]) is None):
                raise PermissionError('Active BAM session required')
            if environ.get('QUERY_STRING'):
                raise ValueError('Query fields are not accepted')
            body=self._parse(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server clock')
            result=self.api.update_held_priority(
                session_token=bearer[7:],server_now=now,**body)
            return reply('200 OK',self._safe(result,body))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Priority unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Draft unavailable'})
        except ValueError as exc:
            if str(exc)=='Queue priority changed; refresh required':
                return reply('409 Conflict',
                             {'error':'Priority changed; refresh required'})
            return reply('400 Bad Request',{'error':'Invalid priority request'})
        except (TypeError,AttributeError,UnicodeError):
            return reply('400 Bad Request',{'error':'Invalid priority request'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Priority unavailable'})
