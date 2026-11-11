"""Authenticated review-only intake from trusted verification attestations.

This service does not fetch social content or publish it. It intentionally
does not accept client-supplied identity/competitor clearance flags.
"""
import time
from access_policy import Action, Principal

class EditorialIntakeService:
    def __init__(self, *, inbox, sessions, directory, attestations):
        self.inbox=inbox
        self.sessions=sessions
        self.directory=directory
        self.attestations=attestations

    def consider(self, *, token, tenant_id, topic, candidate, now=None):
        timestamp=int(time.time()) if now is None else now
        session=self.sessions.resolve_current(
            token,directory=self.directory,now=timestamp)
        if session is None:
            raise PermissionError('Authentication required')
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if (session.principal.tenant_id!=tenant_id or member is None or
                not self.directory.authorize(
                    Principal(member.subject_id,tenant_id,member.role),
                    Action.APPROVE_ROUTINE,tenant_id)):
            raise PermissionError('Editorial intake access denied')
        verified=self.attestations.resolve(
            tenant_id=tenant_id,original_url=candidate.original_url,now=timestamp)
        if verified is None:
            return 'approval_required','fresh_server_verification_required'
        return self.inbox.consider(tenant_id=tenant_id,topic=topic,
                                   candidate=candidate,**verified)
