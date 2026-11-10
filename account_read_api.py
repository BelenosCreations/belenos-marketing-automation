"""Fail-closed request adapter for the offline BAM account dashboard.

This is not an HTTP server. A future HTTPS transport must authenticate the
caller, provide a bearer session token and perform rate limiting/CSRF controls.
The adapter never accepts tenant IDs or roles from client body claims.
"""
from account_dashboard import AccountDashboard

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
        return self.dashboard.overview(
            token=self._token(session_token),now=self._now(server_now))

    def activate_business(self, *, session_token, target_tenant_id, server_now):
        """Change business only after verifying target membership.

        Return a replacement session token only through a trusted transport.
        """
        if (not isinstance(target_tenant_id,str)
                or not target_tenant_id.strip()
                or len(target_tenant_id)>128):
            raise ValueError('Valid target business required')
        return self.dashboard.switch_and_overview(
            token=self._token(session_token),
            target_tenant_id=target_tenant_id,now=self._now(server_now))

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
