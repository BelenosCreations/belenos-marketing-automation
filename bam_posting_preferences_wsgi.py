"""Disabled-by-default owner-only posting-time preference transport.

The trusted AccountReadAPI derives business and role from the BAM session.
Saving preferences does not schedule, publish, or enable an optimizer.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_CLOCK=re.compile(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z')
_PATH='/api/v1/posting-preferences'

def _unique_object(pairs):
    value={}
    for key,item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON field')
        value[key]=item
    return value

class BAMPostingPreferencesWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean enabled state required')
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
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    @staticmethod
    def _parse(environ):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('Strict JSON required')
        length=environ.get('CONTENT_LENGTH')
        if (type(length) is not str or not length.isascii()
                or not length.isdecimal() or len(length)>4
                or not 1<=int(length)<=4096):
            raise ValueError('Invalid request size')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing JSON body')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete JSON body')
        data=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique_object)
        if type(data) is not dict or set(data)!={'mode','timezone','manual_times'}:
            raise ValueError('Unexpected posting preference fields')
        if data['mode'] not in ('smart','manual'):
            raise ValueError('Invalid posting preference mode')
        timezone=data['timezone']
        if (type(timezone) is not str or not timezone.strip()
                or timezone!=timezone.strip() or len(timezone)>80):
            raise ValueError('IANA timezone required')
        times=data['manual_times']
        if (type(times) is not list or len(times)>24
                or any(type(v) is not str or _CLOCK.fullmatch(v) is None
                       for v in times)
                or len(set(times))!=len(times)):
            raise ValueError('Invalid manual times')
        if data['mode']=='manual' and not times:
            raise ValueError('Manual mode needs times')
        if data['mode']=='smart' and times:
            raise ValueError('Smart mode has no fixed times')
        return data

    @staticmethod
    def _safe(result):
        if (type(result) is not dict
                or set(result)!={'tenant_id','mode','timezone','manual_times',
                                  'configured','publishing_enabled'}
                or type(result['tenant_id']) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or result['mode'] not in ('smart','manual')
                or type(result['timezone']) is not str
                or not result['timezone']
                or len(result['timezone'])>80
                or result['configured'] is not True
                or result['publishing_enabled'] is not False
                or type(result['manual_times']) is not list
                or len(result['manual_times'])>24
                or any(type(v) is not str or _CLOCK.fullmatch(v) is None
                       for v in result['manual_times'])
                or len(set(result['manual_times']))!=len(result['manual_times'])
                or (result['mode']=='manual' and not result['manual_times'])
                or (result['mode']=='smart' and result['manual_times'])):
            raise RuntimeError('Invalid trusted preference result')
        return result

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
                         {'error':'Posting preference writes disabled'})
        try:
            header=environ.get('HTTP_AUTHORIZATION')
            if (type(header) is not str or not header.startswith('Bearer ')
                    or _TOKEN.fullmatch(header[7:]) is None):
                raise PermissionError('BAM session required')
            data=self._parse(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server time')
            result=self.api.set_posting_preferences(
                session_token=header[7:],server_now=now,**data)
            return reply('200 OK',self._safe(result))
        except PermissionError:
            return reply('401 Unauthorized',
                         {'error':'Preference write access unavailable'})
        except (ValueError,TypeError,UnicodeDecodeError,
                json.JSONDecodeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid preferences'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Posting preference service unavailable'})
