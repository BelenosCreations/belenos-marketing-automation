"""Strict HTTPS interface for non-executable BAM calendar proposals.

GET lists private proposals; POST assigns an owner-configured *possible* time
to an unpublished held draft; DELETE removes only a proposal. No schedule
executor, approval or social publication can be reached from these routes.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[a-f0-9]{32}\Z')
_UTC=re.compile(r'\d{4}-\d\d-\d\dT(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\+00:00\Z')
_DAY=re.compile(r'\d{4}-\d\d-\d\d\Z')
_CLOCK=re.compile(r'(?:[01]\d|2[0-3]):[0-5]\d\Z')

def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key]=value
    return result

class BAMCalendarProposalsWSGI:
    def __init__(self,service=None,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit enabled switch required')
        self.service=service
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
    def _parse(environ,method):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('JSON required')
        length=environ.get('CONTENT_LENGTH')
        if (type(length) is not str or not length.isascii() or
                not length.isdecimal() or len(length)>4
                or not 1<=int(length)<=512):
            raise ValueError('Invalid request body length')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing body')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete request')
        body=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
        keys={'request_id','expected_revision','utc_at'} if method=='POST' else {'request_id'}
        if type(body) is not dict or set(body)!=keys or
            type(body['request_id']) is not str or
            _ID.fullmatch(body['request_id']) is None:
            raise ValueError('Invalid proposed content draft')
        if method=='POST' and (
                type(body['expected_revision']) is not int or
                body['expected_revision']<1 or
                type(body['utc_at']) is not str or
                _UTC.fullmatch(body['utc_at']) is None):
            raise ValueError('Invalid proposed time')
        return body

    @staticmethod
    def _safe(result,method,body=None):
        if (type(result) is not dict or
                type(result.get('tenant_id')) is not str or
                not result['tenant_id'].strip() or
                len(result['tenant_id'])>128 or
                result.get('status')!='proposal_only' or
                result.get('posts_scheduled')!=0 or
                result.get('publishing_enabled') is not False):
            raise RuntimeError('Unsafe calendar proposal result')
        if method=='GET':
            if (set(result)!={'tenant_id','status','items',
                              'posts_scheduled','publishing_enabled'} or
                    type(result['items']) is not list or
                    len(result['items'])>200):
                raise RuntimeError('Invalid proposal list')
            previous=None
            for item in result['items']:
                if (type(item) is not dict or set(item)!={
                    'request_id','draft_revision','current_revision',
                    'utc_at','local_date','local_time','timezone',
                    'content_changed','slot_current','publishing_enabled'}
                    or type(item['request_id']) is not str
                    or _ID.fullmatch(item['request_id']) is None
                    or type(item['draft_revision']) is not int
                    or item['draft_revision']<1
                    or (item['current_revision'] is not None and
                        (type(item['current_revision']) is not int or
                         item['current_revision']<1))
                    or type(item['utc_at']) is not str
                    or _UTC.fullmatch(item['utc_at']) is None
                    or type(item['local_date']) is not str
                    or _DAY.fullmatch(item['local_date']) is None
                    or type(item['local_time']) is not str
                    or _CLOCK.fullmatch(item['local_time']) is None
                    or type(item['timezone']) is not str
                    or not item['timezone'].strip()
                    or len(item['timezone'])>80
                    or type(item['content_changed']) is not bool
                    or type(item['slot_current']) is not bool
                    or item['publishing_enabled'] is not False
                    or (previous is not None and previous>item['utc_at'])):
                    raise RuntimeError('Unsafe proposal item')
                previous=item['utc_at']
        elif method=='POST':
            if (set(result)!={'tenant_id','request_id','utc_at',
                              'status','posts_scheduled',
                              'publishing_enabled'} or
                    result['request_id']!=body['request_id'] or
                    result['utc_at']!=body['utc_at']):
                raise RuntimeError('Invalid saved proposal')
        elif method=='DELETE':
            if (set(result)!={'tenant_id','request_id','removed','status',
                              'posts_scheduled','publishing_enabled'} or
                    result['request_id']!=body['request_id'] or
                    type(result['removed']) is not int or
                    result['removed'] not in (0,1)):
                raise RuntimeError('Invalid deleted proposal')
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/calendar-proposals':
            return reply('404 Not Found',{'error':'Not found'})
        method=environ.get('REQUEST_METHOD')
        if method not in ('GET','POST','DELETE'):
            return reply('405 Method Not Allowed',
                         {'error':'GET POST or DELETE required'})
        if not self.enabled or self.service is None:
            return reply('503 Service Unavailable',
                         {'error':'Calendar proposals disabled'})
        try:
            bearer=environ.get('HTTP_AUTHORIZATION')
            if (type(bearer) is not str or not bearer.startswith('Bearer ')
                    or _TOKEN.fullmatch(bearer[7:]) is None):
                raise PermissionError('Active BAM session required')
            if environ.get('QUERY_STRING'):
                raise ValueError('Untrusted query')
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server time')
            data=self._parse(environ,method) if method!='GET' else None
            if method=='GET':
                answer=self.service.list_mine_business(
                    token=bearer[7:],now=now)
            elif method=='POST':
                answer=self.service.propose(token=bearer[7:],now=now,**data)
            else:
                answer=self.service.discard(token=bearer[7:],now=now,**data)
            return reply('201 Created' if method=='POST' else '200 OK',
                         self._safe(answer,method,data))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Calendar unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Draft unavailable'})
        except ValueError as error:
            if str(error) in ('Draft changed; refresh before proposing',
                             'Proposed time already used by this business'):
                return reply('409 Conflict',
                             {'error':'Calendar changed; refresh required'})
            return reply('400 Bad Request',{'error':'Invalid calendar request'})
        except (TypeError,UnicodeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid calendar request'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Calendar unavailable'})
