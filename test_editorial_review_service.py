import sqlite3
from dataclasses import replace
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from optimizer import Candidate
from recommendation_gate import RecommendationGate
from editorial_inbox import EditorialInbox
from editorial_review_service import EditorialReviewService
from editorial_attestations import EditorialAttestations

class EditorialReviewServiceTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('belenos','owner')
        self.directory.bootstrap_owner('busy_b','other_owner')
        self.directory.set_member(Principal('owner','belenos',Role.OWNER),'manager',Role.MARKETING_MANAGER)
        self.directory.set_member(Principal('owner','belenos',Role.OWNER),'viewer',Role.VIEWER)
        self.sessions=SessionStore(self.db)
        self.tokens={name:self.sessions.issue(Principal(name,'belenos',role),now=100)
            for name,role in [('owner',Role.OWNER),('manager',Role.MARKETING_MANAGER),('viewer',Role.VIEWER)]}
        self.gate=RecommendationGate(self.db)
        self.gate.sources.create_profile('belenos','Belenos','printing',['3d_printing'])
        self.gate.sources.create_profile('busy_b','Busy B','cleaning',['facility_care'])
        self.gate.sources.add_source(tenant_id='belenos',source_url='https://example.org/maker',
                                     source_name='Maker',topic='3d_printing',approved=True)
        self.gate.creators.set_status(tenant_id='belenos',platform='youtube',
                                      account_id='maker',status='approved',reason='educator')
        self.inbox=EditorialInbox(self.db,self.gate)
        self.candidate=Candidate(source_name='Maker',source_url='https://example.org/maker',
                                 original_url='https://example.org/maker/post',category='education',
                                 summary='Print tips',source_approved=True,verified_facts=True)
        self.args=dict(tenant_id='belenos',topic='3d_printing',candidate=self.candidate,
                       platform='youtube',account_id='maker',identity_verified=True,
                       local_competitor_risk='cleared')
        self.inbox.consider(**self.args)
        self.attestations=EditorialAttestations(self.db)
        self.attestations.record_trusted(tenant_id='belenos',original_url=self.candidate.original_url,
            platform='youtube',account_id='maker',identity_verified=True,
            competitor_status='cleared',verified_at=100,expires_at=200)
        self.service=EditorialReviewService(inbox=self.inbox,sessions=self.sessions,
                                            directory=self.directory,attestations=self.attestations)

    def check(self,name='owner',**kwargs):
        args=dict(tenant_id='belenos',topic='3d_printing',candidate=self.candidate)
        args.update(kwargs)
        return self.service.recheck(token=self.tokens[name],now=101,**args)

    def test_owner_can_recheck(self):
        self.assertEqual(self.check()[0],'eligible_for_human_review')

    def test_manager_can_recheck(self):
        self.assertEqual(self.check('manager')[0],'eligible_for_human_review')

    def test_viewer_denied(self):
        with self.assertRaises(PermissionError):self.check('viewer')

    def test_manager_deactivated_denied(self):
        self.directory.set_member(Principal('owner','belenos',Role.OWNER),'manager',Role.MARKETING_MANAGER,active=False)
        with self.assertRaises(PermissionError):self.check('manager')

    def test_cross_business_denied(self):
        with self.assertRaises(PermissionError):self.check(tenant_id='busy_b',topic='facility_care')

    def test_revoked_token_denied(self):
        self.sessions.revoke(self.tokens['owner'],now=100)
        with self.assertRaises(PermissionError):self.check()

    def test_expired_token_denied(self):
        with self.assertRaises(PermissionError):
            self.service.recheck(token=self.tokens['owner'],now=4000,tenant_id='belenos',topic='3d_printing',candidate=self.candidate)

    def test_competitor_revocation_blocks_review(self):
        self.gate.creators.set_status(tenant_id='belenos',platform='youtube',
                                      account_id='maker',status='blocked',reason='competitor')
        self.assertEqual(self.check()[0],'blocked')

    def test_unverified_creator_held(self):
        self.attestations.record_trusted(tenant_id='belenos',original_url=self.candidate.original_url,
            platform='youtube',account_id='maker',identity_verified=False,
            competitor_status='cleared',verified_at=100,expires_at=200)
        self.assertEqual(self.check()[0],'approval_required')

    def test_unknown_competitor_status_held(self):
        self.attestations.record_trusted(tenant_id='belenos',original_url=self.candidate.original_url,
            platform='youtube',account_id='maker',identity_verified=True,
            competitor_status='unknown',verified_at=100,expires_at=200)
        self.assertEqual(self.check()[0],'approval_required')

    def test_expired_attestation_held(self):
        self.attestations.record_trusted(tenant_id='belenos',original_url=self.candidate.original_url,
            platform='youtube',account_id='maker',identity_verified=True,
            competitor_status='cleared',verified_at=90,expires_at=101)
        self.assertEqual(self.check()[0],'approval_required')

    def test_modified_summary_cannot_replace_queued_content(self):
        modified=replace(self.candidate,summary='Different claims')
        self.assertEqual(self.check(candidate=modified),
                         ('blocked','queued_identity_or_topic_mismatch'))

    def test_modified_source_cannot_replace_queued_content(self):
        modified=replace(self.candidate,source_url='https://elsewhere.example/post')
        self.assertEqual(self.check(candidate=modified)[0],'blocked')

    def test_modified_verification_flags_cannot_replace_queued_content(self):
        modified=replace(self.candidate,verified_facts=False)
        self.assertEqual(self.check(candidate=modified)[0],'blocked')

    def test_mobile_cannot_pass_clearance_flag(self):
        with self.assertRaises(TypeError):self.check(identity_verified=True)

if __name__=='__main__':unittest.main()
