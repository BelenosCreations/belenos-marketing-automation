"""Private, authenticated GET-only review-preparation summary.

Everything remains held. This adapter cannot approve, dispatch, schedule,
publish or start an external service. Its response describes content state
only and deliberately never exposes stored media reference or secret data.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_ID=re.compile(r'[a-f0-9]{32}\Z')
_CHANNELS=frozenset(('facebook','instagram','linkedin','pinterest','tiktok','youtube'))
_STATUSES=frozenset(('needs_content','ready_for_review','postponed','unavailable'))
_BLOCKERS=frozenset(('draft_held','missing_required_content',
    'unverified_or_unexpected_content','not_ready_for_editorial_review',
    'truthguard_review_required','owner_approval_not_implemented',
    'social_publishing_disabled'))
_ALWAYS=frozenset(('truthguard_review_required',
    'owner_approval_not_implemented','social_publishing_disabled'))

class BAMReviewReadinessWSGI:
    def __init__(self,service=None,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit adapter enablement required')
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
    def _safe(value):
        if (type(value) is not dict or set(value)!={
              'tenant_id','status','held_count',
              'editorial_material_complete_count','items','approved_count',
              'publishing_enabled'}
            or type(value['tenant_id']) is not str
            or not value['tenant_id'].strip()
            or len(value['tenant_id'])>128
            or value['status']!='review_preview_only'
            or type(value['held_count']) is not int
            or not 0<=value['held_count']<=200
            or type(value['editorial_material_complete_count']) is not int
            or not 0<=value['editorial_material_complete_count']<=value['held_count']
            or type(value['items']) is not list
            or len(value['items'])!=value['held_count']
            or value['approved_count']!=0 or type(value['approved_count']) is not int
            or value['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe editorial review preview')
        seen=set()
        complete=0
        for row in value['items']:
            if (type(row) is not dict or set(row)!={
                  'request_id','revision','channel','status',
                  'missing_items','unverified_items',
                  'editorial_material_complete','blockers',
                  'approved','publishing_enabled'}
                or type(row['request_id']) is not str
                or _ID.fullmatch(row['request_id']) is None
                or row['request_id'] in seen
                or type(row['revision']) is not int or row['revision']<1
                or row['channel'] not in _CHANNELS
                or row['status'] not in _STATUSES
                or type(row['missing_items']) is not list
                or type(row['unverified_items']) is not list
                or type(row['blockers']) is not list
                or len(row['blockers'])>7 or len(row['blockers'])<3
                or any(type(x) is not str or not x.strip() or
                       len(x)>80 for x in (
                        row['missing_items']+row['unverified_items']))
                or any(len(x)>20 for x in (
                    row['missing_items'],row['unverified_items']))
                or len(row['missing_items'])!=len(set(row['missing_items']))
                or len(row['unverified_items'])!=len(set(row['unverified_items']))
                or set(row['missing_items']) & set(row['unverified_items'])
                or any(type(x) is not str or x not in _BLOCKERS
                       for x in row['blockers'])
                or len(set(row['blockers']))!=len(row['blockers'])
                or not _ALWAYS.issubset(row['blockers'])
                or type(row['editorial_material_complete']) is not bool
                or (row['editorial_material_complete'] and (
                     row['status']!='ready_for_review'
                     or row['missing_items'] or row['unverified_items']
                     or len(row['blockers'])!=3))
                or row['approved'] is not False
                or row['publishing_enabled'] is not False):
                raise RuntimeError('Unsafe individual held review')
            seen.add(row['request_id'])
            complete+=int(row['editorial_material_complete'])
        if complete!=value['editorial_material_complete_count']:
            raise RuntimeError('Unsafe editorial review count')
        return value

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/review-readiness':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='GET':
            return reply('405 Method Not Allowed',{'error':'GET required'})
        if not self.enabled or self.service is None:
            return reply('503 Service Unavailable',{'error':'Review preview disabled'})
        try:
            auth=environ.get('HTTP_AUTHORIZATION')
            if (type(auth) is not str or not auth.startswith('Bearer ')
                    or _TOKEN.fullmatch(auth[7:]) is None):
                raise PermissionError('BAM session required')
            if environ.get('QUERY_STRING'):
                raise ValueError('Query fields are not accepted')
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server clock')
            result=self.service.list_current_business(
                token=auth[7:],now=now)
            return reply('200 OK',self._safe(result))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Review preview unavailable'})
        except (ValueError,TypeError,AttributeError,UnicodeError):
            return reply('400 Bad Request',{'error':'Invalid review preview request'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Review preview unavailable'})
