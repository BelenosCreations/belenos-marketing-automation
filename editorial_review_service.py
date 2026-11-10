"""Authenticated editorial review with trusted, expiring server attestations.

No mobile-provided identity_verified or competitor clearance accepted.
No scheduling, posting, or media reuse is authorized here.
"""
import time
from access_policy import Action, Principal

class EditorialReviewService:
    def __init__(self, *, inbox, sessions, directory, attestations):
        self.inbox=inbox
        self.sessions=sessions
        self.directory=directory
        self.attestations=attestations

    def recheck(self, *, token, tenant_id, topic, candidate, now=None):
        timestamp=int(time.time()) if now is None else now
        session=self.sessions.resolve(token,now=timestamp)
        if session is None:
            raise PermissionError('Authentication required')
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if member is None or not self.directory.authorize(
            Principal(member.subject_id,tenant_id,member.role),
            Action.APPROVE_ROUTINE,tenant_id):
            raise PermissionError('Editorial review access denied')
        attestation=self.attestations.resolve(
            tenant_id=tenant_id,original_url=candidate.original_url,now=timestamp)
        if attestation is None:
            return 'approval_required','fresh_server_verification_required'
        return self.inbox.recheck_for_editorial_review(
            tenant_id=tenant_id,topic=topic,candidate=candidate,**attestation)
