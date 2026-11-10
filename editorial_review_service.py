"""Offline authenticated editorial review boundary.

Never exposes publish or scheduling actions. Caller must supply trusted,
freshly resolved creator identity, candidate and competitor classification.
"""
from access_policy import Action, Principal

class EditorialReviewService:
    def __init__(self, *, inbox, sessions, directory):
        self.inbox=inbox
        self.sessions=sessions
        self.directory=directory

    def recheck(self, *, token, tenant_id, topic, candidate, platform,
                account_id, identity_verified=False,
                local_competitor_risk='unknown', now=None):
        session=self.sessions.resolve(token,now=now)
        if session is None:
            raise PermissionError('Authentication required')
        # A token issued for one tenant can authenticate the subject, but the
        # directory MUST confirm current membership in the requested tenant.
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if member is None or not self.directory.authorize(
            Principal(member.subject_id,tenant_id,member.role),
            Action.APPROVE_ROUTINE,tenant_id):
            raise PermissionError('Editorial review access denied')
        return self.inbox.recheck_for_editorial_review(
            tenant_id=tenant_id,topic=topic,candidate=candidate,
            platform=platform,account_id=account_id,
            identity_verified=identity_verified,
            local_competitor_risk=local_competitor_risk)
