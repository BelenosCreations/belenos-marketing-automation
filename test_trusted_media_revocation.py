"""Signed media revocation integrity and denial regressions."""
import hashlib
import hmac
import json
import unittest

from trusted_media_revocation import (
    append_revocation_event, verify_revocation_chain,
    verify_signed_media_with_revocations)

SCAN = b'synthetic-scanner-worker-secret-1234567890'
RIGHTS = b'synthetic-rights-reviewer-secret-123456789'
AUDIT = b'separate-synthetic-audit-secret-123456789'
EMPTY = '0' * 64
BINDING = {'attachment_id': 'a'*32, 'tenant_id': 'tenant-a',
           'request_id': 'request1', 'item': 'image', 'media_type': 'image/png',
           'sha256': 'f'*64}


def signed(payload, key):
    result = dict(payload)
    canonical = json.dumps(result, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=True).encode('utf-8')
    result['signature'] = hmac.new(key, canonical, hashlib.sha256).hexdigest()
    return result


class RevocationAuditTests(unittest.TestCase):
    def setUp(self):
        self.pending = {**BINDING, 'status': 'pending', 'created_at': 100}
        self.scan = signed({**BINDING, 'kind': 'scan', 'verdict': 'clean',
                            'issuer': 'scanner-worker', 'engine': 'synthetic',
                            'issued_at': 110, 'expires_at': 200}, SCAN)
        self.rights = signed({**BINDING, 'kind': 'rights',
                              'verdict': 'authorized', 'issuer': 'review-worker',
                              'basis': 'owned', 'proof_ref': 'synthetic',
                              'channel': 'facebook',
                              'issued_at': 110, 'expires_at': 200}, RIGHTS)

    def checked(self, chain=(), head=EMPTY, **kwargs):
        opts = dict(pending=self.pending, scan=self.scan, rights=self.rights,
                    channel='facebook', now=150, scanner_key=SCAN,
                    rights_key=RIGHTS, audit_key=AUDIT,
                    chain=chain, expected_head=head)
        opts.update(kwargs)
        return verify_signed_media_with_revocations(**opts)

    def revoke(self, claim, kind, chain=(), head=EMPTY, reason='operator_hold'):
        return append_revocation_event(
            chain=chain, expected_head=head, audit_key=AUDIT,
            claim=claim, kind=kind, reason=reason, now=145)

    def test_clean_empty_chain_remains_nonpublishing(self):
        result = self.checked()
        self.assertEqual(result['audit_event_count'], 0)
        self.assertFalse(result['production_ready'])
        self.assertFalse(result['actual_scanning_performed'])
        self.assertFalse(result['revocation_log_persisted'])
        self.assertNotIn('tenant-a', str(result))

    def test_scan_and_rights_revocations_block_replay(self):
        scan_chain, scan_head = self.revoke(self.scan, 'scan')
        with self.assertRaises(PermissionError):
            self.checked(scan_chain, scan_head)
        rights_chain, rights_head = self.revoke(
            self.rights, 'rights', scan_chain, scan_head, 'rights_withdrawn')
        with self.assertRaises(PermissionError):
            self.checked(rights_chain, rights_head)
        with self.assertRaises(PermissionError):
            self.revoke(self.scan, 'scan', scan_chain, scan_head)
        inspected = verify_revocation_chain(
            chain=rights_chain, audit_key=AUDIT,
            expected_head=rights_head, now=150)
        self.assertEqual(inspected['event_count'], 2)

    def test_chain_truncation_reorder_and_mutation_rejected(self):
        chain, head = self.revoke(self.scan, 'scan')
        chain, final = self.revoke(
            self.rights, 'rights', chain, head, 'rights_withdrawn')
        candidates = [(chain[:1], final), (chain[::-1], final),
                      (({**chain[0], 'reason': 'rights_withdrawn'}, chain[1]), final),
                      (chain, EMPTY)]
        for entries, anchor in candidates:
            with self.subTest(anchor=anchor, entries=entries), self.assertRaises(PermissionError):
                verify_revocation_chain(
                    chain=entries, audit_key=AUDIT,
                    expected_head=anchor, now=150)
        with self.assertRaises(PermissionError):
            verify_revocation_chain(
                chain=chain, audit_key=b'x'*32, expected_head=final, now=150)

    def test_cross_tenant_revocation_does_not_overreach(self):
        chain, head = self.revoke(self.scan, 'scan')
        other = {**BINDING, 'tenant_id': 'tenant-b'}
        alt_pending = {**other, 'status': 'pending', 'created_at': 100}
        alt_scan = signed({**{k:v for k,v in self.scan.items()
                              if k!='signature'}, 'tenant_id': 'tenant-b'}, SCAN)
        alt_rights = signed({**{k:v for k,v in self.rights.items()
                                if k!='signature'}, 'tenant_id': 'tenant-b'}, RIGHTS)
        result = self.checked(
            chain, head, pending=alt_pending, scan=alt_scan, rights=alt_rights)
        self.assertEqual(result['audit_event_count'], 1)

    def test_unpinned_invalid_claim_or_shared_worker_key_denied(self):
        with self.assertRaises(ValueError):
            self.checked(expected_head='bad')
        with self.assertRaises(ValueError):
            self.checked(audit_key=SCAN)
        with self.assertRaises(ValueError):
            self.revoke({**self.scan, 'signature': 'broken'}, 'scan')
        with self.assertRaises(ValueError):
            self.revoke(self.scan, 'rights')
        with self.assertRaises(PermissionError):
            self.checked(scan={**self.scan, 'verdict': 'unknown'})


if __name__ == '__main__':
    unittest.main()
