"""Authenticated application boundary for business-specific Content Requests.

Offline only. Session tokens must be issued by a trusted identity flow.
This service cannot schedule or publish, and does not verify asset existence.
"""
import time
from access_policy import Action, Principal

class ContentRequestService:
    def __init__(self, *, requests, sessions, directory, attachments):
        self.requests=requests
        self.sessions=sessions
        self.directory=directory
        self.attachments=attachments

    def _authorize(self, *, token, tenant_id, action, now):
        session=self.sessions.resolve_current(token,directory=self.directory,now=now)
        if session is None:
            raise PermissionError('Authentication required')
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if (member is None or session.principal.tenant_id!=tenant_id
                or not self.directory.authorize(
                    Principal(member.subject_id,tenant_id,member.role),action,tenant_id)):
            raise PermissionError('Content request access denied')

    @staticmethod
    def _now(now):
        return int(time.time()) if now is None else now

    def create(self, *, token, tenant_id, channel, draft_text, suggestion,
               required_items, priority=0, now=None):
        now=self._now(now)
        self._authorize(token=token,tenant_id=tenant_id,action=Action.CREATE_DRAFT,now=now)
        return self.requests.create(tenant_id=tenant_id,channel=channel,
            draft_text=draft_text,suggestion=suggestion,
            required_items=required_items,priority=priority,now=now)

    def get(self, *, token, tenant_id, request_id, now=None):
        now=self._now(now)
        self._authorize(token=token,tenant_id=tenant_id,action=Action.READ_DRAFTS,now=now)
        return self.requests.get(tenant_id=tenant_id,request_id=request_id)

    def list_for_business(self, *, token, tenant_id, status=None, now=None):
        now=self._now(now)
        self._authorize(token=token,tenant_id=tenant_id,action=Action.READ_DRAFTS,now=now)
        return self.requests.list_for_business(tenant_id=tenant_id,status=status)

    def provide(self, *, token, tenant_id, request_id, item, attachment_id, now=None):
        now=self._now(now)
        self._authorize(token=token,tenant_id=tenant_id,action=Action.EDIT_DRAFT,now=now)
        verified=self.attachments.resolve_verified(tenant_id=tenant_id,
            request_id=request_id,item=item,attachment_id=attachment_id)
        if verified is None:
            raise PermissionError('Verified attachment for this request and item required')
        return self.requests.provide(tenant_id=tenant_id,request_id=request_id,
            item=item,content_reference='verified-attachment:'+verified,now=now)

    def set_hold(self, *, token, tenant_id, request_id, status, now=None):
        now=self._now(now)
        self._authorize(token=token,tenant_id=tenant_id,action=Action.EDIT_DRAFT,now=now)
        return self.requests.set_hold(tenant_id=tenant_id,request_id=request_id,
            status=status,now=now)
