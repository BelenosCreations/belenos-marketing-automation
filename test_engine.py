import sqlite3
import unittest
from datetime import datetime, timezone
from engine import initialize, stage, may_publish, classify

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        initialize(self.db)
        self.now=datetime(2026,11,10,12,tzinfo=timezone.utc)
    def test_community_eligible_but_not_published(self):
        key,d=stage(self.db,slot='A',content='Favorite holiday tradition?',category='community',now=self.now)
        self.assertEqual(d.status,'auto_eligible')
        self.assertFalse(may_publish(self.db,key))
    def test_invented_offer_blocked(self):
        _,d=stage(self.db,slot='A',content='50% off',category='invented_offer',now=self.now)
        self.assertEqual(d.status,'blocked')
    def test_new_promotion_needs_approval(self):
        _,d=stage(self.db,slot='A',content='New product',category='promotion',now=self.now)
        self.assertEqual(d.status,'approval_required')
    def test_duplicate(self):
        kwargs=dict(slot='A',content='Hello Marion',category='community',now=self.now)
        stage(self.db,**kwargs)
        _,d=stage(self.db,**kwargs)
        self.assertEqual(d.status,'duplicate')
    def test_authorization_exact_terms_and_expiry(self):
        self.db.execute('INSERT INTO authorizations VALUES (?,?,?,?,?,?)',('x','deadline','December 3 custom-order deadline','2026-11-01T00:00:00+00:00','2026-12-04T00:00:00+00:00',self.now.isoformat()))
        d=classify(self.db,content='Remember the December 3 custom-order deadline',category='promotion',authorization_id='x',now=self.now)
        self.assertEqual(d.status,'auto_eligible')
        d=classify(self.db,content='Deadline extended to December 5',category='promotion',authorization_id='x',now=self.now)
        self.assertEqual(d.status,'approval_required')
    def test_unverified_blocked(self):
        self.assertEqual(classify(self.db,content='Event tonight',category='community',now=self.now,verified=False).status,'blocked')

if __name__=='__main__': unittest.main()
