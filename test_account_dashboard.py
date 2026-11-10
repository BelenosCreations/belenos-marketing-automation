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
from account_read_api import AccountReadAPI
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService

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
        requests=ContentRequests(self.db)
        self.attachments=AttachmentRegistry(self.db)
        self.first_request=requests.create(tenant_id='first',channel='facebook',
            draft_text='First draft',suggestion='Photograph product',
            required_items=['photo'],now=100)
        requests.create(tenant_id='second',channel='instagram',
            draft_text='Second draft',suggestion='Photograph cleaning team',
            required_items=['team_photo'],now=100)
        content=ContentRequestService(requests=requests,sessions=self.sessions,
            directory=self.directory,attachments=self.attachments)
        switcher=BusinessSwitcher(self.db,self.sessions,self.directory)
        social=SocialConnectionDirectory(registry=self.registry,
            directory=self.directory,sessions=self.sessions)
        self.dashboard=AccountDashboard(sessions=self.sessions,
            directory=self.directory,switcher=switcher,social_connections=social,
            content_service=content)

    def test_owner_sees_only_current_business_connections(self):
        result=self.dashboard.overview(token=self.owner,now=101)
        self.assertEqual(result['tenant_id'],'first')
        self.assertEqual([x['platform'] for x in result['social_connections']],['facebook'])
        self.assertNotIn('vault/first/page',str(result))
        self.assertFalse(result['publishing_enabled'])

    def test_held_drafts_are_tenant_scoped(self):
        first=self.dashboard.overview(token=self.owner,now=101)
        self.assertEqual([x['draft_text'] for x in first['pending_content_requests']],
                         ['First draft'])
        self.assertEqual(first['pending_content_requests'][0]['missing_items'],['photo'])
        second=self.dashboard.switch_and_overview(
            token=self.owner,target_tenant_id='second',now=101)
        self.assertEqual([x['draft_text'] for x in
                          second['overview']['pending_content_requests']],
                         ['Second draft'])
        self.assertFalse(second['publishing_enabled'])

    def test_verified_content_completion_requires_trusted_attachment(self):
        api=AccountReadAPI(self.dashboard)
        with self.assertRaises((PermissionError,ValueError)):
            api.supply_verified_content(session_token=self.owner,server_now=102,
                request_id=self.first_request,item='photo',
                attachment_id='0'*32)
        attachment=self.attachments.register_pending(
            tenant_id='first',request_id=self.first_request,item='photo',
            media_type='image/png',sha256='a'*64,
            storage_key='private/test-photo',now=102)
        with self.assertRaises(PermissionError):
            api.supply_verified_content(session_token=self.owner,server_now=103,
                request_id=self.first_request,item='photo',
                attachment_id=attachment)
        self.attachments.validate_trusted(tenant_id='first',
            attachment_id=attachment,approved=True)
        result=api.supply_verified_content(session_token=self.owner,
            server_now=104,request_id=self.first_request,
            item='photo',attachment_id=attachment)
        self.assertEqual(result['status'],'ready_for_review')
        self.assertFalse(result['publishing_enabled'])
        view=api.get_dashboard_view(session_token=self.owner,server_now=105)
        self.assertEqual(view['cards'][1]['value'],1)
        self.assertEqual(view['cards'][2]['value'],0)
        self.assertNotIn('private/test-photo',str(view))

    def test_all_held_draft_statuses_are_tenant_scoped(self):
        api=AccountReadAPI(self.dashboard)
        self.assertEqual(len(api.list_held_drafts(
            session_token=self.owner,server_now=101)['drafts']),1)
        api.update_draft_hold(session_token=self.owner,server_now=102,
            request_id=self.first_request,status='postponed')
        overview=api.get_dashboard_view(session_token=self.owner,server_now=103)
        self.assertEqual(overview['drafts'],[])
        postponed=api.list_held_drafts(session_token=self.owner,
            server_now=103,status='postponed')['drafts']
        self.assertEqual(len(postponed),1)
        self.assertEqual(postponed[0]['draft_text'],'First draft')
        self.assertNotIn('provided_items',postponed[0])
        switched=api.activate_business(session_token=self.owner,
            target_tenant_id='second',server_now=103)
        other=api.list_held_drafts(session_token=switched['session_token'],
            server_now=104)['drafts']
        self.assertEqual([item['draft_text'] for item in other],['Second draft'])
        self.assertNotIn('First draft',str(other))
        with self.assertRaises(ValueError):
            api.list_held_drafts(session_token=self.owner,server_now=104,
                status='published')

    def test_authenticated_ui_payload_is_business_scoped(self):
        api=AccountReadAPI(self.dashboard)
        first=api.get_dashboard_view(session_token=self.owner,server_now=101)
        self.assertEqual(first['tenant_id'],'first')
        self.assertEqual(len(first['drafts']),1)
        self.assertEqual(first['drafts'][0]['draft_text'],'First draft')
        self.assertEqual(first['cards'][2]['value'],1)
        self.assertEqual(first['cards'][3]['value'],1)
        self.assertNotIn('vault/',str(first))
        switched=api.activate_business(session_token=self.owner,
            target_tenant_id='second',server_now=101)
        second=api.get_dashboard_view(session_token=switched['session_token'],
            server_now=101)
        self.assertEqual(second['tenant_id'],'second')
        self.assertEqual([x['draft_text'] for x in second['drafts']],
                         ['Second draft'])
        self.assertIsNone(second['cards'][3]['value'])
        self.assertEqual(second['cards'][3]['availability'],'restricted')
        self.assertNotIn('First draft',str(second))
        self.assertFalse(second['publishing_enabled'])

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
