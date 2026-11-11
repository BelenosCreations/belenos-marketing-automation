"""Persist verified-pending AI draft components per user and business.

Offline workflow only. Drafts are never scheduled or published. The caller
must have already validated AI output and verified the source facts before
staging; no browser-supplied tenant/subject or approval flags are trusted.
"""
import json
import secrets
from access_policy import Action,Resource,require_permission
from ai_content_plan import AIContentPlan

class AIContentDraftStore:
    def __init__(self, *, db, policy_store):
        self.db=db
        self.policy=policy_store
        db.execute("""CREATE TABLE IF NOT EXISTS bam_ai_draft_components(
            tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
            draft_id TEXT NOT NULL,platform TEXT NOT NULL,
            post_text TEXT NOT NULL,image_prompt TEXT,
            needs_media INTEGER NOT NULL,
            revision INTEGER NOT NULL,
            created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,
            PRIMARY KEY(tenant_id,subject_id,draft_id))""")
        db.commit()

    def _writer(self, token, now):
        principal=self.policy._principal(token,now)
        require_permission(principal,Action.CREATE_DRAFT,Resource(principal.tenant_id))
        return principal

    def stage(self, *, token, now, platform, response,
              include_image_prompt, needs_media=False):
        principal=self._writer(token,now)
        if platform not in ('facebook','instagram','linkedin',
                            'pinterest','tiktok','youtube'):
            raise ValueError('Unsupported platform')
        if type(needs_media) is not bool:
            raise ValueError('Media requirement must be boolean')
        parsed=AIContentPlan.parse_response(
            response,include_image_prompt=include_image_prompt)
        if needs_media and parsed['image_prompt'] is None:
            raise ValueError('Required media needs a prompt or a separate content request')
        draft_id=secrets.token_hex(16)
        with self.db:
            self.db.execute("""INSERT INTO bam_ai_draft_components
                (tenant_id,subject_id,draft_id,platform,post_text,
                 image_prompt,needs_media,revision,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (principal.tenant_id,principal.subject_id,draft_id,
                 platform,parsed['post_text'],parsed['image_prompt'],
                 int(needs_media),1,now,now))
        return self.get(token=token,now=now,draft_id=draft_id)

    def get(self, *, token, now, draft_id):
        principal=self.policy._principal(token,now)
        if type(draft_id) is not str or len(draft_id)!=32 or any(
            c not in '0123456789abcdef' for c in draft_id):
            raise ValueError('Invalid draft ID')
        row=self.db.execute("""SELECT platform,post_text,image_prompt,
            needs_media,revision FROM bam_ai_draft_components
            WHERE tenant_id=? AND subject_id=? AND draft_id=?""",
            (principal.tenant_id,principal.subject_id,draft_id)).fetchone()
        if row is None:
            raise LookupError('Draft not found')
        return {'tenant_id':principal.tenant_id,
                'draft_id':draft_id,'platform':row[0],
                'post_text':row[1],'image_prompt':row[2],
                'needs_media':bool(row[3]),
                'media_attached':False,
                'status':'needs_media' if row[3] else 'draft_pending_verification',
                'revision':row[4],
                'publishing_enabled':False}

    def list_mine(self, *, token, now):
        principal=self.policy._principal(token,now)
        rows=self.db.execute("""SELECT draft_id FROM bam_ai_draft_components
            WHERE tenant_id=? AND subject_id=? ORDER BY updated_at DESC,draft_id""",
            (principal.tenant_id,principal.subject_id)).fetchall()
        return {'tenant_id':principal.tenant_id,
                'drafts':[self.get(token=token,now=now,draft_id=row[0])
                          for row in rows],
                'publishing_enabled':False}

    def revise(self, *, token, now, draft_id, target, revised_text,
               expected_revision):
        principal=self._writer(token,now)
        if type(expected_revision) is not int or expected_revision<1:
            raise ValueError('Valid revision required')
        old=self.get(token=token,now=now,draft_id=draft_id)
        updated=AIContentPlan.apply_revision(old,target=target,
                                             revised_text=revised_text)
        with self.db:
            result=self.db.execute("""UPDATE bam_ai_draft_components
                SET post_text=?,image_prompt=?,revision=revision+1,
                    updated_at=? WHERE tenant_id=? AND subject_id=?
                    AND draft_id=? AND revision=?""",
                (updated['post_text'],updated['image_prompt'],now,
                 principal.tenant_id,principal.subject_id,draft_id,
                 expected_revision))
            if result.rowcount!=1:
                raise ValueError('Draft changed; refresh before revising')
        return self.get(token=token,now=now,draft_id=draft_id)
