"""Atomic session-bound attachment-to-draft binding on disposable PostgreSQL.

Only a *previously verified* synthetic attachment row may be linked to its
own tenant, request and required item. This does not verify/upload media, give
approval, start scheduling, authorize social providers or execute publishing.
"""
import hashlib
import re

_SESSION=re.compile(r"[A-Za-z0-9_-]{40,256}\Z")
_TENANT=re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_ID=re.compile(r"[a-f0-9]{32}\Z")
_ITEM=re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")

_SQL="""UPDATE content_requests AS c
    SET provided_items=jsonb_set(
            c.provided_items::jsonb,ARRAY[%s],
            to_jsonb(('verified-attachment:' || %s)::text),true)::text,
        status=CASE WHEN NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements_text(c.required_items::jsonb)
                AS needed(value)
            WHERE needed.value<>%s
              AND NOT (c.provided_items::jsonb ? needed.value)
        ) AND NOT EXISTS (
            SELECT 1 FROM jsonb_object_keys(c.provided_items::jsonb)
                AS extra(name)
            WHERE NOT (c.required_items::jsonb ? extra.name)
        ) THEN 'ready_for_review' ELSE 'needs_content' END,
        updated_at=%s,revision=c.revision+1
    WHERE c.tenant_id=%s AND c.request_id=%s
      AND c.revision=%s
      AND c.status IN ('needs_content','ready_for_review')
      AND jsonb_typeof(c.required_items::jsonb)='array'
      AND jsonb_typeof(c.provided_items::jsonb)='object'
      AND c.required_items::jsonb ? %s
      AND EXISTS (
        SELECT 1 FROM content_attachments a
        WHERE a.tenant_id=c.tenant_id AND a.request_id=c.request_id
          AND a.item=%s AND a.attachment_id=%s AND a.status='verified'
      )
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
             AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=c.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator')
      )
    RETURNING c.request_id,c.revision,c.status"""

_HELD=frozenset(("needs_content","ready_for_review"))


def prepare_session_verified_attachment_binding(*,raw_session_token,
                                                tenant_id,request_id,item,
                                                attachment_id,
                                                expected_revision,server_now):
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(request_id) is not str
            or _ID.fullmatch(request_id) is None
            or type(attachment_id) is not str
            or _ID.fullmatch(attachment_id) is None
            or type(item) is not str or _ITEM.fullmatch(item) is None
            or type(expected_revision) is not int
            or not 1<=expected_revision<2**31-1
            or type(server_now) is not int
            or not 0<=server_now<2**63):
        raise ValueError("Current editor, draft revision and attachment required")
    digest=hashlib.sha256(raw_session_token.encode("ascii")).hexdigest()
    return _SQL,(item,attachment_id,item,server_now,tenant_id,request_id,
                 expected_revision,item,item,attachment_id,digest,server_now)


def summarize_session_verified_attachment_binding(row,*,tenant_id,request_id,
                                                   item,attachment_id,
                                                   expected_revision):
    if row is None:
        # No information about which component (scope, permission,
        # verification state or stale revision) denied the operation.
        raise PermissionError("Current verified attachment and editor required")
    if (type(row) not in (tuple,list) or len(row)!=3
            or row[0]!=request_id or type(row[1]) is not int
            or row[1]!=expected_revision+1
            or row[2] not in _HELD):
        raise ValueError("Unexpected held draft attachment response")
    return {"tenant_id":tenant_id,"request_id":request_id,"item":item,
            "attachment_id":attachment_id,
            "revision":row[1],"status":row[2],
            "editorial_review_required":True,
            "approval_granted":False,"publishing_enabled":False,
            "posts_scheduled":0}
