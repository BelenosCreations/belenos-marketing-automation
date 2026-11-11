"""Disabled-by-default HTTPS endpoint for one-component AI draft revision.

Production must separately authorize a trusted provider executor, encrypted
OpenAI key access, billing and distributed quota protections. This route
cannot choose tenant, user, model, plan, billing month, or publishing state.
"""
from datetime import datetime,timezone
import json
import re
import time

from ai_sponsorship import SponsorshipPlan

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_KEY=re.compile(r'[a-f0-9]{32}\Z')

def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key]=value
    return result

class BAMAIRevisionWSGI:
    def __init__(self, *, workflow, plan_resolver, enabled=False, clock=None):
        if type(enabled) is not bool or not callable(plan_resolver):
            raise ValueError('Trusted plan resolver and enable flag required')
        self.workflow=workflow
        self.plan_resolver=plan_resolver
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted server clock required')

    @staticmethod
    def _response(start_response,status,body):
        raw=json.dumps(body,separators=(',',':')).encode('utf-8')
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
        if (type(length) is not str or not length.isascii() or
                not length.isdecimal() or len(length)>4 or
                not 1<=int(length)<=4096):
            raise ValueError('Invalid request size')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Body required')
        raw=stream.read(int(length))
        if type(raw) is not bytes or len(raw)!=int(length):
            raise ValueError('Incomplete request')
        body=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
        if (type(body) is not dict or set(body)!={
                'draft_id','expected_revision','target','instruction','topic'}):
            raise ValueError('Unsupported request fields')
        if (type(body['draft_id']) is not str or
                _KEY.fullmatch(body['draft_id']) is None or
                type(body['expected_revision']) is not int or
                body['expected_revision']<1 or
                body['target'] not in ('post_text','image_prompt') or
                type(body['instruction']) is not str or
                not body['instruction'].strip() or
                len(body['instruction'])>500 or
                type(body['topic']) is not str or
                not body['topic'].strip() or len(body['topic'])>300):
            raise ValueError('Invalid single-component revision')
        return body

    @staticmethod
    def _safe(result,requested_draft):
        if (type(result) is not dict or type(result.get('revised')) is not bool
                or result.get('publishing_enabled') is not False
                or type(result.get('tenant_id')) is not str
                or not result['tenant_id'].strip() or
                len(result['tenant_id'])>128):
            raise RuntimeError('Unsafe AI revision result')
        if result['revised']:
            draft=result.get('draft')
            if (type(draft) is not dict or
                    draft.get('draft_id')!=requested_draft or
                    draft.get('tenant_id')!=result['tenant_id'] or
                    type(draft.get('revision')) is not int or
                    draft['revision']<2 or
                    draft.get('status') not in (
                        'needs_media','draft_pending_verification') or
                    draft.get('publishing_enabled') is not False):
                raise RuntimeError('Unsafe AI revised draft')
            return {'revised':True,'tenant_id':result['tenant_id'],
                    'draft_id':requested_draft,'revision':draft['revision'],
                    'status':draft['status'],'publishing_enabled':False}
        reason=result.get('reason')
        if reason not in ('already_completed','already_failed',
                          'already_in_progress','limit_reached','not_entitled'):
            raise RuntimeError('Unsafe AI revision hold')
        return {'revised':False,'tenant_id':result['tenant_id'],
                'reason':reason,'publishing_enabled':False}

    def __call__(self,environ,start_response):
        reply=lambda status,body:self._response(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/ai/targeted-revision':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='POST':
            return reply('405 Method Not Allowed',{'error':'POST required'})
        if not self.enabled:
            return reply('503 Service Unavailable',
                         {'error':'AI revision is disabled'})
        auth=environ.get('HTTP_AUTHORIZATION')
        if (type(auth) is not str or not auth.startswith('Bearer ') or
                _TOKEN.fullmatch(auth[7:]) is None):
            return reply('401 Unauthorized',
                         {'error':'BAM session required'})
        key=environ.get('HTTP_IDEMPOTENCY_KEY')
        if type(key) is not str or _KEY.fullmatch(key) is None:
            return reply('400 Bad Request',
                         {'error':'Idempotency key required'})
        try:
            body=self._parse(environ)
        except (ValueError,TypeError,AttributeError,UnicodeError):
            return reply('400 Bad Request',
                         {'error':'Invalid AI revision request'})
        try:
            now=int(self.clock())
            if now<0:raise ValueError('Invalid server time')
            month=datetime.fromtimestamp(now,tz=timezone.utc).strftime('%Y-%m')
            plan=self.plan_resolver(session_token=auth[7:],server_now=now)
            if not isinstance(plan,SponsorshipPlan):
                raise RuntimeError('Trusted sponsorship plan unavailable')
            result=self.workflow.revise_sponsored(
                token=auth[7:],now=now,month=month,
                sponsorship_plan=plan,request_key=key,**body)
            safe=self._safe(result,body['draft_id'])
        except PermissionError:
            return reply('401 Unauthorized',
                         {'error':'AI revision unavailable'})
        except LookupError:
            return reply('404 Not Found',{'error':'Draft unavailable'})
        except ValueError as exc:
            if str(exc) in (
                    'Draft changed; refresh before revising',
                    'Request key reused with different input'):
                return reply('409 Conflict',
                             {'error':'Draft or request changed; refresh required'})
            return reply('422 Unprocessable Entity',
                         {'error':'AI revision could not proceed'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'AI revision unavailable'})
        return reply('200 OK',safe) if not safe['revised'] else reply('201 Created',safe)
