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

    def __post_init__(self):
        if self.scenario not in ('owner','invited','public'):
            raise ValueError('Unknown scenario')
        if type(self.monthly_requests) is not int or not 0<=self.monthly_requests<=100000:
            raise ValueError('Invalid monthly request allowance')
        if type(self.max_output_tokens) is not int or not 1<=self.max_output_tokens<=16384:
            raise ValueError('Invalid per-request token cap')
        if type(self.active) is not bool:
            raise ValueError('Invalid plan status')

class SponsoredAIQuota:
    """Atomic local SQLite quota reservation, not distributed billing."""
    def __init__(self, *, db, policy_store):
        self.db=db
        self.policy_store=policy_store

    def reserve(self, *, token, now, plan, month):
        if not isinstance(plan,SponsorshipPlan):
            raise ValueError('Trusted server plan required')
        if type(month) is not str or re.fullmatch(
            r'[0-9]{4}-(?:0[1-9]|1[0-2])',month) is None:
            raise ValueError('Valid UTC billing month required')
        principal=self.policy_store._principal(token,now)
        mode=self.policy_store.get_mode(token=token,now=now)['mode']
        if mode!='bam_sponsored':
            raise ValueError('Personal-key requests must not use BAM quota')
        if not plan.active or plan.monthly_requests==0:
            return {'reserved':False,'remaining':0,'reason':'not_entitled',
                    'publishing_enabled':False}
        # This single conditional UPDATE is atomic across SQLite connections
        # sharing a database; INSERT OR IGNORE establishes a missing counter.
        with self.db:
            self.db.execute("""INSERT OR IGNORE INTO bam_ai_usage
                (tenant_id,subject_id,month,accepted) VALUES(?,?,?,0)""",
                (principal.tenant_id,principal.subject_id,month))
            cursor=self.db.execute("""UPDATE bam_ai_usage SET accepted=accepted+1
                WHERE tenant_id=? AND subject_id=? AND month=?
                AND accepted<?""",
                (principal.tenant_id,principal.subject_id,month,
                 plan.monthly_requests))
            if cursor.rowcount!=1:
                return {'reserved':False,'remaining':0,'reason':'limit_reached',
                        'publishing_enabled':False}
            used=self.db.execute("""SELECT accepted FROM bam_ai_usage
                WHERE tenant_id=? AND subject_id=? AND month=?""",
                (principal.tenant_id,principal.subject_id,month)).fetchone()[0]
        return {'reserved':True,'remaining':plan.monthly_requests-used,
                'max_output_tokens':plan.max_output_tokens,
                'publishing_enabled':False}
