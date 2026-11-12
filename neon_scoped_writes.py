"""Review-only PostgreSQL draft-priority CAS SQL, never a publisher.

This module only generates one parameterized statement and interprets a
returned row. It does not open a connection, authenticate a session or apply
any database update. A future trusted server must verify the caller's
session, enforce roles, and test the SQL on actual Neon PostgreSQL.
"""
import re
import uuid

_DRAFT=re.compile(r'[a-f0-9]{32}\Z')
_SCOPED_ID=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')

# Write only priority metadata, not approved copy or publishable content.
# Use one atomic SQL statement with in-query active identity/membership
# verification and draft priority_token compare-and-swap.
_SQL="""UPDATE content_requests
    SET priority=%s,priority_token=%s,updated_at=%s
    WHERE tenant_id=%s AND request_id=%s AND priority_token=%s
      AND EXISTS (
        SELECT 1 FROM members AS m
        JOIN bam_identities AS i ON i.subject_id=m.subject_id
        WHERE m.tenant_id=content_requests.tenant_id
          AND m.subject_id=%s
          AND m.active=1
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator')
      )
    RETURNING priority,priority_token,revision"""


def prepare_draft_priority_cas(*,tenant_id,request_id,
                               verified_subject_id,expected_priority_token,
                               priority,server_now):
    """Trusted session actor only. Return SQL+parameters, never execute it."""
    if (type(tenant_id) is not str
            or _SCOPED_ID.fullmatch(tenant_id) is None
            or type(verified_subject_id) is not str
            or _SCOPED_ID.fullmatch(verified_subject_id) is None
            or type(request_id) is not str
            or _DRAFT.fullmatch(request_id) is None
            or type(expected_priority_token) is not str
            or _DRAFT.fullmatch(expected_priority_token) is None
            or type(priority) is not int or not -10<=priority<=10
            or type(server_now) is not int or server_now<0):
        raise ValueError('Valid current business and priority version required')
    new_token=uuid.uuid4().hex
    params=(priority,new_token,server_now,tenant_id,request_id,
            expected_priority_token,verified_subject_id)
    return _SQL,params


def priority_cas_result(row,*,expected_new_token):
    """No returned row means stale, missing or no current edit privilege."""
    if row is None:
        raise PermissionError('Draft priority update unavailable')
    if (type(row) not in (tuple,list) or len(row)!=3
            or type(expected_new_token) is not str
            or _DRAFT.fullmatch(expected_new_token) is None
            or type(row[0]) is not int or not -10<=row[0]<=10
            or row[1]!=expected_new_token
            or type(row[2]) is not int or row[2]<1):
        raise ValueError('Invalid database update receipt')
    return {'priority':row[0],'priority_token':row[1],
            'draft_revision':row[2],'status':'held_draft_only',
            'publishing_enabled':False,'posts_scheduled':0}
