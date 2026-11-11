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

    def test_legacy_content_database_migrates_without_losing_requests(self):
        import json
        old_db=sqlite3.connect(':memory:')
        try:
            old_db.execute("""CREATE TABLE content_requests (
                request_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,
                channel TEXT NOT NULL,draft_text TEXT NOT NULL,
                suggestion TEXT NOT NULL,required_items TEXT NOT NULL,
                provided_items TEXT NOT NULL DEFAULT '{}',status TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)""")
            old_db.execute("""INSERT INTO content_requests
                (request_id,tenant_id,channel,draft_text,suggestion,
                 required_items,provided_items,status,priority,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                ('a'*32,'shop','facebook','Legacy draft','Need image',
                 json.dumps(['image']),'{}','needs_content',1,100,100))
            old_db.commit()
            upgraded=ContentRequests(old_db)
            before=upgraded.get(tenant_id='shop',request_id='a'*32)
            self.assertEqual(before['draft_text'],'Legacy draft')
            self.assertEqual(before['revision'],1)
            self.assertEqual(len(before['priority_token']),32)
            self.assertEqual(before['priority'],1)
            after=upgraded.revise(tenant_id='shop',request_id='a'*32,
                target='suggestion',revised_text='Better guidance',
                expected_revision=1,now=101)
            self.assertEqual(after['revision'],2)
            self.assertEqual(after['draft_text'],'Legacy draft')
            self.assertEqual(after['suggestion'],'Better guidance')
            self.assertEqual(len(upgraded.list_for_business(tenant_id='shop')),1)
            # Reinitialization is idempotent; it does not rotate a saved token.
            ContentRequests(old_db)
            self.assertEqual(upgraded.get(tenant_id='shop',
                request_id='a'*32)['priority_token'],before['priority_token'])
        finally:
            old_db.close()

    def test_priority_edit_rotates_version_without_invalidating_copy(self):
        before=self.queue.get(tenant_id='shop',request_id=self.r)
        saved=self.queue.set_priority(
            tenant_id='shop',request_id=self.r,priority=-2,
            expected_priority_token=before['priority_token'],now=102)
        self.assertEqual(saved['priority'],-2)
        self.assertNotEqual(saved['priority_token'],before['priority_token'])
        self.assertEqual(saved['revision'],before['revision'])
        self.assertEqual(saved['draft_text'],before['draft_text'])
        self.assertEqual(saved['provided_items'],before['provided_items'])
        self.assertEqual(saved['status'],before['status'])
        with self.assertRaises(ValueError):
            self.queue.set_priority(
                tenant_id='shop',request_id=self.r,priority=2,
                expected_priority_token=before['priority_token'],now=103)
        with self.assertRaises(KeyError):
            self.queue.set_priority(
                tenant_id='other',request_id=self.r,priority=2,
                expected_priority_token=saved['priority_token'],now=103)
        with self.assertRaises(ValueError):
            self.queue.set_priority(
                tenant_id='shop',request_id=self.r,priority=True,
                expected_priority_token=saved['priority_token'],now=103)
        for invalid in ('wrong',None,True,4):
            with self.assertRaises(ValueError):
                self.queue.set_priority(
                    tenant_id='shop',request_id=self.r,priority=1,
                    expected_priority_token=invalid,now=103)
        self.assertEqual(self.queue.get(tenant_id='shop',
            request_id=self.r)['priority'],-2)

    def test_priority_sort_uses_latest_stored_metadata(self):
        second=self.queue.create(tenant_id='shop',channel='instagram',
            draft_text='Another draft',suggestion='Confirm artwork',
            required_items=['photo'],now=101,priority=0)
        start=self.queue.get(tenant_id='shop',request_id=self.r)
        self.assertEqual(self.queue.list_for_business(
            tenant_id='shop')[0]['request_id'],self.r)
        lowered=self.queue.set_priority(
            tenant_id='shop',request_id=self.r,priority=-4,
            expected_priority_token=start['priority_token'],now=102)
        self.assertEqual(lowered['revision'],1)
        self.assertEqual(self.queue.list_for_business(
            tenant_id='shop')[0]['request_id'],second)

    def test_partial_content_stays_held(self):
        self.assertEqual(self.queue.provide(tenant_id='shop',request_id=self.r,
            item='photo',content_reference='asset:123',now=101),'needs_content')

    def test_concurrent_media_supply_cannot_lose_previous_attachment(self):
        # A writer that loaded an older snapshot may not overwrite a
        # different item's newly supplied content.
        original=self.queue.get(tenant_id='shop',request_id=self.r)
        self.queue.provide(tenant_id='shop',request_id=self.r,
            item='photo',content_reference='asset:first',now=101)
        current=self.queue.get(tenant_id='shop',request_id=self.r)
        class StaleReader(ContentRequests):
            def get(self, *, tenant_id, request_id):
                if tenant_id=='shop' and request_id==self_id:
                    return original
                return super().get(tenant_id=tenant_id,request_id=request_id)
        self_id=self.r
        stale=StaleReader(self.db)
        with self.assertRaisesRegex(ValueError,'Stale draft revision'):
            stale.provide(tenant_id='shop',request_id=self.r,
                item='customer_permission',
                content_reference='asset:other',now=102)
        saved=self.queue.get(tenant_id='shop',request_id=self.r)
        self.assertEqual(saved['provided_items'],current['provided_items'])
        self.assertEqual(saved['revision'],current['revision'])
        self.assertEqual(saved['status'],'needs_content')

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

    def test_hold_revision_conflict_preserves_latest_status(self):
        original=self.queue.get(tenant_id='shop',request_id=self.r)
        self.queue.set_hold(tenant_id='shop',request_id=self.r,
            status='postponed',now=101,
            expected_revision=original['revision'])
        with self.assertRaisesRegex(ValueError,'Stale draft revision'):
            self.queue.set_hold(tenant_id='shop',request_id=self.r,
                status='needs_content',now=102,
                expected_revision=original['revision'])
        item=self.queue.get(tenant_id='shop',request_id=self.r)
        self.assertEqual(item['status'],'postponed')
        self.assertEqual(item['revision'],original['revision']+1)
        with self.assertRaises(ValueError):
            self.queue.set_hold(tenant_id='shop',request_id=self.r,
                status='needs_content',now=True,
                expected_revision=item['revision'])
        with self.assertRaises(ValueError):
            self.queue.set_hold(tenant_id='shop',request_id=self.r,
                status='needs_content',now=104,expected_revision=True)

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
