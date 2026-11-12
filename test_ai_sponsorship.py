import sqlite3
import unittest
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from ai_account_policy import AIPolicyStore
from ai_sponsorship import SponsorshipPlan,SponsoredAIQuota

class SponsoredAITests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        directory=AccountDirectory(self.db)
        directory.bootstrap_owner('shop','owner')
        self.sessions=SessionStore(self.db)
        self.token=self.sessions.issue(Principal('owner','shop',Role.OWNER),now=100)
        self.policy=AIPolicyStore(db=self.db,sessions=self.sessions,directory=directory)
        self.quota=SponsoredAIQuota(db=self.db,policy_store=self.policy)

    def test_owner_two_daily_posts_can_be_budgeted_without_claiming_unlimited(self):
        plan=SponsorshipPlan('owner',monthly_requests=62,max_output_tokens=600)
        for _ in range(62):
            result=self.quota.reserve(token=self.token,now=101,plan=plan,
                                      month='2026-11')
            self.assertTrue(result['reserved'])
        self.assertEqual(result['remaining'],0)
        self.assertFalse(self.quota.reserve(token=self.token,now=102,
            plan=plan,month='2026-11')['reserved'])
        self.assertFalse(result['publishing_enabled'])

    def test_invited_and_public_policy_are_configurable(self):
        for scenario in ('invited','public'):
            plan=SponsorshipPlan(scenario,monthly_requests=0,max_output_tokens=400)
            self.assertEqual(self.quota.reserve(token=self.token,now=101,
                plan=plan,month='2026-11')['reason'],'not_entitled')
        with self.assertRaises(ValueError):
            SponsorshipPlan('public',monthly_requests=-1,max_output_tokens=100)

    def test_own_key_never_consumes_sponsored_quota(self):
        self.policy.set_mode(token=self.token,now=101,
            mode='own_openai_key',credential_ref='vault:abcdefghijklmnop')
        with self.assertRaises(ValueError):
            self.quota.reserve(token=self.token,now=102,
                plan=SponsorshipPlan('owner',60,400),month='2026-11')
        row=self.db.execute('SELECT COUNT(*) FROM bam_ai_usage').fetchone()[0]
        self.assertEqual(row,0)

    def test_composite_budget_caps_are_atomic_and_business_scoped(self):
        directory=self.policy.directory
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'editor',Role.CONTENT_CREATOR)
        directory.bootstrap_owner('other','other_owner')
        editor=self.sessions.issue(Principal('editor','shop',
            Role.CONTENT_CREATOR),now=100)
        other=self.sessions.issue(Principal('other_owner','other',
            Role.OWNER),now=100)
        plan=SponsorshipPlan('owner',10,400,
            tenant_monthly_requests=2,operator_monthly_requests=3)
        first=self.quota.reserve(token=self.token,now=101,
                                  plan=plan,month='2026-11')
        second=self.quota.reserve(token=editor,now=101,
                                   plan=plan,month='2026-11')
        self.assertEqual(first['remaining'],1)
        self.assertEqual(second['remaining'],0)
        refused=self.quota.reserve(token=self.token,now=101,
                                    plan=plan,month='2026-11')
        self.assertEqual(refused['reason'],'tenant_limit_reached')
        other_accepted=self.quota.reserve(token=other,now=101,
                                           plan=plan,month='2026-11')
        self.assertTrue(other_accepted['reserved'])
        self.assertEqual(other_accepted['remaining'],0)
        other_refused=self.quota.reserve(token=other,now=101,
                                          plan=plan,month='2026-11')
        self.assertEqual(other_refused['reason'],'operator_limit_reached')
        self.assertEqual(self.db.execute("""SELECT accepted FROM
            bam_ai_usage WHERE tenant_id='shop' AND subject_id='owner'
            AND month='2026-11'""").fetchone()[0],1)
        self.assertEqual(self.db.execute("""SELECT accepted FROM
            bam_ai_usage WHERE tenant_id='other' AND month='2026-11'
            """).fetchone()[0],1)
        self.assertEqual(self.db.execute("""SELECT accepted FROM
            bam_ai_tenant_usage WHERE tenant_id='shop'
            AND month='2026-11'""").fetchone()[0],2)
        self.assertEqual(self.db.execute("""SELECT accepted FROM
            bam_ai_operator_usage WHERE month='2026-11'
            """).fetchone()[0],3)
        # A different calendar month has its own request allowance.
        self.assertTrue(self.quota.reserve(token=other,now=102,
            plan=plan,month='2026-12')['reserved'])

    def test_insufficient_budget_rolls_back_all_counters(self):
        plan=SponsorshipPlan('owner',4,100,
            tenant_monthly_requests=2,operator_monthly_requests=1)
        self.assertTrue(self.quota.reserve(token=self.token,now=101,
            plan=plan,month='2026-11')['reserved'])
        self.assertEqual(self.quota.reserve(token=self.token,now=102,
            plan=plan,month='2026-11')['reason'],
            'operator_limit_reached')
        self.assertEqual(self.db.execute("""SELECT accepted FROM
            bam_ai_usage WHERE tenant_id='shop' AND subject_id='owner'
            """).fetchone()[0],1)
        self.assertEqual(self.db.execute("""SELECT accepted FROM
            bam_ai_tenant_usage WHERE tenant_id='shop'
            """).fetchone()[0],1)

    def test_enabling_caps_midmonth_includes_prior_sponsored_requests(self):
        unrestricted=SponsorshipPlan('owner',10,250)
        self.assertTrue(self.quota.reserve(token=self.token,now=101,
            plan=unrestricted,month='2026-11')['reserved'])
        self.assertEqual(self.db.execute("""SELECT accepted FROM
            bam_ai_tenant_usage WHERE tenant_id='shop'
            """).fetchone()[0],1)
        self.assertEqual(self.db.execute("""SELECT accepted FROM
            bam_ai_operator_usage WHERE month='2026-11'
            """).fetchone()[0],1)
        tenant_limited=SponsorshipPlan('owner',10,250,
            tenant_monthly_requests=1,operator_monthly_requests=10)
        self.assertEqual(self.quota.reserve(token=self.token,now=102,
            plan=tenant_limited,month='2026-11')['reason'],
            'tenant_limit_reached')
        operator_limited=SponsorshipPlan('owner',10,250,
            tenant_monthly_requests=10,operator_monthly_requests=1)
        self.assertEqual(self.quota.reserve(token=self.token,now=102,
            plan=operator_limited,month='2026-11')['reason'],
            'operator_limit_reached')
        for table in ('bam_ai_usage','bam_ai_tenant_usage',
                      'bam_ai_operator_usage'):
            self.assertEqual(self.db.execute(
                'SELECT SUM(accepted) FROM '+table).fetchone()[0],1)

    def test_estimated_micro_usd_caps_are_atomic_across_layers(self):
        directory=self.policy.directory
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'editor',Role.CONTENT_CREATOR)
        directory.bootstrap_owner('other','another_owner')
        directory.bootstrap_owner('third','third_owner')
        editor=self.sessions.issue(Principal('editor','shop',
            Role.CONTENT_CREATOR),now=100)
        other=self.sessions.issue(Principal('another_owner','other',
            Role.OWNER),now=100)
        third=self.sessions.issue(Principal('third_owner','third',
            Role.OWNER),now=100)
        plan=SponsorshipPlan('invited',10,400,
            max_request_estimated_micro_usd=1000,
            user_monthly_estimated_micro_usd=2500,
            tenant_monthly_estimated_micro_usd=1800,
            operator_monthly_estimated_micro_usd=2500)
        first=self.quota.reserve(token=self.token,now=101,
            plan=plan,month='2026-11')
        self.assertTrue(first['reserved'])
        self.assertEqual(first['estimated_micro_usd_reserved'],1000)
        self.assertEqual(first['remaining_estimated_micro_usd'],800)
        self.assertFalse(first['actual_billing_verified'])
        refused=self.quota.reserve(token=editor,now=101,
            plan=plan,month='2026-11')
        self.assertEqual(refused['reason'],'tenant_estimated_budget_reached')
        self.assertTrue(self.quota.reserve(token=other,now=101,
            plan=plan,month='2026-11')['reserved'])
        final=self.quota.reserve(token=third,now=101,
            plan=plan,month='2026-11')
        self.assertEqual(final['reason'],'operator_estimated_budget_reached')
        for table,total in [('bam_ai_usage',2),('bam_ai_tenant_usage',2),
                            ('bam_ai_operator_usage',2)]:
            self.assertEqual(self.db.execute(
                'SELECT SUM(accepted) FROM '+table).fetchone()[0],total)
            self.assertEqual(self.db.execute(
                'SELECT SUM(reserved_micro_usd) FROM '+table
                ).fetchone()[0],2000)

    def test_user_estimate_cap_and_zero_estimated_limit(self):
        plan=SponsorshipPlan('owner',20,400,
            max_request_estimated_micro_usd=750,
            user_monthly_estimated_micro_usd=1500)
        self.assertTrue(self.quota.reserve(token=self.token,now=101,
            plan=plan,month='2026-11')['reserved'])
        self.assertTrue(self.quota.reserve(token=self.token,now=101,
            plan=plan,month='2026-11')['reserved'])
        self.assertEqual(self.quota.reserve(token=self.token,now=101,
            plan=plan,month='2026-11')['reason'],
            'user_estimated_budget_reached')
        self.assertEqual(self.db.execute(
            "SELECT accepted FROM bam_ai_usage WHERE tenant_id='shop'"
            ).fetchone()[0],2)
        with self.assertRaises(ValueError):
            SponsorshipPlan('owner',5,100,
                tenant_monthly_estimated_micro_usd=1000)
        with self.assertRaises(ValueError):
            SponsorshipPlan('owner',5,100,
                max_request_estimated_micro_usd=0)

    def test_estimate_caps_reject_unpriced_prior_reservations(self):
        initial=SponsorshipPlan('owner',10,100)
        self.assertTrue(self.quota.reserve(token=self.token,now=101,
            plan=initial,month='2026-11')['reserved'])
        now_capped=SponsorshipPlan('owner',10,100,
            max_request_estimated_micro_usd=10,
            user_monthly_estimated_micro_usd=100,
            tenant_monthly_estimated_micro_usd=100,
            operator_monthly_estimated_micro_usd=100)
        result=self.quota.reserve(token=self.token,now=101,
            plan=now_capped,month='2026-11')
        self.assertEqual(result['reason'],'historical_estimated_cost_unknown')
        for table in ('bam_ai_usage','bam_ai_tenant_usage',
                      'bam_ai_operator_usage'):
            self.assertEqual(self.db.execute(
                'SELECT reserved_micro_usd,unpriced_requests FROM '+table
                ).fetchone(),(0,1))
        self.assertTrue(self.quota.reserve(token=self.token,now=101,
            plan=now_capped,month='2026-12')['reserved'])

    def test_invalid_estimated_budget_config(self):
        for value in (True,-1,10**12+1,1.5,'100'):
            with self.assertRaises(ValueError):
                SponsorshipPlan('owner',10,400,
                    max_request_estimated_micro_usd=value)
            with self.assertRaises(ValueError):
                SponsorshipPlan('owner',10,400,
                    max_request_estimated_micro_usd=100,
                    operator_monthly_estimated_micro_usd=value)

    def test_legacy_migration_marks_all_unpriced_requests_unknown(self):
        old=sqlite3.connect(':memory:')
        try:
            directory=AccountDirectory(old)
            directory.bootstrap_owner('shop','owner')
            sessions=SessionStore(old)
            token=sessions.issue(Principal('owner','shop',Role.OWNER),
                                 now=100)
            policy=AIPolicyStore(db=old,sessions=sessions,directory=directory)
            old.execute("""INSERT INTO bam_ai_usage
                VALUES ('shop','owner','2026-11',3)""")
            old.execute("""CREATE TABLE bam_ai_tenant_usage(
                tenant_id TEXT NOT NULL,month TEXT NOT NULL,
                accepted INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(tenant_id,month))""")
            old.execute("""CREATE TABLE bam_ai_operator_usage(
                month TEXT PRIMARY KEY,
                accepted INTEGER NOT NULL DEFAULT 0)""")
            old.execute("""INSERT INTO bam_ai_tenant_usage
                VALUES('shop','2026-11',3)""")
            old.execute("""INSERT INTO bam_ai_operator_usage
                VALUES('2026-11',3)""")
            old.commit()
            first=SponsoredAIQuota(db=old,policy_store=policy)
            # An independent reinitialization cannot count migration twice.
            SponsoredAIQuota(db=old,policy_store=policy)
            for table in ('bam_ai_usage','bam_ai_tenant_usage',
                          'bam_ai_operator_usage'):
                self.assertEqual(old.execute(
                    'SELECT accepted,reserved_micro_usd,unpriced_requests '
                    'FROM '+table).fetchone(),(3,0,3))
            cap=SponsorshipPlan('owner',10,100,
                max_request_estimated_micro_usd=100,
                operator_monthly_estimated_micro_usd=1000)
            self.assertEqual(first.reserve(token=token,now=101,
                plan=cap,month='2026-11')['reason'],
                'historical_estimated_cost_unknown')
            self.assertEqual(old.execute('SELECT accepted FROM '
                'bam_ai_operator_usage').fetchone()[0],3)
        finally:
            old.close()

    def test_invalid_caps_and_viewer_cannot_reserve(self):
        for cap in (True,-1,10000001,0.5,'10'):
            with self.assertRaises(ValueError):
                SponsorshipPlan('owner',10,200,
                    tenant_monthly_requests=cap)
            with self.assertRaises(ValueError):
                SponsorshipPlan('owner',10,200,
                    operator_monthly_requests=cap)
        directory=self.policy.directory
        directory.set_member(Principal('owner','shop',Role.OWNER),
                             'viewer',Role.VIEWER)
        viewer=self.sessions.issue(Principal('viewer','shop',Role.VIEWER),
                                    now=100)
        with self.assertRaises(PermissionError):
            self.quota.reserve(token=viewer,now=101,
                plan=SponsorshipPlan('owner',10,400),
                month='2026-11')
        self.assertEqual(self.db.execute("""SELECT count(*) FROM
            bam_ai_usage""").fetchone()[0],0)

    def test_months_are_isolated(self):
        plan=SponsorshipPlan('owner',1,400)
        self.assertTrue(self.quota.reserve(token=self.token,now=101,
            plan=plan,month='2026-11')['reserved'])
        self.assertTrue(self.quota.reserve(token=self.token,now=102,
            plan=plan,month='2026-12')['reserved'])
        with self.assertRaises(ValueError):
            self.quota.reserve(token=self.token,now=103,
                plan=plan,month='2026-13')

if __name__=='__main__':
    unittest.main()
