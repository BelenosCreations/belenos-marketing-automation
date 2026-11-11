"""Authorization boundary for native tenant-scoped offline content.

Does not expose HTTP routes or publish. Caller must use this facade for
all protected decisions; session issuance remains a separate security task.
"""
from access_policy import Action
from tenant_content import TenantContentStore

class TenantApprovalService:
    def __init__(self, db, sessions, directory):
        self.content=TenantContentStore(db)
        self.sessions=sessions
        self.directory=directory

    def _actor(self, token, tenant_id, action, now):
        session=self.sessions.resolve_current(token,directory=self.directory,now=now)
        if session is None or not self.directory.authorize(session.principal,action,tenant_id):
            raise PermissionError('Access denied')
        return session.principal.subject_id

    def decide_post(self, *, token, tenant_id, post_id, decision, now):
        post=self.content.get_post(tenant_id,post_id)
        if post is None:
            raise PermissionError('Post not owned by tenant')
        category=post[1]
        action=(Action.APPROVE_ROUTINE if category=='community' and decision in ('approved','rejected')
                else Action.APPROVE_PROMOTION)
        actor=self._actor(token,tenant_id,action,now)
        self.content.decide_post(tenant_id,post_id,actor,decision)

    def decide_event(self, *, token, tenant_id, event_id, confirmed, now):
        actor=self._actor(token,tenant_id,Action.APPROVE_PROMOTION,now)
        self.content.decide_event(tenant_id,event_id,confirmed)
