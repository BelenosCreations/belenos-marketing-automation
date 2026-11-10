"""Offline multi-platform connection directory for independent BAM accounts.

No social login, provider API calls, or automatic publishing. Connection
metadata comes from a trusted server-side registry, not client credentials.
"""
from access_policy import Action, Resource, require_permission

class SocialConnectionDirectory:
    def __init__(self, *, registry, directory, sessions):
        self.registry=registry
        self.directory=directory
        self.sessions=sessions

    def _authorize(self, *, token, tenant_id, now):
        session=self.sessions.resolve_current(token,directory=self.directory,now=now)
        if session is None or session.principal.tenant_id!=tenant_id:
            raise PermissionError('Authenticated business membership required')
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        require_permission(member,Action.READ_ANALYTICS,Resource(tenant_id))
        return member

    def list_connections(self, *, token, tenant_id, now):
        self._authorize(token=token,tenant_id=tenant_id,now=now)
        rows=self.registry.db.execute(
            """SELECT platform,account_id FROM provider_connections
               WHERE tenant_id=? ORDER BY platform,account_id""",
            (tenant_id,)).fetchall()
        return {'tenant_id':tenant_id,'connections':[
            dict(platform=platform,account_id=account_id,
                 **self.registry.status(tenant_id=tenant_id,
                      platform=platform,account_id=account_id,now=now))
            for platform,account_id in rows],
            'publishing_enabled':False}

    def connection_status(self, *, token, tenant_id, platform, account_id, now):
        self._authorize(token=token,tenant_id=tenant_id,now=now)
        return self.registry.status(tenant_id=tenant_id,platform=platform,
                                    account_id=account_id,now=now)
