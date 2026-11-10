"""Fail-closed request adapter for BAM account and held-draft workflows.

This is not an HTTP server. A future HTTPS transport must authenticate the
caller, provide a bearer session token and perform rate limiting/CSRF controls.
The adapter never accepts tenant IDs or roles from client body claims.
"""
from account_dashboard import AccountDashboard
from dashboard_cards import build_dashboard_cards
from dashboard_view import build_dashboard_view

class AccountReadAPI:
    def __init__(self, dashboard: AccountDashboard):
        self.dashboard=dashboard

    @staticmethod
    def _token(value):
        if not isinstance(value,str) or not value.strip() or len(value)>2048:
            raise PermissionError('Valid BAM session required')
        return value

    @staticmethod
    def _now(value):
        if type(value) is not int or value<0:
            raise ValueError('Server timestamp required')
        return value

    def get_overview(self, *, session_token, server_now):
        """Read-only current business overview; no caller-supplied tenant."""
        overview=self.dashboard.overview(
            token=self._token(session_token),now=self._now(server_now))
        overview['dashboard_cards']=build_dashboard_cards(overview)['cards']
        return overview

    def get_dashboard_view(self, *, session_token, server_now):
        """Minimal presentation payload from authenticated tenant data."""
        overview=self.get_overview(session_token=session_token,server_now=server_now)
        return build_dashboard_view(overview)

    def activate_business(self, *, session_token, target_tenant_id, server_now):
        """Change business only after verifying target membership.

        Return a replacement session token only through a trusted transport.
        """
        if (not isinstance(target_tenant_id,str)
                or not target_tenant_id.strip()
                or len(target_tenant_id)>128):
            raise ValueError('Valid target business required')
        result=self.dashboard.switch_and_overview(
            token=self._token(session_token),
            target_tenant_id=target_tenant_id,now=self._now(server_now))
        result['overview']['dashboard_cards']=build_dashboard_cards(result['overview'])['cards']
        return result

    def logout(self, *, session_token, server_now):
        token=self._token(session_token)
        self._now(server_now)
        self.dashboard.sessions.revoke(token,now=server_now)
        return {'signed_out':True,'publishing_enabled':False}

    def logout_everywhere(self, *, session_token, server_now):
        """Revoke only the authenticated identity's sessions across businesses."""
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        count=self.dashboard.sessions.revoke_identity(
            session.principal.subject_id,now=now)
        return {'signed_out':True,'sessions_revoked':count,
                'publishing_enabled':False}

    def create_held_draft(self, *, session_token, server_now,
                          channel, draft_text, suggestion, required_items,
                          priority=0):
        """Create a business-scoped content request, never a scheduled post."""
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        service=self.dashboard.content_service
        if service is None:
            raise RuntimeError('Content Requests not configured')
        if (not isinstance(channel,str) or channel not in
                ('facebook','instagram','linkedin','pinterest','tiktok','youtube')):
            raise ValueError('Unsupported content channel')
        for value in (draft_text,suggestion):
            if not isinstance(value,str) or not value.strip() or len(value)>2000:
                raise ValueError('Invalid draft or content suggestion')
        if (not isinstance(required_items,list) or not 1<=len(required_items)<=12
                or any(not isinstance(item,str) or not item.strip()
                       or len(item)>80 for item in required_items)
                or len(set(required_items))!=len(required_items)):
            raise ValueError('Invalid required content items')
        if type(priority) is not int or not -10<=priority<=10:
            raise ValueError('Invalid priority')
        request_id=service.create(token=token,tenant_id=session.principal.tenant_id,
            channel=channel,draft_text=draft_text,suggestion=suggestion,
            required_items=required_items,priority=priority,now=now)
        return {'tenant_id':session.principal.tenant_id,
                'request_id':request_id,'status':'needs_content',
                'publishing_enabled':False}

    def update_draft_hold(self, *, session_token, server_now, request_id, status):
        """Postpone, mark unavailable or reopen an incomplete draft."""
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        service=self.dashboard.content_service
        if service is None:
            raise RuntimeError('Content Requests not configured')
        if (not isinstance(request_id,str) or len(request_id)!=32
                or any(char not in '0123456789abcdef' for char in request_id)):
            raise ValueError('Invalid request ID')
        if status not in ('postponed','unavailable','needs_content'):
            raise ValueError('Invalid hold status')
        result=service.set_hold(token=token,tenant_id=session.principal.tenant_id,
                                request_id=request_id,status=status,now=now)
        return {'tenant_id':session.principal.tenant_id,'request_id':request_id,
                'status':result,'publishing_enabled':False}
