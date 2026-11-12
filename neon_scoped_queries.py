"""Review-only, parameterized PostgreSQL tenant read-query contracts.

Trusted server must FIRST validate the session and establish the actor
identity. The SQL deliberately rechecks current verified identity and active
membership in the SAME read query to prevent stale/removed role privileges.
This module never opens a DB, fetches data, authenticates users or publishes.
"""
import re

_ID=re.compile(r'[a-f0-9]{32}\Z')
_TENANT=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_ROLE_CLAUSE="""('owner','marketing_manager','content_creator',
                   'employee','viewer')"""

_DRAFT_SQL="""SELECT c.request_id,c.channel,c.draft_text,c.status,c.revision
    FROM content_requests AS c
    JOIN members AS m ON m.tenant_id=c.tenant_id
    JOIN bam_identities AS i ON i.subject_id=m.subject_id
    WHERE c.tenant_id=%s AND c.request_id=%s
      AND m.subject_id=%s AND m.active=1
      AND i.active=1 AND i.email_verified=1
      AND m.role IN """+_ROLE_CLAUSE

_CALENDAR_SQL="""SELECT p.request_id,p.utc_at,p.draft_revision,p.proposal_token
    FROM bam_calendar_proposals AS p
    JOIN members AS m ON m.tenant_id=p.tenant_id
    JOIN bam_identities AS i ON i.subject_id=m.subject_id
    WHERE p.tenant_id=%s AND p.request_id=%s
      AND m.subject_id=%s AND m.active=1
      AND i.active=1 AND i.email_verified=1
      AND m.role IN """+_ROLE_CLAUSE


def _scope(*,tenant_id,request_id,verified_subject_id):
    if (type(tenant_id) is not str or
            _TENANT.fullmatch(tenant_id) is None or
            type(request_id) is not str or
            _ID.fullmatch(request_id) is None or
            type(verified_subject_id) is not str or
            _TENANT.fullmatch(verified_subject_id) is None):
        raise ValueError('Trusted tenant, member and draft IDs required')
    return (tenant_id,request_id,verified_subject_id)


def draft_select_for_verified_member(*,tenant_id,request_id,verified_subject_id):
    """Return prepared statement + params; no DB execution capability."""
    return _DRAFT_SQL, _scope(tenant_id=tenant_id,request_id=request_id,
                             verified_subject_id=verified_subject_id)


def calendar_select_for_verified_member(*,tenant_id,request_id,
                                        verified_subject_id):
    """Only reads held proposals: not an executable scheduling query."""
    return _CALENDAR_SQL, _scope(tenant_id=tenant_id,request_id=request_id,
                                 verified_subject_id=verified_subject_id)


def summarize_held_draft_row(row):
    """Explicitly non-publishing output mapping; no permissions assumed."""
    if row is None:
        return None
    if (type(row) not in (tuple,list) or len(row)!=5
            or type(row[0]) is not str or _ID.fullmatch(row[0]) is None
            or type(row[1]) is not str or not row[1]
            or type(row[2]) is not str
            or row[3] not in (
                'needs_content','ready_for_review','postponed','unavailable')
            or type(row[4]) is not int or row[4]<1):
        raise ValueError('Unexpected held draft row')
    return {'request_id':row[0],'channel':row[1],
            'draft_text':row[2],'status':row[3],
            'revision':row[4],'publishing_enabled':False,
            'posts_scheduled':0}


def summarize_calendar_row(row):
    if row is None:
        return None
    if (type(row) not in (tuple,list) or len(row)!=4
            or type(row[0]) is not str or _ID.fullmatch(row[0]) is None
            or type(row[1]) is not str
            or type(row[2]) is not int or row[2]<1
            or type(row[3]) is not str or _ID.fullmatch(row[3]) is None):
        raise ValueError('Unexpected calendar proposal row')
    return {'request_id':row[0],'utc_at':row[1],
            'draft_revision':row[2],'proposal_token':row[3],
            'status':'proposal_only','publishing_enabled':False,
            'posts_scheduled':0}
