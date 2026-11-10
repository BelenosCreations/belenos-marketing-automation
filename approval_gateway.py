"""Offline authenticated-session approval facade; never publishes or schedules posts."""
from access_policy import Action
from workflow import record_approval, decide_event
from tenant_resources import TenantResources

class ApprovalGateway:
    def __init__(self, sessions, directory, db):
        self.sessions = sessions
        self.directory = directory
        self.db = db
        self.ownership = TenantResources(db)

    def _principal(self, token, tenant_id, action, now):
        session = self.sessions.resolve(token, now=now)
        if session is None or not self.directory.authorize(session.principal, action, tenant_id):
            raise PermissionError('Access denied')
        return self.directory.resolve(tenant_id, session.principal.subject_id)

    def decide_post(self, *, token, tenant_id, post_id, decision, at):
        if decision not in ('approved', 'rejected', 'revoked'):
            raise ValueError('Invalid decision')
        row = self.db.execute('SELECT classification, status FROM posts WHERE id=?', (post_id,)).fetchone()
        if row is None or row[1] == 'blocked':
            raise ValueError('Unknown or blocked post')
        self.ownership.require(kind='post', resource_id=post_id, tenant_id=tenant_id)
        action = Action.APPROVE_PROMOTION if row[0] != 'community' or decision == 'revoked' else Action.APPROVE_ROUTINE
        principal = self._principal(token, tenant_id, action, int(at.timestamp()))
        record_approval(self.db, post_id=post_id, decision=decision, actor=principal.subject_id, at=at)

    def decide_event(self, *, token, tenant_id, event_id, confirmed, at):
        self.ownership.require(kind='event', resource_id=event_id, tenant_id=tenant_id)
        principal = self._principal(token, tenant_id, Action.APPROVE_PROMOTION, int(at.timestamp()))
        decide_event(self.db, event_id=event_id, confirmed=confirmed, actor=principal.subject_id, at=at)
