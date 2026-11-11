"""Strict authenticated private editorial feedback transport.

Only a current business manager/owner can write; the service independently
checks this. Feedback is never approval or authorization to publish.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[a-f0-9]{32}\Z')

def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key]=value
    return result

class BAMReviewFeedbackWSGI:
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
        if (type(length) is not str or not length.isascii()
                or not length.isdecimal() or len(length)>4
                or not 1<=int(length)<=2048):
            raise ValueError('Invalid request body length')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing body')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete request')
        body=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
        fields=({'request_id','expected_revision',
                 'expected_feedback_token','note'} if method=='PUT'
                else {'request_id','expected_feedback_token'})
        if (type(body) is not dict or set(body)!=fields or
                type(body['request_id']) is not str
                or _ID.fullmatch(body['request_id']) is None):
            raise ValueError('Current draft ID required')
        version=body['expected_feedback_token']
        if ((version is None and method!='PUT') or
            (version is not None and
             (type(version) is not str or _ID.fullmatch(version) is None))):
            raise ValueError('Current feedback version required')
        if method=='PUT' and (
            type(body['expected_revision']) is not int
            or body['expected_revision']<1
            or type(body['note']) is not str
            or not 1<=len(body['note'])<=1000
            or body['note']!=body['note'].strip()
            or any(ord(ch)<32 and ch not in '\n\t'
                   for ch in body['note'])):
            raise ValueError('Valid review note required')
        return body

    @staticmethod
    def _safe(result,method,body=None):
        if (type(result) is not dict
                or type(result.get('tenant_id')) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or result.get('status')!='feedback_only'
                or result.get('approval_granted') is not False
                or result.get('publishing_enabled') is not False):
            raise RuntimeError('Unsafe review feedback response')
        if method=='GET':
            if (set(result)!={'tenant_id','status','items',
                              'approval_granted','publishing_enabled'}
                or type(result['items']) is not list
                or len(result['items'])>200):
                raise RuntimeError('Unsafe feedback list')
            seen=set()
            for row in result['items']:
                if (type(row) is not dict or set(row)!={
                    'request_id','draft_revision','current_revision','stale',
                    'note','feedback_token','updated_at',
                    'approval_granted','publishing_enabled'}
                    or type(row['request_id']) is not str
                    or _ID.fullmatch(row['request_id']) is None
                    or row['request_id'] in seen
                    or type(row['feedback_token']) is not str
                    or _ID.fullmatch(row['feedback_token']) is None
                    or type(row['draft_revision']) is not int
                    or row['draft_revision']<1
                    or type(row['current_revision']) is not int
                    or row['current_revision']<1
                    or type(row['stale']) is not bool
                    or row['stale']!=(row['draft_revision']!=row['current_revision'])
                    or type(row['note']) is not str
                    or not 1<=len(row['note'])<=1000
                    or row['note']!=row['note'].strip()
                    or type(row['updated_at']) is not int
                    or row['updated_at']<0
                    or row['approval_granted'] is not False
                    or row['publishing_enabled'] is not False):
                    raise RuntimeError('Unsafe feedback entry')
                seen.add(row['request_id'])
        elif method=='PUT':
            if (set(result)!={'tenant_id','request_id','draft_revision',
                'feedback_token','status','approval_granted',
                'publishing_enabled'}
                or result['request_id']!=body['request_id']
                or result['draft_revision']!=body['expected_revision']
                or type(result['draft_revision']) is not int
                or type(result['feedback_token']) is not str
                or _ID.fullmatch(result['feedback_token']) is None):
                raise RuntimeError('Unsafe saved feedback')
        elif method=='DELETE':
            if (set(result)!={'tenant_id','request_id','removed',
                'status','approval_granted','publishing_enabled'}
                or result['request_id']!=body['request_id']
                or type(result['removed']) is not int
                or result['removed']!=1):
                raise RuntimeError('Unsafe removed feedback')
        return result

    @staticmethod
    def _safe_history(result):
        if (type(result) is not dict or set(result)!={
                'tenant_id','status','events','truncated',
                'approval_granted','publishing_enabled'}
                or type(result['tenant_id']) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or result['status']!='feedback_history_only'
                or type(result['events']) is not list
                or len(result['events'])>50
                or type(result['truncated']) is not bool
                or (result['truncated'] and len(result['events'])!=50)
                or result['approval_granted'] is not False
                or result['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe review feedback history')
        seen=set()
        for event in result['events']:
            if (type(event) is not dict
                    or set(event)!={'event_id','request_id','action',
                                    'draft_revision','occurred_at'}
                    or type(event['event_id']) is not str
                    or _ID.fullmatch(event['event_id']) is None
                    or event['event_id'] in seen
                    or type(event['request_id']) is not str
                    or _ID.fullmatch(event['request_id']) is None
                    or event['action'] not in ('created','updated','removed')
                    or type(event['draft_revision']) is not int
                    or event['draft_revision']<1
                    or type(event['occurred_at']) is not int
                    or event['occurred_at']<0):
                raise RuntimeError('Unsafe review feedback event')
            seen.add(event['event_id'])
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        path=environ.get('PATH_INFO')
        if path not in ('/api/v1/review-feedback',
                        '/api/v1/review-feedback-history'):
            return reply('404 Not Found',{'error':'Not found'})
        history=path=='/api/v1/review-feedback-history'
        method=environ.get('REQUEST_METHOD')
        if method not in (('GET',) if history else ('GET','PUT','DELETE')):
            return reply('405 Method Not Allowed',{'error':'GET PUT or DELETE required'})
        if not self.enabled or self.service is None:
            return reply('503 Service Unavailable',{'error':'Feedback unavailable'})
        try:
            auth=environ.get('HTTP_AUTHORIZATION')
            if (type(auth) is not str or not auth.startswith('Bearer ')
                    or _TOKEN.fullmatch(auth[7:]) is None):
                raise PermissionError('BAM session required')
            if environ.get('QUERY_STRING'):
                raise ValueError('Unexpected query parameters')
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server time')
            body=self._parse(environ,method) if method!='GET' else None
            if history:
                result=self.service.history_current_business(
                    token=auth[7:],now=now)
                return reply('200 OK',self._safe_history(result))
            if method=='GET':
                result=self.service.list_current_business(
                    token=auth[7:],now=now)
            elif method=='PUT':
                result=self.service.save(token=auth[7:],now=now,**body)
            else:
                result=self.service.discard(token=auth[7:],now=now,**body)
            return reply('200 OK',self._safe(result,method,body))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Feedback unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Draft unavailable'})
        except ValueError as error:
            if str(error) in ('Draft changed; refresh feedback',
                              'Feedback changed; refresh required'):
                return reply('409 Conflict',{'error':'Refresh feedback required'})
            return reply('400 Bad Request',{'error':'Invalid feedback request'})
        except (TypeError,AttributeError,UnicodeError):
            return reply('400 Bad Request',{'error':'Invalid feedback request'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Feedback unavailable'})
