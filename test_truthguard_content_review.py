import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from truthguard_knowledge import TruthGuardKnowledge
from truthguard_review import TruthGuardReviewer
from truthguard_content_review import TruthGuardContentReview

class TruthGuardContentReviewTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','otherowner')
        sessions=SessionStore(db)
        self.owner=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.other=sessions.issue(Principal('otherowner','other',Role.OWNER),now=100)
        requests=ContentRequests(db)
        self.request_id=requests.create(tenant_id='shop',channel='facebook',
            draft_text='Custom resin-printed artwork',suggestion='Provide photo',
            required_items=['photo'],now=101)
        service=ContentRequestService(requests=requests,sessions=sessions,
            directory=directory,attachments=AttachmentRegistry(db))
        knowledge=TruthGuardKnowledge(db)
        knowledge.approve(tenant_id='shop',claim_key='product',
            value='Custom resin-printed artwork',source='owner-confirmed',
            approved_by='owner',now=100)
        self.review=TruthGuardContentReview(content_service=service,
            reviewer=TruthGuardReviewer(knowledge))
        self.claims=[{'key':'product','text':'Custom resin-printed artwork'}]

    def inspect(self,**changes):
        args=dict(token=self.owner,tenant_id='shop',
                  request_id=self.request_id,claims=self.claims,now=102)
        args.update(changes)
        return self.review.review(**args)

    def test_verified_claim_still_held(self):
        report=self.inspect()
        self.assertEqual(report['truthguard']['claims'][0]['status'],'verified')
        self.assertEqual(report['status'],'held')
        self.assertFalse(report['publishing_enabled'])

    def test_missing_content_is_not_complete(self):
        self.assertFalse(self.inspect()['content_complete'])

    def test_unsupported_claim_held(self):
        report=self.inspect(claims=[{'key':'guarantee','text':'Lasts 50 years'}])
        self.assertEqual(report['truthguard']['claims'][0]['status'],'unsupported')

    def test_cross_business_denied(self):
        with self.assertRaises(PermissionError):
            self.inspect(tenant_id='other')

    def test_other_token_denied(self):
        with self.assertRaises(PermissionError):
            self.inspect(token=self.other)

    def test_expired_session_denied(self):
        with self.assertRaises(PermissionError):
            self.inspect(now=4000)

    def test_span_audit_exposes_unannotated_text(self):
        report=self.inspect()
        self.assertFalse(report['span_audit']['all_text_annotated'])
        self.assertFalse(report['span_audit']['publish_eligible'])

    def test_span_annotation_remains_nonpublishing(self):
        text='Custom resin-printed artwork'
        report=self.inspect(annotations=[{'start':0,'end':len(text),
            'key':'product','text':text}])
        self.assertTrue(report['span_audit']['all_text_annotated'])
        self.assertFalse(report['span_audit']['fact_extraction_complete'])
        self.assertEqual(report['status'],'held')

    def test_verified_but_detached_claim_is_not_grounded(self):
        report=self.inspect()
        self.assertEqual(report['truthguard']['claims'][0]['status'],'verified')
        self.assertFalse(report['claims_grounded_in_draft'])
        self.assertEqual(len(report['detached_claims']),1)

    def test_verified_claim_with_exact_span_is_grounded_but_held(self):
        text='Custom resin-printed artwork'
        report=self.inspect(annotations=[{'start':0,'end':len(text),
            'key':'product','text':text}])
        self.assertTrue(report['claims_grounded_in_draft'])
        self.assertEqual(report['detached_claims'],[])
        self.assertFalse(report['publishing_enabled'])

    def test_mismatched_claim_span_rejected(self):
        report=self.inspect(annotations=[{'start':0,'end':6,
            'key':'product','text':'Custom'}])
        self.assertFalse(report['claims_grounded_in_draft'])
        self.assertEqual(len(report['detached_claims']),1)

    def test_unhashable_claim_rejected_cleanly(self):
        with self.assertRaises(ValueError):
            self.inspect(claims=[{'key':['invalid'],'text':'hello'}])

    def test_too_many_claims_rejected(self):
        with self.assertRaises(ValueError):
            self.inspect(claims=self.claims*101)

    def test_high_risk_statement_without_annotation_is_uncovered(self):
        request_id=self.review.content_service.create(token=self.owner,
            tenant_id='shop',channel='facebook',draft_text='Today only $18',
            suggestion='Provide photo',required_items=['photo'],now=102)
        report=self.inspect(request_id=request_id)
        self.assertFalse(report['risk_signals_annotated'])
        self.assertTrue(report['uncovered_risk_signals'])

    def test_high_risk_statement_annotated_still_held(self):
        text='Today only $18'
        request_id=self.review.content_service.create(token=self.owner,
            tenant_id='shop',channel='facebook',draft_text=text,
            suggestion='Provide photo',required_items=['photo'],now=102)
        report=self.inspect(request_id=request_id,claims=[],
            annotations=[{'start':0,'end':len(text),'key':'offer','text':text}])
        self.assertTrue(report['risk_signals_annotated'])
        self.assertEqual(report['uncovered_risk_signals'],[])
        self.assertFalse(report['publishing_enabled'])

    def test_unknown_request_denied(self):
        with self.assertRaises(KeyError):
            self.inspect(request_id='missing')

if __name__=='__main__':unittest.main()
