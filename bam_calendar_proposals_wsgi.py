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
        keys=({'request_id','expected_revision','utc_at',
              'expected_proposal_token'} if method=='POST'
              else {'request_id','expected_proposal_token'})
        if (type(body) is not dict or set(body)!=keys or
                type(body['request_id']) is not str or
                _ID.fullmatch(body['request_id']) is None):
            raise ValueError('Invalid proposed content draft')
        if method=='POST' and (
                type(body['expected_revision']) is not int or
                body['expected_revision']<1 or
                type(body['utc_at']) is not str or
                _UTC.fullmatch(body['utc_at']) is None):
            raise ValueError('Invalid proposed time')
        version=body['expected_proposal_token']
        if ((version is None and method!='POST') or
            (version is not None and
                (type(version) is not str or _ID.fullmatch(version) is None))):
            raise ValueError('Current proposal version required')
        return body

    @staticmethod
    def _safe(result,method,body=None):
        if (type(result) is not dict or
                type(result.get('tenant_id')) is not str or
                not result['tenant_id'].strip() or
                len(result['tenant_id'])>128 or
                result.get('status')!=('suggestion_preview_only'
                    if method=='SUGGESTIONS' else
                    'readiness_preview_only' if method=='READINESS'
                    else 'proposal_only') or
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
                    'proposal_token','content_changed','slot_current',
                    'publishing_enabled'}
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
                    or type(item['proposal_token']) is not str
                    or _ID.fullmatch(item['proposal_token']) is None
                    or type(item['content_changed']) is not bool
                    or type(item['slot_current']) is not bool
                    or item['publishing_enabled'] is not False
                    or (previous is not None and previous>item['utc_at'])):
                    raise RuntimeError('Unsafe proposal item')
                previous=item['utc_at']
        elif method=='READINESS':
            if (set(result)!={'tenant_id','status','proposal_count',
                 'draft_refresh_count','time_refresh_count','items',
                 'posts_scheduled','publishing_enabled'}
                 or result['status']!='readiness_preview_only'
                 or type(result['proposal_count']) is not int
                 or not 0<=result['proposal_count']<=200
                 or type(result['draft_refresh_count']) is not int
                 or type(result['time_refresh_count']) is not int
                 or type(result['items']) is not list
                 or len(result['items'])!=result['proposal_count']
                 or not 0<=result['draft_refresh_count']<=result['proposal_count']
                 or not 0<=result['time_refresh_count']<=result['proposal_count']):
                raise RuntimeError('Unsafe readiness digest')
            expected={'final_publication_review_unavailable',
                      'social_publishing_unavailable'}
            draft_count=time_count=0
            seen=set()
            for item in result['items']:
                if (type(item) is not dict or set(item)!={'request_id',
                     'draft_revision','utc_at','status','blockers',
                     'publishing_enabled'}
                     or type(item['request_id']) is not str
                     or _ID.fullmatch(item['request_id']) is None
                     or item['request_id'] in seen
                     or type(item['draft_revision']) is not int
                     or item['draft_revision']<1
                     or type(item['utc_at']) is not str
                     or _UTC.fullmatch(item['utc_at']) is None
                     or item['status']!='held'
                     or type(item['blockers']) is not list
                     or len(item['blockers'])!=len(set(item['blockers']))
                     or not expected.issubset(item['blockers'])
                     or not set(item['blockers']).issubset(expected|{
                         'draft_requires_refresh',
                         'posting_time_requires_refresh'})
                     or item['publishing_enabled'] is not False):
                    raise RuntimeError('Invalid readiness entry')
                seen.add(item['request_id'])
                draft_count+=('draft_requires_refresh' in item['blockers'])
                time_count+=('posting_time_requires_refresh' in item['blockers'])
            if (result['draft_refresh_count']!=draft_count
                or result['time_refresh_count']!=time_count):
                raise RuntimeError('Invalid readiness totals')
        elif method=='SUGGESTIONS':
            if (set(result)!={'tenant_id','status','preference_status',
                              'unassigned_held_count','available_slot_count',
                              'items','posts_scheduled','publishing_enabled'}
                    or result['status']!='suggestion_preview_only'
                    or result['preference_status'] not in (
                        'manual_preview','not_configured',
                        'needs_audience_data')
                    or type(result['unassigned_held_count']) is not int
                    or result['unassigned_held_count']<0
                    or result['unassigned_held_count']>5000
                    or type(result['available_slot_count']) is not int
                    or not 0<=result['available_slot_count']<=100
                    or type(result['items']) is not list
                    or len(result['items'])>20
                    or len(result['items'])>
                       min(result['unassigned_held_count'],
                           result['available_slot_count'])
                    or (result['preference_status']!='manual_preview'
                        and result['items'])):
                raise RuntimeError('Invalid calendar suggestions')
            seen_ids=set()
            seen_times=set()
            for item in result['items']:
                if (type(item) is not dict or set(item)!={
                    'request_id','draft_revision','utc_at','local_date',
                    'local_time','timezone','publishing_enabled'}
                    or type(item['request_id']) is not str
                    or _ID.fullmatch(item['request_id']) is None
                    or type(item['draft_revision']) is not int
                    or item['draft_revision']<1
                    or type(item['utc_at']) is not str
                    or _UTC.fullmatch(item['utc_at']) is None
                    or type(item['local_date']) is not str
                    or _DAY.fullmatch(item['local_date']) is None
                    or type(item['local_time']) is not str
                    or _CLOCK.fullmatch(item['local_time']) is None
                    or type(item['timezone']) is not str
                    or not item['timezone'].strip()
                    or len(item['timezone'])>80
                    or item['publishing_enabled'] is not False
                    or item['request_id'] in seen_ids
                    or item['utc_at'] in seen_times):
                    raise RuntimeError('Unsafe calendar suggestion')
                seen_ids.add(item['request_id'])
                seen_times.add(item['utc_at'])
        elif method=='POST':
            if (set(result)!={'tenant_id','request_id','utc_at',
                              'proposal_token','status','posts_scheduled',
                              'publishing_enabled'} or
                    result['request_id']!=body['request_id'] or
                    result['utc_at']!=body['utc_at'] or
                    type(result['proposal_token']) is not str or
                    _ID.fullmatch(result['proposal_token']) is None):
                raise RuntimeError('Invalid saved proposal')
        elif method=='DELETE':
            if (set(result)!={'tenant_id','request_id','removed','status',
                              'posts_scheduled','publishing_enabled'} or
                    result['request_id']!=body['request_id'] or
                    type(result['removed']) is not int or
                    result['removed']!=1):
                raise RuntimeError('Invalid deleted proposal')
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        path=environ.get('PATH_INFO')
        if path not in ('/api/v1/calendar-proposals',
                        '/api/v1/calendar-suggestions',
                        '/api/v1/calendar-readiness'):
            return reply('404 Not Found',{'error':'Not found'})
        suggestions=path=='/api/v1/calendar-suggestions'
        readiness=path=='/api/v1/calendar-readiness'
        method=environ.get('REQUEST_METHOD')
        if method not in (('GET',) if suggestions or readiness else
                          ('GET','POST','DELETE')):
            return reply('405 Method Not Allowed',
                         {'error':'Method not allowed'})
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
            if readiness:
                answer=self.service.readiness_digest(
                    token=bearer[7:],now=now)
            elif suggestions:
                answer=self.service.suggest_unassigned(
                    token=bearer[7:],now=now)
            elif method=='GET':
                answer=self.service.list_mine_business(
                    token=bearer[7:],now=now)
            elif method=='POST':
                answer=self.service.propose(token=bearer[7:],now=now,**data)
            else:
                answer=self.service.discard(token=bearer[7:],now=now,**data)
            return reply('201 Created' if method=='POST' else '200 OK',
                         self._safe(answer,'READINESS' if readiness else
                                    'SUGGESTIONS' if suggestions else
                                    method,data))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Calendar unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Draft unavailable'})
        except ValueError as error:
            if str(error) in ('Draft changed; refresh before proposing',
                             'Proposed time already used by this business',
                             'Proposal changed; refresh before changing date',
                             'Proposal changed; refresh before removing date'):
                return reply('409 Conflict',
                             {'error':'Calendar changed; refresh required'})
            return reply('400 Bad Request',{'error':'Invalid calendar request'})
        except (TypeError,UnicodeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid calendar request'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Calendar unavailable'})
