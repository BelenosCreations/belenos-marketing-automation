import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from optimizer import Candidate
from recommendation_gate import RecommendationGate
from editorial_inbox import EditorialInbox
from editorial_attestations import EditorialAttestations
from editorial_intake_service import EditorialIntakeService

class EditorialIntakeTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','otherowner')
        self.directory.set_member(Principal('owner','shop',Role.OWNER),'manager',Role.MARKETING_MANAGER)
        self.directory.set_member(Principal('owner','shop',Role.OWNER),'viewer',Role.VIEWER)
        self.sessions=SessionStore(self.db)
        self.tokens={n:self.sessions.issue(Principal(n,'shop',role),now=100)
            for n,role in [('owner',Role.OWNER),('manager',Role.MARKETING_MANAGER),('viewer',Role.VIEWER)]}
        self.gate=RecommendationGate(self.db)
        self.gate.sources.create_profile('shop','Shop','printing',['education'])
        self.gate.sources.create_profile('other','Other','cleaning',['cleaning'])
        self.url='https://example.org/maker'
        self.gate.sources.add_source(tenant_id='shop',source_url=self.url,source_name='Maker',topic='education',approved=True)
        self.gate.creators.set_status(tenant_id='shop',platform='youtube',account_id='maker',status='approved',reason='educator')
        self.candidate=Candidate(source_name='Maker',source_url=self.url,original_url=self.url+'/post',category='education',summary='Tips',source_approved=True,verified_facts=True)
        self.inbox=EditorialInbox(self.db,self.gate)
        self.attestations=EditorialAttestations(self.db)
        self.service=EditorialIntakeService(inbox=self.inbox,sessions=self.sessions,directory=self.directory,attestations=self.attestations)

    def attest(self, verified=True, risk='cleared', expires=200):
        self.attestations.record_trusted(tenant_id='shop',original_url=self.candidate.original_url,
            platform='youtube',account_id='maker',identity_verified=verified,
            competitor_status=risk,verified_at=100,expires_at=expires)

    def consider(self, user='owner', **kwargs):
        args=dict(token=self.tokens[user],tenant_id='shop',topic='education',candidate=self.candidate,now=101)
        args.update(kwargs)
        return self.service.consider(**args)

    def test_missing_attestation_holds(self):
        self.assertEqual(self.consider()[0],'approval_required')
        self.assertEqual(self.inbox.list_for_business('shop'),[])

    def test_verified_creator_queues_review_only(self):
        self.attest()
        self.assertEqual(self.consider()[0],'review')
        self.assertEqual(self.inbox.list_for_business('shop')[0][3],'review')

    def test_unverified_creator_holds(self):
        self.attest(verified=False)
        self.assertEqual(self.consider(),('review','identity_not_verified'))
        self.assertEqual(self.inbox.list_for_business('shop')[0][3],'review')

    def test_expired_attestation_holds(self):
        self.attest(expires=101)
        self.assertEqual(self.consider()[0],'approval_required')

    def test_manager_can_intake(self):
        self.attest()
        self.assertEqual(self.consider('manager')[0],'review')

    def test_viewer_denied(self):
        self.attest()
        with self.assertRaises(PermissionError):self.consider('viewer')

    def test_removed_manager_denied(self):
        self.attest()
        self.directory.set_member(Principal('owner','shop',Role.OWNER),'manager',Role.MARKETING_MANAGER,active=False)
        with self.assertRaises(PermissionError):self.consider('manager')

    def test_cross_tenant_denied(self):
        self.attest()
        with self.assertRaises(PermissionError):self.consider(tenant_id='other',topic='cleaning')

    def test_client_cannot_override_competitor_clearance(self):
        self.attest(risk='possible')
        with self.assertRaises(TypeError):self.consider(local_competitor_risk='cleared')

    def test_competitor_block_removes_existing_queue(self):
        self.attest()
        self.consider()
        self.gate.creators.set_status(tenant_id='shop',platform='youtube',account_id='maker',status='blocked',reason='competitor')
        self.assertEqual(self.consider()[0],'blocked')
        self.assertEqual(self.inbox.list_for_business('shop'),[])

if __name__=='__main__':unittest.main()
