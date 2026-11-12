"""Server-controlled BAM AI sponsorship and per-request cost guardrails.

No plan pricing is assumed. Owner, invited-circle, and public enrollment
are supported as separate policies. Production billing/subscriptions and
actual OpenAI requests are NOT implemented here.
"""
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class SponsorshipPlan:
    scenario: str
    monthly_requests: int
    max_output_tokens: int
    active: bool = True
    tenant_monthly_requests: int | None = None
    operator_monthly_requests: int | None = None
    # All amounts are operator-estimated micro-USD reservation ceilings,
    # NOT measured provider bills. No model call can be authorized by these
    # figures until input bounds, verified pricing, and billing reconciliation
    # are independently implemented and approved.
    max_request_estimated_micro_usd: int | None = None
    user_monthly_estimated_micro_usd: int | None = None
    tenant_monthly_estimated_micro_usd: int | None = None
    operator_monthly_estimated_micro_usd: int | None = None

    def __post_init__(self):
        if self.scenario not in ('owner','invited','public'):
            raise ValueError('Unknown scenario')
        if type(self.monthly_requests) is not int or not 0<=self.monthly_requests<=100000:
            raise ValueError('Invalid monthly request allowance')
        if type(self.max_output_tokens) is not int or not 1<=self.max_output_tokens<=16384:
            raise ValueError('Invalid per-request token cap')
        if type(self.active) is not bool:
            raise ValueError('Invalid plan status')
        for cap in (self.tenant_monthly_requests,self.operator_monthly_requests):
            if cap is not None and (type(cap) is not int or not 0<=cap<=10000000):
                raise ValueError('Trusted business/operator quota required')
        estimated_caps=(self.user_monthly_estimated_micro_usd,
                        self.tenant_monthly_estimated_micro_usd,
                        self.operator_monthly_estimated_micro_usd)
        values=(self.max_request_estimated_micro_usd,*estimated_caps)
        if any(value is not None and
               (type(value) is not int or not 0<=value<=10**12)
               for value in values):
            raise ValueError('Trusted estimated micro-USD ceilings required')
        # Bound the aggregate integer math: at most 10 million operator
        # reservations times 1 billion micro-USD each fits SQLite int64.
        if (self.max_request_estimated_micro_usd is not None and
            self.max_request_estimated_micro_usd>10**9):
            raise ValueError('Per-request estimate exceeds safe maximum')
        if (self.max_request_estimated_micro_usd==0 or
            (any(value is not None for value in estimated_caps) and
             self.max_request_estimated_micro_usd is None)):
            raise ValueError('Nonzero trusted per-request estimate required')

class _QuotaExhausted(Exception):
    """Internal transaction abort: never commit a partially charged counter."""
    def __init__(self,reason):
        self.reason=reason


class SponsoredAIQuota:
    """Atomic local SQLite quota reservation, not distributed billing."""
    def __init__(self, *, db, policy_store):
        self.db=db
        self.policy_store=policy_store
        # These are aggregate request *counts*, not USD spend caps or a
        # prediction of real provider invoices. No API traffic occurs here.
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_tenant_usage(
            tenant_id TEXT NOT NULL,month TEXT NOT NULL,
            accepted INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(tenant_id,month))""")
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_operator_usage(
            month TEXT PRIMARY KEY,
            accepted INTEGER NOT NULL DEFAULT 0)""")
        # Existing databases predate estimated-cost accounting. Never
        # retroactively pretend legacy sponsored requests have known prices.
        # Backfill them as unpriced; adding a USD estimate ceiling mid-month
        # must fail closed until the operator reconciles historic usage.
        for table in ('bam_ai_usage','bam_ai_tenant_usage',
                      'bam_ai_operator_usage'):
            columns={row[1] for row in db.execute(
                'PRAGMA table_info('+table+')')}
            if 'reserved_micro_usd' not in columns:
                db.execute('ALTER TABLE '+table+
                           ' ADD COLUMN reserved_micro_usd INTEGER NOT NULL DEFAULT 0')
            if 'unpriced_requests' not in columns:
                db.execute('ALTER TABLE '+table+
                           ' ADD COLUMN unpriced_requests INTEGER NOT NULL DEFAULT 0')
                db.execute('UPDATE '+table+' SET unpriced_requests=accepted')
        db.commit()

    @staticmethod
    def _check_estimate(*,row,delta,cap,reason):
        if cap is None:
            return None
        if row[2]!=0:
            raise _QuotaExhausted('historical_estimated_cost_unknown')
        if row[1]+delta>cap:
            raise _QuotaExhausted(reason)
        return cap-(row[1]+delta)

    def reserve(self, *, token, now, plan, month):
        if not isinstance(plan,SponsorshipPlan):
            raise ValueError('Trusted server plan required')
        if type(month) is not str or re.fullmatch(
            r'[0-9]{4}-(?:0[1-9]|1[0-2])',month) is None:
            raise ValueError('Valid UTC billing month required')
        principal=self.policy_store._editor(token,now)
        mode=self.policy_store.get_mode(token=token,now=now)['mode']
        if mode!='bam_sponsored':
            raise ValueError('Personal-key requests must not use BAM quota')
        if not plan.active or plan.monthly_requests==0:
            return {'reserved':False,'remaining':0,'reason':'not_entitled',
                    'publishing_enabled':False}
        micro=plan.max_request_estimated_micro_usd or 0
        unpriced=int(plan.max_request_estimated_micro_usd is None)
        remaining_micro=[]
        # Revalidate role and funding mode under SQLite's write lock. A
        # demoted writer or a user who switched to a personal key between
        # the initial check and lock acquisition cannot spend BAM quota.
        # Every count/cost tier succeeds or rolls back as one transaction.
        try:
            with self.db:
                self.db.execute('BEGIN IMMEDIATE')
                current=self.policy_store._editor(token,now)
                if current!=principal:
                    raise PermissionError('Current business role changed')
                if self.policy_store.get_mode(token=token,now=now)[
                        'mode']!='bam_sponsored':
                    raise PermissionError('Sponsored mode changed')
                self.db.execute("""INSERT OR IGNORE INTO bam_ai_usage
                    (tenant_id,subject_id,month,accepted)
                    VALUES(?,?,?,0)""",
                    (principal.tenant_id,principal.subject_id,month))
                user=self.db.execute("""SELECT accepted,reserved_micro_usd,
                    unpriced_requests FROM bam_ai_usage WHERE
                    tenant_id=? AND subject_id=? AND month=?""",
                    (principal.tenant_id,principal.subject_id,month)).fetchone()
                if user[0]>=plan.monthly_requests:
                    raise _QuotaExhausted('limit_reached')
                left=self._check_estimate(row=user,delta=micro,
                    cap=plan.user_monthly_estimated_micro_usd,
                    reason='user_estimated_budget_reached')
                if left is not None:remaining_micro.append(left)
                self.db.execute("""UPDATE bam_ai_usage SET accepted=accepted+1,
                    reserved_micro_usd=reserved_micro_usd+?,
                    unpriced_requests=unpriced_requests+?
                    WHERE tenant_id=? AND subject_id=? AND month=?""",
                    (micro,unpriced,principal.tenant_id,principal.subject_id,month))
                remaining=[plan.monthly_requests-user[0]-1]

                self.db.execute("""INSERT OR IGNORE INTO bam_ai_tenant_usage
                    (tenant_id,month,accepted) VALUES(?,?,0)""",
                    (principal.tenant_id,month))
                tenant=self.db.execute("""SELECT accepted,reserved_micro_usd,
                    unpriced_requests FROM bam_ai_tenant_usage
                    WHERE tenant_id=? AND month=?""",
                    (principal.tenant_id,month)).fetchone()
                if (plan.tenant_monthly_requests is not None and
                    tenant[0]>=plan.tenant_monthly_requests):
                    raise _QuotaExhausted('tenant_limit_reached')
                left=self._check_estimate(row=tenant,delta=micro,
                    cap=plan.tenant_monthly_estimated_micro_usd,
                    reason='tenant_estimated_budget_reached')
                if left is not None:remaining_micro.append(left)
                self.db.execute("""UPDATE bam_ai_tenant_usage SET
                    accepted=accepted+1,
                    reserved_micro_usd=reserved_micro_usd+?,
                    unpriced_requests=unpriced_requests+?
                    WHERE tenant_id=? AND month=?""",
                    (micro,unpriced,principal.tenant_id,month))
                if plan.tenant_monthly_requests is not None:
                    remaining.append(plan.tenant_monthly_requests-tenant[0]-1)

                self.db.execute("""INSERT OR IGNORE INTO bam_ai_operator_usage
                    (month,accepted) VALUES(?,0)""",(month,))
                operator=self.db.execute("""SELECT accepted,reserved_micro_usd,
                    unpriced_requests FROM bam_ai_operator_usage
                    WHERE month=?""",(month,)).fetchone()
                if (plan.operator_monthly_requests is not None and
                    operator[0]>=plan.operator_monthly_requests):
                    raise _QuotaExhausted('operator_limit_reached')
                left=self._check_estimate(row=operator,delta=micro,
                    cap=plan.operator_monthly_estimated_micro_usd,
                    reason='operator_estimated_budget_reached')
                if left is not None:remaining_micro.append(left)
                self.db.execute("""UPDATE bam_ai_operator_usage SET
                    accepted=accepted+1,
                    reserved_micro_usd=reserved_micro_usd+?,
                    unpriced_requests=unpriced_requests+?
                    WHERE month=?""",(micro,unpriced,month))
                if plan.operator_monthly_requests is not None:
                    remaining.append(plan.operator_monthly_requests-operator[0]-1)
        except _QuotaExhausted as exc:
            return {'reserved':False,'remaining':0,'reason':exc.reason,
                    'publishing_enabled':False}
        return {'reserved':True,'remaining':min(remaining),
                'max_output_tokens':plan.max_output_tokens,
                'estimated_micro_usd_reserved':(
                    plan.max_request_estimated_micro_usd),
                'remaining_estimated_micro_usd':(
                    min(remaining_micro) if remaining_micro else None),
                'actual_billing_verified':False,
                'publishing_enabled':False}
