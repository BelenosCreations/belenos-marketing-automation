"""Offline contract for TWO independent authenticated media attestations.

Neither malware scanning nor rights review is performed by this module. A
trusted storage/scanner worker and a separate authorized rights-review process
must provide independently signed claims about bytes actually inspected.
This pure validator is not wired to an upload, status transition or publishing.
"""
import hashlib
import hmac
import json
import re

_BINDING=('attachment_id','tenant_id','request_id','item','media_type','sha256')
_COMMON=set(_BINDING)|{'kind','verdict','issuer','issued_at','expires_at','signature'}
_SCAN_FIELDS=_COMMON|{'engine'}
_RIGHTS_FIELDS=_COMMON|{'channel','basis','proof_ref'}
_ALLOWED_MEDIA={'image/jpeg','image/png','image/webp','video/mp4',
                'text/plain','application/pdf'}
_ALLOWED_CHANNELS={'facebook','instagram','linkedin','pinterest','tiktok'}
_MAX_AGE=24*60*60


def _canonical(claim):
    return json.dumps({k:v for k,v in claim.items() if k!='signature'},
                      sort_keys=True,separators=(',',':'),
                      ensure_ascii=True).encode('utf-8')


def _small_string(value):
    return type(value) is str and 0<len(value)<=128 and value.strip()==value


class OfflineMediaEvidenceGate:
    """Fail-closed signed-claim verifier; use only trusted server-side keys.

    The caller must load the pending attachment from an authenticated database,
    not client-supplied fields. No signing keys are stored or generated here.
    HMAC proves claimed provenance, not that a scanner ran or a license exists.
    """

    def __init__(self,*,scanner_key,rights_key):
        if (type(scanner_key) is not bytes or len(scanner_key)<32
                or type(rights_key) is not bytes or len(rights_key)<32
                or hmac.compare_digest(scanner_key,rights_key)):
            raise ValueError('Distinct trusted 32-byte worker keys required')
        self._scanner_key=scanner_key
        self._rights_key=rights_key

    @staticmethod
    def _check_pending(pending):
        if (type(pending) is not dict
                or not set(_BINDING).issubset(pending)
                or pending.get('status')!='pending'
                or type(pending.get('created_at')) is not int
                or pending['created_at']<0):
            raise ValueError('Current pending registry record required')
        if (type(pending['attachment_id']) is not str or
                not re.fullmatch('[0-9a-f]{32}',pending['attachment_id'])
                or type(pending['sha256']) is not str or
                not re.fullmatch('[0-9a-f]{64}',pending['sha256'])
                or type(pending['item']) is not str or
                not re.fullmatch('[a-z][a-z0-9_-]{0,63}',pending['item'])
                or pending['media_type'] not in _ALLOWED_MEDIA
                or not _small_string(pending['tenant_id'])
                or not _small_string(pending['request_id'])):
            raise ValueError('Malformed attachment registry binding')

    @staticmethod
    def _check_claim(claim,*,fields,kind,pending,now,key):
        if type(claim) is not dict or set(claim)!=fields:
            raise ValueError('Unexpected evidence claim shape')
        for field in _BINDING:
            if type(claim[field]) is not str or claim[field]!=pending[field]:
                raise PermissionError('Evidence attachment binding mismatch')
        if (claim['kind']!=kind or not _small_string(claim['issuer'])
                or type(claim['issued_at']) is not int
                or type(claim['expires_at']) is not int
                or claim['issued_at']<pending['created_at']
                or claim['issued_at']>now
                or not now<claim['expires_at']
                or claim['expires_at']-claim['issued_at']>_MAX_AGE):
            raise PermissionError('Untrusted or stale media evidence')
        signature=claim['signature']
        if (type(signature) is not str
                or not re.fullmatch('[0-9a-f]{64}',signature)):
            raise PermissionError('Invalid media evidence signature')
        expected=hmac.new(key,_canonical(claim),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,signature):
            raise PermissionError('Media evidence signature mismatch')

    def verify(self,*,pending,scan,rights,channel,now):
        """Evaluate signed evidence without changing any media state."""
        if type(now) is not int or now<0 or channel not in _ALLOWED_CHANNELS:
            raise ValueError('Invalid offline verification context')
        self._check_pending(pending)
        self._check_claim(scan,fields=_SCAN_FIELDS,kind='scan',
                          pending=pending,now=now,key=self._scanner_key)
        self._check_claim(rights,fields=_RIGHTS_FIELDS,kind='rights',
                          pending=pending,now=now,key=self._rights_key)
        if scan['verdict']!='clean' or not _small_string(scan['engine']):
            raise PermissionError('Trusted clean scan claim absent')
        if (rights['verdict']!='authorized'
                or rights['channel']!=channel
                or rights['basis'] not in ('owned','licensed')
                or not _small_string(rights['proof_ref'])):
            raise PermissionError('Trusted channel-specific rights claim absent')
        return {'status':'offline_evidence_contract_passed',
                'actual_scanning_performed':False,
                'actual_rights_review_performed':False,
                'attachment_state_changed':False,
                'production_ready':False,
                'publishing_enabled':False}
