"""CI-only authenticated backup envelope; no file writes or production activation."""
import base64
import binascii
import json
import os
import re
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_FORMAT = 'bam-disposable-backup-envelope-v1'
_INFO = b'BAM disposable PostgreSQL backup envelope v1'
_MAX_PLAINTEXT = 4 * 1024 * 1024
_MAX_ENVELOPE = 8 * 1024 * 1024
_MAX_AGE = 7 * 24 * 60 * 60
_FIELDS = {'format', 'purpose', 'schema_fingerprint', 'issued_at',
           'salt', 'nonce', 'ciphertext'}
_FINGERPRINT = re.compile(r'[0-9a-f]{64}\Z')


def _guard(key, fingerprint, now):
    if os.environ.get('BAM_EPHEMERAL_PG_TEST') != '1':
        raise PermissionError('Disposable offline backup rehearsal only')
    if type(key) is not bytes or len(key) != 32:
        raise ValueError('A separately managed 32-byte backup key is required')
    if (type(fingerprint) is not str or
            _FINGERPRINT.fullmatch(fingerprint) is None):
        raise ValueError('Exact reviewed schema fingerprint required')
    if type(now) is not int or now < 0:
        raise ValueError('Invalid operator-supplied time')


def _canonical(header):
    return json.dumps(header, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True).encode('ascii')


def _derive(key, salt):
    return HKDF(algorithm=SHA256(), length=32, salt=salt, info=_INFO).derive(key)


def _b64(value):
    return base64.b64encode(value).decode('ascii')


def _unb64(value, size):
    if type(value) is not str or len(value) > 2 * size + 8:
        raise ValueError('Invalid backup envelope field')
    try:
        data = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('Invalid backup envelope encoding') from exc
    if len(data) != size:
        raise ValueError('Invalid backup envelope field length')
    return data


def seal_disposable_backup(*, plaintext, root_key, schema_fingerprint, now):
    """Encrypt synthetic rehearsal bytes without persisting them."""
    _guard(root_key, schema_fingerprint, now)
    if (type(plaintext) is not bytes or
            not 0 < len(plaintext) <= _MAX_PLAINTEXT):
        raise ValueError('Invalid bounded synthetic backup data')
    salt, nonce = os.urandom(16), os.urandom(12)
    header = {'format': _FORMAT, 'purpose': 'synthetic-ci-restore-rehearsal',
              'schema_fingerprint': schema_fingerprint,
              'issued_at': now, 'salt': _b64(salt), 'nonce': _b64(nonce)}
    ciphertext = AESGCM(_derive(root_key, salt)).encrypt(
        nonce, plaintext, _canonical(header))
    result = _canonical({**header, 'ciphertext': _b64(ciphertext)})
    if len(result) > _MAX_ENVELOPE:
        raise ValueError('Synthetic backup envelope is too large')
    return result


def open_disposable_backup(*, envelope, root_key,
                           expected_schema_fingerprint, now):
    """Authenticate schema/freshness/metadata/ciphertext before release."""
    _guard(root_key, expected_schema_fingerprint, now)
    if (type(envelope) is not bytes or
            not 0 < len(envelope) <= _MAX_ENVELOPE):
        raise ValueError('Invalid synthetic backup envelope')
    try:
        obj = json.loads(envelope.decode('ascii'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Malformed synthetic backup envelope') from exc
    if type(obj) is not dict or set(obj) != _FIELDS:
        raise ValueError('Unexpected backup envelope metadata')
    if (obj['format'] != _FORMAT or
            obj['purpose'] != 'synthetic-ci-restore-rehearsal' or
            type(obj['schema_fingerprint']) is not str or
            obj['schema_fingerprint'] != expected_schema_fingerprint or
            type(obj['issued_at']) is not int or
            not now - _MAX_AGE <= obj['issued_at'] <= now):
        raise PermissionError('Backup source or freshness check failed')
    salt = _unb64(obj['salt'], 16)
    nonce = _unb64(obj['nonce'], 12)
    encoded = obj['ciphertext']
    if type(encoded) is not str or len(encoded) > 2 * (_MAX_PLAINTEXT + 16) + 8:
        raise ValueError('Invalid backup ciphertext size')
    try:
        ciphertext = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError('Malformed backup ciphertext') from exc
    if not 16 < len(ciphertext) <= _MAX_PLAINTEXT + 16:
        raise ValueError('Invalid backup ciphertext length')
    header = {k: obj[k] for k in obj if k != 'ciphertext'}
    try:
        plaintext = AESGCM(_derive(root_key, salt)).decrypt(
            nonce, ciphertext, _canonical(header))
    except Exception as exc:
        raise PermissionError('Backup authentication failed') from exc
    if not 0 < len(plaintext) <= _MAX_PLAINTEXT:
        raise ValueError('Invalid decrypted backup size')
    return plaintext
