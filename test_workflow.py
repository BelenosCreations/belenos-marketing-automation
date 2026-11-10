import sqlite3
import unittest
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from engine import initialize,stage
from workflow import setup,record_approval,upsert_discovery,decide_event,next_slots,prepare_dry_run,set_pause

UTC=timezone.utc
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');initialize(self.db);setup(self.db)
        self.now=datetime(2026,11,10,12,tzinfo=UTC)
    def post(self,category='promotion',auth=None):
        return stage(self.db,slot='2026-11-11T10:00:00-05:00',content='Example product',category=category,now=self.now,authorization_id=auth)[0]
    def test_approval_needed_before_preview(self):
        p=self.post()
        with self.assertRaises(PermissionError):prepare_dry_run(self.db,post_id=p,slot=datetime(2026,11,11,15,tzinfo=UTC),at=self.now)
        record_approval(self.db,post_id=p,decision='approved',actor='owner',at=self.now)
        self.assertEqual(prepare_dry_run(self.db,post_id=p,slot=datetime(2026,11,11,15,tzinfo=UTC),at=self.now)['mode'],'DRY_RUN_ONLY')
    def test_revocation_overrides_approval(self):
        p=self.post();record_approval(self.db,post_id=p,decision='approved',actor='owner',at=self.now)
        record_approval(self.db,post_id=p,decision='revoked',actor='owner',at=self.now)
        with self.assertRaises(PermissionError):prepare_dry_run(self.db,post_id=p,slot=datetime(2026,11,11,15,tzinfo=UTC),at=self.now)
    def test_duplicate_slot_refused(self):
        a=self.post('community');b=stage(self.db,slot='other',content='Different',category='community',now=self.now)[0]
        t=datetime(2026,11,11,15,tzinfo=UTC)
        prepare_dry_run(self.db,post_id=a,slot=t,at=self.now)
        with self.assertRaises(sqlite3.IntegrityError):prepare_dry_run(self.db,post_id=b,slot=t,at=self.now)
    def test_event_requires_confirmation(self):
        e=upsert_discovery(self.db,title='Market',event_start=datetime(2026,11,20,12,tzinfo=UTC),source_url='https://example.org/event',participation='unknown',at=self.now)
        self.assertEqual(self.db.execute('SELECT state FROM discovered_events WHERE id=?',(e,)).fetchone()[0],'unconfirmed')
        decide_event(self.db,event_id=e,confirmed=True,actor='owner',at=self.now)
        self.assertEqual(self.db.execute('SELECT state FROM discovered_events WHERE id=?',(e,)).fetchone()[0],'confirmed')
    def test_dst_offsets(self):
        slots=list(next_slots(datetime(2027,3,12,12,tzinfo=UTC),days=4))
        mornings=[t for kind,t in slots if kind=='morning']
        self.assertIn(-4*3600,[int(x.utcoffset().total_seconds()) for x in mornings])
        self.assertIn(-5*3600,[int(x.utcoffset().total_seconds()) for x in mornings])
    def test_pause_cannot_be_disabled(self):
        with self.assertRaises(PermissionError):set_pause(self.db,paused=False,actor='system',at=self.now)
    def test_blocked_post_cannot_approve(self):
        p=self.post('invented_offer')
        with self.assertRaises(ValueError):record_approval(self.db,post_id=p,decision='approved',actor='owner',at=self.now)
    def test_preview_future_only(self):
        p=self.post('community')
        with self.assertRaises(ValueError):prepare_dry_run(self.db,post_id=p,slot=self.now,at=self.now)
    def test_audit_records(self):
        p=self.post();record_approval(self.db,post_id=p,decision='approved',actor='owner',at=self.now)
        self.assertEqual(self.db.execute('SELECT count(*) FROM audit').fetchone()[0],1)
if __name__=='__main__':unittest.main()
