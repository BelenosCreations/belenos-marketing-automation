"""Offline BAM account dashboard composition; no HTTP or publishing.

Trusted server code supplies services. Every view revalidates BAM membership.
"""
from access_policy import Action, Resource, require_permission

class AccountDashboard:
    def __init__(self, *, sessions, directory, switcher, social_connections):
        self.sessions=sessions
        self.directory=directory
        self.switcher=switcher
        self.social_connections=social_connections

    def overview(self, *, token, now):
        session=self.sessions.resolve_current(token,directory=self.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        tenant_id=session.principal.tenant_id
        require_permission(session.principal,Action.READ_DRAFTS,Resource(tenant_id))
        businesses=self.switcher.list_businesses(token=token,now=now)
        # Employees who can read drafts are not necessarily allowed to see
        # analytics or account connection metadata.
        from access_policy import authorized
        if authorized(session.principal,Action.READ_ANALYTICS,Resource(tenant_id)):
            social=self.social_connections.list_connections(
                token=token,tenant_id=tenant_id,now=now)['connections']
        else:
            social=None
        return {'tenant_id':tenant_id,'role':session.principal.role.value,
                'businesses':businesses,'social_connections':social,
                'connection_visibility':'authorized' if social is not None else 'restricted',
                'publishing_enabled':False}

    def switch_and_overview(self, *, token, target_tenant_id, now):
        activated=self.switcher.activate_business(
            token=token,tenant_id=target_tenant_id,now=now)
        # Session token returned only to authenticated client over future HTTPS;
        # do not log or persist it in an analytics/audit payload.
        overview=self.overview(token=activated['token'],now=now)
        return {'session_token':activated['token'],'overview':overview,
                'publishing_enabled':False}
