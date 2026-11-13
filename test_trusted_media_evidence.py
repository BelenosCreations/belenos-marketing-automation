import hashlib
import hmac
import json
import unittest
from trusted_media_evidence import OfflineMediaEvidenceGate

_SCAN_KEY=b'synthetic-scanner-worker-secret-1234567890'
_RIGHTS_KEY=b'synthetic-rights-reviewer-secret-123456789'
_BINDING={'attachment_id':'a'*32,'tenant_id':'shop-a',
          'request_id':'request1','item':'image','media_type':'image/png',
          'sha256':'f'*64}


def signed(claim,key):
    claim=dict(claim)
    payload=json.dumps(claim,sort_keys=True,separators=(',',':'),
                       ensure_ascii=True).encode('utf-8')
    claim['signature']=hmac.new(key,payload,hashlib.sha256).hexdigest()
    return claim


class OfflineMediaEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.gate=OfflineMediaEvidenceGate(scanner_key=_SCAN_KEY,
                                           rights_key=_RIGHTS_KEY)
        self.pending={**_BINDING,'status':'pending',
                      'created_at':100,'storage_key':'private/synthetic'}
        self.scan=signed({**_BINDING,'kind':'scan','verdict':'clean',
                          'issuer':'scanner-worker','engine':'synthetic',
                          'issued_at':110,'expires_at':200},_SCAN_KEY)
        self.rights=signed({**_BINDING,'kind':'rights',
                            'verdict':'authorized','issuer':'rights-reviewer',
                            'basis':'owned','proof_ref':'synthetic-record',
                            'channel':'facebook',
                            'issued_at':110,'expires_at':200},_RIGHTS_KEY)

    def check(self,**changes):
        options={'pending':self.pending,'scan':self.scan,
                 'rights':self.rights,'channel':'facebook','now':150}
        options.update(changes)
        return self.gate.verify(**options)

    def test_valid_separate_signed_claims_are_nonpublishing_only(self):
        report=self.check()
        self.assertEqual(report['status'],'offline_evidence_contract_passed')
        for value in (_SCAN_KEY,_RIGHTS_KEY,self.pending['storage_key'],
                      self.pending['sha256'],self.pending['tenant_id']):
            if type(value) is bytes:
                value=value.decode('ascii')
            self.assertNotIn(value,str(report))
        self.assertFalse(report['actual_scanning_performed'])
        self.assertFalse(report['attachment_state_changed'])
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['publishing_enabled'])

    def test_keys_must_be_independent_and_server_managed(self):
        for a,b in ((b'weak',_RIGHTS_KEY),(_SCAN_KEY,_SCAN_KEY),
                    ('not-bytes',_RIGHTS_KEY)):
            with self.assertRaises(ValueError):
                OfflineMediaEvidenceGate(scanner_key=a,rights_key=b)

    def test_pending_only(self):
        with self.assertRaises(ValueError):
            self.check(pending=dict(self.pending,status='verified'))
        with self.assertRaises(ValueError):
            self.check(pending=dict(self.pending,sha256='garbage'))

    def test_wrong_tenant_attachment_and_digest_rejected(self):
        for field,value in (('tenant_id','other'),('attachment_id','b'*32),
                            ('sha256','e'*64),('item','artwork')):
            with self.subTest(field=field):
                with self.assertRaises(PermissionError):
                    self.check(pending=dict(self.pending,**{field:value}))

    def test_cannot_use_scanner_signature_as_rights_signature(self):
        with self.assertRaises(PermissionError):
            self.check(rights=signed({k:v for k,v in self.rights.items()
                                      if k!='signature'},_SCAN_KEY))

    def test_tampering_with_evidence_rejected(self):
        for change in ({'verdict':'clean-ish'},
                       {'engine':'untrusted'}, {'issued_at':120},
                       {'tenant_id':'other'}):
            with self.subTest(change=change):
                with self.assertRaises(PermissionError):
                    self.check(scan=dict(self.scan,**change))

    def test_signed_nonclean_or_unlicensed_claims_are_rejected(self):
        for field,value in (('verdict','not-clean'),
                            ('engine',''),('issued_at',99)):
            with self.subTest(field=field):
                fields={k:v for k,v in self.scan.items() if k!='signature'}
                fields[field]=value
                with self.assertRaises(PermissionError):
                    self.check(scan=signed(fields,_SCAN_KEY))
        for field,value in (('basis','unknown'),('verdict','denied'),
                            ('proof_ref',''),('channel','instagram')):
            with self.subTest(field=field):
                fields={k:v for k,v in self.rights.items() if k!='signature'}
                fields[field]=value
                with self.assertRaises(PermissionError):
                    self.check(rights=signed(fields,_RIGHTS_KEY))

    def test_expired_or_future_dated_claim_rejected(self):
        with self.assertRaises(PermissionError):
            self.check(now=200)
        with self.assertRaises(PermissionError):
            self.check(now=109)
        with self.assertRaises(PermissionError):
            self.check(rights=signed(
                {**{k:v for k,v in self.rights.items() if k!='signature'},
                 'expires_at':100000},_RIGHTS_KEY))

    def test_missing_fields_and_invalid_types_rejected(self):
        with self.assertRaises(ValueError):
            self.check(scan={k:v for k,v in self.scan.items() if k!='engine'})
        with self.assertRaises(ValueError):
            self.check(now=True)
        with self.assertRaises(ValueError):
            self.check(channel='unknown')
        with self.assertRaises(PermissionError):
            self.check(scan=dict(self.scan,signature='0'*64))


if __name__=='__main__':
    unittest.main()
