import sqlite3
import unittest
from content_requests import ContentRequests

class ContentRequestsTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.queue=ContentRequests(self.db)
        self.r=self.queue.create(tenant_id='shop',channel='facebook',
            draft_text='A custom project we loved...',suggestion='Take a product photo',
            required_items=['photo','customer_permission'],now=100,priority=5)

    def test_draft_starts_held(self):
        item=self.queue.get(tenant_id='shop',request_id=self.r)
        self.assertEqual(item['status'],'needs_content')
        self.assertEqual(item['provided_items'],{})

    def test_single_component_revision_and_stale_conflict(self):
        start=self.queue.get(tenant_id='shop',request_id=self.r)
        self.assertEqual(start['revision'],1)
        revised=self.queue.revise(tenant_id='shop',request_id=self.r,
            target='draft_text',revised_text='Updated project',
            expected_revision=1,now=101)
        self.assertEqual(revised['revision'],2)
        self.assertEqual(revised['draft_text'],'Updated project')
        self.assertEqual(revised['suggestion'],'Take a product photo')
        self.assertEqual(revised['status'],'needs_content')
        with self.assertRaises(ValueError):
            self.queue.revise(tenant_id='shop',request_id=self.r,
                target='suggestion',revised_text='Stale',
                expected_revision=1,now=102)
        revised=self.queue.revise(tenant_id='shop',request_id=self.r,
            target='suggestion',revised_text='Updated guidance',
            expected_revision=2,now=102)
        self.assertEqual(revised['revision'],3)
        self.assertEqual(revised['draft_text'],'Updated project')
        self.assertEqual(revised['suggestion'],'Updated guidance')
        for invalid in ('publish','status','required_items'):
            with self.assertRaises(ValueError):
                self.queue.revise(tenant_id='shop',request_id=self.r,
                    target=invalid,revised_text='hijack',
                    expected_revision=3,now=103)
        with self.assertRaises(KeyError):
            self.queue.revise(tenant_id='another',request_id=self.r,
                target='draft_text',revised_text='Cross-tenant',
                expected_revision=3,now=103)
        self.assertEqual(self.queue.get(tenant_id='shop',
            request_id=self.r)['revision'],3)

    def test_revision_changes_after_hold_and_supply(self):
        self.queue.set_hold(tenant_id='shop',request_id=self.r,
            status='postponed',now=101)
        self.assertEqual(self.queue.get(tenant_id='shop',
            request_id=self.r)['revision'],2)
        with self.assertRaises(ValueError):
            self.queue.revise(tenant_id='shop',request_id=self.r,
                target='draft_text',revised_text='Stale',
                expected_revision=1,now=102)
        self.queue.set_hold(tenant_id='shop',request_id=self.r,
            status='needs_content',now=102)
        self.queue.provide(tenant_id='shop',request_id=self.r,
            item='photo',content_reference='asset:123',now=103)
        self.assertEqual(self.queue.get(tenant_id='shop',
            request_id=self.r)['revision'],4)

    def test_partial_content_stays_held(self):
        self.assertEqual(self.queue.provide(tenant_id='shop',request_id=self.r,
            item='photo',content_reference='asset:123',now=101),'needs_content')

    def test_complete_content_requires_review(self):
        self.queue.provide(tenant_id='shop',request_id=self.r,
            item='photo',content_reference='asset:123',now=101)
        self.assertEqual(self.queue.provide(tenant_id='shop',request_id=self.r,
            item='customer_permission',content_reference='approval:456',now=102),'ready_for_review')
        self.assertNotIn('publish',str(self.queue.get(tenant_id='shop',request_id=self.r)['status']))

    def test_missing_content_reference_rejected(self):
        with self.assertRaises(ValueError):
            self.queue.provide(tenant_id='shop',request_id=self.r,
                item='photo',content_reference='',now=101)

    def test_cross_business_access_fails(self):
        self.assertIsNone(self.queue.get(tenant_id='other',request_id=self.r))
        with self.assertRaises(KeyError):
            self.queue.provide(tenant_id='other',request_id=self.r,
                item='photo',content_reference='asset:123',now=101)

    def test_postpone_and_resume(self):
        self.queue.set_hold(tenant_id='shop',request_id=self.r,status='postponed',now=101)
        with self.assertRaises(ValueError):
            self.queue.provide(tenant_id='shop',request_id=self.r,
                item='photo',content_reference='asset:123',now=102)
        self.queue.set_hold(tenant_id='shop',request_id=self.r,status='needs_content',now=103)
        self.assertEqual(self.queue.get(tenant_id='shop',request_id=self.r)['status'],'needs_content')

    def test_unavailable_stays_held(self):
        self.queue.set_hold(tenant_id='shop',request_id=self.r,status='unavailable',now=101)
        self.assertEqual(self.queue.list_for_business(tenant_id='shop',status='unavailable')[0]['request_id'],self.r)

    def test_no_false_incomplete_after_completion(self):
        for item in ['photo','customer_permission']:
            self.queue.provide(tenant_id='shop',request_id=self.r,item=item,
                content_reference='asset:'+item,now=101)
        with self.assertRaises(ValueError):
            self.queue.set_hold(tenant_id='shop',request_id=self.r,status='needs_content',now=102)

    def test_invalid_required_items(self):
        with self.assertRaises(ValueError):
            self.queue.create(tenant_id='shop',channel='facebook',draft_text='Hi',
                suggestion='Photo',required_items=['photo','photo'],now=101)

if __name__=='__main__':unittest.main()
