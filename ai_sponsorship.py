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
        db.commit()

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
        # Every reservation counter is saved within one SQLite writer
        # transaction. A denied tenant/operator cap rolls back the successful
        # per-user increment. Separate connections cannot over-reserve.
        try:
            with self.db:
                self.db.execute("""INSERT OR IGNORE INTO bam_ai_usage
                    (tenant_id,subject_id,month,accepted) VALUES(?,?,?,0)""",
                    (principal.tenant_id,principal.subject_id,month))
                cursor=self.db.execute("""UPDATE bam_ai_usage
                    SET accepted=accepted+1 WHERE tenant_id=?
                    AND subject_id=? AND month=? AND accepted<?""",
                    (principal.tenant_id,principal.subject_id,month,
                     plan.monthly_requests))
                if cursor.rowcount!=1:
                    raise _QuotaExhausted('limit_reached')
                used=self.db.execute("""SELECT accepted FROM bam_ai_usage
                    WHERE tenant_id=? AND subject_id=? AND month=?""",
                    (principal.tenant_id,principal.subject_id,month)
                    ).fetchone()[0]
                remaining=[plan.monthly_requests-used]
                # Always meter aggregate attempts that were admitted, even
                # when these optional caps are not active. Enabling a trusted
                # cap mid-month must not forget earlier sponsored requests.
                self.db.execute("""INSERT OR IGNORE INTO
                    bam_ai_tenant_usage (tenant_id,month,accepted)
                    VALUES(?,?,0)""",(principal.tenant_id,month))
                cursor=self.db.execute("""UPDATE bam_ai_tenant_usage
                    SET accepted=accepted+1 WHERE tenant_id=? AND month=?
                    AND (? IS NULL OR accepted<?)""",
                    (principal.tenant_id,month,
                     plan.tenant_monthly_requests,
                     plan.tenant_monthly_requests))
                if cursor.rowcount!=1:
                    raise _QuotaExhausted('tenant_limit_reached')
                tenant_used=self.db.execute("""SELECT accepted FROM
                    bam_ai_tenant_usage WHERE tenant_id=? AND month=?""",
                    (principal.tenant_id,month)).fetchone()[0]
                if plan.tenant_monthly_requests is not None:
                    remaining.append(plan.tenant_monthly_requests-tenant_used)
                self.db.execute("""INSERT OR IGNORE INTO
                    bam_ai_operator_usage (month,accepted)
                    VALUES(?,0)""",(month,))
                cursor=self.db.execute("""UPDATE bam_ai_operator_usage
                    SET accepted=accepted+1 WHERE month=?
                    AND (? IS NULL OR accepted<?)""",
                    (month,plan.operator_monthly_requests,
                     plan.operator_monthly_requests))
                if cursor.rowcount!=1:
                    raise _QuotaExhausted('operator_limit_reached')
                operator_used=self.db.execute("""SELECT accepted FROM
                    bam_ai_operator_usage WHERE month=?""",
                    (month,)).fetchone()[0]
                if plan.operator_monthly_requests is not None:
                    remaining.append(plan.operator_monthly_requests-operator_used)
        except _QuotaExhausted as exc:
            return {'reserved':False,'remaining':0,'reason':exc.reason,
                    'publishing_enabled':False}
        return {'reserved':True,'remaining':min(remaining),
                'max_output_tokens':plan.max_output_tokens,
                'publishing_enabled':False}
