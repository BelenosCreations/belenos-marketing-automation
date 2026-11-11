"""Owner-only offline read/cancel adapter for existing pending invitations.

No invitation creation, external delivery, acceptance, paid or publish route.
Explicit trusted delivery callback configuration is required by the gateway.
"""
import json
import re
import time

TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
IDENT=re.compile(r'[a-f0-9]{32}\Z')
ROLES=frozenset(('marketing_manager','content_creator','employee','viewer'))

def unique(pairs):
    obj={}
    for key,value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON field')
        obj[key]=value
    return obj

class BAMTeamInvitationsWSGI:
    def __init__(self,service=None,*,enabled=False,clock=None):
        if type(enabled) is not bool: raise ValueError('Boolean enable required')
        self.service=service
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock): raise ValueError('Trusted clock required')

    @staticmethod
    def reply(start_response,status,body):
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
    def parse(environ):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('JSON content type required')
        n=environ.get('CONTENT_LENGTH')
        if (type(n) is not str or not n.isascii() or not n.isdecimal()
                or len(n)>4 or not 1<=int(n)<=2048):
            raise ValueError('Bounded body required')
        stream=environ.get('wsgi.input')
        if stream is None: raise ValueError('Missing body')
        raw=stream.read(int(n))
        if type(raw) is not bytes or len(raw)!=int(n):
            raise ValueError('Incomplete body')
        obj=json.loads(raw.decode('utf-8'),object_pairs_hook=unique)
        if (type(obj) is not dict or set(obj)!={'invitation_id'}
                or type(obj['invitation_id']) is not str
                or IDENT.fullmatch(obj['invitation_id']) is None):
            raise ValueError('Invalid cancellation')
        return obj

    @staticmethod
    def safe_list(obj):
        if (type(obj) is not dict or set(obj)!={
                'tenant_id','status','items','publishing_enabled'}
            or type(obj['tenant_id']) is not str
            or not obj['tenant_id'].strip() or len(obj['tenant_id'])>128
            or obj['status']!='private_pending_invitations'
            or type(obj['items']) is not list or len(obj['items'])>50
            or obj['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe invitation summary')
        seen=set()
        for item in obj['items']:
            if (type(item) is not dict or set(item)!={
                    'invitation_id','email','role','expires_at'}
                or type(item['invitation_id']) is not str
                or IDENT.fullmatch(item['invitation_id']) is None
                or item['invitation_id'] in seen
                or type(item['email']) is not str
                or not 3<=len(item['email'])<=254 or '@' not in item['email']
                or item['role'] not in ROLES
                or type(item['expires_at']) is not int
                or item['expires_at']<0):
                raise RuntimeError('Unsafe invitation item')
            seen.add(item['invitation_id'])
        return obj

    @staticmethod
    def safe_history(obj):
        """Strict metadata-only invitation activity, never addresses/tokens."""
        if (type(obj) is not dict or set(obj)!={
                'tenant_id','status','events','publishing_enabled'}
            or type(obj['tenant_id']) is not str
            or not obj['tenant_id'].strip() or len(obj['tenant_id'])>128
            or obj['status']!='private_invitation_activity'
            or type(obj['events']) is not list or len(obj['events'])>30
            or obj['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe invitation activity')
        previous=None
        for event in obj['events']:
            if (type(event) is not dict or set(event)!={
                    'event_id','invitation_id','action','occurred_at'}
                or type(event['event_id']) is not int
                or event['event_id']<1
                or (previous is not None and event['event_id']>=previous)
                or type(event['invitation_id']) is not str
                or IDENT.fullmatch(event['invitation_id']) is None
                or event['action'] not in
                   ('delivered','delivery_failed','cancelled','accepted')
                or type(event['occurred_at']) is not int
                or event['occurred_at']<0):
                raise RuntimeError('Unsafe invitation history item')
            previous=event['event_id']
        return obj

    @staticmethod
    def safe_cancel(obj,request):
        if (type(obj) is not dict or set(obj)!={
                'tenant_id','invitation_id','status','publishing_enabled'}
            or type(obj['tenant_id']) is not str
            or not obj['tenant_id'].strip() or len(obj['tenant_id'])>128
            or obj['invitation_id']!=request['invitation_id']
            or obj['status']!='cancelled'
            or obj['publishing_enabled'] is not False):
            raise RuntimeError('Unsafe cancellation result')
        return obj

    def __call__(self,environ,start_response):
        reply=lambda status,body:self.reply(start_response,status,body)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        path=environ.get('PATH_INFO')
        if path not in ('/api/v1/team/invitations',
                        '/api/v1/team/invitations/activity',
                        '/api/v1/team/invitations/cancel'):
            return reply('404 Not Found',{'error':'Not found'})
        method=environ.get('REQUEST_METHOD')
        if ((path in ('/api/v1/team/invitations',
                      '/api/v1/team/invitations/activity') and method!='GET') or
            (path=='/api/v1/team/invitations/cancel' and method!='POST')):
            return reply('405 Method Not Allowed',{'error':'Method not allowed'})
        if not self.enabled or self.service is None:
            return reply('503 Service Unavailable',{'error':'Invitation preview disabled'})
        try:
            header=environ.get('HTTP_AUTHORIZATION')
            if (type(header) is not str or not header.startswith('Bearer ')
                    or TOKEN.fullmatch(header[7:]) is None):
                raise PermissionError('Owner session required')
            if environ.get('QUERY_STRING'):
                raise ValueError('No client tenant fields')
            now=int(self.clock())
            if now<0: raise RuntimeError('Invalid clock')
            if path=='/api/v1/team/invitations/activity':
                return reply('200 OK',self.safe_history(
                    self.service.history_current(
                        owner_session=header[7:],now=now)))
            if method=='GET':
                return reply('200 OK',self.safe_list(
                    self.service.pending_current(
                        owner_session=header[7:],now=now)))
            request=self.parse(environ)
            return reply('200 OK',self.safe_cancel(
                self.service.cancel_current(
                    owner_session=header[7:],now=now,**request),request))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Invitation access unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Pending invitation unavailable'})
        except (ValueError,TypeError,AttributeError,UnicodeError,json.JSONDecodeError):
            return reply('400 Bad Request',{'error':'Invalid invitation request'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Invitation preview unavailable'})
