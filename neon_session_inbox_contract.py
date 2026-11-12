"""Session-authenticated, keyset-paginated held-draft inbox (SQL only).

No customer connection, API endpoint, scheduler, approval or social publish.
Every statement verifies the current session, identity and tenant membership
in PostgreSQL; the bearer is hashed before it reaches SQL parameters.
"""
import hashlib
import re

from neon_scoped_queries import summarize_held_draft_row

_SESSION=re.compile(r'[A-Za-z0-9_-]{40,256}\Z')
_TENANT=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_REQUEST=re.compile(r'[a-f0-9]{32}\Z')
_STATUSES=frozenset(('needs_content','ready_for_review',
                     'postponed','unavailable'))

_BASE="""SELECT c.request_id,c.channel,c.draft_text,c.status,c.revision,
           c.created_at
    FROM content_requests c
    WHERE c.tenant_id=%s
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
              AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=c.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator',
                         'employee','viewer')
      )"""


def prepare_session_inbox_page(*,raw_session_token,tenant_id,server_now,
                               limit=20,after_created_at=None,
                               after_request_id=None,status=None):
    """Return one bounded, deterministic SELECT, never an executable post.

    Cursor is (created_at, request_id), not a mutable priority/version.
    A forged cursor cannot expand the tenant/session visibility boundary.
    Request limit + 1 rows to determine whether another page exists.
    """
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(server_now) is not int
            or not 0<=server_now<2**63
            or type(limit) is not int or not 1<=limit<=50
            or (status is not None and (
                type(status) is not str or status not in _STATUSES))):
        raise ValueError('Valid current session and bounded inbox query required')
    if (after_created_at is None)!=(after_request_id is None):
        raise ValueError('Incomplete inbox cursor')
    if after_created_at is not None and (
            type(after_created_at) is not int
            or not 0<=after_created_at<2**63
            or type(after_request_id) is not str
            or _REQUEST.fullmatch(after_request_id) is None):
        raise ValueError('Invalid inbox cursor')
    digest=hashlib.sha256(raw_session_token.encode('ascii')).hexdigest()
    sql=_BASE
    params=[tenant_id,digest,server_now]
    if status is not None:
        sql+=' AND c.status=%s'
        params.append(status)
    if after_created_at is not None:
        sql+=' AND (c.created_at,c.request_id)>(%s,%s)'
        params.extend((after_created_at,after_request_id))
    sql+=' ORDER BY c.created_at ASC,c.request_id ASC LIMIT %s'
    params.append(limit+1)
    return sql,tuple(params)


def summarize_inbox_page(rows,*,limit):
    """Map only held draft rows and expose a bounded, opaque-ish cursor."""
    if (type(limit) is not int or not 1<=limit<=50
            or type(rows) not in (tuple,list) or len(rows)>limit+1):
        raise ValueError('Unexpected inbox page')
    items=[]
    previous=None
    for row in rows:
        if (type(row) not in (tuple,list) or len(row)!=6
                or type(row[5]) is not int
                or not 0<=row[5]<2**63):
            raise ValueError('Unexpected inbox draft metadata')
        key=(row[5],row[0])
        if previous is not None and key<=previous:
            raise ValueError('Unordered inbox query result')
        previous=key
        draft=summarize_held_draft_row(row[:5])
        draft['created_at']=row[5]
        items.append(draft)
    has_more=len(items)>limit
    visible=items[:limit]
    last=visible[-1] if has_more else None
    return {'status':'held_draft_inbox_only','items':visible,
            'has_more':has_more,
            'next_cursor':({'created_at':last['created_at'],
                            'request_id':last['request_id']}
                           if last else None),
            'publishing_enabled':False,'posts_scheduled':0}
