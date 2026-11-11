"""Authenticated attachment upload preflight; no file transfer is performed.

The storage key is server-generated, not chosen by the mobile client.
The resulting record stays pending until a separate trusted verifier approves.
"""
import uuid
from access_policy import Action

MAX_BYTES={
    'image/jpeg':20*1024*1024,
    'image/png':20*1024*1024,
    'image/webp':20*1024*1024,
    'video/mp4':250*1024*1024,
    'text/plain':1024*1024,
    'application/pdf':20*1024*1024,
}

class ContentUploadPreflight:
    def __init__(self, *, service):
        self.service=service

    def begin(self, *, token, tenant_id, request_id, item,
              media_type, sha256, byte_count, now=None):
        now=self.service._now(now)
        self.service._authorize(token=token,tenant_id=tenant_id,
                                action=Action.EDIT_DRAFT,now=now)
        request=self.service.requests.get(tenant_id=tenant_id,request_id=request_id)
        if request is None:
            raise KeyError('Content request not found')
        if request['status'] in ('postponed','unavailable'):
            raise ValueError('Reactivate request before upload')
        if item not in request['required_items']:
            raise ValueError('Item is not on the required checklist')
        if media_type not in MAX_BYTES:
            raise ValueError('Unsupported media type')
        if type(byte_count) is not int or not 0<byte_count<=MAX_BYTES[media_type]:
            raise ValueError('Invalid or oversized attachment')
        # This key is a server-owned identifier, not an upload URL or capability.
        key='private-content/'+uuid.uuid4().hex
        aid=self.service.attachments.register_pending(
            tenant_id=tenant_id,request_id=request_id,item=item,
            media_type=media_type,sha256=sha256,storage_key=key,now=now)
        return {
            'attachment_id':aid,
            'status':'pending',
            'max_bytes':MAX_BYTES[media_type],
            'upload_url':None,
            'note':'A trusted storage adapter must authorize and perform the upload',
        }
