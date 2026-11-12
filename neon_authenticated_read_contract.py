"""Offline trusted-session PostgreSQL SELECT contracts, not a production API.

Unlike earlier query previews this SQL accepts a bearer token, hashes it
server-side, and checks session expiration/revocation plus CURRENT identity
and tenant membership in the SAME PostgreSQL read statement. Caller must
still enforce trusted HTTPS transport, CSRF/origin, admission throttles and
any production token policy; no connection or public gateway exists here.
"""
import hashlib
import re

_TOKEN=re.compile(r'[A-Za-z0-9_-]{40,256}\Z')
_TENANT=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_REQUEST=re.compile(r'[a-f0-9]{32}\Z')

_ACCESS="""FROM sessions s
    JOIN members m ON m.tenant_id=s.tenant_id
          AND m.subject_id=s.subject_id
    JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE s.token_hash=%s AND s.tenant_id=%s
      AND s.revoked_at IS NULL AND s.expires_at>%s
      AND m.active=1 AND m.role=s.role
      AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager','content_creator',
                     'employee','viewer')"""

_DRAFT_SQL="""SELECT c.request_id,c.channel,c.draft_text,c.status,c.revision
    FROM content_requests c
    JOIN sessions s ON s.tenant_id=c.tenant_id
    JOIN members m ON m.tenant_id=s.tenant_id
          AND m.subject_id=s.subject_id
    JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE s.token_hash=%s AND s.tenant_id=%s
      AND c.request_id=%s AND s.revoked_at IS NULL
      AND s.expires_at>%s AND m.active=1 AND m.role=s.role
      AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager','content_creator',
                     'employee','viewer')"""

_CALENDAR_SQL="""SELECT p.request_id,p.utc_at,p.draft_revision,p.proposal_token
    FROM bam_calendar_proposals p
    JOIN sessions s ON s.tenant_id=p.tenant_id
    JOIN members m ON m.tenant_id=s.tenant_id
          AND m.subject_id=s.subject_id
    JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE s.token_hash=%s AND s.tenant_id=%s
      AND p.request_id=%s AND s.revoked_at IS NULL
      AND s.expires_at>%s AND m.active=1 AND m.role=s.role
      AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager','content_creator',
                     'employee','viewer')"""


def _params(*,raw_session_token,tenant_id,request_id,server_now):
    if (type(raw_session_token) is not str
            or _TOKEN.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(request_id) is not str
            or _REQUEST.fullmatch(request_id) is None
            or type(server_now) is not int or server_now<0):
        raise ValueError('Server-validated session context required')
    digest=hashlib.sha256(raw_session_token.encode('ascii')).hexdigest()
    return digest,tenant_id,request_id,server_now


def prepare_session_draft_read(*,raw_session_token,tenant_id,
                               request_id,server_now):
    """Produces a strict read-only, credential-hash-bound SELECT."""
    return _DRAFT_SQL,_params(raw_session_token=raw_session_token,
        tenant_id=tenant_id,request_id=request_id,server_now=server_now)


def prepare_session_calendar_read(*,raw_session_token,tenant_id,
                                  request_id,server_now):
    """Only returns held, non-executable calendar proposal metadata."""
    return _CALENDAR_SQL,_params(raw_session_token=raw_session_token,
        tenant_id=tenant_id,request_id=request_id,server_now=server_now)
