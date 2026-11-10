import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from business_curation import BusinessCuration
from business_switcher import BusinessSwitcher
from provider_connection_registry import ProviderConnectionRegistry
from social_connection_directory import SocialConnectionDirectory
from account_dashboard import AccountDashboard
from account_read_api import AccountReadAPI

class AccountReadAPITests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        directory=AccountDirectory(self.db)
        directory.bootstrap_owner('a','owner')
        directory.bootstrap_owner('b','other')
        directory.set_member(Principal('other','b',Role.OWNER),'owner',Role.VIEWER)
        self.sessions=SessionStore(self.db)
        self.token=self.sessions.issue(Principal('owner','a',Role.OWNER),now=100)
        curation=BusinessCuration(self.db)
        curation.create_profile('a','A Shop','retail',['retail'])
        curation.create_profile('b','B Shop','services',['services'])
        registry=ProviderConnectionRegistry(self.db)
        registry.register_trusted(tenant_id='a',platform='facebook',
            account_id='a_page',vault_reference='vault/a',
            scope='read_insights',state='connected',expires_at=1000,now=100)
        registry.register_trusted(tenant_id='b',platform='instagram',
            account_id='b_page',vault_reference='vault/b',
            scope='read_insights',state='connected',expires_at=1000,now=100)
        dashboard=AccountDashboard(
            sessions=self.sessions,directory=directory,
            switcher=BusinessSwitcher(self.db,self.sessions,directory),
            social_connections=SocialConnectionDirectory(
                registry=registry,directory=directory,sessions=self.sessions))
        self.api=AccountReadAPI(dashboard)

    def tearDown(self):
        self.db.close()

    def test_overview_is_current_business_only(self):
        response=self.api.get_overview(session_token=self.token,server_now=101)
        self.assertEqual(response['tenant_id'],'a')
        self.assertEqual([x['platform'] for x in response['social_connections']],['facebook'])
        self.assertNotIn('vault/',str(response))
        cards={card['id']:card for card in response['dashboard_cards']}
        self.assertEqual(cards['connections']['value'],1)
        self.assertIsNone(cards['scheduled']['value'])
        self.assertEqual(cards['scheduled']['availability'],'not_connected')

    def test_switch_uses_target_permissions(self):
        response=self.api.activate_business(session_token=self.token,
            target_tenant_id='b',server_now=101)
        self.assertEqual(response['overview']['role'],'viewer')
        self.assertEqual([x['platform'] for x in response['overview']['social_connections']],['instagram'])
        self.assertNotEqual(response['session_token'],self.token)
        self.assertFalse(response['publishing_enabled'])
        switched_cards={card['id']:card for card in response['overview']['dashboard_cards']}
        self.assertEqual(switched_cards['connections']['value'],1)
        self.assertEqual(switched_cards['content']['value'],0)

    def test_dashboard_view_is_authenticated_and_does_not_invent_metrics(self):
        view=self.api.get_dashboard_view(session_token=self.token,server_now=101)
        self.assertEqual(view['schema_version'],1)
        self.assertEqual(view['tenant_id'],'a')
        self.assertEqual(view['drafts'],[])
        self.assertIsNone(view['analytics']['series'])
        self.assertIsNone(view['schedule']['posts'])
        self.assertFalse(view['publishing_enabled'])
        self.assertNotIn('vault/',str(view))
        with self.assertRaises(PermissionError):
            self.api.get_dashboard_view(session_token='wrong',server_now=101)

    def test_logout_revokes_token(self):
        self.assertTrue(self.api.logout(session_token=self.token,server_now=101)['signed_out'])
        with self.assertRaises(PermissionError):
            self.api.get_overview(session_token=self.token,server_now=102)

    def test_logout_everywhere_revokes_all_business_sessions(self):
        other=self.sessions.issue(Principal('owner','b',Role.VIEWER),now=100)
        unrelated=self.sessions.issue(Principal('someone','a',Role.VIEWER),now=100)
        result=self.api.logout_everywhere(session_token=self.token,server_now=101)
        self.assertEqual(result['sessions_revoked'],2)
        self.assertIsNone(self.sessions.resolve(self.token,now=102))
        self.assertIsNone(self.sessions.resolve(other,now=102))
        self.assertIsNotNone(self.sessions.resolve(unrelated,now=102))

    def test_logout_everywhere_denies_revoked_session(self):
        self.sessions.revoke(self.token,now=101)
        with self.assertRaises(PermissionError):
            self.api.logout_everywhere(session_token=self.token,server_now=102)

    def test_invalid_tokens_fail_closed(self):
        for token in (None,'','not-a-real-session',42):
            with self.assertRaises(PermissionError):
                self.api.get_overview(session_token=token,server_now=101)

    def test_bad_target_denied(self):
        for tenant in ('',None,'missing'):
            with self.assertRaises((PermissionError,ValueError)):
                self.api.activate_business(session_token=self.token,
                    target_tenant_id=tenant,server_now=101)

    def test_reject_client_supplied_timestamp_types(self):
        for now in (None,True,'101',-1):
            with self.assertRaises(ValueError):
                self.api.get_overview(session_token=self.token,server_now=now)

if __name__=='__main__':unittest.main()
