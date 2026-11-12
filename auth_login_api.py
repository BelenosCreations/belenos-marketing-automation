"""Trusted BAM authentication entrypoint.

No automatic membership provisioning, social login, or password reset.
Production must supply a verified Google verifier and network-level rate limits.
"""
import time

class AuthLoginAPI:
    def __init__(self,*,auth,google_verifier,challenges,throttle=None,
                 invitations=None,allow_invitation_redemption=False):
        if type(allow_invitation_redemption) is not bool:
            raise ValueError('Explicit invitation redemption switch required')
        if allow_invitation_redemption and (
                invitations is None or throttle is None):
            raise ValueError('Trusted invitation service and rate limit required')
        self.invitations=invitations
        self.allow_invitation_redemption=allow_invitation_redemption
        self.auth=auth
        self.google_verifier=google_verifier
        self.challenges=challenges
        self.throttle=throttle

    @staticmethod
    def _now(now):
        timestamp=int(time.time()) if now is None else now
        if type(timestamp) is not int or timestamp<0:
            raise ValueError('Invalid time')
        return timestamp

    def password_login(self,*,email,password,tenant_id,server_now):
        timestamp=self._now(server_now)
        if self.throttle is not None:
            self.throttle.check(email=email,now=timestamp)
        try:
            token=self.auth.login_password(email=email,password=password,
                tenant_id=tenant_id,now=timestamp)
        except PermissionError:
            if self.throttle is not None:
                self.throttle.failure(email=email,now=timestamp)
            raise
        if self.throttle is not None:
            self.throttle.success(email=email)
        return {'session_token':token,'publishing_enabled':False}

    def redeem_invitation_password(self,*,email,password,token,server_now):
        """Trusted internal gate for new members, not an HTTP endpoint.

        Does not issue a session. Both this explicit switch and a trusted
        shared credential throttle are mandatory; any future HTTP adapter
        must also enforce IP/global limits, HTTPS and safe response handling.
        """
        if not self.allow_invitation_redemption:
            raise PermissionError('Invitation redemption unavailable')
        timestamp=self._now(server_now)
        self.throttle.check(email=email,now=timestamp)
        try:
            result=self.invitations.accept_password_trusted(
                email=email,password=password,token=token,now=timestamp)
        except (PermissionError,ValueError):
            self.throttle.failure(email=email,now=timestamp)
            raise PermissionError('Invitation redemption unavailable') from None
        self.throttle.success(email=email)
        # An invitation is never an authenticated session. Login using the
        # newly granted business membership is a separate credential step.
        return {**result,'session_token':None}

    def begin_google(self,*,server_now):
        return self.challenges.begin(now=self._now(server_now))

    def google_login(self,*,challenge_id,id_token,tenant_id,server_now):
        timestamp=self._now(server_now)
        nonce=self.challenges.consume(challenge_id=challenge_id,now=timestamp)
        claims=self.google_verifier.verify(id_token=id_token,
            expected_nonce=nonce,now=timestamp)
        token=self.auth.login_google_verified(tenant_id=tenant_id,now=timestamp,
            **claims)
        return {'session_token':token,'publishing_enabled':False}

    def register_google(self,*,challenge_id,id_token,server_now):
        """Create Google-only BAM identity, pending business invitation."""
        timestamp=self._now(server_now)
        nonce=self.challenges.consume(challenge_id=challenge_id,now=timestamp)
        claims=self.google_verifier.verify(id_token=id_token,
            expected_nonce=nonce,now=timestamp)
        subject=self.auth.register_google_verified(now=timestamp,**claims)
        return {'subject_id':subject,'business_membership_required':True,
                'session_token':None,'publishing_enabled':False}

    def link_google_with_password(self,*,session_token,password,
                                  challenge_id,id_token,server_now):
        """Explicit link with a fresh password proof; never email auto-link."""
        timestamp=self._now(server_now)
        session=self.auth.sessions.resolve_current(
            session_token,directory=self.auth.directory,now=timestamp)
        if session is None:
            raise PermissionError('Active BAM session required')
        row=self.auth.db.execute("""SELECT email FROM bam_identities
            WHERE subject_id=? AND active=1 AND email_verified=1""",
            (session.principal.subject_id,)).fetchone()
        if row is None:
            raise PermissionError('Verified BAM account required')
        # Require password reauthentication before linking external identity.
        probe=self.auth.login_password(email=row[0],password=password,
            tenant_id=session.principal.tenant_id,now=timestamp)
        self.auth.sessions.revoke(probe,now=timestamp)
        nonce=self.challenges.consume(challenge_id=challenge_id,now=timestamp)
        claims=self.google_verifier.verify(id_token=id_token,
            expected_nonce=nonce,now=timestamp)
        self.auth.link_google_verified(subject_id=session.principal.subject_id,
            **claims)
        return {'linked':True,'publishing_enabled':False}
