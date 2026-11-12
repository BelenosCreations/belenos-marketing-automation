"""Session-checked draft review feedback SQL for disposable PostgreSQL only.

Private notes are *never* approval, review completion, scheduled jobs or
publishing permission. The CI adapter must execute save + audit in a single
database transaction; this module never opens a connection or HTTP listener.
"""
import hashlib
import re
import uuid

_SESSION=re.compile(r"[A-Za-z0-9_-]{40,256}\Z")
_TENANT=re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_ID=re.compile(r"[a-f0-9]{32}\Z")
_ACTIONS=frozenset(("created","updated"))

_AUTH="""s.revoked_at IS NULL AND s.expires_at>%s
      AND m.active=1 AND m.role=s.role
      AND i.active=1 AND i.email_verified=1"""
_EDITOR="""m.role IN ('owner','marketing_manager')"""

_LIST="""SELECT f.request_id,f.draft_revision,c.revision,f.note,
           f.feedback_token,f.updated_at
    FROM bam_review_feedback f
    JOIN content_requests c ON c.tenant_id=f.tenant_id
         AND c.request_id=f.request_id
    WHERE f.tenant_id=%s
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
             AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=f.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator',
                         'employee','viewer')
      )
    ORDER BY f.updated_at DESC,f.request_id LIMIT 201"""

_INSERT="""INSERT INTO bam_review_feedback
    (tenant_id,request_id,draft_revision,note,feedback_token,
     updated_at,updated_by)
    SELECT c.tenant_id,c.request_id,c.revision,%s,%s,%s,s.subject_id
    FROM content_requests c
    JOIN sessions s ON s.tenant_id=c.tenant_id
    JOIN members m ON m.tenant_id=s.tenant_id
         AND m.subject_id=s.subject_id
    JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE c.tenant_id=%s AND c.request_id=%s AND c.revision=%s
      AND s.token_hash=%s AND s.revoked_at IS NULL
      AND s.expires_at>%s AND m.active=1 AND m.role=s.role
      AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager')
    RETURNING tenant_id,request_id,draft_revision,feedback_token,updated_by"""

_REPLACE="""UPDATE bam_review_feedback
    SET draft_revision=%s,note=%s,feedback_token=%s,updated_at=%s,
        updated_by=(SELECT s.subject_id FROM sessions s
                    WHERE s.token_hash=%s)
    WHERE tenant_id=%s AND request_id=%s AND feedback_token=%s
      AND EXISTS (
        SELECT 1 FROM content_requests c
        JOIN sessions s ON s.tenant_id=c.tenant_id
        JOIN members m ON m.tenant_id=s.tenant_id
             AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE c.tenant_id=bam_review_feedback.tenant_id
          AND c.request_id=bam_review_feedback.request_id
          AND c.revision=%s AND s.token_hash=%s
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager')
      )
    RETURNING tenant_id,request_id,draft_revision,feedback_token,updated_by"""

_EVENT="""INSERT INTO bam_review_feedback_events
    (event_id,tenant_id,request_id,action,draft_revision,occurred_at,actor_id)
    SELECT %s,f.tenant_id,f.request_id,%s,f.draft_revision,%s,s.subject_id
    FROM bam_review_feedback f
    JOIN sessions s ON s.tenant_id=f.tenant_id
    JOIN members m ON m.tenant_id=s.tenant_id
         AND m.subject_id=s.subject_id
    JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE f.tenant_id=%s AND f.request_id=%s AND f.feedback_token=%s
      AND s.token_hash=%s AND s.revoked_at IS NULL AND s.expires_at>%s
      AND m.active=1 AND m.role=s.role
      AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager')
    RETURNING event_id"""


def _context(raw_session_token,tenant_id,server_now):
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None
            or type(server_now) is not int
            or not 0<=server_now<2**63):
        raise ValueError("Current trusted session context required")
    return hashlib.sha256(raw_session_token.encode("ascii")).hexdigest()


def _note(value):
    return (type(value) is str and value==value.strip()
            and 1<=len(value)<=1000
            and all(ord(c)>=32 or c in "\n\t" for c in value))


def prepare_session_feedback_list(*,raw_session_token,tenant_id,server_now):
    digest=_context(raw_session_token,tenant_id,server_now)
    return _LIST,(tenant_id,digest,server_now)


def summarize_session_feedback_list(rows,*,tenant_id):
    if (type(rows) not in (tuple,list)
            or len(rows)>200 or type(tenant_id) is not str
            or _TENANT.fullmatch(tenant_id) is None):
        raise ValueError("Unexpected private feedback list")
    items=[]
    seen=set()
    for row in rows:
        if (type(row) not in (tuple,list) or len(row)!=6
                or type(row[0]) is not str or _ID.fullmatch(row[0]) is None
                or row[0] in seen
                or type(row[1]) is not int or row[1]<1
                or type(row[2]) is not int or row[2]<1
                or not _note(row[3])
                or type(row[4]) is not str or _ID.fullmatch(row[4]) is None
                or type(row[5]) is not int or row[5]<0):
            raise ValueError("Invalid private feedback entry")
        seen.add(row[0])
        items.append({"request_id":row[0],"draft_revision":row[1],
                      "current_revision":row[2],
                      "stale":row[1]!=row[2],"note":row[3],
                      "feedback_token":row[4],"updated_at":row[5],
                      "approval_granted":False,"publishing_enabled":False})
    return {"tenant_id":tenant_id,"status":"feedback_only","items":items,
            "approval_granted":False,"publishing_enabled":False}


def prepare_session_feedback_save(*,raw_session_token,tenant_id,request_id,
                                  expected_revision,expected_feedback_token,
                                  note,server_now):
    digest=_context(raw_session_token,tenant_id,server_now)
    if (type(request_id) is not str or _ID.fullmatch(request_id) is None
            or type(expected_revision) is not int
            or not 1<=expected_revision<2**31
            or (expected_feedback_token is not None
                and (type(expected_feedback_token) is not str
                     or _ID.fullmatch(expected_feedback_token) is None))
            or not _note(note)):
        raise ValueError("Valid current private feedback draft required")
    version=uuid.uuid4().hex
    if expected_feedback_token is None:
        return (_INSERT,(note,version,server_now,tenant_id,request_id,
                         expected_revision,digest,server_now),
                "created",version)
    return (_REPLACE,(
        expected_revision,note,version,server_now,digest,tenant_id,
        request_id,expected_feedback_token,expected_revision,digest,
        server_now), "updated",version)


def summarize_session_feedback_save(row,*,tenant_id,request_id,
                                    expected_revision,expected_new_token):
    if row is None:
        raise PermissionError("Current reviewer and feedback version required")
    if (type(row) not in (tuple,list) or len(row)!=5
            or tuple(row[:4])!=(tenant_id,request_id,expected_revision,
                                 expected_new_token)
            or type(row[4]) is not str
            or _TENANT.fullmatch(row[4]) is None):
        raise ValueError("Unexpected private feedback write")
    return {"tenant_id":tenant_id,"request_id":request_id,
            "draft_revision":expected_revision,
            "feedback_token":expected_new_token,
            "status":"feedback_only","approval_granted":False,
            "publishing_enabled":False}


def prepare_session_feedback_event(*,raw_session_token,tenant_id,request_id,
                                   current_feedback_token,action,server_now):
    digest=_context(raw_session_token,tenant_id,server_now)
    if (type(request_id) is not str or _ID.fullmatch(request_id) is None
            or type(current_feedback_token) is not str
            or _ID.fullmatch(current_feedback_token) is None
            or action not in _ACTIONS):
        raise ValueError("Current feedback event version required")
    eid=uuid.uuid4().hex
    return _EVENT,(eid,action,server_now,tenant_id,request_id,
                   current_feedback_token,digest,server_now)


def assert_feedback_event_saved(row,*,expected_event_id):
    if row is None:
        raise PermissionError("Feedback event not authorized; rollback")
    if row!=(expected_event_id,):
        raise ValueError("Unexpected private feedback audit result")
