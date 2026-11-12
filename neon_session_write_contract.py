"""SQL-only, token-authenticated PostgreSQL draft-priority compare-and-swap.

No database connection, HTTP API, content publication or paid service.
Production use requires a separately approved secure gateway and DB adapter.
"""
import hashlib
import re
import uuid
from neon_scoped_writes import priority_cas_result

_SESSION = re.compile(r'[A-Za-z0-9_-]{40,256}\Z')
_TENANT = re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_TOKEN = re.compile(r'[a-f0-9]{32}\Z')

_SQL = """UPDATE content_requests
    SET priority=%s,priority_token=%s,updated_at=%s
    WHERE tenant_id=%s AND request_id=%s AND priority_token=%s
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
              AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s
          AND s.tenant_id=content_requests.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator')
      )
    RETURNING priority,priority_token,revision"""


def prepare_session_priority_cas(*, raw_session_token, tenant_id,
                                 request_id, expected_priority_token,
                                 priority, server_now):
    """Only priority metadata can change; never trusts a client subject ID.

    Missing/stale/revoked/other-business/unauthorized updates return no row.
    This builder does not execute the statement or enable publishing.
    """
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(request_id) is not str
            or _TOKEN.fullmatch(request_id) is None
            or type(expected_priority_token) is not str
            or _TOKEN.fullmatch(expected_priority_token) is None
            or type(priority) is not int or not -10 <= priority <= 10
            or type(server_now) is not int or not 0 <= server_now < 2**63):
        raise ValueError('Current trusted session and draft version required')
    digest = hashlib.sha256(raw_session_token.encode('ascii')).hexdigest()
    new_token = uuid.uuid4().hex
    return _SQL, (priority, new_token, server_now, tenant_id, request_id,
                  expected_priority_token, digest, server_now)


__all__ = ['prepare_session_priority_cas', 'priority_cas_result']
