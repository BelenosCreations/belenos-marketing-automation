"""Disposable typed attachment rehearsal using synthetic rows and PNG bytes."""
from contextlib import closing
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from synthetic_media_fixture import PNG
from trusted_media_evidence import OfflineMediaEvidenceGate
from trusted_media_revocation import (
    append_revocation_event, verify_revocation_chain)


_SCAN_KEY = b'synthetic typed scan fixture key only'
_RIGHTS_KEY = b'synthetic typed rights fixture key only'
_AUDIT_KEY = b'synthetic typed audit fixture key only'
_EMPTY_HEAD = '0' * 64
_DRAFT = 'a' * 32
_AI_PARENT = ('ai_draft', 'shop', 'owner', _DRAFT)
_REQUEST_PARENT = ('request', 'shop', None, _DRAFT)


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True).encode('ascii')


def _sign(value, key):
    return {**value, 'signature': hmac.digest(key, _encode(value), 'sha256').hex()}


def _digest(value):
    return hashlib.sha256(_encode(value)).hexdigest()


class DisposableTypedAttachmentBindingTests(unittest.TestCase):
    def setUp(self):
        # The connection and storage are created here. Tests accept no real input.
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.database_path = self.root / 'fixture.sqlite3'
        self.db = self.enterContext(closing(sqlite3.connect(self.database_path)))
        self.db.executescript("""
            CREATE TABLE fixture_attachment (
                attachment_id TEXT PRIMARY KEY, parent_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL, subject_id TEXT, parent_id TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('pending','discarding','discarded')),
                CHECK ((parent_type='request' AND subject_id IS NULL)
                    OR (parent_type='ai_draft' AND subject_id IS NOT NULL))
            );
            CREATE TRIGGER fixture_parent_is_immutable
                BEFORE UPDATE OF attachment_id,parent_type,tenant_id,subject_id,parent_id
                ON fixture_attachment
                BEGIN SELECT RAISE(ABORT,'immutable fixture binding'); END;
            CREATE TABLE fixture_member (
                tenant_id TEXT NOT NULL, subject_id TEXT NOT NULL, active INTEGER NOT NULL,
                PRIMARY KEY(tenant_id,subject_id)
            );
            INSERT INTO fixture_member VALUES ('shop','owner',1),('shop','viewer',1);
        """)
        self.ai_id = 'b' * 32
        self.request_id = 'c' * 32
        self.add_attachment(self.ai_id, _AI_PARENT)
        self.add_attachment(self.request_id, _REQUEST_PARENT)
        self.png_digest = hashlib.sha256(PNG).hexdigest()
        self.legacy = dict(attachment_id=self.ai_id, tenant_id='shop',
                           request_id=_DRAFT, item='image', media_type='image/png',
                           sha256=self.png_digest)
        common = dict(issuer='fixture', issued_at=101, expires_at=200)
        self.scan = _sign(dict(self.legacy, **common, kind='scan', verdict='clean',
                               engine='fixture'), _SCAN_KEY)
        self.rights = _sign(dict(self.legacy, **common, kind='rights', verdict='authorized',
                                 channel='facebook', basis='owned', proof_ref='fixture'),
                            _RIGHTS_KEY)
        self.typed_scan = self.typed_claim(self.scan, _AI_PARENT, _SCAN_KEY)
        self.typed_rights = self.typed_claim(self.rights, _AI_PARENT, _RIGHTS_KEY)

    def add_attachment(self, aid, parent):
        with self.db:
            self.db.execute("INSERT INTO fixture_attachment VALUES (?,?,?,?,?,'pending')",
                            (aid, *parent))

    def path(self, aid):
        return self.root / (aid + '.pending')

    def state(self, aid, parent, actor):
        row = self.db.execute("""SELECT a.state FROM fixture_attachment AS a
            JOIN fixture_member AS m ON m.tenant_id=a.tenant_id AND m.subject_id=?
            WHERE m.active=1 AND a.attachment_id=? AND a.parent_type=?
              AND a.tenant_id=? AND a.subject_id IS ? AND a.parent_id=?
              AND (a.parent_type='request' OR a.subject_id=m.subject_id)""",
            (actor, aid, *parent)).fetchone()
        if row is None:
            raise PermissionError('Current attachment binding required')
        return row[0]

    def receive(self, aid, parent, actor):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if self.state(aid, parent, actor) != 'pending':
                raise PermissionError('Pending attachment required')
            with self.path(aid).open('xb') as stream:
                stream.write(PNG)

    def discard(self, aid, parent, actor):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if self.state(aid, parent, actor) == 'discarded':
                return
            self.db.execute("""UPDATE fixture_attachment SET state='discarding'
                WHERE attachment_id=? AND state='pending'""", (aid,))
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if self.state(aid, parent, actor) == 'discarded':
                return
            self.path(aid).unlink(missing_ok=True)
            self.db.execute("""UPDATE fixture_attachment SET state='discarded'
                WHERE attachment_id=? AND state='discarding'""", (aid,))

    @staticmethod
    def typed_claim(claim, parent, key):
        return _sign(dict(version='typed-fixture-v2', kind=claim['kind'],
                          parent=list(parent), claim=claim), key)

    def verify(self, aid, parent, actor, scan, rights, *, chain=(), head=_EMPTY_HEAD,
               historical_claims=()):
        if self.state(aid, parent, actor) != 'pending':
            raise PermissionError('Pending attachment required')
        stored_digest = hashlib.sha256(self.path(aid).read_bytes()).hexdigest()
        for envelope, key in ((scan, _SCAN_KEY), (rights, _RIGHTS_KEY)):
            if set(envelope) != {'version','kind','parent','claim','signature'}:
                raise PermissionError('Typed claim required')
            payload = {field: value for field, value in envelope.items() if field != 'signature'}
            expected = _sign(payload, key)['signature']
            if (not hmac.compare_digest(expected, envelope['signature'])
                    or envelope['version'] != 'typed-fixture-v2'
                    or envelope['parent'] != list(parent)
                    or envelope['kind'] != envelope['claim']['kind']):
                raise PermissionError('Typed claim scope mismatch')
        pending = dict(self.legacy, attachment_id=aid, tenant_id=parent[1],
                       request_id=parent[3], sha256=stored_digest,
                       status='pending', created_at=100)
        OfflineMediaEvidenceGate(scanner_key=_SCAN_KEY, rights_key=_RIGHTS_KEY).verify(
            pending=pending, scan=scan['claim'], rights=rights['claim'],
            channel='facebook', now=110)
        ledger = verify_revocation_chain(chain=chain, audit_key=_AUDIT_KEY,
                                         expected_head=head, now=110)
        # The existing chain only carries claim digests. The caller fixture
        # supplies a complete synthetic claim index or this rehearsal holds.
        indexed = {_digest(claim): claim for claim in historical_claims}
        for revoked in ledger['revoked_claim_hashes']:
            if revoked not in indexed:
                raise PermissionError('Unresolved revocation')
            original = indexed[revoked].get('claim', indexed[revoked])
            if original['attachment_id'] == aid:
                raise PermissionError('Attachment has a revoked claim')
        return True

    def test_typed_evidence_refuses_namespace_subject_and_attachment_substitution(self):
        self.receive(self.ai_id, _AI_PARENT, 'owner')
        self.receive(self.request_id, _REQUEST_PARENT, 'owner')
        self.assertTrue(self.verify(self.ai_id, _AI_PARENT, 'owner',
                                    self.typed_scan, self.typed_rights))
        other_subject = ('ai_draft','shop','viewer',_DRAFT)
        for candidate in (
            self.scan,
            {**self.typed_scan, 'parent':list(_REQUEST_PARENT)},
            self.typed_claim(self.scan, _REQUEST_PARENT, _SCAN_KEY),
            self.typed_claim(self.scan, other_subject, _SCAN_KEY),
        ):
            with self.subTest(candidate=candidate.get('parent')), self.assertRaises(PermissionError):
                self.verify(self.ai_id, _AI_PARENT, 'owner', candidate, self.typed_rights)
        with self.assertRaises(PermissionError):
            self.verify(self.request_id, _REQUEST_PARENT, 'owner',
                        self.typed_claim(self.scan, _REQUEST_PARENT, _SCAN_KEY),
                        self.typed_claim(self.rights, _REQUEST_PARENT, _RIGHTS_KEY))
        with self.assertRaises(PermissionError):
            self.verify(self.ai_id, _AI_PARENT, 'owner', self.typed_scan,
                        self.typed_claim(self.rights, other_subject, _RIGHTS_KEY))
        ordinary_claims = []
        for claim, key in ((self.scan, _SCAN_KEY), (self.rights, _RIGHTS_KEY)):
            ordinary = {field:value for field,value in claim.items() if field!='signature'}
            ordinary['attachment_id'] = self.request_id
            ordinary_claims.append(self.typed_claim(_sign(ordinary, key), _REQUEST_PARENT, key))
        self.assertTrue(self.verify(self.request_id, _REQUEST_PARENT, 'owner', *ordinary_claims))
        self.assertEqual(self.path(self.ai_id).read_bytes(), self.path(self.request_id).read_bytes())

    def test_legacy_and_typed_revocations_hold_even_after_reissue_or_stale_restore(self):
        self.receive(self.ai_id, _AI_PARENT, 'owner')
        renewed = _sign({**{key:value for key,value in self.scan.items() if key!='signature'},
                         'issued_at':109}, _SCAN_KEY)
        for revoked in (self.scan, self.typed_scan):
            chain, head = append_revocation_event(
                chain=(), expected_head=_EMPTY_HEAD, audit_key=_AUDIT_KEY,
                claim=revoked, kind='scan', reason='scanner_recall', now=108)
            options = (self.ai_id, _AI_PARENT, 'owner',
                       self.typed_claim(renewed, _AI_PARENT, _SCAN_KEY), self.typed_rights)
            with self.subTest(version=revoked.get('version')):
                with self.assertRaisesRegex(PermissionError, 'revoked claim'):
                    self.verify(*options, chain=chain, head=head, historical_claims=(revoked,))
                with self.assertRaisesRegex(PermissionError, 'Unresolved revocation'):
                    self.verify(*options, chain=chain, head=head)
                with self.assertRaisesRegex(PermissionError, 'independent pin'):
                    self.verify(*options, head=head)
        unrelated = _sign({**{key:value for key,value in self.scan.items() if key!='signature'},
                           'attachment_id':self.request_id}, _SCAN_KEY)
        chain, head = append_revocation_event(
            chain=(), expected_head=_EMPTY_HEAD, audit_key=_AUDIT_KEY,
            claim=unrelated, kind='scan', reason='scanner_recall', now=108)
        self.assertTrue(self.verify(*options, chain=chain, head=head,
                                    historical_claims=(unrelated,)))

    def test_colliding_receipt_and_interrupted_discard_keep_other_parent_intact(self):
        with self.assertRaises(PermissionError):
            self.receive(self.ai_id, _REQUEST_PARENT, 'owner')
        self.assertFalse(self.path(self.ai_id).exists())
        self.receive(self.ai_id, _AI_PARENT, 'owner')
        self.receive(self.request_id, _REQUEST_PARENT, 'owner')
        with self.assertRaises(PermissionError):
            self.discard(self.ai_id, _REQUEST_PARENT, 'owner')
        with self.assertRaises(PermissionError):
            self.discard(self.ai_id, _AI_PARENT, 'viewer')
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable fixture binding'):
            with self.db:
                self.db.execute("""UPDATE fixture_attachment SET parent_id='changed'
                    WHERE attachment_id=?""", (self.ai_id,))

        # A failure before unlink keeps the bytes and blocks another receipt.
        with patch.object(Path, 'unlink', side_effect=OSError('fixture unlink failed')):
            with self.assertRaisesRegex(OSError, 'fixture unlink failed'):
                self.discard(self.ai_id, _AI_PARENT, 'owner')
        self.assertEqual(self.state(self.ai_id, _AI_PARENT, 'owner'), 'discarding')
        self.assertEqual(self.path(self.ai_id).read_bytes(), PNG)

        # A failed metadata finalize leaves a durable discard intent.
        self.db.executescript("""CREATE TRIGGER fail_fixture_discard
            BEFORE UPDATE ON fixture_attachment WHEN NEW.state='discarded'
            BEGIN SELECT RAISE(ABORT,'interrupted fixture'); END;""")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'interrupted fixture'):
            self.discard(self.ai_id, _AI_PARENT, 'owner')
        self.assertEqual(self.state(self.ai_id, _AI_PARENT, 'owner'), 'discarding')
        self.assertFalse(self.path(self.ai_id).exists())
        self.db.close()
        self.db = self.enterContext(closing(sqlite3.connect(self.database_path)))
        with self.assertRaises(PermissionError):
            self.receive(self.ai_id, _AI_PARENT, 'owner')
        self.db.execute("DROP TRIGGER fail_fixture_discard")
        with self.db:
            self.db.execute("UPDATE fixture_member SET active=0 WHERE subject_id='owner'")
        with self.assertRaises(PermissionError):
            self.discard(self.ai_id, _AI_PARENT, 'owner')
        with self.db:
            self.db.execute("UPDATE fixture_member SET active=1 WHERE subject_id='owner'")
        self.discard(self.ai_id, _AI_PARENT, 'owner')
        self.discard(self.ai_id, _AI_PARENT, 'owner')
        self.assertEqual(self.state(self.ai_id, _AI_PARENT, 'owner'), 'discarded')
        self.assertEqual(self.state(self.request_id, _REQUEST_PARENT, 'owner'), 'pending')
        self.assertEqual(self.path(self.request_id).read_bytes(), PNG)
