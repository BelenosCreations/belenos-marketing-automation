"""Offline-only authenticated revocation audit for signed media evidence.

Independent HMAC-chained revocations bind to an entire signed scan or
rights claim. The caller MUST independently pin the latest audit head.
This does not operate a scanner, conduct rights review, persist an audit log,
authorize attachment state transitions or publish content.
"""
import hashlib
import hmac
import json
import re

from trusted_media_evidence import OfflineMediaEvidenceGate

_SHA = re.compile(r'[0-9a-f]{64}\Z')
_REASONS = frozenset(('scanner_recall', 'rights_withdrawn',
                      'issuer_compromised', 'operator_hold'))
_FIELDS = frozenset(('sequence', 'issued_at', 'kind', 'reason',
                     'claim_sha256', 'previous_mac', 'mac'))
_EMPTY_HEAD = '0' * 64
_MAX_EVENTS = 256


def _key(key):
    if type(key) is not bytes or len(key) < 32:
        raise ValueError('Independently controlled 32-byte audit key required')


def _sha(value):
    return type(value) is str and _SHA.fullmatch(value) is not None


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True).encode('ascii')


def _claim_sha256(claim):
    if (type(claim) is not dict or not _sha(claim.get('signature'))):
        raise ValueError('Signed claim required for revocation')
    return hashlib.sha256(_canonical(claim)).hexdigest()


def _mac(event, key):
    return hmac.new(key, _canonical({k: v for k, v in event.items()
                                     if k != 'mac'}), hashlib.sha256).hexdigest()


def verify_revocation_chain(*, chain, audit_key, expected_head, now):
    """Validate EVERY event and a separately supplied current-head pin.

    Returning an empty-chain result is not proof that no revocations exist:
    only an authoritative, independently maintained head can establish that.
    """
    _key(audit_key)
    if (type(now) is not int or now < 0 or
            not _sha(expected_head) or type(chain) not in (tuple, list)
            or len(chain) > _MAX_EVENTS):
        raise ValueError('Invalid bounded revocation audit context')
    previous = _EMPTY_HEAD
    prior_time = 0
    revoked = set()
    for number, event in enumerate(chain, 1):
        if type(event) is not dict or set(event) != _FIELDS:
            raise PermissionError('Invalid revocation event shape')
        digest = event['claim_sha256']
        if (type(event['sequence']) is not int
                or event['sequence'] != number
                or type(event['issued_at']) is not int
                or not prior_time <= event['issued_at'] <= now
                or event['kind'] not in ('scan', 'rights')
                or event['reason'] not in _REASONS
                or not _sha(digest) or digest in revoked
                or event['previous_mac'] != previous
                or not _sha(event['mac'])):
            raise PermissionError('Revocation event order or binding mismatch')
        expected = _mac(event, audit_key)
        if not hmac.compare_digest(event['mac'], expected):
            raise PermissionError('Revocation audit authentication failed')
        revoked.add(digest)
        previous = event['mac']
        prior_time = event['issued_at']
    if not hmac.compare_digest(previous, expected_head):
        raise PermissionError('Revocation head does not match independent pin')
    return {'head': previous, 'event_count': len(chain),
            'revoked_claim_hashes': frozenset(revoked)}


def append_revocation_event(*, chain, expected_head, audit_key, claim,
                            kind, reason, now):
    """Pure event builder; trusted caller must durably and externally pin head."""
    inspected = verify_revocation_chain(
        chain=chain, audit_key=audit_key, expected_head=expected_head, now=now)
    if kind not in ('scan', 'rights') or reason not in _REASONS:
        raise ValueError('Invalid revocation category')
    if len(chain) >= _MAX_EVENTS:
        raise PermissionError('Offline revocation ledger capacity exceeded')
    digest = _claim_sha256(claim)
    if claim.get('kind') != kind:
        raise ValueError('Revocation kind does not match signed claim')
    if digest in inspected['revoked_claim_hashes']:
        raise PermissionError('Signed claim already revoked')
    event = {'sequence': len(chain) + 1, 'issued_at': now, 'kind': kind,
             'reason': reason, 'claim_sha256': digest,
             'previous_mac': inspected['head']}
    event['mac'] = _mac(event, audit_key)
    return tuple(chain) + (event,), event['mac']


def verify_signed_media_with_revocations(*, pending, scan, rights, channel,
                                          now, scanner_key, rights_key,
                                          audit_key, chain, expected_head):
    """Demand valid independent worker signatures AND non-revoked evidence."""
    _key(audit_key)
    if (type(scanner_key) is not bytes or type(rights_key) is not bytes
            or hmac.compare_digest(audit_key, scanner_key)
            or hmac.compare_digest(audit_key, rights_key)):
        raise ValueError('Audit and issuing keys must remain distinct')
    OfflineMediaEvidenceGate(
        scanner_key=scanner_key, rights_key=rights_key).verify(
            pending=pending, scan=scan, rights=rights, channel=channel, now=now)
    ledger = verify_revocation_chain(
        chain=chain, audit_key=audit_key, expected_head=expected_head, now=now)
    if (_claim_sha256(scan) in ledger['revoked_claim_hashes']
            or _claim_sha256(rights) in ledger['revoked_claim_hashes']):
        raise PermissionError('Signed media evidence has been revoked')
    return {'status': 'offline_media_evidence_and_revocations_checked',
            'audit_event_count': ledger['event_count'],
            'actual_scanning_performed': False,
            'actual_rights_review_performed': False,
            'revocation_log_persisted': False,
            'authoritative_head_service_connected': False,
            'attachment_state_changed': False,
            'production_ready': False,
            'publishing_enabled': False}
