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

    def test_real_identity_to_dashboard_and_ai_panels(self):
        token=self.login()
        meta,dashboard=self.call('/api/v1/dashboard',token=token)
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(dashboard['tenant_id'],'shop')
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
