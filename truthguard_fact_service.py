"""Authenticated TruthGuard fact administration.

Owner or marketing manager may propose facts; only owner may approve/revoke
business facts in this initial conservative policy.
"""
import time
from access_policy import Action,Role

class TruthGuardFactService:
    def __init__(self,*,knowledge,sessions,directory):
        self.knowledge=knowledge
        self.sessions=sessions
        self.directory=directory

    def _actor(self,*,token,tenant_id,now):
        session=self.sessions.resolve_current(token,directory=self.directory,now=now)
        if session is None or session.principal.tenant_id!=tenant_id:
            raise PermissionError('Authenticated business session required')
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if member is None:
            raise PermissionError('Active business membership required')
        if member.role!=Role.OWNER:
            raise PermissionError('Only business owner may approve or revoke facts')
        return member

    def approve(self,*,token,tenant_id,claim_key,value,source,
                expires_at=None,now=None):
        timestamp=int(time.time()) if now is None else now
        actor=self._actor(token=token,tenant_id=tenant_id,now=timestamp)
        return self.knowledge.approve(tenant_id=tenant_id,claim_key=claim_key,
            value=value,source=source,approved_by=actor.subject_id,
            now=timestamp,expires_at=expires_at)

    def revoke(self,*,token,tenant_id,fact_id,now=None):
        timestamp=int(time.time()) if now is None else now
        self._actor(token=token,tenant_id=tenant_id,now=timestamp)
        return self.knowledge.revoke(tenant_id=tenant_id,fact_id=fact_id,now=timestamp)

    def lookup(self,*,token,tenant_id,claim_key,now=None):
        timestamp=int(time.time()) if now is None else now
        self._actor(token=token,tenant_id=tenant_id,now=timestamp)
        return self.knowledge.lookup(tenant_id=tenant_id,claim_key=claim_key,now=timestamp)
