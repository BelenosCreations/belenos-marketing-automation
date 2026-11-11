import sqlite3
import unittest
from business_curation import BusinessCuration
from optimizer import Candidate

class BusinessCurationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.curation=BusinessCuration(self.db)
        self.curation.create_profile('belenos','Belenos Creations','custom products',['3d_printing','local'])
        self.curation.create_profile('busy_b','Busy B Cleaning','commercial cleaning',['facility_care','local'])
        self.print_source='https://example.org/maker'
        self.clean_source='https://example.org/cleaning'
        self.curation.add_source(tenant_id='belenos',source_url=self.print_source,source_name='Maker',topic='3d_printing',approved=True)
        self.curation.add_source(tenant_id='busy_b',source_url=self.clean_source,source_name='Facility Expert',topic='facility_care',approved=True)

    def candidate(self,source_url):
        return Candidate(source_name='Expert',source_url=source_url,original_url=source_url+'/post',
                         category='education',summary='Helpful information',source_approved=True,verified_facts=True)

    def test_belenos_printing_source_allowed(self):
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='3d_printing',candidate=self.candidate(self.print_source),local_competitor_risk='cleared')[0],'eligible_link_only')

    def test_busy_b_printing_source_not_approved(self):
        self.assertEqual(self.curation.evaluate(tenant_id='busy_b',topic='3d_printing',candidate=self.candidate(self.print_source),local_competitor_risk='cleared')[0],'approval_required')

    def test_busy_b_facility_source_allowed(self):
        self.assertEqual(self.curation.evaluate(tenant_id='busy_b',topic='facility_care',candidate=self.candidate(self.clean_source),local_competitor_risk='cleared')[0],'eligible_link_only')

    def test_belenos_facility_source_not_approved(self):
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='facility_care',candidate=self.candidate(self.clean_source),local_competitor_risk='cleared')[0],'approval_required')

    def test_cross_topic_same_business_denied(self):
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='local',candidate=self.candidate(self.print_source),local_competitor_risk='cleared')[0],'approval_required')

    def test_unapproved_source_denied(self):
        self.curation.add_source(tenant_id='belenos',source_url='https://example.org/new',source_name='New',topic='3d_printing',approved=False)
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='3d_printing',candidate=self.candidate('https://example.org/new'))[0],'approval_required')

    def test_source_cannot_register_for_foreign_topic(self):
        with self.assertRaises(PermissionError):
            self.curation.add_source(tenant_id='busy_b',source_url=self.print_source,source_name='Maker',topic='3d_printing',approved=True)

    def test_candidate_claim_cannot_override_business_approval(self):
        self.assertEqual(self.curation.evaluate(tenant_id='busy_b',topic='facility_care',candidate=self.candidate(self.print_source),local_competitor_risk='cleared')[0],'approval_required')

    def test_missing_tenant_denied(self):
        self.assertEqual(self.curation.evaluate(tenant_id='unknown',topic='3d_printing',candidate=self.candidate(self.print_source),local_competitor_risk='cleared')[0],'approval_required')

    def test_invalid_source_url_denied(self):
        with self.assertRaises(ValueError):
            self.curation.add_source(tenant_id='belenos',source_url='http://example.org',source_name='Bad',topic='3d_printing',approved=True)

    def test_shared_facebook_domain_cannot_be_blocked_globally(self):
        with self.assertRaises(ValueError):
            self.curation.block_competitor(tenant_id='belenos',
                                          source_url='https://facebook.com/competitor')

    def test_shared_youtube_domain_cannot_be_blocked_globally(self):
        with self.assertRaises(ValueError):
            self.curation.block_competitor(tenant_id='belenos',
                                          source_url='https://youtube.com/@competitor')

    def test_source_approval_can_be_revoked(self):
        self.curation.add_source(tenant_id='belenos',source_url=self.print_source,source_name='Maker',topic='3d_printing',approved=False)
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='3d_printing',candidate=self.candidate(self.print_source),local_competitor_risk='cleared')[0],'approval_required')

    def test_duplicate_business_profile_denied(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.curation.create_profile('belenos','Duplicate','other',['other'])

    def test_known_competitor_blocked_even_if_approved(self):
        self.curation.block_competitor(tenant_id='belenos',source_url=self.print_source)
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='3d_printing',candidate=self.candidate(self.print_source),local_competitor_risk='cleared')[0],'blocked')

    def test_competitor_block_is_business_specific(self):
        self.curation.block_competitor(tenant_id='busy_b',source_url=self.print_source)
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='3d_printing',candidate=self.candidate(self.print_source),local_competitor_risk='cleared')[0],'eligible_link_only')

    def test_unscreened_creator_held(self):
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='3d_printing',candidate=self.candidate(self.print_source))[0],'approval_required')

    def test_possible_local_competitor_held(self):
        self.assertEqual(self.curation.evaluate(tenant_id='belenos',topic='3d_printing',candidate=self.candidate(self.print_source),local_competitor_risk='possible')[0],'approval_required')

    def test_competitor_subdomain_blocked(self):
        self.curation.block_competitor(tenant_id='belenos',source_url=self.print_source)
        item=Candidate(source_name='Maker',source_url='https://shop.example.org/maker',original_url='https://shop.example.org/maker/post',category='education',summary='Print tips',source_approved=True,verified_facts=True)
        result=self.curation.evaluate(tenant_id='belenos',topic='3d_printing',candidate=item,local_competitor_risk='cleared')
        self.assertEqual(result,('blocked','known_competitor'))

if __name__=='__main__': unittest.main()
