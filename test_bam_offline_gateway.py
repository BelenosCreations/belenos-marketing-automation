"""End-to-end offline WSGI tests of independent BAM business accounts."""
import io
import json
import sqlite3
import unittest

from access_policy import Principal, Role
from bam_offline_gateway import BAMOfflineGateway


class BAMOfflineGatewayTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.app = BAMOfflineGateway(self.db, enabled=True, clock=lambda:101)
        self.subject = self.app.identities.register_password(
            email='owner@example.com',
            password='correct horse battery staple', now=100)
        self.app.identities.set_email_verified_trusted(
            subject_id=self.subject, verified=True)
        self.app.directory.bootstrap_owner('shop',self.subject)
        self.app.directory.bootstrap_owner('other','other-owner')
        self.app.directory.set_member(
            Principal('other-owner','other',Role.OWNER),
            self.subject,Role.CONTENT_CREATOR)
        self.app.curation.create_profile(
            'shop','Example Shop','retail',['custom products'])
        self.app.curation.create_profile(
            'other','Second Service','services',['facility care'])
        self.app.requests.create(
            tenant_id='shop',channel='facebook',
            draft_text='A sample product preview.',
            suggestion='Add an approved product photograph.',
            required_items=['photo'],now=100)
        self.app.requests.create(
            tenant_id='other',channel='facebook',
            draft_text='A different business preview.',
            suggestion='Add an approved workplace photograph.',
            required_items=['photo'],now=100)

    def tearDown(self):
        self.db.close()

    def call(self,path,*,method='GET',body=None,token=None,scheme='https',
             extra=None):
        source = {'wsgi.url_scheme':scheme, 'PATH_INFO':path,
                  'REQUEST_METHOD':method}
        if token is not None:
            source['HTTP_AUTHORIZATION']='Bearer '+token
        if body is not None:
            raw=json.dumps(body).encode('utf-8')
            source.update({'CONTENT_TYPE':'application/json',
                           'CONTENT_LENGTH':str(len(raw)),
                           'wsgi.input':io.BytesIO(raw)})
        if extra:source.update(extra)
        got={}
        raw=b''.join(self.app(source,lambda status,headers:
            got.update(status=status,headers=dict(headers))))
        return got,json.loads(raw)

    def login(self,tenant='shop'):
        meta, result=self.call(
            '/api/v1/auth/password',method='POST',body={
            'email':'owner@example.com',
            'password':'correct horse battery staple',
            'tenant_id':tenant})
        self.assertEqual(meta['status'],'200 OK')
        self.assertFalse(result['publishing_enabled'])
        return result['session_token']

    def test_default_off_and_unknown_route(self):
        disabled=BAMOfflineGateway(self.db)
        got={}
        body=b''.join(disabled({'wsgi.url_scheme':'https',
            'PATH_INFO':'/api/v1/dashboard','REQUEST_METHOD':'GET'},
            lambda status,headers:got.update(status=status)))
        self.assertEqual(got['status'],'503 Service Unavailable')
        self.assertNotIn(b'token',body)
        self.assertEqual(self.call('/api/v1/publish')[0]['status'],'404 Not Found')
        self.assertEqual(self.call('/api/v1/ai-generate',
            method='POST',body={})[0]['status'],'404 Not Found')

    def test_authenticated_browser_shell_is_a_separate_explicit_opt_in(self):
        from bam_signed_in_assets_wsgi import BAMSignedInAssetsWSGI
        default=self.call('/ui/bam_signed_in_shell.html')[0]
        self.assertEqual(default['status'],'404 Not Found')
        enabled=BAMOfflineGateway(self.db,enabled=True,
            serve_browser_assets=True,clock=lambda:101)
        meta={}
        data=b''.join(enabled({'wsgi.url_scheme':'https',
            'PATH_INFO':'/ui/bam_signed_in_shell.html',
            'REQUEST_METHOD':'GET'},
            lambda status,headers:meta.update(status=status,headers=dict(headers))))
        self.assertEqual(meta['status'],'200 OK')
        self.assertIn(b'Belenos Automatic Marketing',data)
        self.assertIn(b'script-src',str(meta['headers']).encode())
        meta={}
        icon=b''.join(enabled({'wsgi.url_scheme':'https',
            'PATH_INFO':'/branding/source/app_icon.svg',
            'REQUEST_METHOD':'GET'},
            lambda status,headers:meta.update(status=status)))
        self.assertEqual(meta['status'],'200 OK')
        self.assertIn(b'<svg',icon)

    def test_real_identity_to_dashboard_and_ai_panels(self):
        token=self.login()
        meta,dashboard=self.call('/api/v1/dashboard',token=token)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(dashboard['tenant_id'],'shop')
        self.assertFalse(dashboard['pending_media_available'])
        self.assertEqual(dashboard['cards'][2]['value'],1)
        self.assertEqual(dashboard['cards'][0]['value'],None)
        self.assertEqual(dashboard['schedule']['availability'],'not_connected')
        self.assertEqual(len(dashboard['drafts']),1)
        self.assertEqual(dashboard['drafts'][0]['draft_text'],
                         'A sample product preview.')
        self.assertNotIn('correct horse',str(dashboard))
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        for path,expected in [
            ('/api/v1/ai-drafts','drafts'),
            ('/api/v1/ai-settings','mode'),
            ('/api/v1/ai-business-facts','facts'),
            ('/api/v1/ai-cost-summary','events'),
            ('/api/v1/posting-preferences','mode'),
            ('/api/v1/drafts','drafts')]:
            with self.subTest(path=path):
                status, value=self.call(path,token=token)
                self.assertEqual(status['status'],'200 OK')
                self.assertEqual(value['tenant_id'],'shop')
                self.assertIn(expected,value)
                self.assertFalse(value['publishing_enabled'])

    def test_team_overview_owner_only_aggregate_without_ids(self):
        owner=self.login('shop')
        meta,overview=self.call('/api/v1/team-overview',token=owner)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(overview['tenant_id'],'shop')
        self.assertEqual(overview['roles']['owner'],1)
        self.assertEqual(overview['active_members'],1)
        self.assertEqual(overview['inactive_members'],0)
        self.assertEqual(overview['invitation_status'],'not_connected')
        self.assertFalse(overview['publishing_enabled'])
        self.assertNotIn(self.subject,str(overview))
        self.assertNotIn('owner@example.com',str(overview))
        creator=self.login('other')
        self.assertEqual(self.call('/api/v1/team-overview',token=creator)[0]
                         ['status'],'401 Unauthorized')
        self.assertEqual(self.call('/api/v1/team-overview',token=owner,
            method='POST',body={'role':'owner'})[0]['status'],
            '405 Method Not Allowed')
        self.assertEqual(self.call('/api/v1/team-overview',token=owner,
            extra={'QUERY_STRING':'tenant_id=other'})[0]['status'],
            '400 Bad Request')
        self.assertEqual(self.call('/api/v1/team-overview')[0]['status'],
            '401 Unauthorized')
        self.app.directory.set_member(
            Principal(self.subject,'shop',Role.OWNER),
            'worker',Role.VIEWER)
        _,added=self.call('/api/v1/team-overview',token=owner)
        self.assertEqual(added['roles']['viewer'],1)
        self.assertEqual(added['active_members'],2)
        self.app.directory.set_member(
            Principal(self.subject,'shop',Role.OWNER),
            'worker',Role.VIEWER,active=False)
        _,inactive=self.call('/api/v1/team-overview',token=owner)
        self.assertEqual(inactive['roles']['viewer'],0)
        self.assertEqual(inactive['inactive_members'],1)

    def test_connection_details_are_private_read_only_and_tenant_scoped(self):
        token=self.login('shop')
        self.app.connections.register_trusted(
            tenant_id='shop',platform='facebook',account_id='shop-page',
            vault_reference='vault/private/oauth-access-token',
            scope='read_insights',state='connected',expires_at=999,
            now=100)
        meta,body=self.call('/api/v1/connections',token=token)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(body['tenant_id'],'shop')
        self.assertEqual(body['visibility'],'authorized')
        self.assertEqual(body['connections'],[{
            'platform':'facebook','account_id':'shop-page',
            'status':'connected','scope':'read_insights',
            'updated_at':100,'expires_at':999,'publishing_enabled':False}])
        self.assertNotIn('vault/',str(body))
        self.assertNotIn('oauth-access-token',str(body))
        self.assertFalse(body['publishing_enabled'])
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        self.assertEqual(self.call('/api/v1/connections',token=token,
            extra={'QUERY_STRING':'tenant_id=other'})[0]['status'],
            '400 Bad Request')
        self.assertEqual(self.call('/api/v1/connections',
            token=token,method='POST',body={'role':'owner'})[0]['status'],
            '405 Method Not Allowed')
        other=self.login('other')
        self.assertEqual(self.call('/api/v1/connections',
            token=other)[0]['status'],'401 Unauthorized')
        self.assertEqual(self.call('/api/v1/connections')[0]['status'],
            '401 Unauthorized')

    def test_two_businesses_same_user_isolated(self):
        one=self.login('shop')
        two=self.login('other')
        _,shop=self.call('/api/v1/dashboard',token=one)
        _,other=self.call('/api/v1/dashboard',token=two)
        self.assertEqual(shop['tenant_id'],'shop')
        self.assertEqual(other['tenant_id'],'other')
        self.assertEqual(other['cards'][2]['value'],1)
        self.assertNotIn('product preview',str(other))
        self.assertNotIn('workplace photograph',str(shop))
        self.assertEqual(other['cards'][3]['availability'],'restricted')
        self.assertEqual(shop['cards'][3]['availability'],'available')
        self.assertEqual(self.call('/api/v1/ai-settings',
                         token=two)[0]['status'],'200 OK')

    def test_wrong_membership_and_password_denied(self):
        meta,result=self.call('/api/v1/auth/password',
            method='POST',body={'email':'owner@example.com',
                'password':'correct horse battery staple',
                'tenant_id':'unknown'})
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('session_token',result)
        meta,result=self.call('/api/v1/auth/password',
            method='POST',body={'email':'owner@example.com',
                'password':'wrong password wrong password',
                'tenant_id':'shop'})
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('session_token',result)

    def test_logout_revokes_token(self):
        token=self.login()
        meta,body=self.call('/api/v1/auth/logout',
            method='POST',body={},token=token)
        self.assertEqual(meta['status'],'200 OK')
        self.assertTrue(body['signed_out'])
        self.assertEqual(self.call('/api/v1/dashboard',
            token=token)[0]['status'],'401 Unauthorized')

    def test_logout_everywhere_revokes_all_tenant_sessions(self):
        a=self.login('shop')
        b=self.login('other')
        meta,body=self.call('/api/v1/auth/logout-everywhere',
            method='POST',body={},token=a)
        self.assertEqual(meta['status'],'200 OK')
        self.assertGreaterEqual(body['sessions_revoked'],2)
        self.assertEqual(self.call('/api/v1/dashboard',
            token=b)[0]['status'],'401 Unauthorized')

    def test_session_role_freshness_denies_old_token(self):
        token=self.login('shop')
        self.app.directory.set_member(
            Principal(self.subject,'shop',Role.OWNER),
            'staff',Role.CONTENT_CREATOR)
        self.db.execute('UPDATE members SET role=? WHERE tenant_id=? AND subject_id=?',
                        (Role.VIEWER.value,'shop',self.subject))
        self.db.commit()
        self.assertEqual(self.call('/api/v1/dashboard',
            token=token)[0]['status'],'401 Unauthorized')

    def test_untrusted_http_or_client_role_not_accepted(self):
        token=self.login()
        meta,_=self.call('/api/v1/dashboard',token=token,scheme='http',
            extra={'HTTP_X_FORWARDED_PROTO':'https'})
        self.assertEqual(meta['status'],'403 Forbidden')
        meta,_=self.call('/api/v1/dashboard',token=token,method='POST',
            body={'tenant_id':'other','role':'owner'})
        self.assertEqual(meta['status'],'405 Method Not Allowed')
        meta,_=self.call('/api/v1/auth/password',method='POST',
            body={'email':'owner@example.com',
                  'password':'correct horse battery staple',
                  'tenant_id':'shop','role':'owner'})
        self.assertEqual(meta['status'],'400 Bad Request')

    def test_business_switch_issues_replacement_and_revokes_old_token(self):
        original=self.login('shop')
        meta,activated=self.call('/api/v1/businesses/activate',
            method='POST',token=original,body={
                'target_tenant_id':'other'})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(activated['tenant_id'],'other')
        self.assertFalse(activated['publishing_enabled'])
        self.assertNotEqual(activated['session_token'],original)
        self.assertNotIn('overview',activated)
        self.assertEqual(self.call('/api/v1/dashboard',token=original)[0]
                         ['status'],'401 Unauthorized')
        _,view=self.call('/api/v1/dashboard',
            token=activated['session_token'])
        self.assertEqual(view['tenant_id'],'other')
        self.assertNotIn('sample product',str(view))

    def test_business_switch_refuses_nonmember_and_role_claims(self):
        token=self.login('shop')
        meta,_=self.call('/api/v1/businesses/activate',
            method='POST',token=token,body={
                'target_tenant_id':'unknown'})
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertEqual(self.call('/api/v1/dashboard',
            token=token)[0]['status'],'200 OK')
        meta,_=self.call('/api/v1/businesses/activate',
            method='POST',token=token,body={
                'target_tenant_id':'other','role':'owner'})
        self.assertEqual(meta['status'],'400 Bad Request')
        meta,_=self.call('/api/v1/businesses/activate',
            method='POST',body={'target_tenant_id':'other'})
        self.assertEqual(meta['status'],'401 Unauthorized')

    def test_business_switch_requires_https(self):
        token=self.login('shop')
        meta,_=self.call('/api/v1/businesses/activate',
            method='POST',token=token,body={
                'target_tenant_id':'other'},scheme='http',
            extra={'HTTP_X_FORWARDED_PROTO':'https'})
        self.assertEqual(meta['status'],'403 Forbidden')
        self.assertEqual(self.call('/api/v1/dashboard',
            token=token)[0]['status'],'200 OK')

    def test_google_without_verified_provider_unavailable(self):
        meta,challenge=self.call(
            '/api/v1/auth/google-challenge',method='POST',body={})
        self.assertEqual(meta['status'],'200 OK')
        meta,body=self.call('/api/v1/auth/google',method='POST',
            body={'challenge_id':challenge['challenge_id'],
                  'id_token':'unverified-client-token',
                  'tenant_id':'shop'})
        self.assertEqual(meta['status'],'401 Unauthorized')
        self.assertNotIn('session_token',body)

    def test_held_draft_copy_edit_requires_fresh_revision(self):
        token=self.login('shop')
        meta,created=self.call('/api/v1/content/drafts',method='POST',
            token=token,body={'channel':'facebook',
                'draft_text':'Initial text','suggestion':'Initial guidance',
                'required_items':['photo']})
        self.assertEqual(meta['status'],'201 Created')
        rid=created['request_id']
        _,before=self.call('/api/v1/drafts',token=token)
        original=next(x for x in before['drafts'] if x['request_id']==rid)
        self.assertEqual(original['revision'],1)
        meta,updated=self.call('/api/v1/content/drafts',method='PUT',
            token=token,body={'request_id':rid,'target':'draft_text',
                'revised_text':'Corrected copy','expected_revision':1})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(updated['revision'],2)
        self.assertEqual(updated['status'],'needs_content')
        self.assertFalse(updated['publishing_enabled'])
        _,after=self.call('/api/v1/drafts',token=token)
        item=next(x for x in after['drafts'] if x['request_id']==rid)
        self.assertEqual(item['draft_text'],'Corrected copy')
        self.assertEqual(item['suggestion'],'Initial guidance')
        self.assertEqual(item['revision'],2)
        self.assertEqual(self.call('/api/v1/content/drafts',
            method='PUT',token=token,body={'request_id':rid,
                'target':'suggestion','revised_text':'Stale',
                'expected_revision':1})[0]['status'],'409 Conflict')
        another=self.login('other')
        self.assertNotEqual(self.call('/api/v1/content/drafts',
            method='PUT',token=another,body={'request_id':rid,
                'target':'draft_text','revised_text':'Cross business',
                'expected_revision':2})[0]['status'],'200 OK')

    def test_authenticated_held_draft_create_and_hold(self):
        shop=self.login('shop')
        meta,created=self.call('/api/v1/content/drafts',
            method='POST',token=shop,body={
                'channel':'instagram',
                'draft_text':'Original product introduction',
                'suggestion':'Owner must review image and factual claims',
                'required_items':['image']})
        self.assertEqual(meta['status'],'201 Created')
        self.assertEqual(created['tenant_id'],'shop')
        self.assertEqual(created['status'],'needs_content')
        self.assertFalse(created['publishing_enabled'])
        _,all_drafts=self.call('/api/v1/drafts',token=shop)
        self.assertEqual(len(all_drafts['drafts']),2)
        draft_id=created['request_id']
        meta,held=self.call('/api/v1/content/hold',
            method='POST',token=shop,
            body={'request_id':draft_id,'status':'postponed'})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(held['status'],'postponed')
        _,remaining=self.call('/api/v1/dashboard',token=shop)
        self.assertEqual(len(remaining['drafts']),1)
        other=self.login('other')
        meta,_=self.call('/api/v1/content/hold',
            method='POST',token=other,
            body={'request_id':draft_id,'status':'needs_content'})
        self.assertIn(meta['status'],('401 Unauthorized','404 Not Found'))
        _,other_data=self.call('/api/v1/drafts',token=other)
        self.assertNotIn('Original product introduction',str(other_data))
        meta,reopened=self.call('/api/v1/content/hold',
            method='POST',token=shop,
            body={'request_id':draft_id,'status':'needs_content'})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(reopened['status'],'needs_content')

    def test_held_draft_api_refuses_publish_fields(self):
        token=self.login('shop')
        meta,result=self.call('/api/v1/content/drafts',
            method='POST',token=token,body={
                'channel':'facebook','draft_text':'Sample text',
                'suggestion':'Review manually',
                'required_items':['owner_review'],
                'publish_now':True})
        self.assertEqual(meta['status'],'400 Bad Request')
        self.assertNotIn('request_id',result)
        meta,result=self.call('/api/v1/content/hold',
            method='POST',token=token,
            body={'request_id':'a'*32,'status':'published'})
        self.assertEqual(meta['status'],'400 Bad Request')


    def test_owner_can_set_smart_and_manual_times_without_publishing(self):
        token=self.login('shop')
        manual={'mode':'manual','timezone':'America/New_York',
                'manual_times':['18:30','10:00']}
        meta,result=self.call('/api/v1/posting-preferences',
            method='PUT',token=token,body=manual)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(result['mode'],'manual')
        self.assertEqual(result['manual_times'],['10:00','18:30'])
        self.assertFalse(result['publishing_enabled'])
        _,read=self.call('/api/v1/posting-preferences',token=token)
        self.assertEqual(read['manual_times'],['10:00','18:30'])
        other=self.login('other')
        self.assertEqual(self.call('/api/v1/posting-preferences',
            method='PUT',token=other,body=manual)[0]['status'],
            '401 Unauthorized')
        _,other_read=self.call('/api/v1/posting-preferences',token=other)
        self.assertFalse(other_read['configured'])
        _,smart=self.call('/api/v1/posting-preferences',
            method='PUT',token=token,
            body={'mode':'smart','timezone':'America/New_York',
                  'manual_times':[]})
        self.assertEqual(smart['mode'],'smart')
        self.assertEqual(smart['manual_times'],[])

    def test_posting_write_refuses_privilege_claims_and_invalid_times(self):
        token=self.login()
        for bad in [
                {'mode':'manual','timezone':'America/New_York',
                 'manual_times':['10:00'],'tenant_id':'other'},
                {'mode':'manual','timezone':'America/New_York',
                 'manual_times':['10:00'],'publish':True},
                {'mode':'manual','timezone':'America/New_York',
                 'manual_times':['25:00']},
                {'mode':'smart','timezone':'America/New_York',
                 'manual_times':['10:00']}]:
            meta,_=self.call('/api/v1/posting-preferences',
                method='PUT',token=token,body=bad)
            self.assertEqual(meta['status'],'400 Bad Request')
        _,saved=self.call('/api/v1/posting-preferences',token=token)
        self.assertFalse(saved['configured'])

    def test_pending_only_media_preflight_never_grants_upload_or_publish(self):
        shop=self.login('shop')
        status,created=self.call('/api/v1/content/drafts',
            method='POST',token=shop,
            body={'channel':'facebook','draft_text':'Needs a photo',
                  'suggestion':'Image confirmation required',
                  'required_items':['image']})
        self.assertEqual(status['status'],'201 Created')
        request_id=created['request_id']
        meta,pending=self.call('/api/v1/content/upload-preflight',
            method='POST',token=shop,
            body={'request_id':request_id,'item':'image',
                  'media_type':'image/png','sha256':'f'*64,
                  'byte_count':200})
        self.assertEqual(meta['status'],'202 Accepted')
        self.assertEqual(pending['tenant_id'],'shop')
        self.assertEqual(pending['status'],'pending')
        self.assertIsNone(pending['upload_url'])
        self.assertFalse(pending['publishing_enabled'])
        self.assertNotIn('storage_key',pending)
        self.assertIsNone(self.app.attachments.resolve_verified(
            tenant_id='shop',request_id=request_id,item='image',
            attachment_id=pending['attachment_id']))
        other=self.login('other')
        bad,_=self.call('/api/v1/content/upload-preflight',
            method='POST',token=other,
            body={'request_id':request_id,'item':'image',
                  'media_type':'image/png','sha256':'f'*64,
                  'byte_count':200})
        self.assertIn(bad['status'],('404 Not Found','401 Unauthorized'))
        bad,_=self.call('/api/v1/content/upload-preflight',
            method='POST',token=shop,
            body={'request_id':request_id,'item':'image',
                  'media_type':'image/png','sha256':'f'*64,
                  'byte_count':200,'role':'owner'})
        self.assertEqual(bad['status'],'400 Bad Request')

    def test_owner_confirmed_fact_write_is_business_scoped(self):
        shop=self.login('shop')
        meta,saved=self.call('/api/v1/ai-business-facts',
            method='PUT',token=shop,
            body={'facts':{'business_name':'Example Shop',
                           'product':'Custom tumblers'},
                  'expected_revision':0})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(saved['revision'],1)
        self.assertEqual(saved['provenance'],'owner_confirmed')
        self.assertFalse(saved['publishing_enabled'])
        _,shop_facts=self.call('/api/v1/ai-business-facts',token=shop)
        self.assertEqual(shop_facts['facts']['product'],'Custom tumblers')
        other=self.login('other')
        _,other_facts=self.call('/api/v1/ai-business-facts',token=other)
        self.assertEqual(other_facts['facts'],{})
        denied,_=self.call('/api/v1/ai-business-facts',
            method='PUT',token=other,
            body={'facts':{'business_name':'Forged'},
                  'expected_revision':0})
        self.assertEqual(denied['status'],'403 Forbidden')
        conflict,_=self.call('/api/v1/ai-business-facts',
            method='PUT',token=shop,
            body={'facts':{'business_name':'Stale'},
                  'expected_revision':0})
        self.assertEqual(conflict['status'],'409 Conflict')
        _,again=self.call('/api/v1/ai-business-facts',token=shop)
        self.assertEqual(again['facts']['product'],'Custom tumblers')

    def test_local_product_draft_requires_confirmed_facts_and_costs_zero(self):
        shop=self.login('shop')
        bad,_=self.call('/api/v1/ai/local-product-draft',
            method='POST',token=shop,
            body={'platform':'facebook','include_image_prompt':True})
        self.assertEqual(bad['status'],'400 Bad Request')
        self.app.ai_business_facts.confirm(token=shop,now=101,
            facts={'business_name':'Example Shop','product':'Custom tumblers'})
        meta,created=self.call('/api/v1/ai/local-product-draft',
            method='POST',token=shop,
            body={'platform':'facebook','include_image_prompt':True})
        self.assertEqual(meta['status'],'201 Created')
        self.assertEqual(created['status'],'needs_media')
        self.assertEqual(created['openai_requests'],0)
        self.assertFalse(created['publishing_enabled'])
        self.assertFalse(created['media_attached'])
        self.assertIn('generic marketing illustration',created['image_prompt'])
        _,drafts=self.call('/api/v1/ai-drafts',token=shop)
        self.assertEqual(len(drafts['drafts']),1)
        self.assertEqual(drafts['drafts'][0]['draft_id'],created['draft_id'])
        other=self.login('other')
        _,separate=self.call('/api/v1/ai-drafts',token=other)
        self.assertEqual(separate['drafts'],[])
        bad,_=self.call('/api/v1/ai/local-product-draft',
            method='POST',token=other,
            body={'platform':'facebook','include_image_prompt':False})
        self.assertEqual(bad['status'],'400 Bad Request')
        _,costs=self.call('/api/v1/ai-cost-summary',token=shop)
        self.assertEqual(costs['events'],0)
        self.assertEqual(costs['estimated_micro_usd'],0)

    def test_manual_ai_component_edits_are_private_revision_guarded(self):
        owner=self.login('shop')
        first=self.app.ai_drafts.stage(token=owner,now=101,platform='facebook',
            response={'post_text':'Original copy',
                      'image_prompt':'Original image prompt'},
            include_image_prompt=True,needs_media=True)
        draft_id=first['draft_id']
        meta,edited=self.call('/api/v1/ai-drafts',method='PUT',token=owner,
            body={'draft_id':draft_id,'target':'post_text',
                  'revised_text':'Corrected copy','expected_revision':1})
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(edited['revision'],2)
        self.assertEqual(edited['post_text'],'Corrected copy')
        self.assertEqual(edited['image_prompt'],'Original image prompt')
        self.assertFalse(edited['publishing_enabled'])
        meta,stale=self.call('/api/v1/ai-drafts',method='PUT',token=owner,
            body={'draft_id':draft_id,'target':'post_text',
                  'revised_text':'Older copy','expected_revision':1})
        self.assertEqual(meta['status'],'400 Bad Request')
        other=self.login('other')
        meta,_=self.call('/api/v1/ai-drafts',method='PUT',token=other,
            body={'draft_id':draft_id,'target':'post_text',
                  'revised_text':'Other business','expected_revision':2})
        self.assertEqual(meta['status'],'404 Not Found')
        _,latest=self.call('/api/v1/ai-drafts',token=owner)
        self.assertEqual(latest['drafts'][0]['post_text'],'Corrected copy')
        self.assertEqual(len(latest['drafts']),1)
        self.assertEqual(self.app.ai_costs.summary_trusted(
            tenant_id='shop',subject_id=self.subject)['events'],0)

    def test_local_service_draft_works_for_service_business(self):
        owner=self.app.sessions.issue(
            Principal('other-owner','other',Role.OWNER),now=100)
        self.app.ai_business_facts.confirm(token=owner,now=101,
            facts={'business_name':'Example Services',
                   'service':'Commercial facility cleaning'})
        creator=self.login('other')
        meta,created=self.call('/api/v1/ai/local-service-draft',
            method='POST',token=creator,
            body={'platform':'facebook','include_image_prompt':True})
        self.assertEqual(meta['status'],'201 Created')
        self.assertEqual(created['status'],'needs_media')
        self.assertEqual(created['generation_method'],'local_template')
        self.assertEqual(created['openai_requests'],0)
        self.assertIn('Commercial facility cleaning',created['post_text'])
        self.assertIn('not a photograph of real workers',created['image_prompt'])
        _,mine=self.call('/api/v1/ai-drafts',token=creator)
        self.assertEqual(len(mine['drafts']),1)
        other=self.login('shop')
        _,separate=self.call('/api/v1/ai-drafts',token=other)
        self.assertEqual(separate['drafts'],[])

    def test_manual_image_bytes_are_staged_but_never_verified(self):
        import hashlib
        import tempfile
        from pathlib import Path
        png=b'\x89PNG\r\n\x1a\n'+b'a-test-artwork'
        with tempfile.TemporaryDirectory() as folder:
            self.app=BAMOfflineGateway(self.db,enabled=True,
                clock=lambda:101,pending_media_dir=str(Path(folder)/'pending'))
            token=self.login()
            _,capabilities=self.call('/api/v1/dashboard',token=token)
            self.assertTrue(capabilities['pending_media_available'])
            meta,created=self.call('/api/v1/content/drafts',
                method='POST',token=token,body={
                    'channel':'facebook','draft_text':'Test artwork',
                    'suggestion':'Provide an image',
                    'required_items':['image']})
            self.assertEqual(meta['status'],'201 Created')
            rid=created['request_id']
            meta,intent=self.call('/api/v1/content/upload-preflight',
                method='POST',token=token,body={
                    'request_id':rid,'item':'image',
                    'media_type':'image/png',
                    'sha256':hashlib.sha256(png).hexdigest(),
                    'byte_count':len(png)})
            self.assertEqual(meta['status'],'202 Accepted')
            aid=intent['attachment_id']
            headers={
                'CONTENT_TYPE':'image/png',
                'CONTENT_LENGTH':str(len(png)),
                'HTTP_X_BAM_ATTACHMENT_ID':aid,
                'wsgi.input':io.BytesIO(png)}
            meta,received=self.call('/api/v1/content/media-bytes',
                method='PUT',token=token,extra=headers)
            self.assertEqual(meta['status'],'202 Accepted')
            self.assertEqual(received['status'],'pending_scan')
            self.assertFalse(received['publishing_enabled'])
            self.assertFalse(received['media_verified'])
            self.assertNotIn('storage_key',str(received))
            self.assertEqual(
                (Path(folder)/'pending'/(aid+'.pending')).read_bytes(),png)
            self.assertIsNone(self.app.attachments.resolve_verified(
                tenant_id='shop',request_id=rid,item='image',attachment_id=aid))
            self.assertEqual(self.app.requests.get(
                tenant_id='shop',request_id=rid)['status'],'needs_content')
            other=self.login('other')
            meta,_=self.call('/api/v1/content/media-bytes',
                method='PUT',token=other,
                extra={**headers,'wsgi.input':io.BytesIO(png)})
            self.assertIn(meta['status'],('404 Not Found','401 Unauthorized'))
            meta,_=self.call('/api/v1/content/media-bytes',
                method='PUT',token=token,
                extra={**headers,'wsgi.input':io.BytesIO(png)})
            self.assertEqual(meta['status'],'409 Conflict')

    def test_media_bytes_route_unavailable_without_external_private_storage(self):
        token=self.login()
        meta,_=self.call('/api/v1/content/media-bytes',
            method='PUT',token=token,body={})
        self.assertEqual(meta['status'],'503 Service Unavailable')

    def test_read_only_posting_time_preview_is_session_scoped(self):
        owner=self.login('shop')
        self.app.preferences.set(token=owner,tenant_id='shop',
            mode='manual',timezone='America/New_York',
            manual_times=['10:00','18:30'],now=101)
        meta,preview=self.call('/api/v1/posting-time-preview',token=owner)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(preview['tenant_id'],'shop')
        self.assertEqual(preview['status'],'manual_preview')
        self.assertGreater(len(preview['slots']),0)
        self.assertFalse(preview['publishing_enabled'])
        self.assertNotIn('queued',str(preview))
        other=self.login('other')
        _,missing=self.call('/api/v1/posting-time-preview',token=other)
        self.assertEqual(missing['tenant_id'],'other')
        self.assertEqual(missing['status'],'not_configured')
        self.assertEqual(missing['slots'],[])
        bad,_=self.call('/api/v1/posting-time-preview',
            token=owner,method='POST',body={'tenant_id':'other'})
        self.assertEqual(bad['status'],'405 Method Not Allowed')
        bad,_=self.call('/api/v1/posting-time-preview',
            token=owner,extra={'QUERY_STRING':'tenant_id=other'})
        self.assertEqual(bad['status'],'400 Bad Request')
        bad,_=self.call('/api/v1/posting-time-preview')
        self.assertEqual(bad['status'],'401 Unauthorized')

    def test_ai_drafts_are_scoped_and_unpublished(self):
        shop=self.login('shop')
        other=self.login('other')
        self.app.ai_drafts.stage(token=shop,now=101,
            platform='facebook',
            response={'post_text':'Verified-fact draft example',
                      'image_prompt':'Make an original product scene'},
            include_image_prompt=True,needs_media=True)
        _,first=self.call('/api/v1/ai-drafts',token=shop)
        _,second=self.call('/api/v1/ai-drafts',token=other)
        self.assertEqual(len(first['drafts']),1)
        self.assertEqual(first['drafts'][0]['status'],'needs_media')
        self.assertEqual(second['drafts'],[])
        self.assertFalse(first['publishing_enabled'])


if __name__=='__main__':
    unittest.main()
