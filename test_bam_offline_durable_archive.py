"""Disposable ciphertext durability regression; no production backup operation."""
import os
import pathlib
import stat
import tempfile
import unittest

from offline_encrypted_backup import seal_disposable_backup
from bam_offline_durable_archive import (
    store_disposable_ciphertext, restore_disposable_ciphertext)

_KEY = b'a' * 32
_SCHEMA = 'c' * 64
_TEXT = b'SYNTHETIC_ONLY_123' * 32


class OfflineDurableArchiveTests(unittest.TestCase):
    def setUp(self):
        self.previous = os.environ.get('BAM_EPHEMERAL_PG_TEST')
        os.environ['BAM_EPHEMERAL_PG_TEST'] = '1'
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = self.tmp.name
        os.chmod(self.directory, 0o700)
        self.env = seal_disposable_backup(
            plaintext=_TEXT, root_key=_KEY, schema_fingerprint=_SCHEMA, now=100)

    def tearDown(self):
        self.tmp.cleanup()
        if self.previous is None:
            os.environ.pop('BAM_EPHEMERAL_PG_TEST', None)
        else:
            os.environ['BAM_EPHEMERAL_PG_TEST'] = self.previous

    def put(self, **kwargs):
        settings = dict(directory=self.directory, name='backup_01.bamenc',
                        envelope=self.env, root_key=_KEY,
                        schema_fingerprint=_SCHEMA, now=101)
        settings.update(kwargs)
        return store_disposable_ciphertext(**settings)

    def get(self, receipt, **kwargs):
        settings = dict(directory=self.directory, name='backup_01.bamenc',
                        root_key=_KEY, schema_fingerprint=_SCHEMA,
                        now=101, expected_ciphertext_sha256=receipt['ciphertext_sha256'])
        settings.update(kwargs)
        return restore_disposable_ciphertext(**settings)

    def test_atomic_private_ciphertext_and_authenticated_restore(self):
        receipt = self.put()
        path = pathlib.Path(self.directory) / 'backup_01.bamenc'
        self.assertTrue(path.is_file())
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertNotIn(_TEXT, path.read_bytes())
        self.assertNotIn(_KEY, path.read_bytes())
        self.assertEqual(path.read_bytes(), self.env)
        self.assertEqual(self.get(receipt), _TEXT)
        self.assertFalse(receipt['offsite_copy_verified'])
        self.assertFalse(receipt['production_ready'])
        self.assertEqual(list(pathlib.Path(self.directory).glob('.stage-*')), [])

    def test_existing_archive_is_never_replaced(self):
        first = self.put()
        with self.assertRaises(FileExistsError):
            self.put(envelope=seal_disposable_backup(
                plaintext=b'other synthetic', root_key=_KEY,
                schema_fingerprint=_SCHEMA, now=100))
        self.assertEqual(self.get(first), _TEXT)

    def test_mutation_wrong_key_wrong_pin_and_tampering_rejected(self):
        receipt = self.put()
        with self.assertRaises(PermissionError):
            self.get(receipt, root_key=b'x' * 32)
        with self.assertRaises(PermissionError):
            self.get(receipt, expected_ciphertext_sha256='0' * 64)
        with self.assertRaises(ValueError):
            self.get(receipt, expected_ciphertext_sha256='not-sha256')
        path = pathlib.Path(self.directory) / 'backup_01.bamenc'
        mutated = bytearray(path.read_bytes())
        mutated[-4] ^= 1
        path.write_bytes(mutated)
        with self.assertRaises(PermissionError):
            self.get(receipt)

    def test_symlink_hardlink_and_world_readable_archive_rejected(self):
        receipt = self.put()
        path = pathlib.Path(self.directory) / 'backup_01.bamenc'
        other = pathlib.Path(self.directory) / 'other.bamenc'
        os.link(path, other)
        with self.assertRaises(PermissionError):
            self.get(receipt)
        other.unlink()
        path.chmod(0o644)
        with self.assertRaises(PermissionError):
            self.get(receipt)
        path.unlink()
        other.write_bytes(self.env)
        path.symlink_to(other)
        with self.assertRaises(OSError):
            self.get(receipt)

    def test_disabled_gate_bad_root_and_unsafe_filename(self):
        for filename in ('../backup.bamenc', 'x/backup.bamenc', 'invalid.txt',
                         '.hidden.bamenc', 'a' * 60 + '.bamenc'):
            with self.subTest(filename=filename), self.assertRaises(ValueError):
                self.put(name=filename)
        with self.assertRaises(ValueError):
            self.put(directory='relative/path')
        os.chmod(self.directory, 0o755)
        with self.assertRaises(PermissionError):
            self.put()
        os.chmod(self.directory, 0o700)
        os.environ.pop('BAM_EPHEMERAL_PG_TEST')
        with self.assertRaises(PermissionError):
            self.put()


if __name__ == '__main__':
    unittest.main()
