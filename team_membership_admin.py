"""Offline owner-only team roster and race-safe membership administration.

This is a trusted server service, not an invitation/enrollment endpoint. Owner
may manage *existing active non-owner* memberships only. Reactivation,
creation, invitation delivery and ownership transfer are separate workflows.
Every mutation is tenant-scoped, compare-and-swap and audit recorded, with
same-tenant sessions invalidated atomically. No external service or publishing.
"""
import time

from access_policy import Role

_ALLOWED={Role.MARKETING_MANAGER,Role.CONTENT_CREATOR,Role.EMPLOYEE,Role.VIEWER}


class TeamMembershipAdmin:
    def __init__(self, *, db, sessions, directory):
        self.db=db
        self.sessions=sessions
        self.directory=directory
        db.execute("""CREATE TABLE IF NOT EXISTS bam_team_member_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT NOT NULL,
            member_id TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            previous_role TEXT NOT NULL,
            resulting_role TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('change_role','deactivate')),
            changed_at INTEGER NOT NULL,
            revision_after INTEGER NOT NULL
        )""")
        db.execute("""CREATE INDEX IF NOT EXISTS bam_team_audit_tenant
            ON bam_team_member_audit(tenant_id,id)""")
        db.commit()

    def _owner(self, token, now):
        if type(now) is not int or now<0:
            raise ValueError('Trusted time required')
        session=self.sessions.resolve_current(
            token,directory=self.directory,now=now)
        if session is None or session.principal.role!=Role.OWNER:
            raise PermissionError('Current business owner session required')
        return session.principal

    def list_current(self, *, token, now=None):
        timestamp=int(time.time()) if now is None else now
        owner=self._owner(token,timestamp)
        rows=self.db.execute("""SELECT m.subject_id,m.role,m.active,m.revision,
                    i.email
                FROM members m LEFT JOIN bam_identities i
                  ON i.subject_id=m.subject_id
                  AND i.active=1 AND i.email_verified=1
                WHERE m.tenant_id=?
                ORDER BY m.active DESC,m.role,m.subject_id LIMIT 201""",
                (owner.tenant_id,)).fetchall()
        if len(rows)>200:
            raise RuntimeError('Team directory requires pagination')
        members=[]
        for subject,role,active,revision,email in rows:
            if (role not in {r.value for r in Role} or
                    type(revision) is not int or revision<1):
                raise RuntimeError('Invalid directory row')
            members.append({
                'member_id':subject,'role':role,'active':bool(active),
                'revision':revision,'email':email,
                'is_self':subject==owner.subject_id,
            })
        return {'tenant_id':owner.tenant_id,
                'status':'private_team_preview','members':members,
                'publishing_enabled':False}

    def change_current(self, *, token, member_id, action,
                       expected_revision, role=None, now=None):
        timestamp=int(time.time()) if now is None else now
        owner=self._owner(token,timestamp)
        if (type(member_id) is not str or not member_id.strip() or
                len(member_id)>128 or
                type(expected_revision) is not int or expected_revision<1):
            raise ValueError('Member and current revision required')
        if action not in ('change_role','deactivate'):
            raise ValueError('Unsupported membership change')
        if action=='change_role':
            try:
                selected=Role(role)
            except (TypeError,ValueError):
                raise ValueError('Invalid member role') from None
            if selected not in _ALLOWED:
                raise PermissionError('Owner role requires a separate process')
        elif role is not None:
            raise ValueError('Do not submit a role when deactivating')
        if member_id==owner.subject_id:
            raise PermissionError('Cannot modify your own membership')

        with self.db:
            current=self.db.execute("""SELECT role,active,revision
                FROM members WHERE tenant_id=? AND subject_id=?""",
                (owner.tenant_id,member_id)).fetchone()
            if current is None:
                raise KeyError('Business member unavailable')
            prior_role,active,revision=current
            if prior_role==Role.OWNER.value:
                raise PermissionError('Cannot modify owner membership')
            if active!=1:
                raise PermissionError('Inactive membership must use re-invitation')
            if revision!=expected_revision:
                raise ValueError('Stale team membership revision')
            resulting=selected.value if action=='change_role' else prior_role
            if resulting==prior_role and action=='change_role':
                raise ValueError('Member already has this role')
            new_active=1 if action=='change_role' else 0
            changed=self.db.execute("""UPDATE members SET
                role=?,active=?,revision=revision+1
                WHERE tenant_id=? AND subject_id=? AND revision=?
                  AND active=1 AND role!=?""",
                (resulting,new_active,owner.tenant_id,member_id,
                 expected_revision,Role.OWNER.value))
            if changed.rowcount!=1:
                raise ValueError('Stale team membership revision')
            revoked=self.db.execute("""UPDATE sessions SET revoked_at=?
                WHERE tenant_id=? AND subject_id=? AND revoked_at IS NULL""",
                (timestamp,owner.tenant_id,member_id)).rowcount
            self.db.execute("""INSERT INTO bam_team_member_audit
                (tenant_id,member_id,actor_id,previous_role,resulting_role,
                 action,changed_at,revision_after)
                VALUES (?,?,?,?,?,?,?,?)""",
                (owner.tenant_id,member_id,owner.subject_id,prior_role,
                 resulting,action,timestamp,expected_revision+1))
        return {'tenant_id':owner.tenant_id,'member_id':member_id,
                'status':'updated' if action=='change_role' else 'deactivated',
                'revision':expected_revision+1,
                'sessions_revoked':revoked,'publishing_enabled':False}
