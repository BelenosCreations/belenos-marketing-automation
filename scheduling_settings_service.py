"""Session-authenticated scheduling preferences service for BAM."""
import time
from access_policy import Principal
from scheduling_settings import SchedulingSettings

class SchedulingSettingsService:
    def __init__(self, *, settings, sessions, directory):
        self.settings=settings
        self.sessions=sessions
        self.directory=directory

    def _principal(self, *, token, tenant_id, now):
        session=self.sessions.resolve_current(token,directory=self.directory,now=now)
        if session is None or session.principal.tenant_id!=tenant_id:
            raise PermissionError('Authentication required for this business')
        member=self.directory.resolve(tenant_id,session.principal.subject_id)
        if member is None:
            raise PermissionError('Business membership required')
        return Principal(member.subject_id,tenant_id,member.role)

    def get(self, *, token, tenant_id, now=None):
        timestamp=int(time.time()) if now is None else now
        principal=self._principal(token=token,tenant_id=tenant_id,now=timestamp)
        return self.settings.get(principal=principal,tenant_id=tenant_id)

    def save(self, *, token, tenant_id, preferences, expected_revision=None, now=None):
        timestamp=int(time.time()) if now is None else now
        principal=self._principal(token=token,tenant_id=tenant_id,now=timestamp)
        return self.settings.save(principal=principal,tenant_id=tenant_id,
            preferences=preferences,expected_revision=expected_revision)
