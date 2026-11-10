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
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if member is None or not self.directory.authorize(member,Action.READ_DRAFTS,tenant_id):
            raise PermissionError('Business access denied')
        return dict(tenant_id=tenant_id,subject_id=member.subject_id,role=member.role.value)
