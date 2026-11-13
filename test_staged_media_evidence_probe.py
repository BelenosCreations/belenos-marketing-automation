"""Never transform signed offline media evidence into publication rights."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from access_policy import Principal, Role
from accounts import AccountDirectory
from bam_pending_media_store import BAMPendingMediaStore
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from content_requests import ContentRequests
from content_upload_preflight import ContentUploadPreflight
from sessions import SessionStore
from staged_media_evidence_probe import probe_staged_signed_media
from synthetic_media_fixture import PNG

_SCAN = b'synthetic-scanner-worker-secret-1234567890'
_RIGHTS = b'synthetic-rights-reviewer-secret-123456789'


def signed(claim, key):
    raw = json.dumps(claim, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=True).encode('utf-8')
    return {**claim, 'signature': hmac.new(key, raw, hashlib.sha256).hexdigest()}


class StagedEvidenceProbeTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get('BAM_EPHEMERAL_PG_TEST')
        os.environ['BAM_EPHEMERAL_PG_TEST'] = '1'
        self.tmp = tempfile.TemporaryDirectory()
        self.db = sqlite3.connect(':memory:')
        self.directory = AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','otherowner')
        self.sessions = SessionStore(self.db)
        self.token = self.sessions.issue(
            Principal('owner','shop',Role.OWNER), now=100)
        self.attachments = AttachmentRegistry(self.db)
        self.requests = ContentRequests(self.db)
        self.service = ContentRequestService(
            requests=self.requests, sessions=self.sessions,
            directory=self.directory, attachments=self.attachments)
        self.rid = self.service.create(
            token=self.token, tenant_id='shop', channel='facebook',
            draft_text='Test media', suggestion='Provide image',
            required_items=['image'], now=101)
        self.pending = ContentUploadPreflight(service=self.service).begin(
            token=self.token, tenant_id='shop', request_id=self.rid,
            item='image', media_type='image/png',
            sha256=hashlib.sha256(PNG).hexdigest(),
            byte_count=len(PNG), now=101)
        self.aid = self.pending['attachment_id']
        self.store = BAMPendingMediaStore(
            service=self.service,
            storage_dir=str(Path(self.tmp.name)/'private'))
        self.store.receive(
            token=self.token, attachment_id=self.aid, content=PNG, now=102)
        binding = dict(attachment_id=self.aid, tenant_id='shop',
                       request_id=self.rid, item='image', media_type='image/png',
                       sha256=hashlib.sha256(PNG).hexdigest())
        self.scan = signed({**binding, 'kind':'scan', 'verdict':'clean',
                            'issuer':'scanner', 'engine':'synthetic',
                            'issued_at':103, 'expires_at':200}, _SCAN)
        self.rights = signed({**binding, 'kind':'rights',
                              'verdict':'authorized','issuer':'reviewer',
                              'channel':'facebook', 'basis':'owned',
                              'proof_ref':'synthetic-only',
                              'issued_at':103,'expires_at':200}, _RIGHTS)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()
        if self.prev is None:
            os.environ.pop('BAM_EPHEMERAL_PG_TEST',None)
        else:
            os.environ['BAM_EPHEMERAL_PG_TEST'] = self.prev

    def probe(self, **updates):
        opts = dict(store=self.store, tenant_id='shop',
                    attachment_id=self.aid, scan=self.scan,
                    rights=self.rights, scanner_key=_SCAN,
                    rights_key=_RIGHTS, now=110)
        opts.update(updates)
        return probe_staged_signed_media(**opts)

    def test_valid_proof_inspects_staged_bytes_but_leaves_pending(self):
        result = self.probe()
        self.assertEqual(result['status'],'staged_signed_evidence_probe_passed')
        self.assertFalse(result['media_verified'])
        self.assertFalse(result['attachment_state_changed'])
        self.assertFalse(result['audit_persisted'])
        self.assertFalse(result['publishing_enabled'])
        row = self.db.execute(
            'SELECT status FROM content_attachments WHERE attachment_id=?',
            (self.aid,)).fetchone()
        self.assertEqual(row[0],'pending')
        for secret in (_SCAN.decode(), _RIGHTS.decode(), self.aid,
                       self.rid, str(self.store.root)):
            self.assertNotIn(secret,repr(result))

    def test_tampered_staging_bytes_fail(self):
        path = self.store.root / (self.aid+'.pending')
        path.write_bytes(b'not the registered image')
        with self.assertRaises(ValueError):
            self.probe()

    def test_symlink_and_world_readable_staging_refused(self):
        path = self.store.root / (self.aid+'.pending')
        path.chmod(0o644)
        with self.assertRaises(PermissionError):
            self.probe()
        path.unlink()
        target = Path(self.tmp.name)/'outside'
        target.write_bytes(PNG)
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaises(PermissionError):
            self.probe()

    def test_foreign_or_finalized_registry_record_fail_closed(self):
        with self.assertRaises(KeyError):
            self.probe(tenant_id='other')
        self.attachments.validate_trusted(
            tenant_id='shop', attachment_id=self.aid, approved=False)
        with self.assertRaises(KeyError):
            self.probe()

    def test_closed_request_and_missing_file_fail(self):
        self.service.set_hold(
            token=self.token, tenant_id='shop', request_id=self.rid,
            status='postponed', now=105)
        with self.assertRaises(PermissionError):
            self.probe()
        self.service.set_hold(
            token=self.token, tenant_id='shop', request_id=self.rid,
            status='needs_content', now=106)
        (self.store.root/(self.aid+'.pending')).unlink()
        with self.assertRaises(PermissionError):
            self.probe()

    def test_scan_or_rights_tamper_or_wrong_channel_refused(self):
        with self.assertRaises(PermissionError):
            self.probe(scan={**self.scan, 'verdict':'changed'})
        other = {k:v for k,v in self.rights.items() if k!='signature'}
        other['channel'] = 'instagram'
        with self.assertRaises(PermissionError):
            self.probe(rights=signed(other, _RIGHTS))
        with self.assertRaises(PermissionError):
            self.probe(rights=signed(other, _SCAN))

    def test_outside_offline_ci_prohibited(self):
        os.environ.pop('BAM_EPHEMERAL_PG_TEST',None)
        with self.assertRaises(PermissionError):
            self.probe()


    def revocable_probe(self, chain=(), head='0'*64, **kwargs):
        from staged_media_evidence_probe import (
            probe_staged_signed_media_with_revocations)
        opts = dict(store=self.store, tenant_id='shop',
                    attachment_id=self.aid, scan=self.scan,
                    rights=self.rights, scanner_key=_SCAN,
                    rights_key=_RIGHTS, now=110,
                    audit_key=b'separate-synthetic-audit-secret-123456789',
                    revocation_chain=chain, expected_head=head)
        opts.update(kwargs)
        return probe_staged_signed_media_with_revocations(**opts)

    def test_revocation_aware_staged_bytes_are_still_never_approved(self):
        result = self.revocable_probe()
        self.assertEqual(result['status'],
                         'staged_signed_revocation_probe_passed')
        self.assertTrue(result['revocation_chain_checked'])
        self.assertFalse(result['media_verified'])
        self.assertFalse(result['audit_persisted'])
        self.assertFalse(result['authoritative_revocation_head_connected'])
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(self.db.execute(
            'SELECT status FROM content_attachments WHERE attachment_id=?',
            (self.aid,)).fetchone()[0], 'pending')
        self.assertNotIn(self.aid, str(result))
        self.assertNotIn(self.rid, str(result))

    def test_revoked_scan_or_rights_never_pass_staged_probe(self):
        from trusted_media_revocation import append_revocation_event
        audit = b'separate-synthetic-audit-secret-123456789'
        chain, head = append_revocation_event(
            chain=(), expected_head='0'*64, audit_key=audit,
            claim=self.scan, kind='scan', reason='scanner_recall', now=108)
        with self.assertRaises(PermissionError):
            self.revocable_probe(chain, head)
        # Independently revoke the rights claim (also tied to exact staged SHA).
        chain, head = append_revocation_event(
            chain=(), expected_head='0'*64, audit_key=audit,
            claim=self.rights, kind='rights', reason='rights_withdrawn', now=108)
        with self.assertRaises(PermissionError):
            self.revocable_probe(chain, head)
        with self.assertRaises(PermissionError):
            self.revocable_probe(chain, '0'*64)

    def test_revocable_probe_preserves_staged_inode_and_tenant_safety(self):
        with self.assertRaises(KeyError):
            self.revocable_probe(tenant_id='other')
        with self.assertRaises(ValueError):
            self.revocable_probe(expected_head='untrusted')
        path = self.store.root / (self.aid + '.pending')
        path.write_bytes(b'malicious replacement')
        with self.assertRaises(ValueError):
            self.revocable_probe()

if __name__=='__main__':
    unittest.main()
