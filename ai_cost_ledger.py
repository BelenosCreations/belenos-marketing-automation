"""Trusted server-side AI token and estimated-cost audit.

Pricing is configuration supplied by the operator, never invented here.
Provider usage is accepted only through a trusted server-side caller. Estimates
are not invoices, real OpenAI bills or proof of payment.
"""
import sqlite3
import hashlib
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal,ROUND_HALF_UP,ROUND_CEILING

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

def conservative_request_cost_micro_usd(*,pricing,
                                        max_input_tokens,max_output_tokens):
    """Operator-provided pricing and assumed token ceilings only.

    The caller must independently enforce both token ceilings and verify
    actual current provider pricing before using this for real paid calls.
    Ceil, rather than round down, each whole-request micro-USD projection.
    No API access, invoice, usage measurement or approval occurs here.
    """
    if type(pricing) is not AITokenPricing:
        raise ValueError('Explicit operator pricing required')
    if (type(max_input_tokens) is not int or
        not 1<=max_input_tokens<=1000000 or
        type(max_output_tokens) is not int or
        not 1<=max_output_tokens<=16384):
        raise ValueError('Bounded assumed input/output token ceilings required')
    projected=(Decimal(max_input_tokens)*pricing.input_per_million_usd+
               Decimal(max_output_tokens)*pricing.output_per_million_usd)
    return int(projected.quantize(Decimal('1'),rounding=ROUND_CEILING))


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
        # Migration: original ledger rows have no trusted usage reference.
        # Never infer historical provider request IDs or backfill invented
        # deduplication claims.
        columns={row[1] for row in
                 db.execute('PRAGMA table_info(bam_ai_cost_events)')}
        if 'trusted_usage_hash' not in columns:
            db.execute("""ALTER TABLE bam_ai_cost_events
                ADD COLUMN trusted_usage_hash TEXT""")
        db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS
            bam_ai_cost_trusted_ref
            ON bam_ai_cost_events(tenant_id,subject_id,trusted_usage_hash)
            WHERE trusted_usage_hash IS NOT NULL""")
        db.commit()

    def record_trusted(self, *, tenant_id,subject_id,model,
                       input_tokens,output_tokens,pricing,now,
                       usage_ref=None):
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
        if (usage_ref is not None and (
                type(usage_ref) is not str or
                re.fullmatch(r'[0-9a-f]{32}',usage_ref) is None)):
            raise ValueError('Trusted server-owned usage reference required')
        usage_hash=(hashlib.sha256(usage_ref.encode('ascii')).hexdigest()
                    if usage_ref is not None else None)
        # micro-USD = tokens * dollars-per-million (rounded to integer).
        micro=(Decimal(input_tokens)*pricing.input_per_million_usd+
               Decimal(output_tokens)*pricing.output_per_million_usd)
        micro=int(micro.quantize(Decimal('1'),rounding=ROUND_HALF_UP))
        event_id=uuid.uuid4().hex
        with self.db:
            fields=(event_id,tenant_id,subject_id,'openai',model,
                    input_tokens,output_tokens,micro,now,usage_hash)
            if usage_hash is None:
                # Legacy callers are supported, but have no deduplication
                # guarantee until they provide a stable trusted reference.
                self.db.execute("""INSERT INTO bam_ai_cost_events
                    (event_id,tenant_id,subject_id,provider,model,
                     input_tokens,output_tokens,estimated_micro_usd,
                     occurred_at,trusted_usage_hash)
                     VALUES(?,?,?,?,?,?,?,?,?,?)""",fields)
                replayed=False
            else:
                inserted=self.db.execute("""INSERT OR IGNORE INTO
                    bam_ai_cost_events
                    (event_id,tenant_id,subject_id,provider,model,
                     input_tokens,output_tokens,estimated_micro_usd,
                     occurred_at,trusted_usage_hash)
                     VALUES(?,?,?,?,?,?,?,?,?,?)""",fields)
                replayed=inserted.rowcount==0
                if replayed:
                    existing=self.db.execute("""SELECT event_id,model,
                        input_tokens,output_tokens,estimated_micro_usd
                        FROM bam_ai_cost_events
                        WHERE tenant_id=? AND subject_id=?
                        AND trusted_usage_hash=?""",
                        (tenant_id,subject_id,usage_hash)).fetchone()
                    if existing is None or existing[1:]!=(
                            model,input_tokens,output_tokens,micro):
                        raise ValueError(
                            'Trusted usage reference reused with different data')
                    event_id=existing[0]
        return {'event_id':event_id,'estimated_micro_usd':micro,
                'replayed':replayed,
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
