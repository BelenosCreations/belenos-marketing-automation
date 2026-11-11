import unittest
from google_token_verifier import GoogleTokenVerifier

class GoogleVerifierTests(unittest.TestCase):
    def setUp(self):
        self.claims={'iss':'https://accounts.google.com','aud':'client-id',
            'exp':200,'iat':100,'sub':'google-sub','email':'owner@example.com',
            'email_verified':True,'nonce':'nonce-value-123456789'}
        self.verifier=GoogleTokenVerifier(client_id='client-id',
            verify_func=lambda token,audience:self.claims.copy())

    def verify(self):
        return self.verifier.verify(id_token='x'*24,now=110,
                                    expected_nonce='nonce-value-123456789')

    def test_verified_claims(self):
        self.assertEqual(self.verify()['google_sub'],'google-sub')

    def test_wrong_audience(self):
        self.claims['aud']='attacker'
        with self.assertRaises(PermissionError):self.verify()

    def test_expired(self):
        self.claims['exp']=110
        with self.assertRaises(PermissionError):self.verify()

    def test_issuer(self):
        self.claims['iss']='https://attacker.example'
        with self.assertRaises(PermissionError):self.verify()

    def test_nonce(self):
        self.claims['nonce']='wrong'
        with self.assertRaises(PermissionError):self.verify()

    def test_unverified_email(self):
        self.claims['email_verified']=False
        with self.assertRaises(PermissionError):self.verify()

    def test_missing_subject(self):
        self.claims['sub']=''
        with self.assertRaises(PermissionError):self.verify()

    def test_future_issue_time(self):
        self.claims['iat']=500
        with self.assertRaises(PermissionError):self.verify()

    def test_invalid_token(self):
        with self.assertRaises(PermissionError):
            self.verifier.verify(id_token='short',now=110)

if __name__=='__main__':unittest.main()
