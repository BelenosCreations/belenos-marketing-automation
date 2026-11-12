"""Prepared read-only tenant queries for social metadata and private AI usage.

External provider token/vault references are NEVER selected. The current
trusted BAM actor is supplied by a future independent verified server
session. These are query contracts, not a production API or real OAuth.
"""
import re

_ID=re.compile(r'[A-Za-z0-9_-]{1,128}\Z')
_MONTH=re.compile(r'20[0-9]{2}-(?:0[1-9]|1[0-2])\Z')

_CONNECTIONS="""SELECT c.platform,c.account_id,c.scope,c.state,c.expires_at
    FROM provider_connections AS c
    JOIN members AS m ON m.tenant_id=c.tenant_id
    JOIN bam_identities AS i ON i.subject_id=m.subject_id
    WHERE c.tenant_id=%s AND m.subject_id=%s AND m.active=1
      AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager','viewer')
    ORDER BY c.platform,c.account_id LIMIT 50"""

_PERSONAL_USAGE="""SELECT u.accepted FROM bam_ai_usage AS u
    JOIN members AS m ON m.tenant_id=u.tenant_id
       AND m.subject_id=u.subject_id
    JOIN bam_identities AS i ON i.subject_id=m.subject_id
    WHERE u.tenant_id=%s AND u.subject_id=%s AND u.month=%s
      AND m.active=1 AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager',
                     'content_creator','employee','viewer')"""


def _scoped(tenant_id,subject_id):
    if (type(tenant_id) is not str or _ID.fullmatch(tenant_id) is None
            or type(subject_id) is not str or
            _ID.fullmatch(subject_id) is None):
        raise ValueError('Trusted business/session actor required')
    return (tenant_id,subject_id)

def prepare_connections_read(*,tenant_id,verified_subject_id):
    return _CONNECTIONS,_scoped(tenant_id,verified_subject_id)

def prepare_personal_ai_usage(*,tenant_id,verified_subject_id,month):
    scope=_scoped(tenant_id,verified_subject_id)
    if type(month) is not str or _MONTH.fullmatch(month) is None:
        raise ValueError('Validated accounting month required')
    return _PERSONAL_USAGE,scope+(month,)

def safe_connection_preview(row):
    """Connection *metadata* does not prove real provider authorization."""
    if type(row) not in (tuple,list) or len(row)!=5:
        raise ValueError('Invalid connection metadata')
    platform,account,scope,state,expiration=row
    if (any(type(x) is not str or not x or len(x)>128
            for x in (platform,account,scope,state))
            or expiration is not None and
                (type(expiration) is not int or expiration<0)):
        raise ValueError('Invalid connection metadata')
    return {'platform':platform,'account_id':account,
            'scope':scope,'state':state,'expires_at':expiration,
            'live_provider_verified':False,'publishing_enabled':False}
