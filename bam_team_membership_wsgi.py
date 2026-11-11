"""Disabled-by-default owner-only offline team management transport.

HTTPS, strict JSON and a current BAM owner session are mandatory.
Only list/role-change/deactivate *existing* members. No client tenant claim,
invitation dispatch, owner transfer, new member enrollment or publishing.
"""
import json
import re
import time

_TOKEN=re.compile(r'[A-Za-z0-9_-]{32,2048}\Z')
_MEMBER=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_ROLES=frozenset(('owner','marketing_manager','content_creator','employee','viewer'))
_ACTIONS=frozenset(('change_role','deactivate'))
_PATHS=frozenset(('/api/v1/team/members','/api/v1/team/membership'))

def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key]=value
    return result


class BAMTeamMembershipWSGI:
    def __init__(self, service=None, *, enabled=False, clock=None):
        if type(enabled) is not bool:
            raise ValueError('Explicit boolean enabled switch required')
        self.service=service
        self.enabled=enabled
        self.clock=time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted clock required')

    @staticmethod
    def _reply(start_response,status,data):
        raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode('utf-8')
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
    def _body(environ):
        if environ.get('CONTENT_TYPE')!='application/json':
            raise ValueError('Strict JSON required')
        n=environ.get('CONTENT_LENGTH')
        if (type(n) is not str or not n.isascii() or not n.isdecimal()
                or len(n)>4 or not 1<=int(n)<=2048):
            raise ValueError('Invalid content size')
        stream=environ.get('wsgi.input')
        if stream is None:
            raise ValueError('Missing body')
        raw=stream.read(int(n))
        if type(raw) is not bytes or len(raw)!=int(n):
            raise ValueError('Incorrect content size')
        data=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
        if type(data) is not dict:
            raise ValueError('JSON object required')
        if data.get('action') not in _ACTIONS:
            raise ValueError('Invalid membership action')
        required=({'member_id','action','role','expected_revision'}
                  if data['action']=='change_role'
                  else {'member_id','action','expected_revision'})
        if (set(data)!=required or
                type(data['member_id']) is not str or
                _MEMBER.fullmatch(data['member_id']) is None or
                type(data['expected_revision']) is not int or
                data['expected_revision']<1):
            raise ValueError('Unexpected member fields')
        if data['action']=='change_role' and (
                type(data['role']) is not str or
                data['role'] not in _ROLES-{'owner'}):
            raise ValueError('Non-owner role required')
        return data

    @staticmethod
    def _safe_roster(value):
        if (type(value) is not dict or set(value)!={
                'tenant_id','status','members','publishing_enabled'} or
                type(value['tenant_id']) is not str or
                not value['tenant_id'].strip() or
                len(value['tenant_id'])>128 or
                value['status']!='private_team_preview' or
                type(value['members']) is not list or
                not 1<=len(value['members'])<=200 or
                value['publishing_enabled'] is not False):
            raise RuntimeError('Invalid private team roster')
        seen=set()
        owners=0
        for member in value['members']:
            if (type(member) is not dict or set(member)!={
                    'member_id','role','active','revision','email','is_self'} or
                    type(member['member_id']) is not str or
                    _MEMBER.fullmatch(member['member_id']) is None or
                    member['member_id'] in seen or
                    member['role'] not in _ROLES or
                    type(member['active']) is not bool or
                    type(member['is_self']) is not bool or
                    type(member['revision']) is not int or
                    member['revision']<1 or
                    (member['email'] is not None and (
                        type(member['email']) is not str or
                        len(member['email'])>254))):
                raise RuntimeError('Invalid team member response')
            seen.add(member['member_id'])
            if member['is_self'] and (not member['active'] or member['role']!='owner'):
                raise RuntimeError('Invalid team self identity')
            owners+=int(member['is_self'])
        if owners!=1:
            raise RuntimeError('Invalid owner roster')
        return value

    @staticmethod
    def _safe_mutation(value,requested):
        if (type(value) is not dict or set(value)!={
                'tenant_id','member_id','status','revision','sessions_revoked',
                'publishing_enabled'} or
                type(value['tenant_id']) is not str or
                not value['tenant_id'].strip() or
                len(value['tenant_id'])>128 or
                value['member_id']!=requested['member_id'] or
                value['status']!=(
                    'updated' if requested['action']=='change_role'
                    else 'deactivated') or
                type(value['revision']) is not int or
                value['revision']!=requested['expected_revision']+1 or
                type(value['sessions_revoked']) is not int or
                not 0<=value['sessions_revoked']<=100000 or
                value['publishing_enabled'] is not False):
            raise RuntimeError('Invalid private team mutation')
        return value

    def __call__(self,environ,start_response):
        reply=lambda status,data:self._reply(start_response,status,data)
        if environ.get('wsgi.url_scheme')!='https':
            return reply('403 Forbidden',{'error':'HTTPS required'})
        path=environ.get('PATH_INFO')
        if path not in _PATHS:
            return reply('404 Not Found',{'error':'Not found'})
        method=environ.get('REQUEST_METHOD')
        if ((path=='/api/v1/team/members' and method!='GET') or
                (path=='/api/v1/team/membership' and method!='POST')):
            return reply('405 Method Not Allowed',{'error':'Method not allowed'})
        if not self.enabled or self.service is None:
            return reply('503 Service Unavailable',{'error':'Team management disabled'})
        try:
            header=environ.get('HTTP_AUTHORIZATION')
            if (type(header) is not str or
                    not header.startswith('Bearer ') or
                    _TOKEN.fullmatch(header[7:]) is None):
                raise PermissionError('BAM owner session required')
            if environ.get('QUERY_STRING'):
                raise ValueError('Team query fields not accepted')
            now=int(self.clock())
            if now<0:
                raise RuntimeError('Invalid trusted clock')
            if method=='GET':
                result=self.service.list_current(token=header[7:],now=now)
                return reply('200 OK',self._safe_roster(result))
            data=self._body(environ)
            result=self.service.change_current(
                token=header[7:],now=now,**data)
            return reply('200 OK',self._safe_mutation(result,data))
        except PermissionError:
            return reply('401 Unauthorized',{'error':'Team access unavailable'})
        except KeyError:
            return reply('404 Not Found',{'error':'Business member unavailable'})
        except ValueError as exc:
            if str(exc)=='Stale team membership revision':
                return reply('409 Conflict',{'error':'Member changed; refresh required'})
            return reply('400 Bad Request',{'error':'Invalid team request'})
        except (TypeError,AttributeError,UnicodeError,json.JSONDecodeError):
            return reply('400 Bad Request',{'error':'Invalid team request'})
        except Exception:
            return reply('503 Service Unavailable',{'error':'Team service unavailable'})
