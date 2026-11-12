"""Session-scoped, metadata-only attachment status lookup.

Reads never include storage keys, hashes, file bytes or actual URLs. A stored
'verified' status is only a synthetic CI database value: this interface does
not scan media or grant editorial approval/publishing permission.
"""
import hashlib
import re

_SESSION=re.compile(r"[A-Za-z0-9_-]{40,256}\Z")
_TENANT=re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_REQUEST=re.compile(r"[a-f0-9]{32}\Z")
_ATTACHMENT=_REQUEST
_ITEM=re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
_TYPES=frozenset(("image/jpeg","image/png","image/webp","video/mp4",
                  "text/plain","application/pdf"))
_STATES=frozenset(("pending","verified","rejected"))

_SQL="""SELECT a.attachment_id,a.item,a.media_type,a.status,a.created_at
    FROM content_attachments a
    JOIN content_requests c ON c.request_id=a.request_id
         AND c.tenant_id=a.tenant_id
    WHERE a.tenant_id=%s AND a.request_id=%s
      AND EXISTS (
        SELECT 1 FROM sessions s
        JOIN members m ON m.tenant_id=s.tenant_id
             AND m.subject_id=s.subject_id
        JOIN bam_identities i ON i.subject_id=s.subject_id
        WHERE s.token_hash=%s AND s.tenant_id=a.tenant_id
          AND s.revoked_at IS NULL AND s.expires_at>%s
          AND m.active=1 AND m.role=s.role
          AND i.active=1 AND i.email_verified=1
          AND m.role IN ('owner','marketing_manager','content_creator',
                         'employee','viewer')
      )
    ORDER BY a.created_at DESC,a.attachment_id DESC LIMIT 101"""


def prepare_session_attachment_statuses(*,raw_session_token,tenant_id,
                                         request_id,server_now):
    if (type(raw_session_token) is not str
            or _SESSION.fullmatch(raw_session_token) is None
            or type(tenant_id) is not str or _TENANT.fullmatch(tenant_id) is None
            or type(request_id) is not str
            or _REQUEST.fullmatch(request_id) is None
            or type(server_now) is not int or not 0<=server_now<2**63):
        raise ValueError("Current business session and draft ID required")
    digest=hashlib.sha256(raw_session_token.encode("ascii")).hexdigest()
    return _SQL,(tenant_id,request_id,digest,server_now)


def summarize_session_attachment_statuses(rows,*,tenant_id,request_id):
    if (type(tenant_id) is not str or _TENANT.fullmatch(tenant_id) is None
            or type(request_id) is not str
            or _REQUEST.fullmatch(request_id) is None
            or type(rows) not in (list,tuple)
            or len(rows)>100):
        raise ValueError("Unexpected private attachment metadata")
    items=[]
    seen=set()
    previous=None
    for row in rows:
        if (type(row) not in (tuple,list) or len(row)!=5
                or type(row[0]) is not str
                or _ATTACHMENT.fullmatch(row[0]) is None
                or row[0] in seen
                or type(row[1]) is not str
                or _ITEM.fullmatch(row[1]) is None
                or type(row[2]) is not str or row[2] not in _TYPES
                or type(row[3]) is not str or row[3] not in _STATES
                or type(row[4]) is not int or row[4]<0):
            raise ValueError("Invalid private attachment row")
        key=(row[4],row[0])
        if previous is not None and key>=previous:
            raise ValueError("Attachment order violated")
        previous=key
        seen.add(row[0])
        items.append({"attachment_id":row[0],"item":row[1],
                      "media_type":row[2],"status":row[3],
                      "created_at":row[4]})
    return {"tenant_id":tenant_id,"request_id":request_id,
            "status":"attachment_metadata_only","items":items,
            "files_uploaded":0,"scanning_performed_by_adapter":False,
            "approval_granted":False,"publishing_enabled":False}
