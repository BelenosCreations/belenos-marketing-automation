"""Read-only multi-business account selector for authenticated users.

The server derives available businesses from current membership, never from
client-provided roles. No integrations or publishing are exposed here.
"""
from access_policy import Action

class BusinessSwitcher:
    def __init__(self, db, sessions, directory):
        self.db=db
        self.sessions=sessions
        self.directory=directory

    def list_businesses(self, *, token, now=None):
        session=self.sessions.resolve(token,now=now)
        if session is None:
            raise PermissionError('Authentication required')
        subject=session.principal.subject_id
        if self.directory.resolve(session.principal.tenant_id,subject) is None:
            raise PermissionError('Current business membership inactive')
        rows=self.db.execute("""SELECT m.tenant_id,m.role,p.display_name,p.industry
            FROM members m LEFT JOIN business_profiles p ON p.tenant_id=m.tenant_id
            WHERE m.subject_id=? AND m.active=1 ORDER BY m.tenant_id""",(subject,)).fetchall()
        return [dict(tenant_id=tenant,role=role,display_name=name or tenant,industry=industry)
                for tenant,role,name,industry in rows
                if self.directory.authorize(session.principal if session.principal.tenant_id==tenant
                    else self.directory.resolve(tenant,subject),Action.READ_DRAFTS,tenant)]

    def select_business(self, *, token, tenant_id, now=None):
        session=self.sessions.resolve(token,now=now)
        if session is None:
            raise PermissionError('Authentication required')
        if self.directory.resolve(session.principal.tenant_id,session.principal.subject_id) is None:
            raise PermissionError('Current business membership inactive')
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if member is None or not self.directory.authorize(member,Action.READ_DRAFTS,tenant_id):
            raise PermissionError('Business access denied')
        return dict(tenant_id=tenant_id,subject_id=member.subject_id,role=member.role.value)

    def activate_business(self, *, token, tenant_id, now=None, ttl_seconds=3600):
        """Issue a new business-scoped session after membership revalidation.

        This does not authenticate the user anew or revoke the source session.
        """
        import time
        timestamp=int(time.time()) if now is None else now
        selected=self.select_business(token=token,tenant_id=tenant_id,now=timestamp)
        member=self.directory.resolve(tenant_id,selected['subject_id'])
        if member is None:
            raise PermissionError('Target membership inactive')
        new_token=self.sessions.issue(member,ttl_seconds=ttl_seconds,now=timestamp)
        return {'tenant_id':tenant_id,'token':new_token,
                'role':member.role.value,'publishing_enabled':False}
