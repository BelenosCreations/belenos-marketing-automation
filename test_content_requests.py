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
