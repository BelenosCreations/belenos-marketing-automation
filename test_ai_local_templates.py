import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_draft_request import AIDraftRequestBuilder
from ai_local_templates import LocalDraftTemplates

class LocalTemplateTests(unittest.TestCase):
    def setUp(self):
        db=sqlite3.connect(':memory:')
        directory=AccountDirectory(db)
        directory.bootstrap_owner('shop','owner')
        sessions=SessionStore(db)
        self.token=sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.templates=LocalDraftTemplates(request_builder=AIDraftRequestBuilder(
            policy_store=AIPolicyStore(db=db,sessions=sessions,
                                       directory=directory)))

    def test_literal_verified_facts_only_and_no_api_cost(self):
        draft=self.templates.product_spotlight(token=self.token,now=101,
            verified_facts={'business_name':'Example Shop',
                            'product':'Custom tumblers'},
            platform='facebook')
        self.assertEqual(draft['post_text'],
                         'Example Shop: Custom tumblers. Contact us for details.')
        self.assertEqual(draft['openai_requests'],0)
        self.assertEqual(draft['status'],'draft_pending_verification')
        self.assertFalse(draft['publishing_enabled'])
        self.assertNotIn('discount',draft['post_text'].lower())

    def test_optional_generic_image_prompt_has_no_paid_calls(self):
        draft=self.templates.product_spotlight(token=self.token,now=101,
            verified_facts={'business_name':'Example Shop',
                            'product':'Custom tumblers'},
            platform='facebook',include_image_prompt=True)
        self.assertEqual(draft['generation_method'],'local_template')
        self.assertEqual(draft['openai_requests'],0)
        self.assertIn('generic marketing illustration',draft['image_prompt'])
        self.assertEqual(draft['status'],'needs_media')
        self.assertNotIn('20 oz',draft['image_prompt'])
        self.assertFalse(draft['publishing_enabled'])

    def test_missing_fact_rejected(self):
        with self.assertRaises(ValueError):
            self.templates.product_spotlight(token=self.token,now=101,
                verified_facts={'business_name':'Example Shop'},
                platform='facebook')

if __name__=='__main__':
    unittest.main()
