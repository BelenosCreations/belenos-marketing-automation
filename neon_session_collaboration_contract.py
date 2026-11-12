"""SQL-only PostgreSQL owner invitation preview tied to a real session hash.

No gateway, database connection, delivery, customer rows or hosted service.
A trusted future HTTPS gateway must separately enforce transport, origin,
CSRF, throttling and authorization of the session bearer.
"""
import hashlib
import re

_SESSION=re.compile(r'[A-Za-z0-9_-]{40,256}\Z')
_TENANT=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')

_QUERY="""SELECT v.invitation_id,v.email,v.role,v.expires_at
    FROM bam_business_invitations v
    WHERE v.tenant_id=%s AND v.expires_at>%s
      AND v.consumed_at IS NULL AND v.revoked_at IS NULL
      AND v.delivery_state='delivered'
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
              AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=v.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role AND m.role='owner'
          AND i.active=1 AND i.email_verified=1
      )
    ORDER BY v.expires_at,v.invitation_id LIMIT 50"""


def prepare_session_pending_owner_invitations(*,raw_session_token,tenant_id,
                                              server_now):
    """Produce owner-private metadata SELECT; no subject-id input or tokens."""
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(server_now) is not int
            or not 0 <= server_now < 2**63):
        raise ValueError('Server-validated owner session required')
    digest=hashlib.sha256(raw_session_token.encode('ascii')).hexdigest()
    return _QUERY,(tenant_id,server_now,digest,server_now)
