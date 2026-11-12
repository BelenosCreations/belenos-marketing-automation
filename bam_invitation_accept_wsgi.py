"""Offline-only, separately enabled invitation acceptance test adapter.

This module must NEVER be deployed as a standalone/public enrollment route.
Production needs verified email enrollment, IP/global abuse protections,
TLS enforcement, CSRF-safe browser integration and operational review.
No invitation bearer token, password, Google ID token or BAM login session
is returned from this adapter. No publishing is enabled.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{20,256}\Z')
_NONCE=re.compile(r'[A-Za-z0-9_-]{20,256}\Z')
_PATHS={
    '/api/v1/team/invitations/accept-password':
        frozenset(('email','password','invitation_token')),
    '/api/v1/team/invitations/accept-google':
        frozenset(('challenge_id','id_token','invitation_token')),
}
_ROLES=frozenset(('marketing_manager','content_creator','employee','viewer'))

def _unique_json(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key]=value
    return result

def _text(value,limit):
    return type(value) is str and bool(value.strip()) and (
        len(value)<=limit and all(ord(c)>=32 for c in value))

class BAMInvitationAcceptWSGI:
    def __init__(self,api=None,*,enabled=False,clock=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean acceptance flag required')
        if enabled and (api is None or
                        getattr(api,'allow_invitation_redemption',False)
                        is not True or getattr(api,'throttle',None) is None):
            raise ValueError('Trusted invitation admission gate required')
        self.api=api
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response,status,obj):
        data=json.dumps(obj,separators=(',',':')).encode('utf-8')
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(data))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'")])
        return [data]

    @staticmethod
    def _read(environ,allowed):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('JSON content type required')
        raw_size=environ.get('CONTENT_LENGTH')
        if (type(raw_size) is not str or not raw_size.isascii()
                or not raw_size.isdecimal() or len(raw_size)>4
                or not 1<=int(raw_size)<=8192):
            raise ValueError('Bounded request required')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Body stream required')
        data=stream.read(int(raw_size))
        if type(data) is not bytes or len(data)!=int(raw_size):
            raise ValueError('Incomplete request')
        parsed=json.loads(data.decode('utf-8'),object_pairs_hook=_unique_json)
        if type(parsed) is not dict or set(parsed)!=allowed:
            raise ValueError('Unexpected invitation fields')
        if (not _text(parsed.get('invitation_token'),256)
            or _TOKEN.fullmatch(parsed['invitation_token']) is None):
            raise ValueError('Invalid invitation token')
        if 'password' in parsed:
            if (not _text(parsed.get('email'),254)
                or type(parsed.get('password')) is not str
                or not 12<=len(parsed['password'].encode('utf-8'))<=1024):
                raise ValueError('Invalid password invitation payload')
        else:
            if (type(parsed.get('challenge_id')) is not str or
                    _NONCE.fullmatch(parsed['challenge_id']) is None or
                    not _text(parsed.get('id_token'),4096)):
                raise ValueError('Invalid Google invitation payload')
        return parsed

    @staticmethod
    def _result(result):
        if (type(result) is not dict
                or set(result)!={'tenant_id','role',
                    'membership_created','publishing_enabled','session_token'}
                or not _text(result['tenant_id'],128)
                or result['role'] not in _ROLES
                or result['membership_created'] is not True
                or result['publishing_enabled'] is not False
                or result['session_token'] is not None):
            raise RuntimeError('Unsafe invitation acceptance')
        return {'membership_created':True,
                'tenant_id':result['tenant_id'],
                'role':result['role'],
                'publishing_enabled':False}

    def __call__(self,environ,start_response):
        reply=lambda status,obj:self._reply(start_response,status,obj)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        path=environ.get('PATH_INFO')
        if path not in _PATHS or not self.enabled:
            return reply('404 Not Found',{'error':'Not found'})
        if environ.get('REQUEST_METHOD')!='POST':
            return reply('405 Method Not Allowed',{'error':'Method not allowed'})
        try:
            # Never accept an existing session or a tenant/subject selector:
            # the invitation and verified identity choose the membership.
            if environ.get('QUERY_STRING') or environ.get('HTTP_AUTHORIZATION'):
                raise ValueError('Unexpected authenticated invitation request')
            body=self._read(environ,_PATHS[path])
            now=self.clock()
            if type(now) is not int and type(now) is not float:
                raise RuntimeError('Trusted clock unavailable')
            timestamp=int(now)
            if timestamp<0:
                raise RuntimeError('Trusted clock unavailable')
            invitation_token=body.pop('invitation_token')
            if path.endswith('accept-password'):
                result=self.api.redeem_invitation_password(
                    **body,token=invitation_token,server_now=timestamp)
            else:
                result=self.api.redeem_invitation_google(
                    **body,token=invitation_token,server_now=timestamp)
            return reply('200 OK',self._result(result))
        except PermissionError:
            return reply('401 Unauthorized',
                         {'error':'Invitation acceptance unavailable'})
        except (ValueError,TypeError,UnicodeError,json.JSONDecodeError,
                AttributeError,OverflowError):
            return reply('400 Bad Request',
                         {'error':'Invalid invitation request'})
        except Exception:
            return reply('503 Service Unavailable',
                         {'error':'Invitation acceptance unavailable'})
