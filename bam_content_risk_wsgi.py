"""Read-only heuristic claim-risk preview; never TruthGuard publication approval.

Only the current tenant's draft copy can be scanned. This route does not
verify facts, grant approval, schedule posts or call any external model.
"""
import json
import re
import time
from urllib.parse import parse_qs

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_REQUEST=re.compile(r'[a-f0-9]{32}\Z')
_CATEGORIES=frozenset(('price_or_discount','guarantee',
                        'urgency_or_availability','business_hours',
                        'testimonial'))

class BAMContentRiskWSGI:
    def __init__(self,api,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit enabled state required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response,status,document):
        raw=json.dumps(document,separators=(',',':'),
                       ensure_ascii=False).encode('utf-8')
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(raw))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('Referrer-Policy','no-referrer'),
            ('X-Content-Type-Options','nosniff'),
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    @staticmethod
    def _request_id(environ):
        query=environ.get('QUERY_STRING','')
        if type(query) is not str or len(query)>128:
            raise ValueError('Invalid risk query')
        parsed=parse_qs(query,keep_blank_values=True,
                        strict_parsing=True,encoding='ascii',errors='strict')
        if set(parsed)!={'request_id'} or len(parsed['request_id'])!=1:
            raise ValueError('Single request_id required')
        rid=parsed['request_id'][0]
        if _REQUEST.fullmatch(rid) is None:
            raise ValueError('Invalid request_id')
        return rid

    @staticmethod
    def _safe(result,rid):
        if (type(result) is not dict or set(result)!={
                'tenant_id','request_id','revision','signals',
                'signal_count','truncated','review_required',
                'extraction_complete','status','publishing_enabled'}
                or type(result['tenant_id']) is not str
                or not result['tenant_id'].strip()
                or len(result['tenant_id'])>128
                or result['request_id']!=rid
                or type(result['revision']) is not int
                or result['revision']<1
                or type(result['signals']) is not list
                or len(result['signals'])>50
                or type(result['signal_count']) is not int
                or result['signal_count']<len(result['signals'])
                or type(result['truncated']) is not bool
                or result['truncated']!=(result['signal_count']>len(result['signals']))
                or result['review_required'] is not True
                or result['extraction_complete'] is not False
                or result['status']!='held'
                or result['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe risk preview')
        for signal in result['signals']:
            if (type(signal) is not dict
                    or set(signal)!={'category','start','end','text'}
                    or signal['category'] not in _CATEGORIES
                    or type(signal['start']) is not int
                    or type(signal['end']) is not int
                    or not 0<=signal['start']<signal['end']<=2000
                    or type(signal['text']) is not str
                    or not signal['text']
                    or len(signal['text'])!=signal['end']-signal['start']):
                raise RuntimeError('Unsafe risk signal')
        return result

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/content/risk-preview':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='GET':
            return reply('405 Method Not Allowed',{'error':'GET required'})
        if not self.enabled:
            return reply('503 Service Unavailable',{'error':'Risk preview disabled'})
        try:
            auth=environ.get('HTTP_AUTHORIZATION')
            if (type(auth) is not str or not auth.startswith('Bearer ')
                    or _TOKEN.fullmatch(auth[7:]) is None):
                raise PermissionError('BAM session required')
            rid=self._request_id(environ)
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid server time')
            result=self.api.get_content_risk_preview(
                session_token=auth[7:],server_now=now,request_id=rid)
            return reply('200 OK',self._safe(result,rid))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Risk preview unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Draft unavailable'})
        except (ValueError,TypeError,UnicodeDecodeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid risk preview request'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Risk preview unavailable'})
