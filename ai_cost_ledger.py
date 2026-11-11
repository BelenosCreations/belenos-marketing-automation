"""Trusted server-side AI token and estimated-cost audit.

Pricing is configuration supplied by the operator, never invented here.
Provider usage is accepted only through a trusted server-side caller. Estimates
are not invoices, real OpenAI bills or proof of payment.
"""
import sqlite3
import uuid
from dataclasses import dataclass
from decimal import Decimal,ROUND_HALF_UP

@dataclass(frozen=True)
class AITokenPricing:
    input_per_million_usd: Decimal
    output_per_million_usd: Decimal

    def __post_init__(self):
        for price in (self.input_per_million_usd,
                      self.output_per_million_usd):
            if type(price) is not Decimal or not price.is_finite() or (
                price<0 or price>Decimal('10000')):
                raise ValueError('Operator-configured token prices required')

class AICostLedger:
    def __init__(self, db:sqlite3.Connection):
        self.db=db
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_cost_events(
            event_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
            provider TEXT NOT NULL,model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,output_tokens INTEGER NOT NULL,
            estimated_micro_usd INTEGER NOT NULL,
            occurred_at INTEGER NOT NULL)""")
        db.execute("""CREATE INDEX IF NOT EXISTS bam_ai_cost_scope
            ON bam_ai_cost_events(tenant_id,subject_id,occurred_at)""")
        db.commit()

    def record_trusted(self, *, tenant_id,subject_id,model,
                       input_tokens,output_tokens,pricing,now):
        if not all(type(x) is str and x.strip() and len(x)<=128
                   for x in (tenant_id,subject_id,model)):
            raise ValueError('Valid trusted scope and model required')
        if type(pricing) is not AITokenPricing:
            raise ValueError('Explicit operator pricing required')
        if any(type(n) is not int or not 0<=n<=100000000
               for n in (input_tokens,output_tokens)):
            raise ValueError('Invalid provider token counts')
        if type(now) is not int or now<0:
            raise ValueError('Server timestamp required')
        # micro-USD = tokens * dollars-per-million (rounded to integer).
        micro=(Decimal(input_tokens)*pricing.input_per_million_usd+
               Decimal(output_tokens)*pricing.output_per_million_usd)
        micro=int(micro.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        event_id=uuid.uuid4().hex
        with self.db:
            self.db.execute("""INSERT INTO bam_ai_cost_events
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (event_id,tenant_id,subject_id,'openai',model,
                 input_tokens,output_tokens,micro,now))
        return {'event_id':event_id,'estimated_micro_usd':micro,
                'pricing_basis':'operator_configured',
                'actual_billing_verified':False}

    def summary_trusted(self, *, tenant_id,subject_id):
        if any(type(x) is not str or not x.strip() for x in
               (tenant_id,subject_id)):
            raise ValueError('Scope required')
        row=self.db.execute("""SELECT COUNT(*),COALESCE(SUM(input_tokens),0),
            COALESCE(SUM(output_tokens),0),
            COALESCE(SUM(estimated_micro_usd),0)
            FROM bam_ai_cost_events WHERE tenant_id=? AND subject_id=?""",
            (tenant_id,subject_id)).fetchone()
        return {'events':row[0],'input_tokens':row[1],
                'output_tokens':row[2],
                'estimated_micro_usd':row[3],
                'pricing_basis':'operator_configured',
                'actual_billing_verified':False}
