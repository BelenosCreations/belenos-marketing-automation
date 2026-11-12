"""Owner-private PostgreSQL team roster SELECT for disposable CI fixtures.

Matches the existing offline team's read-only roster contract. Never grants
membership, changes roles, sends invitations or opens a database connection.
A production gateway and separately approved migrations do not exist here.
"""
import hashlib
import re

_SESSION=re.compile(r'[A-Za-z0-9_-]{40,256}\Z')
_TENANT=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_MEMBER=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_ROLES=frozenset(('owner','marketing_manager','content_creator',
                  'employee','viewer'))

_SQL="""SELECT m.subject_id,m.role,m.active,m.revision,i.email,
                 CASE WHEN m.subject_id=s.subject_id THEN 1 ELSE 0 END
    FROM sessions s
    JOIN members actor ON actor.tenant_id=s.tenant_id
          AND actor.subject_id=s.subject_id
    JOIN bam_identities auth ON auth.subject_id=s.subject_id
    JOIN members m ON m.tenant_id=s.tenant_id
    LEFT JOIN bam_identities i ON i.subject_id=m.subject_id
          AND i.active=1 AND i.email_verified=1
    WHERE s.token_hash=%s AND s.tenant_id=%s
      AND s.revoked_at IS NULL AND s.expires_at>%s
      AND actor.active=1 AND actor.role=s.role AND actor.role='owner'
      AND auth.active=1 AND auth.email_verified=1
    ORDER BY CASE WHEN m.subject_id=s.subject_id THEN 0 ELSE 1 END,
             m.active DESC,m.role,m.subject_id LIMIT 201"""


def prepare_session_owner_team_roster(*,raw_session_token,tenant_id,server_now):
    """SELECT scope comes entirely from the current owner session and tenant."""
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(server_now) is not int
            or not 0<=server_now<2**63):
        raise ValueError('Current trusted owner session required')
    digest=hashlib.sha256(raw_session_token.encode('ascii')).hexdigest()
    return _SQL,(digest,tenant_id,server_now)


def summarize_owner_team_roster(rows,*,tenant_id):
    """Return only owner-private roster metadata; fail closed on bad rows.

    201 rows are intentionally requested so that >200 is detected rather than
    silently truncating a team or hiding owner membership. Large-team paging
    requires a separately tested contract, matching the offline behavior.
    """
    if (type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(rows) not in (tuple,list)):
        raise ValueError('Unexpected private team roster')
    if len(rows)>200:
        raise RuntimeError('Team directory requires pagination')
    members=[]
    seen=set()
    self_count=0
    for row in rows:
        if (type(row) not in (tuple,list) or len(row)!=6
                or type(row[0]) is not str
                or _MEMBER.fullmatch(row[0]) is None
                or row[0] in seen
                or type(row[1]) is not str or row[1] not in _ROLES
                or type(row[2]) is not int or row[2] not in (0,1)
                or type(row[3]) is not int or row[3]<1
                or (row[4] is not None and (
                    type(row[4]) is not str or len(row[4])>254))
                or type(row[5]) is not int or row[5] not in (0,1)):
            raise ValueError('Invalid team member metadata')
        is_self=bool(row[5])
        if is_self and (not row[2] or row[1]!='owner'):
            raise ValueError('Current owner cannot be inactive')
        seen.add(row[0])
        self_count+=int(is_self)
        members.append({'member_id':row[0],'role':row[1],
                        'active':bool(row[2]),'revision':row[3],
                        'email':row[4],'is_self':is_self})
    if self_count!=1:
        # Missing owner means authorization failed or source response changed:
        # do not misrepresent it as an empty team.
        raise PermissionError('Current owner roster unavailable')
    return {'tenant_id':tenant_id,'status':'private_team_preview',
            'members':members,'publishing_enabled':False}
