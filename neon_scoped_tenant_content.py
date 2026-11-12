"""Read-only prepared PostgreSQL views of tenant-owned legacy draft settings.

Caller must be an independently authenticated, verified subject; this
module does NOT verify sessions or execute database operations.
"""
import re

_SCOPE=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')

_POST="""SELECT p.post_id,p.content,p.category,p.status,a.decision
    FROM tenant_posts p
    LEFT JOIN tenant_approvals a
      ON a.tenant_id=p.tenant_id AND a.post_id=p.post_id
    JOIN members m ON m.tenant_id=p.tenant_id
    JOIN bam_identities i ON i.subject_id=m.subject_id
    WHERE p.tenant_id=%s AND p.post_id=%s AND m.subject_id=%s
      AND m.active=1 AND m.role IN ('owner','marketing_manager')
      AND i.active=1 AND i.email_verified=1"""

_PREFS="""SELECT s.mode,s.timezone_name,s.weekly_json,
           s.preferred_hours_json,s.revision
    FROM scheduling_settings s
    JOIN members m ON m.tenant_id=s.tenant_id
    JOIN bam_identities i ON i.subject_id=m.subject_id
    WHERE s.tenant_id=%s AND m.subject_id=%s
      AND m.active=1 AND m.role='owner'
      AND i.active=1 AND i.email_verified=1"""


def _check(*parts):
    if any(type(x) is not str or _SCOPE.fullmatch(x) is None for x in parts):
        raise ValueError('Trusted tenant and verified identity required')


def prepare_tenant_post_review(*,tenant_id,post_id,verified_subject_id):
    _check(tenant_id,post_id,verified_subject_id)
    return _POST,(tenant_id,post_id,verified_subject_id)


def prepare_tenant_schedule_read(*,tenant_id,verified_subject_id):
    _check(tenant_id,verified_subject_id)
    return _PREFS,(tenant_id,verified_subject_id)
