"""Nonpublishing, session-authenticated PostgreSQL editorial readiness preview.

A media status is a synthetic database snapshot, NOT permission proof from a
production scanner. Even material-complete drafts remain blocked for TruthGuard,
owner approval and social publishing. No HTTP, AI, provider or job execution.
"""
import hashlib
import json
import re

_SESSION=re.compile(r"[A-Za-z0-9_-]{40,256}\Z")
_TENANT=re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_ID=re.compile(r"[a-f0-9]{32}\Z")
_ITEM=re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_CHANNEL=re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_STATUSES=frozenset(("needs_content","ready_for_review","postponed",
                     "unavailable"))

_QUERY="""SELECT c.request_id,c.revision,c.channel,c.status,
                 c.required_items,c.provided_items,
                 COALESCE(
                   (SELECT jsonb_agg(jsonb_build_object(
                            'attachment_id',v.attachment_id,
                            'item',v.item))
                    FROM (SELECT a.attachment_id,a.item
                          FROM content_attachments a
                          WHERE a.tenant_id=c.tenant_id
                            AND a.request_id=c.request_id
                            AND a.status='verified'
                          ORDER BY a.attachment_id LIMIT 101) v),
                   '[]'::jsonb)::text
    FROM content_requests c
    WHERE c.tenant_id=%s AND c.request_id=%s
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
             AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=c.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator',
                         'employee','viewer')
      )"""


def prepare_session_review_readiness(*,raw_session_token,tenant_id,
                                     request_id,server_now):
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(request_id) is not str
            or _ID.fullmatch(request_id) is None
            or type(server_now) is not int
            or not 0<=server_now<2**63):
        raise ValueError("Current business session and draft ID required")
    digest=hashlib.sha256(raw_session_token.encode("ascii")).hexdigest()
    return _QUERY,(tenant_id,request_id,digest,server_now)


def summarize_session_review_readiness(row,*,tenant_id,request_id):
    if (type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(request_id) is not str or _ID.fullmatch(request_id) is None):
        raise ValueError("Trusted tenant and request required")
    if row is None:
        return {"tenant_id":tenant_id,"status":"review_preview_only",
                "held_count":0,"editorial_material_complete_count":0,
                "items":[],"approved_count":0,
                "publishing_enabled":False}
    if (type(row) not in (tuple,list) or len(row)!=7
            or row[0]!=request_id
            or type(row[1]) is not int or row[1]<1
            or type(row[2]) is not str
            or _CHANNEL.fullmatch(row[2]) is None
            or type(row[3]) is not str or row[3] not in _STATUSES
            or any(type(x) is not str for x in row[4:])):
        raise ValueError("Unexpected private review data")
    try:
        required=json.loads(row[4])
        provided=json.loads(row[5])
        verified=json.loads(row[6])
    except (json.JSONDecodeError,TypeError,ValueError) as exc:
        raise ValueError("Invalid private editorial JSON") from exc
    if (type(required) is not list or not 1<=len(required)<=20
            or any(type(item) is not str or
                   _ITEM.fullmatch(item) is None for item in required)
            or len(set(required))!=len(required)
            or type(provided) is not dict
            or len(provided)>20
            or any(type(k) is not str or _ITEM.fullmatch(k) is None
                   or type(ref) is not str or len(ref)>100
                   for k,ref in provided.items())
            or type(verified) is not list or len(verified)>100):
        raise ValueError("Malformed held draft or verified attachment snapshot")
    matched=set()
    for item in verified:
        if (type(item) is not dict
                or set(item)!={"attachment_id","item"}
                or type(item["attachment_id"]) is not str
                or _ID.fullmatch(item["attachment_id"]) is None
                or type(item["item"]) is not str
                or _ITEM.fullmatch(item["item"]) is None):
            raise ValueError("Invalid private media verification metadata")
        key=(item["item"],item["attachment_id"])
        if key in matched:
            raise ValueError("Duplicated verified attachment metadata")
        matched.add(key)
    missing=[item for item in required if item not in provided]
    unverified=[]
    for item in required:
        if item not in provided:
            continue
        ref=provided[item]
        if not ref.startswith("verified-attachment:"):
            unverified.append(item)
            continue
        aid=ref[len("verified-attachment:"):]
        if _ID.fullmatch(aid) is None or (item,aid) not in matched:
            unverified.append(item)
    extra=set(provided)-set(required)
    complete=(row[3]=="ready_for_review" and not missing and
              not unverified and not extra)
    blockers=[]
    if row[3] in ("postponed","unavailable"):
        blockers.append("draft_held")
    if missing:
        blockers.append("missing_required_content")
    if unverified or extra:
        blockers.append("unverified_or_unexpected_content")
    if not complete and not blockers:
        blockers.append("not_ready_for_editorial_review")
    blockers.extend(("truthguard_review_required",
                     "owner_approval_not_implemented",
                     "social_publishing_disabled"))
    summary={"request_id":request_id,"revision":row[1],
             "channel":row[2],"status":row[3],
             "missing_items":missing,"unverified_items":unverified,
             "editorial_material_complete":complete,
             "blockers":blockers,"approved":False,
             "publishing_enabled":False}
    return {"tenant_id":tenant_id,"status":"review_preview_only",
            "held_count":1,
            "editorial_material_complete_count":int(complete),
            "items":[summary],"approved_count":0,
            "publishing_enabled":False}
