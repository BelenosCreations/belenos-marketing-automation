"""Concurrent SQLite-only sponsorship admission safety, no paid OpenAI calls.

Two separate database connections simulate business users competing for a
configured shared request budget. This is not an API-cost forecast or bill.
"""
import os
import sqlite3
import tempfile
import threading
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_sponsorship import SponsorshipPlan,SponsoredAIQuota


class SponsoredAIConcurrentBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='bam-ai-quota-')
        path=os.path.join(self.tmp.name,'quota.sqlite3')
        self.db1=sqlite3.connect(path,timeout=10,check_same_thread=False)
        self.db2=sqlite3.connect(path,timeout=10,check_same_thread=False)
        directory=AccountDirectory(self.db1)
        directory.bootstrap_owner('shop','owner')
        directory.bootstrap_owner('other','otherowner')
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'writer',Role.CONTENT_CREATOR)
        sessions=SessionStore(self.db1)
        self.shop_owner=sessions.issue(
            Principal('owner','shop',Role.OWNER),now=100)
        self.shop_writer=sessions.issue(
            Principal('writer','shop',Role.CONTENT_CREATOR),now=100)
        self.other=sessions.issue(
            Principal('otherowner','other',Role.OWNER),now=100)
        self.quota1=SponsoredAIQuota(db=self.db1,policy_store=AIPolicyStore(
            db=self.db1,sessions=sessions,directory=directory))
        directory2=AccountDirectory(self.db2)
        sessions2=SessionStore(self.db2)
        self.quota2=SponsoredAIQuota(db=self.db2,policy_store=AIPolicyStore(
            db=self.db2,sessions=sessions2,directory=directory2))

    def tearDown(self):
        self.db2.close()
        self.db1.close()
        self.tmp.cleanup()

    def race(self,ops):
        start=threading.Barrier(len(ops)+1)
        results=[None]*len(ops)
        def worker(i,fn):
            try:
                start.wait(timeout=8)
                results[i]=fn()
            except Exception as exc:
                results[i]=exc
        threads=[threading.Thread(target=worker,
                 args=(i,fn),daemon=True) for i,fn in enumerate(ops)]
        for t in threads:t.start()
        start.wait(timeout=8)
        for t in threads:t.join(timeout=12)
        self.assertFalse(any(t.is_alive() for t in threads),
                         'Budget race test timed out')
        return results

    def reserve(self,quota,token,plan):
        return quota.reserve(token=token,now=101,plan=plan,month='2026-11')

    def test_two_workers_cannot_exceed_one_business_reservation(self):
        plan=SponsorshipPlan('invited',10,300,
            tenant_monthly_requests=1,operator_monthly_requests=5)
        results=self.race([
            lambda:self.reserve(self.quota1,self.shop_owner,plan),
            lambda:self.reserve(self.quota2,self.shop_writer,plan)
        ])
        self.assertTrue(all(isinstance(x,dict) for x in results),results)
        self.assertEqual(sum(x['reserved'] for x in results),1,results)
        self.assertEqual([x['reason'] for x in results if not x['reserved']],
                         ['tenant_limit_reached'])
        self.assertEqual(self.db1.execute("""SELECT SUM(accepted) FROM
            bam_ai_usage WHERE tenant_id='shop'""").fetchone()[0],1)
        self.assertEqual(self.db1.execute("""SELECT accepted FROM
            bam_ai_tenant_usage WHERE tenant_id='shop'""").fetchone()[0],1)
        self.assertEqual(self.db1.execute("""SELECT accepted FROM
            bam_ai_operator_usage""").fetchone()[0],1)

    def test_operator_budget_shared_between_independent_businesses(self):
        plan=SponsorshipPlan('owner',10,300,
            tenant_monthly_requests=10,operator_monthly_requests=1)
        results=self.race([
            lambda:self.reserve(self.quota1,self.shop_owner,plan),
            lambda:self.reserve(self.quota2,self.other,plan)
        ])
        self.assertTrue(all(isinstance(x,dict) for x in results),results)
        self.assertEqual(sum(x['reserved'] for x in results),1,results)
        self.assertEqual([x['reason'] for x in results if not x['reserved']],
                         ['operator_limit_reached'])
        self.assertEqual(self.db1.execute("""SELECT SUM(accepted) FROM
            bam_ai_usage""").fetchone()[0],1)
        self.assertEqual(self.db1.execute("""SELECT SUM(accepted) FROM
            bam_ai_tenant_usage""").fetchone()[0],1)
        self.assertEqual(self.db1.execute("""SELECT accepted FROM
            bam_ai_operator_usage""").fetchone()[0],1)


if __name__=='__main__':
    unittest.main()
