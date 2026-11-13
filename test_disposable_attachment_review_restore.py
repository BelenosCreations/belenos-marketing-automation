"""CI rehearsal for restoring a typed attachment review and revocation index."""
from contextlib import closing
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

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
