"""Server-side Google ID token verifier.

Requires optional google-auth dependency in a trusted backend deployment.
Never trust unverified client-submitted sub/email/email_verified claims.
This module performs no OAuth browser flow and stores no Google credentials.
"""
import time

class GoogleTokenVerifier:
    def __init__(self,*,client_id,verify_func=None):
        if not isinstance(client_id,str) or not client_id.strip():
            raise ValueError('Configured Google OAuth client ID required')
        self.client_id=client_id
        self._verify_func=verify_func

    def verify(self,*,id_token,expected_nonce=None,now=None):
        if not isinstance(id_token,str) or not 20<=len(id_token)<=16384:
            raise PermissionError('Invalid Google ID token')
        if expected_nonce is not None and (
                not isinstance(expected_nonce,str) or len(expected_nonce)<16):
            raise PermissionError('Invalid expected nonce')
        if self._verify_func is None:
            try:
                from google.auth.transport.requests import Request
                from google.oauth2 import id_token as google_id_token
            except ImportError as exc:
                raise RuntimeError('google-auth is required for Google sign-in') from exc
            try:
                claims=google_id_token.verify_oauth2_token(
                    id_token,Request(),self.client_id)
            except Exception as exc:
                raise PermissionError('Google token verification failed') from exc
        else:
            # Only trusted tests or a production server verifier may inject this.
            claims=self._verify_func(id_token,self.client_id)
        if not isinstance(claims,dict):
            raise PermissionError('Invalid verified Google claims')
        timestamp=int(time.time()) if now is None else now
        if type(timestamp) is not int or timestamp<0:
            raise ValueError('Invalid verification timestamp')
        issuer=claims.get('iss')
        audience=claims.get('aud')
        exp=claims.get('exp')
        iat=claims.get('iat')
        if (issuer not in ('accounts.google.com','https://accounts.google.com')
                or audience!=self.client_id or type(exp) is not int
                or exp<=timestamp or type(iat) is not int
                or iat>timestamp+60):
            raise PermissionError('Invalid Google token issuer, audience or time')
        if expected_nonce is not None and claims.get('nonce')!=expected_nonce:
            raise PermissionError('Google sign-in nonce mismatch')
        subject=claims.get('sub')
        email=claims.get('email')
        if (not isinstance(subject,str) or not subject.strip()
                or len(subject)>255 or not isinstance(email,str)
                or claims.get('email_verified') not in (True,'true')):
            raise PermissionError('Google account not verified')
        return {'google_sub':subject,'email':email,'email_verified':True}
