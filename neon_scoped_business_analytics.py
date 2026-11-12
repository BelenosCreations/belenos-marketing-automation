"""Non-executing, strictly tenant-scoped PostgreSQL reporting queries.

The future server, not clients, must resolve verified_subject_id from an
authenticated session. These return private research and synthetic metrics
only; no real analytics connector, competitor scraper or approval endpoint.
"""
import re

_SCOPE=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')

_SOURCES="""SELECT s.source_url,s.source_name,s.topic,s.approved
    FROM business_sources s
    JOIN members m ON m.tenant_id=s.tenant_id
    JOIN bam_identities i ON i.subject_id=m.subject_id
    WHERE s.tenant_id=%s AND m.subject_id=%s
      AND m.active=1 AND m.role IN ('owner','marketing_manager')
      AND i.active=1 AND i.email_verified=1
    ORDER BY s.source_url LIMIT 100"""

_AUDIENCE="""SELECT o.source_post_id,o.candidate,
         o.engagement_rate,o.measured_at
    FROM audience_observations o
    JOIN members m ON m.tenant_id=o.tenant_id
    JOIN bam_identities i ON i.subject_id=m.subject_id
    WHERE o.tenant_id=%s AND o.platform=%s AND m.subject_id=%s
      AND m.active=1 AND m.role='owner'
      AND i.active=1 AND i.email_verified=1
    ORDER BY o.measured_at DESC,o.source_post_id LIMIT 100"""


def _check(*values):
    if any(type(value) is not str or _SCOPE.fullmatch(value) is None
           for value in values):
        raise ValueError('Trusted scope and verified session actor required')


def prepare_business_sources_read(*,tenant_id,verified_subject_id):
    _check(tenant_id,verified_subject_id)
    return _SOURCES,(tenant_id,verified_subject_id)


def prepare_private_audience_read(*,tenant_id,platform,verified_subject_id):
    _check(tenant_id,platform,verified_subject_id)
    return _AUDIENCE,(tenant_id,platform,verified_subject_id)
