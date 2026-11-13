"""CI rehearsal for restoring a typed attachment review and revocation index."""
from contextlib import closing
import hashlib
import hmac
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from bam_offline_durable_archive import store_disposable_ciphertext
from bam_offline_recovery_manifest import (
    append_disposable_recovery_manifest, restore_disposable_recovery_point)
from bam_offline_recovery_relocation import relocate_disposable_ciphertext
from offline_encrypted_backup import seal_disposable_backup

from trusted_media_revocation import append_revocation_event, verify_revocation_chain


_EMPTY_HEAD = '0' * 64
_AUDIT_KEY = b'synthetic review restore audit key'
_OLD_SCAN = b'synthetic archived scan fixture key'
_NEW_SCAN = b'synthetic rotated scan fixture key'
_RIGHTS = b'synthetic rights review fixture key'
_DRAFT = 'a' * 32
_REQUEST = ('request', 'shop', '', _DRAFT)
_ALICE = ('ai_draft', 'shop', 'alice', _DRAFT)
_BOB = ('ai_draft', 'shop', 'bob', _DRAFT)
_OTHER = ('ai_draft', 'other-shop', 'alice', _DRAFT)
_ATTACHMENT_IDS = dict(zip((_REQUEST, _ALICE, _BOB, _OTHER), 'bcde'))
_ISSUERS = {
    ('scan', 'scanner', 'old'): (_OLD_SCAN, 100, 120),
    ('scan', 'scanner', 'new'): (_NEW_SCAN, 120, 200),
    ('rights', 'reviewer', 'only'): (_RIGHTS, 100, 200),
}


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True).encode('ascii')


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _signature(payload, key):
    return hmac.digest(key, _canonical(payload), 'sha256').hex()


def _claim(parent, *, version=2, kind='scan', issued_at=115, **changes):
    namespace, tenant, subject, draft = parent
    key_id, key, issuer = ('old', _OLD_SCAN, 'scanner') if issued_at < 120 else (
        'new', _NEW_SCAN, 'scanner')
    if kind == 'rights':
        key_id, key, issuer = 'only', _RIGHTS, 'reviewer'
    payload = dict(kind=kind, issuer=issuer, issued_at=issued_at, key_id=key_id,
                   attachment_id=_ATTACHMENT_IDS[parent] * 32,
                   tenant_id=tenant, parent_id=draft)
    # Version 1 represents a previously signed claim without type/subject.
    if version != 1:
        payload.update(version=version, parent_type=namespace, subject_id=subject)
    payload.update(changes)
    return dict(payload, signature=_signature(payload, key))


def _resolve_claim(db, raw, event, issuers):
    claim = json.loads(raw)
    if type(claim) is not dict or _canonical(claim) != raw:
        raise PermissionError('Noncanonical historical claim')
    fields = {'kind', 'issuer', 'issued_at', 'key_id', 'attachment_id',
              'tenant_id', 'parent_id', 'signature'}
    legacy = set(claim) == fields
    typed = set(claim) == fields | {'version', 'parent_type', 'subject_id'}
    if not legacy and not (typed and type(claim['version']) is int
                           and claim['version'] == 2):
        raise PermissionError('Unrecognized historical claim')
    strings = set(claim) - {'issued_at', 'version'}
    if (any(type(claim[field]) is not str for field in strings)
            or type(claim['issued_at']) is not int
            or claim['kind'] != event['kind']):
        raise PermissionError('Malformed historical claim')
    issuance = issuers.get((claim['kind'], claim['issuer'], claim['key_id']))
    payload = {field: claim[field] for field in claim if field != 'signature'}
    if issuance is None:
        raise PermissionError('Unknown historical issuer')
    key, start, end = issuance
    if (not start <= claim['issued_at'] < end
            or claim['issued_at'] > event['issued_at']
            or not claim['signature'].isascii()
            or not hmac.compare_digest(claim['signature'], _signature(payload, key))):
        raise PermissionError('Historical issuer authentication failed')
    binding = db.execute("""
        SELECT parent_type, tenant_id, subject_id, parent_id
        FROM attachment WHERE attachment_id=?
        """, (claim['attachment_id'],)).fetchone()
    if binding is None:
        raise PermissionError('Historical claim binding mismatch')
    namespace, tenant, subject, parent = binding
    if ((tenant, parent) != (claim['tenant_id'], claim['parent_id'])
            or (typed and (namespace, subject) != (claim['parent_type'], claim['subject_id']))):
        raise PermissionError('Historical claim binding mismatch')
    return claim['attachment_id']


def _checkpoint(head, inventory):
    # The test's independent witness retains only the checkpoint digest.
    return _sha(_canonical({'format': 1, 'ledger_head': head, 'claims': inventory}))


def _catalog_digest(issuers):
    # Only synthetic key fingerprints and issuance windows are committed.
    return _sha(_canonical([
        (scope, _sha(key), starts_at, ends_at)
        for scope, (key, starts_at, ends_at) in sorted(issuers.items())
    ]))


def _verify_witness(checkpoint, signature, *, pin, epoch, key):
    if (checkpoint['epoch'] != epoch or checkpoint['purpose'] != 'ci-attachment-restore-v1'
            or _sha(_canonical(checkpoint)) != pin or key is None):
        raise PermissionError('Restore witness differs from independent pin or epoch')
    try:
        key.verify(signature, _canonical(checkpoint))
    except InvalidSignature as exc:
        raise PermissionError('Restore witness signature failed') from exc


def _read_state(db):
    stored_claims = db.execute("SELECT digest, body FROM claim_index ORDER BY digest")
    chain = tuple(json.loads(body) for (body,) in db.execute(
        "SELECT body FROM revocation ORDER BY sequence"))
    index = dict(stored_claims)
    head = chain[-1]['mac'] if chain else _EMPTY_HEAD
    inventory = [(digest, _sha(raw)) for digest, raw in index.items()]
    return head, inventory, chain, index


def _read_attachments(db, parent_type, tenant, actor, parent_id, *, review, held):
    rows = db.execute("""
        SELECT a.attachment_id, a.ready FROM attachment AS a
        JOIN parent AS p USING(parent_type, tenant_id, subject_id, parent_id)
        JOIN member AS m ON m.tenant_id=a.tenant_id AND m.subject_id=?
        WHERE a.parent_type=? AND a.tenant_id=? AND a.parent_id=?
          AND m.active=1 AND (a.parent_type='request' OR a.subject_id=m.subject_id)
          AND (?=0 OR m.role IN ('owner', 'marketing_manager'))
        ORDER BY a.attachment_id
        """, (actor, parent_type, tenant, parent_id, review))
    if review:
        return tuple(aid for aid, ready in rows if ready and aid not in held)
    return tuple((aid, aid in held) for aid, _ in rows)


class DisposableAttachmentReviewRestoreTests(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.directory = directory
        self.source = self.enterContext(closing(sqlite3.connect(directory / 'source.sqlite')))
        self.restored = directory / 'restored.sqlite'
        self.source.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE parent(
                parent_type TEXT, tenant_id TEXT, subject_id TEXT, parent_id TEXT,
                PRIMARY KEY(parent_type,tenant_id,subject_id,parent_id),
                CHECK((parent_type='request' AND subject_id='')
                      OR (parent_type='ai_draft' AND subject_id<>''))
            ) WITHOUT ROWID;
            CREATE TABLE attachment(
                attachment_id TEXT PRIMARY KEY NOT NULL, parent_type TEXT NOT NULL,
                tenant_id TEXT NOT NULL, subject_id TEXT NOT NULL, parent_id TEXT NOT NULL,
                ready INTEGER NOT NULL CHECK(ready IN (0,1)),
                FOREIGN KEY(parent_type,tenant_id,subject_id,parent_id)
                    REFERENCES parent(parent_type,tenant_id,subject_id,parent_id)
            );
            CREATE TRIGGER attachment_binding_immutable
                BEFORE UPDATE OF attachment_id,parent_type,tenant_id,subject_id,parent_id
                ON attachment
                BEGIN SELECT RAISE(ABORT,'immutable fixture binding'); END;
            CREATE TABLE legacy_hold(
                attachment_id TEXT PRIMARY KEY, tenant_id TEXT, parent_id TEXT,
                legacy_state TEXT, hold_reason TEXT
            );
            CREATE TABLE member(
                tenant_id TEXT, subject_id TEXT, role TEXT, active INTEGER,
                PRIMARY KEY(tenant_id,subject_id)
            );
            INSERT INTO member VALUES ('shop','alice','owner',1),
                ('shop','bob','marketing_manager',1),('shop','viewer','viewer',1),
                ('shop','disabled','owner',0),('other-shop','alice','owner',1);
            CREATE TABLE claim_index(digest TEXT PRIMARY KEY NOT NULL, body BLOB NOT NULL);
            CREATE TABLE revocation(sequence INTEGER PRIMARY KEY, body BLOB NOT NULL);
        """)
        with self.source:
            for parent, prefix in _ATTACHMENT_IDS.items():
                self.source.execute("INSERT INTO parent VALUES (?,?,?,?)", parent)
                self.source.execute("INSERT INTO attachment VALUES (?,?,?,?,?,1)",
                                    (prefix * 32, *parent))
            self.source.execute("INSERT INTO legacy_hold VALUES (?,?,?,'verified','ambiguous')",
                                ('f' * 32, 'shop', _DRAFT))
            self.source.execute("INSERT INTO attachment VALUES (?,?,?,?,?,0)",
                                ('9' * 32, *_REQUEST))

    def revoke(self, claim, *, at=140):
        with self.source:
            self.source.execute('BEGIN IMMEDIATE')
            head, _, chain, _ = _read_state(self.source)
            events, _ = append_revocation_event(
                chain=chain, expected_head=head, audit_key=_AUDIT_KEY,
                claim=claim, kind=claim['kind'], reason='operator_hold', now=at)
            event = events[-1]
            self.source.execute("INSERT INTO claim_index VALUES (?,?)",
                                (event['claim_sha256'], _canonical(claim)))
            self.source.execute("INSERT INTO revocation VALUES (?,?)",
                                (event['sequence'], _canonical(event)))
        return event['claim_sha256']

    @staticmethod
    def witness(db):
        head, inventory, _, _ = _read_state(db)
        return _checkpoint(head, inventory)

    def backup(self):
        with closing(sqlite3.connect(self.restored)) as copy:
            self.source.backup(copy)

    def open_restored(self):
        return closing(sqlite3.connect(self.restored))

    @staticmethod
    def query(db, pin, parent_type, tenant, actor, *, review=False, issuers=_ISSUERS):
        # Resolve the whole index and make the scoped read on one snapshot.
        with db:
            db.execute("BEGIN")
            head, inventory, chain, index = _read_state(db)
            if not hmac.compare_digest(pin, _checkpoint(head, inventory)):
                raise PermissionError('Restore differs from independent checkpoint')
            verified = verify_revocation_chain(chain=chain, audit_key=_AUDIT_KEY,
                                               expected_head=head, now=160)
            expected = verified['revoked_claim_hashes']
            if expected - index.keys():
                raise PermissionError('Missing historical claim')
            if index.keys() - expected:
                raise PermissionError('Unreferenced historical claim')
            held = set()
            for event in chain:
                digest = event['claim_sha256']
                raw = index[digest]
                if _sha(raw) != digest:
                    raise PermissionError('Historical claim digest mismatch')
                held.add(_resolve_claim(db, raw, event, issuers))
            return _read_attachments(db, parent_type, tenant, actor, _DRAFT,
                                     review=review, held=held)

    def test_typed_read_and_review_visibility_with_colliding_parents(self):
        pin = self.witness(self.source)
        self.backup()
        with self.open_restored() as db:
            self.assertEqual(self.query(db, pin, 'request', 'shop', 'alice'),
                             (('9' * 32, False), ('b' * 32, False)))
            self.assertEqual(self.query(db, pin, 'request', 'shop', 'alice', review=True),
                             ('b' * 32,))
            self.assertEqual(self.query(db, pin, 'request', 'shop', 'viewer'),
                             (('9' * 32, False), ('b' * 32, False)))
            self.assertEqual(self.query(db, pin, 'request', 'shop', 'viewer', review=True), ())
            self.assertEqual(self.query(db, pin, 'ai_draft', 'shop', 'viewer'), ())
            self.assertEqual(self.query(db, pin, 'ai_draft', 'shop', 'disabled'), ())
            self.assertEqual(self.query(db, pin, 'request', 'other-shop', 'alice'), ())
            for parent in (_ALICE, _BOB, _OTHER):
                namespace, tenant, actor, _ = parent
                aid = _ATTACHMENT_IDS[parent] * 32
                with self.subTest(parent=parent):
                    self.assertEqual(self.query(db, pin, namespace, tenant, actor),
                                     ((aid, False),))
                    self.assertEqual(self.query(db, pin, namespace, tenant, actor, review=True),
                                     (aid,))
            with self.assertRaises(sqlite3.IntegrityError), db:
                db.execute("INSERT INTO attachment VALUES (?,?,?,?,?,1)", ('c' * 32, *_BOB))
            with self.assertRaises(sqlite3.IntegrityError), db:
                db.execute("UPDATE attachment SET subject_id='bob' WHERE attachment_id=?",
                           ('c' * 32,))
            self.assertEqual(db.execute("SELECT legacy_state,hold_reason FROM legacy_hold").fetchall(),
                             [('verified', 'ambiguous')])

    def test_old_and_rotated_issuer_keys_restore_with_a_scoped_hold(self):
        self.revoke(_claim(_ALICE, version=1))
        self.revoke(_claim(_ALICE, issued_at=130))
        self.revoke(_claim(_OTHER, kind='rights', issued_at=130))
        pin = self.witness(self.source)
        self.backup()
        with self.open_restored() as db:
            self.assertEqual(self.query(db, pin, 'ai_draft', 'shop', 'alice'),
                             (('c' * 32, True),))
            self.assertEqual(self.query(db, pin, 'ai_draft', 'shop', 'alice', review=True), ())
            self.assertEqual(self.query(db, pin, 'ai_draft', 'other-shop', 'alice', review=True), ())
            self.assertEqual(self.query(db, pin, 'ai_draft', 'shop', 'bob', review=True),
                             ('d' * 32,))
            self.assertEqual(self.query(db, pin, 'request', 'shop', 'alice', review=True),
                             ('b' * 32,))
            active_keys = {scope: value for scope, value in _ISSUERS.items()
                           if scope[-1] != 'old'}
            with self.assertRaisesRegex(PermissionError, 'Unknown historical issuer'):
                self.query(db, pin, 'ai_draft', 'shop', 'alice', issuers=active_keys)

    def test_stale_missing_and_substituted_index_are_held(self):
        stale = self.witness(self.source)
        self.backup()
        digest = self.revoke(_claim(_ALICE))
        current = self.witness(self.source)
        with self.open_restored() as db:
            self.assertEqual(self.query(db, stale, 'ai_draft', 'shop', 'alice', review=True),
                             ('c' * 32,))
            with self.assertRaisesRegex(PermissionError, 'independent checkpoint'):
                self.query(db, current, 'ai_draft', 'shop', 'alice', review=True)
        self.backup()
        with self.open_restored() as db:
            with db:
                db.execute("UPDATE claim_index SET body=? WHERE digest=?",
                           (_canonical(_claim(_OTHER)), digest))
            with self.assertRaisesRegex(PermissionError, 'independent checkpoint'):
                self.query(db, current, 'ai_draft', 'shop', 'alice', review=True)
            with self.assertRaisesRegex(PermissionError, 'digest mismatch'):
                self.query(db, self.witness(db), 'ai_draft', 'shop', 'alice', review=True)
            with db:
                db.execute("DELETE FROM claim_index")
            with self.assertRaisesRegex(PermissionError, 'independent checkpoint'):
                self.query(db, current, 'ai_draft', 'shop', 'alice', review=True)
            with self.assertRaisesRegex(PermissionError, 'Missing historical claim'):
                self.query(db, self.witness(db), 'ai_draft', 'shop', 'alice', review=True)
            with db:
                extra = _canonical(_claim(_OTHER))
                db.executemany("INSERT INTO claim_index VALUES (?,?)", (
                    (digest, _canonical(_claim(_ALICE))), (_sha(extra), extra)))
            with self.assertRaisesRegex(PermissionError, 'Unreferenced historical claim'):
                self.query(db, self.witness(db), 'ai_draft', 'shop', 'alice', review=True)

    def test_signed_but_wrong_scope_version_or_issuer_cannot_clear_review(self):
        valid = _claim(_ALICE)
        cases = (
            (_claim(_ALICE, tenant_id='other-shop'), 'binding mismatch'),
            (_claim(_ALICE, subject_id='bob'), 'binding mismatch'),
            (_claim(_ALICE, parent_type='request'), 'binding mismatch'),
            (_claim(_ALICE, version=3), 'Unrecognized historical claim'),
            (_claim(_ALICE, issuer='other-scanner'), 'Unknown historical issuer'),
            (_claim(_ALICE, issued_at=130, key_id='old'), 'issuer authentication failed'),
            ({**valid, 'signature': '0' * 64}, 'issuer authentication failed'),
        )
        for claim, message in cases:
            with self.subTest(message=message, claim=claim):
                self.revoke(claim)
                pin = self.witness(self.source)
                self.backup()
                with self.open_restored() as db, self.assertRaisesRegex(PermissionError, message):
                    self.query(db, pin, 'ai_draft', 'shop', 'bob', review=True)
                with self.source:
                    self.source.execute("DELETE FROM claim_index")
                    self.source.execute("DELETE FROM revocation")


    def archive_checkpoint(self, epoch, witness_key, *, previous=None):
        # Keys and the witness pin stay outside both SQLite and the replica.
        archive_dir = self.directory / 'ciphertext-source'
        replica_dir = self.directory / 'ciphertext-replica'
        archive_dir.mkdir(mode=0o700, exist_ok=True)
        replica_dir.mkdir(mode=0o700, exist_ok=True)
        name = f'point-{epoch}.bamenc'
        encryption_key = b'e' * 32
        signers = {'manifest': b'm' * 32}
        schema = _sha(b'CI typed attachment SQLite fixture v1')
        with closing(sqlite3.connect(':memory:')) as snapshot:
            self.source.backup(snapshot)
            state_pin = self.witness(snapshot)
            ciphertext = seal_disposable_backup(
                plaintext=snapshot.serialize(), root_key=encryption_key,
                schema_fingerprint=schema, now=145)
        receipt = store_disposable_ciphertext(
            directory=str(archive_dir), name=name, envelope=ciphertext,
            root_key=encryption_key, schema_fingerprint=schema, now=146)
        prior_chain, prior_head = previous or ((), _EMPTY_HEAD)
        chain, head = append_disposable_recovery_manifest(
            chain=prior_chain, expected_head=prior_head, signer_keys=signers,
            schema_fingerprint=schema, now=147, receipt=receipt,
            signer_key_id='manifest', encryption_key_id='replica',
            encryption_root_key=encryption_key, retain_until=200)
        relocate_disposable_ciphertext(
            source_directory=str(archive_dir), destination_directory=str(replica_dir),
            archive_name=name, chain=chain, expected_head=head, signer_keys=signers,
            schema_fingerprint=schema, now=148)
        (archive_dir / name).unlink()
        checkpoint = dict(purpose='ci-attachment-restore-v1', epoch=epoch,
                          catalog=_catalog_digest(_ISSUERS), state=state_pin,
                          archive_name=name, archive_head=head, schema=schema)
        message = _canonical(checkpoint)
        return (checkpoint, witness_key.sign(message), _sha(message)), (chain, head)

    def open_checkpoint(self, checkpoint, signature, *, pin, epoch, key, chain,
                        issuers=_ISSUERS, fail_after_validation=False):
        _verify_witness(checkpoint, signature, pin=pin, epoch=epoch, key=key)
        if _catalog_digest(issuers) != checkpoint['catalog']:
            raise PermissionError('Restore issuer catalog differs from witness')
        plaintext = restore_disposable_recovery_point(
            chain=chain, expected_head=checkpoint['archive_head'],
            signer_keys={'manifest': b'm' * 32}, encryption_keyring={'replica': b'e' * 32},
            directory=str(self.directory / 'ciphertext-replica'),
            archive_name=checkpoint['archive_name'],
            schema_fingerprint=checkpoint['schema'], now=160)
        # Admission stays closed until the isolated copy passes the complete
        # index check. A failed attempt does not publish a restored database.
        with closing(sqlite3.connect(':memory:')) as db:
            db.deserialize(plaintext)
            if (db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]
                    or db.execute('PRAGMA foreign_key_check').fetchall()):
                raise PermissionError('Invalid restored database')
            result = self.query(db, checkpoint['state'], 'ai_draft', 'shop', 'alice',
                                review=True, issuers=issuers)
            if fail_after_validation:
                raise InterruptedError('Restore interrupted before admission')
            return result

    def test_authenticated_replica_rejects_stale_witness_and_key_catalog(self):
        with patch.dict(os.environ, BAM_EPHEMERAL_PG_TEST='1'):
            old_key = Ed25519PrivateKey.generate()
            current_key = Ed25519PrivateKey.generate()
            (old, old_sig, old_pin), prior = self.archive_checkpoint(1, old_key)
            self.revoke(_claim(_ALICE, version=1))
            self.revoke(_claim(_ALICE, issued_at=130))
            (current, sig, pin), (chain, _) = self.archive_checkpoint(
                2, current_key, previous=prior)
            options = dict(pin=pin, epoch=2, key=current_key.public_key(), chain=chain)
            self.assertEqual(self.open_checkpoint(current, sig, **options), ())
            self.assertEqual(self.open_checkpoint(
                old, old_sig, pin=old_pin, epoch=1, key=old_key.public_key(), chain=prior[0]),
                ('c' * 32,))
            with self.assertRaisesRegex(PermissionError, 'pin or epoch'):
                self.open_checkpoint(old, old_sig, **{**options, 'chain': prior[0]})
            with self.assertRaisesRegex(PermissionError, 'pin or epoch'):
                self.open_checkpoint(old, old_sig, **{**options, 'pin': old_pin})
            with self.assertRaisesRegex(PermissionError, 'signature failed'):
                self.open_checkpoint(current, old_key.sign(_canonical(current)), **options)
            with self.assertRaisesRegex(PermissionError, 'pin or epoch'):
                self.open_checkpoint(current, sig, **{**options, 'key': None})
            old_scope = ('scan', 'scanner', 'old')
            new_scope = ('scan', 'scanner', 'new')
            for issuers in (
                {scope: value for scope, value in _ISSUERS.items() if scope != new_scope},
                {scope: value for scope, value in _ISSUERS.items() if scope != old_scope},
                {**_ISSUERS, old_scope: (b'x' * 32, 100, 120)},
                {**_ISSUERS, old_scope: (_OLD_SCAN, 100, 200)},
            ):
                with self.subTest(catalog=tuple(issuers)), self.assertRaisesRegex(
                        PermissionError, 'issuer catalog differs'):
                    self.open_checkpoint(current, sig, issuers=issuers, **options)
            with self.assertRaisesRegex(InterruptedError, 'before admission'):
                self.open_checkpoint(current, sig, fail_after_validation=True, **options)
            self.assertFalse(self.restored.exists())
            self.assertEqual(self.open_checkpoint(current, sig, **options), ())

    def promotion_store(self, *, initialize=False):
        db = sqlite3.connect(self.directory / 'promotion.sqlite', timeout=0)
        if initialize:
            with db:
                db.execute("""CREATE TABLE promotion (
                    id INTEGER PRIMARY KEY CHECK (id=1), generation INTEGER NOT NULL,
                    state_pin TEXT NOT NULL, staged TEXT, active TEXT,
                    receipt TEXT, reconciled INTEGER NOT NULL DEFAULT 0
                )""")
                db.execute("""CREATE TABLE recovery_canary (
                    operation TEXT PRIMARY KEY, generation INTEGER NOT NULL,
                    receipt TEXT NOT NULL
                )""")
                db.execute("INSERT INTO promotion VALUES (1,1,?,NULL,NULL,NULL,0)",
                           (self.witness(self.source),))
        return closing(db)

    def stage_promotion(self, db, generation, checkpoint, signature, **options):
        # Validate the complete replica before staging. The transaction checks
        # that the authority still points to the validated evidence.
        self.open_checkpoint(checkpoint, signature, **options)
        with db:
            result = db.execute("""UPDATE promotion SET staged=?
                WHERE id=1 AND generation=? AND state_pin=? AND active IS NULL
                AND (staged IS NULL OR staged=?)""",
                (options['pin'], generation, checkpoint['state'], options['pin']))
            if result.rowcount != 1:
                raise PermissionError('Restore authority moved before staging')

    @staticmethod
    def promote(db, generation, state_pin, checkpoint_pin, signature, witness_key,
                *, abort=False):
        message = _canonical(['ci-completion-v1', generation, state_pin, checkpoint_pin])
        receipt = _sha(message + signature)
        with db:
            db.execute('BEGIN IMMEDIATE')
            witness_key.verify(signature, message)
            result = db.execute("""UPDATE promotion SET active=staged,staged=NULL,receipt=?
                WHERE id=1 AND generation=? AND state_pin=? AND staged=? AND active IS NULL""",
                (receipt, generation, state_pin, checkpoint_pin))
            if result.rowcount != 1:
                committed = db.execute("""SELECT 1 FROM promotion WHERE id=1
                    AND generation=? AND state_pin=? AND active=? AND receipt=?""",
                    (generation, state_pin, checkpoint_pin, receipt)).fetchone()
                if committed is None:
                    raise PermissionError('Restore candidate is stale or differs from receipt')
            if abort:
                raise InterruptedError('Promotion interrupted before commit')
        return receipt

    @staticmethod
    def begin_recovery(db, independent):
        generation, state_pin, _ = independent
        with db:
            # An older local snapshot cannot set the next generation floor.
            return db.execute("""UPDATE promotion
                SET generation=max(generation,?)+1,state_pin=?,active=NULL,staged=NULL,
                    receipt=NULL,reconciled=0 WHERE id=1 RETURNING generation""",
                (generation, state_pin)).fetchone()[0]

    @staticmethod
    def reconcile_promotion(db, independent):
        generation, state_pin, receipt = independent
        with db:
            changed = db.execute("""UPDATE promotion SET reconciled=1
                WHERE id=1 AND generation=? AND state_pin=? AND active IS NOT NULL
                AND receipt=?""", (generation, state_pin, receipt)).rowcount
            if changed != 1:
                raise PermissionError('Current promotion receipt is unavailable')

    @staticmethod
    def _require_admission(db, generation, state_pin, independent):
        if independent[:2] != (generation, state_pin):
            raise PermissionError('Restore is not admitted at the current generation')
        row = db.execute("""SELECT active FROM promotion WHERE id=1
            AND generation=? AND state_pin=? AND receipt=? AND reconciled=1""",
            independent).fetchone()
        if row is None or row[0] is None:
            raise PermissionError('Restore is not admitted without a reconciled receipt')
        return row[0]

    def promoted_review(self, db, generation, checkpoint, signature, *, independent, **options):
        with db:
            db.execute('BEGIN IMMEDIATE')
            active = self._require_admission(db, generation, checkpoint['state'], independent)
            if active != options['pin']:
                raise PermissionError('Restore is not admitted for this checkpoint')
            return self.open_checkpoint(checkpoint, signature, **options)

    def admitted_write(self, db, generation, state_pin, independent, operation):
        with db:
            db.execute('BEGIN IMMEDIATE')
            self._require_admission(db, generation, state_pin, independent)
            db.execute("INSERT INTO recovery_canary VALUES (?,?,?)",
                       (operation, generation, independent[2]))

    def witness_journal(self, *, initialize=False):
        db = sqlite3.connect(self.directory / 'witness.sqlite', timeout=0)
        if initialize:
            db.execute("""CREATE TABLE witness_record (
                sequence INTEGER PRIMARY KEY, body BLOB NOT NULL, signature BLOB NOT NULL
            )""")
        return closing(db)

    @staticmethod
    def read_witness_journal(db, key, expected_head):
        head, latest = _EMPTY_HEAD, (0, None, None)
        records = db.execute(
            "SELECT sequence,body,signature FROM witness_record ORDER BY sequence")
        for expected_sequence, (sequence, body, signature) in enumerate(records, 1):
            key.verify(signature, body)
            purpose, number, previous, generation, state_pin, receipt = json.loads(body)
            if (purpose != 'ci-witness-journal-v1' or number != sequence
                    or sequence != expected_sequence
                    or previous != head or generation <= latest[0]):
                raise PermissionError('Invalid witness journal sequence')
            head, latest = _sha(body + signature), (generation, state_pin, receipt)
        if head != expected_head:
            raise PermissionError('Witness journal differs from independent head')
        return latest

    @classmethod
    def append_witness_record(cls, db, key, expected_head, state):
        with db:
            db.execute('BEGIN IMMEDIATE')
            latest = cls.read_witness_journal(db, key.public_key(), expected_head)
            if state == latest:
                return expected_head
            if state[0] <= latest[0]:
                raise PermissionError('Witness generation must advance')
            sequence = db.execute("SELECT count(*)+1 FROM witness_record").fetchone()[0]
            body = _canonical(['ci-witness-journal-v1', sequence, expected_head, *state])
            signature = key.sign(body)
            db.execute("INSERT INTO witness_record VALUES (?,?,?)", (sequence, body, signature))
            return _sha(body + signature)

    def test_signed_witness_journal_restart_rollback_and_concurrent_revocation(self):
        with patch.dict(os.environ, BAM_EPHEMERAL_PG_TEST='1'):
            archive_key = Ed25519PrivateKey.generate()
            completion_key = Ed25519PrivateKey.generate()
            journal_key = Ed25519PrivateKey.generate()
            public_key = journal_key.public_key()
            (old, old_sig, old_pin), prior = self.archive_checkpoint(1, archive_key)
            old_options = dict(pin=old_pin, epoch=1, key=archive_key.public_key(), chain=prior[0])
            with self.promotion_store(initialize=True) as authority:
                self.stage_promotion(authority, 1, old, old_sig, **old_options)
                args = (1, old['state'], old_pin)
                completion = completion_key.sign(_canonical(['ci-completion-v1', *args]))
                receipt = self.promote(authority, *args, completion, completion_key.public_key())
            old_state = (1, old['state'], receipt)
            with self.witness_journal(initialize=True) as journal, closing(
                    sqlite3.connect(self.directory / 'old-witness.sqlite')) as older:
                self.append_witness_record(journal, journal_key, _EMPTY_HEAD, old_state)
                # The independent observer retains the signed record's digest.
                body, signature = journal.execute(
                    "SELECT body,signature FROM witness_record WHERE sequence=1").fetchone()
                first_head = _sha(body + signature)
                journal.backup(older)

            # The independent checkpoint has the committed head, even if the
            # writer loses its acknowledgement and reconnects to the journal.
            with self.witness_journal() as journal:
                self.assertEqual(self.append_witness_record(
                    journal, journal_key, first_head, old_state), first_head)
                self.assertEqual(journal.execute("SELECT count(*) FROM witness_record").fetchone(),
                                 (1,))
                with self.assertRaises(InvalidSignature):
                    self.read_witness_journal(journal, completion_key.public_key(), first_head)

            with self.promotion_store() as authority, self.promotion_store() as peer, (
                    self.witness_journal()) as journal:
                retry = self.read_witness_journal(journal, public_key, first_head)
                self.revoke(_claim(_ALICE, version=1))
                (current, sig, pin), (chain, _) = self.archive_checkpoint(
                    2, archive_key, previous=prior)
                options = dict(pin=pin, epoch=2, key=archive_key.public_key(), chain=chain)
                with authority:
                    # Close local admission before publishing the new witness
                    # record. The competing connection has the old signed state.
                    authority.execute("BEGIN IMMEDIATE")
                    authority.execute("""UPDATE promotion SET generation=2,state_pin=?,
                        receipt=NULL,reconciled=0,staged=NULL,active=NULL WHERE id=1""",
                        (current['state'],))
                    with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                        self.reconcile_promotion(peer, retry)
                with self.assertRaisesRegex(PermissionError, 'receipt is unavailable'):
                    self.reconcile_promotion(peer, retry)

                self.stage_promotion(authority, 2, current, sig, **options)
                args = (2, current['state'], pin)
                completion = completion_key.sign(_canonical(['ci-completion-v1', *args]))
                receipt = self.promote(authority, *args, completion, completion_key.public_key())
                current_state = (2, current['state'], receipt)
                second_head = self.append_witness_record(
                    journal, journal_key, first_head, current_state)
                with closing(sqlite3.connect(self.directory / 'old-witness.sqlite')) as older:
                    self.assertEqual(self.read_witness_journal(older, public_key, first_head),
                                     old_state)
                    with self.assertRaisesRegex(PermissionError, 'independent head'):
                        self.read_witness_journal(older, public_key, second_head)
                verified = self.read_witness_journal(journal, public_key, second_head)
                with self.assertRaisesRegex(PermissionError, 'reconciled receipt'):
                    self.admitted_write(peer, 2, current['state'], verified, 'before-reconcile')
                self.reconcile_promotion(authority, verified)
                with self.assertRaisesRegex(PermissionError, 'current generation'):
                    self.promoted_review(peer, 2, current, sig, independent=retry, **options)
                self.assertEqual(self.promoted_review(
                    peer, 2, current, sig, independent=verified, **options), ())
                self.admitted_write(peer, 2, current['state'], verified, 'reconciled')
                self.assertEqual(peer.execute("SELECT operation FROM recovery_canary").fetchall(),
                                 [('reconciled',)])

    def test_staged_replica_requires_independent_completion_after_restart(self):
        with patch.dict(os.environ, BAM_EPHEMERAL_PG_TEST='1'):
            archive_key = Ed25519PrivateKey.generate()
            completion_key = Ed25519PrivateKey.generate()
            (checkpoint, sig, pin), (chain, _) = self.archive_checkpoint(1, archive_key)
            options = dict(pin=pin, epoch=1, key=archive_key.public_key(), chain=chain)
            args = (1, checkpoint['state'], pin)
            independent = (1, checkpoint['state'], None)
            message = _canonical(['ci-completion-v1', *args])
            acknowledgement = completion_key.sign(message)
            with self.promotion_store(initialize=True) as db:
                self.stage_promotion(db, 1, checkpoint, sig, **options)
            with self.promotion_store() as db:
                with self.assertRaisesRegex(PermissionError, 'not admitted'):
                    self.promoted_review(db, 1, checkpoint, sig, independent=independent, **options)
                with self.assertRaises(InvalidSignature):
                    self.promote(db, *args, archive_key.sign(message),
                                 completion_key.public_key())
                with self.assertRaises(InterruptedError):
                    self.promote(db, *args, acknowledgement, completion_key.public_key(),
                                 abort=True)
            with self.promotion_store() as db:
                self.assertEqual(db.execute("SELECT staged,active FROM promotion").fetchone(),
                                 (pin, None))
                receipt = self.promote(db, *args, acknowledgement, completion_key.public_key())
                self.assertEqual(
                    self.promote(db, *args, acknowledgement, completion_key.public_key()), receipt)
                independent = (1, checkpoint['state'], receipt)
                self.reconcile_promotion(db, independent)
                with self.assertRaisesRegex(PermissionError, 'not admitted'):
                    self.promoted_review(db, 2, checkpoint, sig, independent=independent, **options)
                self.assertEqual(self.promoted_review(db, 1, checkpoint, sig, independent=independent, **options),
                                 ('c' * 32,))

                # Even a promoted pointer is insufficient if ciphertext is
                # corrupted before a later review reopens it.
                ciphertext = self.directory / 'ciphertext-replica' / checkpoint['archive_name']
                raw = ciphertext.read_bytes()
                ciphertext.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
                with self.assertRaises(PermissionError):
                    self.promoted_review(db, 1, checkpoint, sig, independent=independent, **options)

    def test_new_revocation_invalidates_staged_candidate_and_old_review(self):
        with patch.dict(os.environ, BAM_EPHEMERAL_PG_TEST='1'):
            archive_key = Ed25519PrivateKey.generate()
            completion_key = Ed25519PrivateKey.generate()
            (old, old_sig, old_pin), prior = self.archive_checkpoint(1, archive_key)
            old_options = dict(pin=old_pin, epoch=1, key=archive_key.public_key(), chain=prior[0])
            with self.promotion_store(initialize=True) as db:
                self.stage_promotion(db, 1, old, old_sig, **old_options)
            self.revoke(_claim(_ALICE, version=1))
            (current, sig, pin), (chain, _) = self.archive_checkpoint(2, archive_key, previous=prior)
            options = dict(pin=pin, epoch=2, key=archive_key.public_key(), chain=chain)
            with self.promotion_store() as db, db:
                db.execute("""UPDATE promotion SET generation=generation+1,state_pin=?,
                    active=NULL,staged=NULL,receipt=NULL,reconciled=0 WHERE id=1""",
                    (current['state'],))
            with self.promotion_store() as db:
                args = (1, old['state'], old_pin)
                stale = completion_key.sign(_canonical(['ci-completion-v1', *args]))
                with self.assertRaisesRegex(PermissionError, 'candidate is stale'):
                    self.promote(db, *args, stale, completion_key.public_key())
                with self.assertRaisesRegex(PermissionError, 'authority moved'):
                    self.stage_promotion(db, 1, old, old_sig, **old_options)
                with self.assertRaisesRegex(PermissionError, 'issuer catalog differs'):
                    self.stage_promotion(db, 2, current, sig, issuers={}, **options)
                self.assertEqual(db.execute("SELECT staged,active FROM promotion").fetchone(),
                                 (None, None))
                self.stage_promotion(db, 2, current, sig, **options)
                args = (2, current['state'], pin)
                fresh = completion_key.sign(_canonical(['ci-completion-v1', *args]))
                receipt = self.promote(db, *args, fresh, completion_key.public_key())
                independent = (2, current['state'], receipt)
                self.reconcile_promotion(db, independent)
                self.assertEqual(self.promoted_review(
                    db, 2, current, sig, independent=independent, **options), ())

    def test_older_authority_restore_requires_current_receipt_after_lost_ack(self):
        with patch.dict(os.environ, BAM_EPHEMERAL_PG_TEST='1'):
            archive_key = Ed25519PrivateKey.generate()
            completion_key = Ed25519PrivateKey.generate()
            (old, old_sig, old_pin), prior = self.archive_checkpoint(1, archive_key)
            old_options = dict(pin=old_pin, epoch=1, key=archive_key.public_key(), chain=prior[0])
            with self.promotion_store(initialize=True) as db, closing(
                    sqlite3.connect(self.directory / 'old-authority.sqlite')) as old_authority:
                self.stage_promotion(db, 1, old, old_sig, **old_options)
                args = (1, old['state'], old_pin)
                signature = completion_key.sign(_canonical(['ci-completion-v1', *args]))
                receipt = self.promote(db, *args, signature, completion_key.public_key())
                self.reconcile_promotion(db, (1, old['state'], receipt))
                db.backup(old_authority)

                self.revoke(_claim(_ALICE, version=1))
                (current, sig, pin), (chain, _) = self.archive_checkpoint(
                    2, archive_key, previous=prior)
                options = dict(pin=pin, epoch=2, key=archive_key.public_key(), chain=chain)
                independent = (2, current['state'], None)
                old_authority.backup(db)

            with self.promotion_store() as db:
                self.assertEqual(db.execute("SELECT generation,reconciled FROM promotion").fetchone(),
                                 (1, 1))
                with self.assertRaisesRegex(PermissionError, 'current generation'):
                    self.promoted_review(db, 1, old, old_sig, independent=independent, **old_options)
                with self.assertRaisesRegex(PermissionError, 'current generation'):
                    self.admitted_write(db, 1, old['state'], independent, 'stale')
                self.assertEqual(self.begin_recovery(db, independent), 3)
                self.stage_promotion(db, 3, current, sig, **options)
                args = (3, current['state'], pin)
                signature = completion_key.sign(_canonical(['ci-completion-v1', *args]))
                self.promote(db, *args, signature, completion_key.public_key())
                # Drop the returned receipt to simulate a lost acknowledgement.
            with self.promotion_store() as db:
                pending = (3, current['state'], None)
                with self.assertRaisesRegex(PermissionError, 'reconciled receipt'):
                    self.promoted_review(db, 3, current, sig, independent=pending, **options)
                with self.assertRaisesRegex(PermissionError, 'reconciled receipt'):
                    self.admitted_write(db, 3, current['state'], pending, 'unreconciled')
                receipt = self.promote(db, *args, signature, completion_key.public_key())
                self.assertEqual(db.execute("SELECT receipt,reconciled FROM promotion").fetchone(),
                                 (receipt, 0))
                with self.assertRaisesRegex(PermissionError, 'receipt is unavailable'):
                    self.reconcile_promotion(db, (3, current['state'], '0' * 64))
                independent = (3, current['state'], receipt)
                self.reconcile_promotion(db, independent)
                self.assertEqual(self.promoted_review(
                    db, 3, current, sig, independent=independent, **options), ())
                self.admitted_write(db, 3, current['state'], independent, 'current')
                self.assertEqual(db.execute("SELECT * FROM recovery_canary").fetchall(),
                                 [('current', 3, receipt)])
