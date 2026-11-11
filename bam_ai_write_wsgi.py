"""Disabled-by-default HTTPS-only AI draft generation WSGI endpoint.

A production composition root must explicitly enable this endpoint and
supply a trusted workflow and sponsorship plan resolver. No cookies, CORS,
user-supplied business IDs, API keys, arbitrary model or publishing actions.
"""
import datetime
import json
import re
import time

def _unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key]=value
    return result

class BAMAIWriteWSGI:
    def __init__(self, *, workflow,plan_resolver,enabled=False,clock=None):
        if not callable(plan_resolver) or type(enabled) is not bool:
            raise ValueError('Trusted plan resolver and enable flag required')
        self.workflow=workflow
        self.plan_resolver=plan_resolver
        self.enabled=enabled
        self.clock=clock if clock is not None else time.time

    @staticmethod
    def _response(start_response,status,body):
        raw=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(raw))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")])
        return [raw]

    def __call__(self,environ,start_response):
        reply=lambda status,body:self._response(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        if environ.get('PATH_INFO')!='/api/v1/ai-generate':
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='POST':
            return reply('405 Method Not Allowed',{'error':'POST required'})
        if not self.enabled:
            return reply('503 Service Unavailable',
                         {'error':'AI generation is not enabled'})
        auth=environ.get('HTTP_AUTHORIZATION','')
        if (type(auth) is not str or not auth.startswith('Bearer ') or
            len(auth)>2060 or not auth[7:].strip() or
            auth[7:]!=auth[7:].strip()):
            return reply('401 Unauthorized',{'error':'Authentication required'})
        key=environ.get('HTTP_IDEMPOTENCY_KEY')
        if type(key) is not str or re.fullmatch(r'[0-9a-f]{32}',key) is None:
            return reply('400 Bad Request',{'error':'Request key required'})
        if environ.get('CONTENT_TYPE')!='application/json':
            return reply('415 Unsupported Media Type',
                         {'error':'JSON required'})
        length=environ.get('CONTENT_LENGTH','')
        if type(length) is not str or len(length)>4 or
            not length.isascii() or not length.isdecimal() or (
            not 1<=int(length)<=4096):
            return reply('413 Content Too Large',
                         {'error':'Invalid request size'})
        stream=environ.get('wsgi.input')
        if stream is None:
            return reply('400 Bad Request',{'error':'Invalid request'})
        try:
            body=stream.read(int(length))
            if len(body)!=int(length):
                raise ValueError('Incomplete request')
            value=json.loads(body.decode('utf-8'),object_pairs_hook=_unique_object)
            if (type(value) is not dict or set(value)!={
                'topic','platform','needs_media','include_image_prompt'} or
                type(value['topic']) is not str or
                not value['topic'].strip() or len(value['topic'])>300 or
                value['platform'] not in (
                    'facebook','instagram','linkedin','pinterest',
                    'tiktok','youtube') or
                type(value['needs_media']) is not bool or
                type(value['include_image_prompt']) is not bool):
                raise ValueError('Invalid draft request')
        except (ValueError,UnicodeDecodeError,TypeError,AttributeError):
            return reply('400 Bad Request',{'error':'Invalid draft request'})
        try:
            now=int(self.clock())
            if now<0:
                raise ValueError('Invalid server time')
            month=datetime.datetime.fromtimestamp(
                now,datetime.timezone.utc).strftime('%Y-%m')
            # The plan resolver is trusted server configuration, never a
            # client-supplied plan or monthly allowance.
            plan=self.plan_resolver(session_token=auth[7:],server_now=now)
            result=self.workflow.generate_sponsored(
                token=auth[7:],now=now,topic=value['topic'],
                platform=value['platform'],month=month,
                sponsorship_plan=plan,needs_media=value['needs_media'],
                include_image_prompt=value['include_image_prompt'],
                request_key=key)
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Authentication required'})
        except ValueError:
            return reply('422 Unprocessable Entity',
                         {'error':'Draft generation could not proceed'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Draft generation unavailable'})
        if result['created']:
            # Never return secrets or the full provider request.
            draft=result['draft']
            return reply('201 Created',{
                'created':True,'tenant_id':draft['tenant_id'],
                'draft_id':draft['draft_id'],'status':draft['status'],
                'publishing_enabled':False})
        return reply('200 OK',{'created':False,
            'tenant_id':result['tenant_id'],
            'reason':result['reason'],'publishing_enabled':False})
