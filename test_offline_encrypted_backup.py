"""Synthetic encryption regression: no live PostgreSQL or stored secrets."""
import json
import os
import unittest
from offline_encrypted_backup import seal_disposable_backup, open_disposable_backup

_KEY = b'k' * 32
_SCHEMA = 'a' * 64
_BYTES = b'private synthetic table payload\n' * 24

class OfflineBackupEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get('BAM_EPHEMERAL_PG_TEST')
        os.environ['BAM_EPHEMERAL_PG_TEST'] = '1'

    def tearDown(self):
        if self.prev is None:
            os.environ.pop('BAM_EPHEMERAL_PG_TEST', None)
        else:
            os.environ['BAM_EPHEMERAL_PG_TEST'] = self.prev

    def seal(self):
        return seal_disposable_backup(
            plaintext=_BYTES, root_key=_KEY, schema_fingerprint=_SCHEMA, now=100)

    def recover(self, envelope, **changes):
        params = dict(envelope=envelope, root_key=_KEY,
                      expected_schema_fingerprint=_SCHEMA, now=101)
        params.update(changes)
        return open_disposable_backup(**params)

    def test_authenticated_roundtrip_randomized_and_private(self):
        a, b = self.seal(), self.seal()
        self.assertNotEqual(a, b)
        self.assertEqual(self.recover(a), _BYTES)
        self.assertNotIn(_BYTES, a)
        self.assertNotIn(_KEY, a)

    def test_wrong_key_schema_expiry_future_rejected(self):
        envelope = self.seal()
        for change in ({'root_key': b'x'*32},
                       {'expected_schema_fingerprint': 'b'*64},
                       {'now': 100 + 8*86400}, {'now': 99}):
            with self.subTest(change=change), self.assertRaises(PermissionError):
                self.recover(envelope, **change)

    def test_metadata_and_ciphertext_tampering_rejected(self):
        for field, value in (('purpose','live-restore'),
                             ('issued_at',101), ('salt','A'*24),
                             ('nonce','A'*16), ('ciphertext','A'*40)):
            obj = json.loads(self.seal())
            obj[field] = value
            with self.subTest(field=field), self.assertRaises((ValueError,PermissionError)):
                self.recover(json.dumps(obj).encode())

    def test_invalid_format_length_and_types(self):
        obj = json.loads(self.seal())
        obj['extra'] = 'unsafe'
        with self.assertRaises(ValueError):
            self.recover(json.dumps(obj).encode())
        for value in (b'', b'not-json', b'['*100, b'x'*(8*1024*1024+1)):
            with self.assertRaises(ValueError):
                self.recover(value)
        for value in (b'', b'a'*(4*1024*1024+1), 'not-bytes'):
            with self.assertRaises(ValueError):
                seal_disposable_backup(plaintext=value, root_key=_KEY,
                                       schema_fingerprint=_SCHEMA, now=100)
        with self.assertRaises(ValueError):
            self.recover(self.seal(), now=True)

    def test_requires_disposable_test_gate_and_valid_key(self):
        envelope = self.seal()
        with self.assertRaises(ValueError):
            self.recover(envelope, root_key=b'weak')
        os.environ.pop('BAM_EPHEMERAL_PG_TEST')
        with self.assertRaises(PermissionError):
            self.recover(envelope)
        with self.assertRaises(PermissionError):
            self.seal()

if __name__ == '__main__':
    unittest.main()
