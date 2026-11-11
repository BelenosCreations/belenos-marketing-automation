"""Owner-confirmed business fact registry for AI draft grounding.

Owner confirmation is provenance, not independent verification of truth.
No automated fact extraction or external source checking is implemented.
"""
import json
from access_policy import Action,Resource,require_permission

class AIBusinessFacts:
    def __init__(self, *, db, policy_store):
        self.db=db
        self.policy=policy_store
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_business_facts(
            tenant_id TEXT PRIMARY KEY, facts_json TEXT NOT NULL,
            revision INTEGER NOT NULL, confirmed_by TEXT NOT NULL,
            confirmed_at INTEGER NOT NULL)""")
        db.commit()

    @staticmethod
    def _validate(facts):
        if type(facts) is not dict or not 1<=len(facts)<=40 or any(
            type(key) is not str or not key.strip() or len(key)>80 or
            type(value) is not str or not value.strip() or len(value)>500
            for key,value in facts.items()):
            raise ValueError('Business facts must be a bounded string dictionary')
        encoded=json.dumps(facts,sort_keys=True,ensure_ascii=False)
        if len(encoded.encode('utf-8'))>16384:
            raise ValueError('Business facts too large')
        return encoded

    def confirm(self, *, token, now, facts, expected_revision=0):
        principal=self.policy._principal(token,now)
        require_permission(principal,Action.MANAGE_TEAM,
                           Resource(principal.tenant_id))
        if type(expected_revision) is not int or expected_revision<0:
            raise ValueError('Valid fact revision required')
        encoded=self._validate(facts)
        with self.db:
            row=self.db.execute("""SELECT revision FROM bam_ai_business_facts
                WHERE tenant_id=?""",(principal.tenant_id,)).fetchone()
            revision=row[0] if row else 0
            if revision!=expected_revision:
                raise ValueError('Facts changed; refresh before confirming')
            self.db.execute("""INSERT INTO bam_ai_business_facts
                (tenant_id,facts_json,revision,confirmed_by,confirmed_at)
                VALUES(?,?,?,?,?) ON CONFLICT(tenant_id) DO UPDATE SET
                facts_json=excluded.facts_json,
                revision=excluded.revision,
                confirmed_by=excluded.confirmed_by,
                confirmed_at=excluded.confirmed_at""",
                (principal.tenant_id,encoded,revision+1,
                 principal.subject_id,now))
        return self.snapshot(token=token,now=now)

    def snapshot(self, *, token, now):
        principal=self.policy._principal(token,now)
        row=self.db.execute("""SELECT facts_json,revision,confirmed_at
            FROM bam_ai_business_facts WHERE tenant_id=?""",
            (principal.tenant_id,)).fetchone()
        if row is None:
            return {'tenant_id':principal.tenant_id,'facts':{},
                    'revision':0,'provenance':'not_configured',
                    'confirmed_at':None,'publishing_enabled':False}
        return {'tenant_id':principal.tenant_id,
                'facts':json.loads(row[0]),'revision':row[1],
                'provenance':'owner_confirmed',
                'confirmed_at':row[2],'publishing_enabled':False}
