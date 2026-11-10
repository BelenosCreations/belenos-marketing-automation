import unittest
from truthguard_span_audit import ClaimSpanAudit

class ClaimSpanAuditTests(unittest.TestCase):
    def setUp(self):
        self.draft='Custom prints available. Same-day pickup guaranteed.'
        self.first={'start':0,'end':23,'key':'product',
                    'text':'Custom prints available.'}

    def test_valid_span(self):
        result=ClaimSpanAudit.audit(draft_text=self.draft,annotations=[self.first])
        self.assertTrue(result['annotation_integrity'])
        self.assertFalse(result['all_text_annotated'])
        self.assertFalse(result['publish_eligible'])

    def test_unannotated_claim_visible(self):
        result=ClaimSpanAudit.audit(draft_text=self.draft,annotations=[self.first])
        self.assertIn('Same-day pickup guaranteed.', ''.join(result['unannotated_text']))

    def test_modified_text_rejected(self):
        bad=dict(self.first,text='Custom prints guaranteed.')
        result=ClaimSpanAudit.audit(draft_text=self.draft,annotations=[bad])
        self.assertEqual(result['issues'][0]['reason'],'span_mismatch')

    def test_overlapping_spans_rejected(self):
        other={'start':7,'end':23,'key':'other','text':self.draft[7:23]}
        result=ClaimSpanAudit.audit(draft_text=self.draft,
                                    annotations=[self.first,other])
        self.assertEqual(result['issues'][0]['reason'],'overlapping_spans')

    def test_full_annotation_does_not_establish_truth(self):
        annotation={'start':0,'end':len(self.draft),'key':'claim','text':self.draft}
        result=ClaimSpanAudit.audit(draft_text=self.draft,annotations=[annotation])
        self.assertTrue(result['all_text_annotated'])
        self.assertFalse(result['fact_extraction_complete'])
        self.assertFalse(result['publish_eligible'])

    def test_empty_claim_list_fails_closed(self):
        result=ClaimSpanAudit.audit(draft_text=self.draft,annotations=[])
        self.assertFalse(result['all_text_annotated'])

    def test_boolean_offsets_rejected(self):
        bad=dict(self.first,start=True)
        result=ClaimSpanAudit.audit(draft_text=self.draft,annotations=[bad])
        self.assertEqual(result['issues'][0]['reason'],'span_mismatch')

    def test_extra_fields_rejected(self):
        bad=dict(self.first,approved=True)
        result=ClaimSpanAudit.audit(draft_text=self.draft,annotations=[bad])
        self.assertEqual(result['issues'][0]['reason'],'invalid_annotation')

    def test_empty_draft_rejected(self):
        with self.assertRaises(ValueError):
            ClaimSpanAudit.audit(draft_text=' ',annotations=[])

    def test_annotation_limit(self):
        with self.assertRaises(ValueError):
            ClaimSpanAudit.audit(draft_text=self.draft,annotations=[self.first]*101)

if __name__=='__main__':unittest.main()
