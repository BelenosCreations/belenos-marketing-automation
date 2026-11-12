"""Non-executing owner-only team-invitation read SQL for PostgreSQL.

Caller identity must come from a trusted, verified server session. The
owner's *current* membership is checked in the same statement. These are
private metadata previews, never bearer token reads or invite delivery.
"""
import re

_SCOPED_ID=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_OWNER_PENDING_SQL="""SELECT v.invitation_id,v.email,v.role,v.expires_at
    FROM bam_business_invitations AS v
    WHERE v.tenant_id=%s
      AND v.expires_at>%s
      AND v.consumed_at IS NULL AND v.revoked_at IS NULL
      AND v.delivery_state='delivered'
      AND EXISTS (
        SELECT 1 FROM members AS m
        JOIN bam_identities AS i ON i.subject_id=m.subject_id
        WHERE m.tenant_id=v.tenant_id AND m.subject_id=%s
          AND m.active=1 AND m.role='owner'
          AND i.active=1 AND i.email_verified=1
      )
    ORDER BY v.expires_at,v.invitation_id LIMIT 50"""

def prepare_pending_owner_invitations(*,tenant_id,
                                      verified_subject_id,server_now):
    if (type(tenant_id) is not str or
            _SCOPED_ID.fullmatch(tenant_id) is None
            or type(verified_subject_id) is not str
            or _SCOPED_ID.fullmatch(verified_subject_id) is None
            or type(server_now) is not int or server_now<0):
        raise ValueError('Trusted owner membership and server time required')
    return _OWNER_PENDING_SQL,(tenant_id,server_now,verified_subject_id)
