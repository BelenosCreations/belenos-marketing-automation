"""Session-validated PostgreSQL held-draft creation and revision SQL contracts.

Pure SQL preparation: no HTTP ingress, DB connections, publication, uploads,
paid AI, scheduled work or provider side effects. In the CI adapter these
queries may execute against synthetic local PostgreSQL only.
"""
import hashlib
import json
import re
import uuid

_SESSION = re.compile(r"[A-Za-z0-9_-]{40,256}\Z")
_TENANT = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_REQUEST = re.compile(r"[a-f0-9]{32}\Z")
_CHANNEL = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_ITEM = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_EDIT_TARGETS = frozenset(("draft_text", "suggestion"))
_HELD_STATUSES = frozenset(
    ("needs_content", "ready_for_review", "postponed", "unavailable")
)

_CREATE = """INSERT INTO content_requests
    (request_id,tenant_id,channel,draft_text,suggestion,
     required_items,provided_items,status,priority,priority_token,
     created_at,updated_at,revision)
    SELECT %s,%s,%s,%s,%s,%s,'{}','needs_content',%s,%s,%s,%s,1
    FROM sessions s
    JOIN members m ON m.tenant_id=s.tenant_id
         AND m.subject_id=s.subject_id
    JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE s.token_hash=%s AND s.tenant_id=%s
      AND s.revoked_at IS NULL AND s.expires_at>%s
      AND m.active=1 AND m.role=s.role
      AND i.active=1 AND i.email_verified=1
      AND m.role IN ('owner','marketing_manager','content_creator')
    RETURNING request_id,tenant_id,status,revision,priority_token"""

_REVISION_TEMPLATE = """UPDATE content_requests
    SET {column}=%s,updated_at=%s,revision=revision+1
    WHERE tenant_id=%s AND request_id=%s AND revision=%s
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
             AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=content_requests.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator')
      )
    RETURNING request_id,revision,status,draft_text,suggestion"""


def _validated_context(raw_session_token, tenant_id, server_now):
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str or _TENANT.fullmatch(tenant_id) is None
            or type(server_now) is not int or not 0 <= server_now < 2**63):
        raise ValueError("Trusted tenant session and timestamp required")
    return hashlib.sha256(raw_session_token.encode("ascii")).hexdigest()


def _valid_copy(text, maximum):
    return (type(text) is str and bool(text.strip()) and
            text == text.strip() and len(text) <= maximum and
            "\x00" not in text)


def prepare_session_held_draft_create(*, raw_session_token, tenant_id,
                                      channel, draft_text, suggestion,
                                      required_items, priority=0, server_now):
    """Generate server-side IDs and create ONLY an unapproved held draft.

    A caller cannot override request ID, priority version, approval state,
    author identity or status; current session access is checked in INSERT.
    """
    digest = _validated_context(raw_session_token, tenant_id, server_now)
    if (type(channel) is not str or _CHANNEL.fullmatch(channel) is None
            or not _valid_copy(draft_text, 2000)
            or not _valid_copy(suggestion, 2000)
            or type(required_items) not in (list, tuple)
            or not 1 <= len(required_items) <= 16
            or any(type(x) is not str or _ITEM.fullmatch(x) is None
                   for x in required_items)
            or len(set(required_items)) != len(required_items)
            or type(priority) is not int or not -10 <= priority <= 10):
        raise ValueError("Valid held draft and required items only")
    request_id = uuid.uuid4().hex
    priority_token = uuid.uuid4().hex
    items_json = json.dumps(list(required_items), separators=(",", ":"))
    return _CREATE, (
        request_id, tenant_id, channel, draft_text, suggestion,
        items_json, priority, priority_token, server_now, server_now,
        digest, tenant_id, server_now
    )


def summarize_held_draft_create(row, *, expected_id, tenant_id,
                                expected_priority_token):
    """Return minimal receipt without ever suggesting a published post."""
    if row is None:
        raise PermissionError("Current editor authorization required")
    if (type(row) not in (list, tuple) or len(row) != 5
            or type(expected_id) is not str
            or _REQUEST.fullmatch(expected_id) is None
            or type(expected_priority_token) is not str
            or _REQUEST.fullmatch(expected_priority_token) is None
            or tuple(row) != (expected_id, tenant_id, "needs_content",
                              1, expected_priority_token)):
        raise ValueError("Unexpected held draft creation receipt")
    return {"status": "needs_content", "request_id": expected_id,
            "tenant_id": tenant_id, "revision": 1,
            "priority_token": expected_priority_token,
            "publishing_enabled": False, "posts_scheduled": 0}


def prepare_session_held_draft_revision(*, raw_session_token, tenant_id,
                                        request_id, target, revised_text,
                                        expected_revision, server_now):
    """Single-statement session-validated, conflict-safe text-only revision."""
    digest = _validated_context(raw_session_token, tenant_id, server_now)
    if (type(request_id) is not str
            or _REQUEST.fullmatch(request_id) is None
            or type(target) is not str or target not in _EDIT_TARGETS
            or not _valid_copy(revised_text, 2000)
            or type(expected_revision) is not int
            or not 1 <= expected_revision < 2**31 - 1):
        raise ValueError("Current draft version and editable text required")
    # Column is inserted from a hard-coded whitelist, never arbitrary input.
    sql = _REVISION_TEMPLATE.format(column=target)
    return sql, (revised_text, server_now, tenant_id, request_id,
                 expected_revision, digest, server_now)


def summarize_held_draft_revision(row, *, request_id, expected_revision):
    """Missing/stale/unauthorized revisions fail identically without data."""
    if row is None:
        raise PermissionError("Current editor or draft revision required")
    if (type(row) not in (list, tuple) or len(row) != 5
            or row[0] != request_id
            or type(row[1]) is not int
            or row[1] != expected_revision + 1
            or row[2] not in _HELD_STATUSES
            or not _valid_copy(row[3], 2000)
            or not _valid_copy(row[4], 2000)):
        raise ValueError("Unexpected held draft revision receipt")
    return {"request_id": request_id, "revision": row[1],
            "status": row[2], "draft_text": row[3],
            "suggestion": row[4], "publishing_enabled": False,
            "posts_scheduled": 0}
