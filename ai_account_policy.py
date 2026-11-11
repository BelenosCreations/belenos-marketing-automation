"""BAM AI policy, independent user memories, and cost-safe request admission.

OpenAI-only provider. This offline module never calls OpenAI, stores raw API
keys, charges customers, generates content, or publishes. Production must use
an encrypted server-side vault and an atomic quota ledger across workers.
"""
import json
import re
from access_policy import Action, Resource, require_permission

AI_MODES = ('bam_sponsored', 'own_openai_key')
SCENARIOS = ('owner', 'invited', 'public')
MEMORY_MAX_BYTES = 16384

class AIPolicyStore:
    def __init__(self, *, db, sessions, directory):
        self.db, self.sessions, self.directory = db, sessions, directory
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_preferences (
            tenant_id TEXT NOT NULL, subject_id TEXT NOT NULL,
            ai_mode TEXT NOT NULL CHECK(ai_mode IN ('bam_sponsored','own_openai_key')),
            credential_ref TEXT, updated_at INTEGER NOT NULL,
            PRIMARY KEY(tenant_id,subject_id))""")
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_memories (
            tenant_id TEXT NOT NULL, subject_id TEXT NOT NULL,
            memory_json TEXT NOT NULL, updated_at INTEGER NOT NULL,
            PRIMARY KEY(tenant_id,subject_id))""")
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_usage (
            tenant_id TEXT NOT NULL, subject_id TEXT NOT NULL,
            month TEXT NOT NULL, accepted INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(tenant_id,subject_id,month))""")
        db.commit()

    def _principal(self, token, now):
        if type(now) is not int or now < 0:
            raise ValueError('Server time required')
        session=self.sessions.resolve_current(token,directory=self.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        require_permission(session.principal,Action.READ_DRAFTS,
                           Resource(session.principal.tenant_id))
        return session.principal

    def get_mode(self, *, token, now):
        principal=self._principal(token,now)
        row=self.db.execute("""SELECT ai_mode,credential_ref
            FROM bam_ai_preferences WHERE tenant_id=? AND subject_id=?""",
            (principal.tenant_id,principal.subject_id)).fetchone()
        mode=row[0] if row else 'bam_sponsored'
        return {'tenant_id':principal.tenant_id,'subject_id':principal.subject_id,
                'provider':'openai','mode':mode,
                'own_key_configured':bool(row and row[1]),
                'key_exposed':False,'publishing_enabled':False}

    def set_mode(self, *, token, now, mode, credential_ref=None):
        principal=self._principal(token,now)
        if type(mode) is not str or mode not in AI_MODES:
            raise ValueError('Unsupported AI mode')
        current=self.db.execute('''SELECT credential_ref FROM bam_ai_preferences
            WHERE tenant_id=? AND subject_id=?''',
            (principal.tenant_id,principal.subject_id)).fetchone()
        existing_ref=current[0] if current else None
        if mode=='own_openai_key':
            # A previously vault-registered key can be reselected without
            # requiring another signup or exposing its raw secret.
            if credential_ref is None:
                credential_ref=existing_ref
            if (type(credential_ref) is not str or
                re.fullmatch(r'vault:[A-Za-z0-9_-]{16,128}',credential_ref) is None):
                raise ValueError('Trusted server-side vault reference required')
        elif credential_ref is not None:
            raise ValueError('Sponsored mode cannot carry a personal credential')
        else:
            # Preserve encrypted-vault reference for effortless mode switching;
            # explicit key revocation must be a separate trusted operation.
            credential_ref=existing_ref
        with self.db:
            self.db.execute("""INSERT INTO bam_ai_preferences
                (tenant_id,subject_id,ai_mode,credential_ref,updated_at)
                VALUES(?,?,?,?,?) ON CONFLICT(tenant_id,subject_id)
                DO UPDATE SET ai_mode=excluded.ai_mode,
                    credential_ref=excluded.credential_ref,
                    updated_at=excluded.updated_at""",
                (principal.tenant_id,principal.subject_id,mode,credential_ref,now))
        return self.get_mode(token=token,now=now)

    def forget_personal_key_reference(self, *, token, now):
        """Remove the account's reference; vault secret deletion is separate.

        A trusted vault service must revoke/delete the underlying secret.
        This method never returns the reference or raw API key.
        """
        principal=self._principal(token,now)
        with self.db:
            self.db.execute("""UPDATE bam_ai_preferences
                SET ai_mode='bam_sponsored',credential_ref=NULL,updated_at=?
                WHERE tenant_id=? AND subject_id=?""",
                (now,principal.tenant_id,principal.subject_id))
        return self.get_mode(token=token,now=now)

    def get_memory(self, *, token, now):
        principal=self._principal(token,now)
        row=self.db.execute("""SELECT memory_json FROM bam_ai_memories
            WHERE tenant_id=? AND subject_id=?""",
            (principal.tenant_id,principal.subject_id)).fetchone()
        return {'tenant_id':principal.tenant_id,'subject_id':principal.subject_id,
                'memory':json.loads(row[0]) if row else {},
                'publishing_enabled':False}

    def replace_memory(self, *, token, now, memory):
        principal=self._principal(token,now)
        if type(memory) is not dict or not all(
            type(k) is str and len(k)<=80 and type(v) is str and len(v)<=2000
            for k,v in memory.items()):
            raise ValueError('Memory must be a small string dictionary')
        encoded=json.dumps(memory,ensure_ascii=False,sort_keys=True)
        if len(encoded.encode('utf-8'))>MEMORY_MAX_BYTES:
            raise ValueError('Memory exceeds size limit')
        with self.db:
            self.db.execute("""INSERT INTO bam_ai_memories
                (tenant_id,subject_id,memory_json,updated_at)
                VALUES(?,?,?,?) ON CONFLICT(tenant_id,subject_id)
                DO UPDATE SET memory_json=excluded.memory_json,
                    updated_at=excluded.updated_at""",
                (principal.tenant_id,principal.subject_id,encoded,now))
        return self.get_memory(token=token,now=now)

    def check_admission(self, *, token, now, scenario, monthly_limit, month):
        """Read-only preflight. Not a reservation or atomic billing authorization."""
        principal=self._principal(token,now)
        if scenario not in SCENARIOS:
            raise ValueError('Unknown enrollment scenario')
        if type(monthly_limit) is not int or monthly_limit<0:
            raise ValueError('Server-configured monthly allowance required')
        if type(month) is not str or re.fullmatch(r'[0-9]{4}-(?:0[1-9]|1[0-2])',month) is None:
            raise ValueError('Valid UTC billing month required')
        mode=self.get_mode(token=token,now=now)['mode']
        if mode=='own_openai_key':
            return {'mode':mode,'eligible':True,'bam_allowance_applies':False,
                    'remaining':None,'billing_configured':True}
        used=self.db.execute("""SELECT accepted FROM bam_ai_usage
            WHERE tenant_id=? AND subject_id=? AND month=?""",
            (principal.tenant_id,principal.subject_id,month)).fetchone()
        used=used[0] if used else 0
        return {'mode':mode,'eligible':used<monthly_limit,
                'bam_allowance_applies':True,'remaining':max(0,monthly_limit-used),
                'billing_configured':True}
