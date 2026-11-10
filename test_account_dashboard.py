import sqlite3
import unittest
from access_policy import Principal, Role
from accounts import AccountDirectory
from sessions import SessionStore
from business_curation import BusinessCuration
from business_switcher import BusinessSwitcher
from provider_connection_registry import ProviderConnectionRegistry
from social_connection_directory import SocialConnectionDirectory
from account_dashboard import AccountDashboard

class AccountDashboardTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('first','owner')
        self.directory.bootstrap_owner('second','other')
        self.directory.set_member(Principal('other','second',Role.OWNER),
                                  'owner',Role.CONTENT_CREATOR)
        self.sessions=SessionStore(self.db)
        self.owner=self.sessions.issue(Principal('owner','first',Role.OWNER),now=100)
        curation=BusinessCuration(self.db)
        curation.create_profile('first','First Shop','retail',['retail'])
        curation.create_profile('second','Second Shop','services',['services'])
        self.registry=ProviderConnectionRegistry(self.db)
        self.registry.register_trusted(tenant_id='first',platform='facebook',
            account_id='page',vault_reference='vault/first/page',
            scope='read_insights',state='connected',expires_at=1000,now=100)
        self.registry.register_trusted(tenant_id='second',platform='instagram',
            account_id='ig',vault_reference='vault/second/ig',
            scope='read_insights',state='connected',expires_at=1000,now=100)
        switcher=BusinessSwitcher(self.db,self.sessions,self.directory)
        social=SocialConnectionDirectory(registry=self.registry,
            directory=self.directory,sessions=self.sessions)
        self.dashboard=AccountDashboard(sessions=self.sessions,
            directory=self.directory,switcher=switcher,social_connections=social)

    def test_owner_sees_only_current_business_connections(self):
        result=self.dashboard.overview(token=self.owner,now=101)
        self.assertEqual(result['tenant_id'],'first')
        self.assertEqual([x['platform'] for x in result['social_connections']],['facebook'])
        self.assertNotIn('vault/first/page',str(result))
        self.assertFalse(result['publishing_enabled'])

    def test_switch_to_creator_role_hides_connections(self):
        result=self.dashboard.switch_and_overview(
            token=self.owner,target_tenant_id='second',now=101)
        self.assertEqual(result['overview']['role'],'content_creator')
        self.assertIsNone(result['overview']['social_connections'])
        self.assertEqual(result['overview']['connection_visibility'],'restricted')

    def test_activation_failure_revokes_new_session(self):
        original=self.dashboard.overview
        def failing_overview(*,token,now):
            raise RuntimeError('Injected dashboard failure')
        self.dashboard.overview=failing_overview
        with self.assertRaises(RuntimeError):
            self.dashboard.switch_and_overview(
                token=self.owner,target_tenant_id='second',now=101)
        rows=self.db.execute(
            "SELECT revoked_at FROM sessions WHERE tenant_id='second' AND subject_id='owner'"
        ).fetchall()
        self.assertEqual(rows,[(101,)])
        self.dashboard.overview=original

    def test_unknown_target_denied(self):
        with self.assertRaises(PermissionError):
            self.dashboard.switch_and_overview(
                token=self.owner,target_tenant_id='unknown',now=101)

    def test_revoked_session_denied(self):
        self.sessions.revoke(self.owner,now=101)
        with self.assertRaises(PermissionError):
            self.dashboard.overview(token=self.owner,now=102)

    def test_role_change_invalidates_existing_session(self):
        self.db.execute('UPDATE members SET role=? WHERE tenant_id=? AND subject_id=?',
                        (Role.VIEWER.value,'first','owner'))
        self.db.commit()
        with self.assertRaises(PermissionError):
            self.dashboard.overview(token=self.owner,now=101)

if __name__=='__main__':unittest.main()
