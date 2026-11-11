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
from posting_preferences import PostingPreferences
from ai_account_policy import AIPolicyStore
from ai_content_drafts import AIContentDraftStore
from ai_business_facts import AIBusinessFacts

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
        ai_policy=AIPolicyStore(db=self.db,sessions=self.sessions,directory=directory)
        self.api=AccountReadAPI(dashboard,posting_preferences=PostingPreferences(
            db=self.db,sessions=self.sessions,directory=directory),
            ai_policy=ai_policy,ai_content_drafts=AIContentDraftStore(
                db=self.db,policy_store=ai_policy),
            ai_business_facts=AIBusinessFacts(db=self.db,policy_store=ai_policy))

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

    def test_posting_preferences_read_write_and_switch_isolation(self):
        initial=self.api.get_posting_preferences(
            session_token=self.token,server_now=101)
        self.assertFalse(initial['configured'])
        self.assertIsNone(initial['timezone'])
        updated=self.api.set_posting_preferences(
            session_token=self.token,server_now=102,mode='manual',
            timezone='America/New_York',manual_times=['18:30','10:00'])
        self.assertEqual(updated['manual_times'],['10:00','18:30'])
        self.assertFalse(updated['publishing_enabled'])
        switched=self.api.activate_business(session_token=self.token,
            target_tenant_id='b',server_now=103)
        second=self.api.get_posting_preferences(
            session_token=switched['session_token'],server_now=103)
        self.assertFalse(second['configured'])
        with self.assertRaises(PermissionError):
            self.api.set_posting_preferences(
                session_token=switched['session_token'],server_now=104,
                mode='manual',timezone='America/New_York',
                manual_times=['11:30'])
        original=self.api.get_posting_preferences(
            session_token=self.token,server_now=104)
        self.assertEqual(original['manual_times'],['10:00','18:30'])

    def test_posting_preferences_require_valid_session(self):
        with self.assertRaises(PermissionError):
            self.api.get_posting_preferences(
                session_token='bad',server_now=101)

    def test_ai_business_facts_read_only_and_business_scoped(self):
        self.api.ai_business_facts.confirm(token=self.token,now=101,
            facts={'business_name':'A Shop'})
        first=self.api.get_ai_business_facts(
            session_token=self.token,server_now=102)
        self.assertEqual(first['provenance'],'owner_confirmed')
        self.assertEqual(first['facts']['business_name'],'A Shop')
        switched=self.api.activate_business(session_token=self.token,
            target_tenant_id='b',server_now=103)
        second=self.api.get_ai_business_facts(
            session_token=switched['session_token'],server_now=104)
        self.assertEqual(second['provenance'],'not_configured')
        self.assertEqual(second['facts'],{})

    def test_ai_settings_and_drafts_isolated_across_business_switch(self):
        self.api.ai_policy.replace_memory(token=self.token,now=101,
            memory={'tone':'friendly'})
        draft=self.api.ai_content_drafts.stage(token=self.token,now=101,
            platform='facebook',
            response={'post_text':'Product spotlight',
                      'image_prompt':'Neutral photo'},
            include_image_prompt=True,needs_media=True)
        settings=self.api.get_ai_settings(
            session_token=self.token,server_now=102)
        self.assertEqual(settings['memory'],{'tone':'friendly'})
        self.assertNotIn('vault:',str(settings))
        drafts=self.api.list_ai_content_drafts(
            session_token=self.token,server_now=102)
        self.assertEqual(drafts['drafts'][0]['draft_id'],draft['draft_id'])
        self.assertFalse(drafts['publishing_enabled'])
        switched=self.api.activate_business(session_token=self.token,
            target_tenant_id='b',server_now=103)
        second=self.api.get_ai_settings(
            session_token=switched['session_token'],server_now=104)
        self.assertEqual(second['memory'],{})
        self.assertEqual(self.api.list_ai_content_drafts(
            session_token=switched['session_token'],
            server_now=104)['drafts'],[])
        self.assertNotIn('friendly',str(second))

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
