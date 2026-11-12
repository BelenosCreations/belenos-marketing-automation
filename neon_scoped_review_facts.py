"""Read-only verified-fact PostgreSQL query; never an approval/publisher.

The future backend must derive verified_subject_id from its trusted session
and independently verify scope. This SQL checks CURRENT business membership
and excludes revoked or expired facts in the same read.
"""
import re

_SCOPE=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')

_SQL="""SELECT f.fact_id,f.claim_key,f.value,f.source,f.approved_at
    FROM truthguard_facts f
    JOIN members m ON m.tenant_id=f.tenant_id
    JOIN bam_identities i ON i.subject_id=m.subject_id
    WHERE f.tenant_id=%s AND m.subject_id=%s
      AND m.active=1 AND m.role IN ('owner','marketing_manager')
      AND i.active=1 AND i.email_verified=1
      AND f.revoked_at IS NULL
      AND (f.expires_at IS NULL OR f.expires_at>%s)
    ORDER BY f.approved_at DESC,f.fact_id LIMIT 100"""


def prepare_current_private_facts(*,tenant_id,verified_subject_id,server_now):
    if (type(tenant_id) is not str or _SCOPE.fullmatch(tenant_id) is None
            or type(verified_subject_id) is not str
            or _SCOPE.fullmatch(verified_subject_id) is None
            or type(server_now) is not int or server_now<0):
        raise ValueError('Trusted verified identity and server time required')
    return _SQL,(tenant_id,verified_subject_id,server_now)
