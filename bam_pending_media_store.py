"""Private, pending-only manual image receipt in BAM's local preview.

No file download, gallery/preview, malware scan, consent verification,
attachment approval, or publishing. This component is DISABLED unless a
private external storage directory is explicitly configured.
"""
import os
from pathlib import Path
import re
import stat
from access_policy import Action
from content_byte_inspector import AttachmentByteInspector
from content_upload_preflight import MAX_BYTES

_IMAGE_TYPES=frozenset(('image/png','image/jpeg','image/webp'))
_ID=re.compile(r'[a-f0-9]{32}\Z')
_SOURCE=Path(__file__).resolve().parent
_MAX_STAGED_FILES=128
_MAX_STAGED_BYTES=128*1024*1024

class BAMPendingMediaStore:
    def __init__(self,*,service,storage_dir):
        if service is None or type(storage_dir) is not str or not storage_dir.strip():
            raise ValueError('Trusted media store configuration required')
        original=Path(storage_dir).expanduser()
        if original.is_symlink():
            raise ValueError('Symlinked storage directory is not allowed')
        destination=original.resolve()
        if destination.is_relative_to(_SOURCE):
            raise ValueError('Media storage must remain outside source repository')
        destination.mkdir(parents=True,mode=0o700,exist_ok=True)
        if os.name=='posix' and stat.S_IMODE(destination.stat().st_mode)&0o077:
            raise PermissionError('Pending media storage must be private (chmod 700)')
        self.service=service
        self.root=destination
        self.inspector=AttachmentByteInspector(service.attachments)

    def authorize_slot(self,*,token,attachment_id,now):
        if (type(attachment_id) is not str or
                _ID.fullmatch(attachment_id) is None):
            raise ValueError('Valid pending attachment ID required')
        session=self.service.sessions.resolve_current(
            token,directory=self.service.directory,now=now)
        if session is None:
            raise PermissionError('Active BAM session required')
        tenant=session.principal.tenant_id
        self.service._authorize(token=token,tenant_id=tenant,
            action=Action.EDIT_DRAFT,now=now)
        row=self.service.attachments.db.execute(
            """SELECT request_id,item,media_type,sha256 FROM content_attachments
            WHERE tenant_id=? AND attachment_id=? AND status='pending'""",
            (tenant,attachment_id)).fetchone()
        if row is None:
            raise KeyError('Pending attachment not found')
        request_id,item,media_type,sha256=row
        if media_type not in _IMAGE_TYPES:
            raise ValueError('Local image receipt accepts PNG, JPEG or WebP only')
        request=self.service.requests.get(tenant_id=tenant,request_id=request_id)
        if (request is None or request['status'] in ('postponed','unavailable')
                or item not in request['required_items']
                or item in request['provided_items']):
            raise PermissionError('Attachment no longer needed')
        return {'tenant_id':tenant,'attachment_id':attachment_id,
                'media_type':media_type,'sha256':sha256,
                'max_bytes':MAX_BYTES[media_type]}


    def statuses(self,*,token,now):
        """List current-business pending receipt states, without file metadata."""
        session=self.service.sessions.resolve_current(
            token,directory=self.service.directory,now=now)
        if session is None:
            raise PermissionError('Active BAM session required')
        tenant=session.principal.tenant_id
        self.service._authorize(token=token,tenant_id=tenant,
                                action=Action.READ_DRAFTS,now=now)
        rows=self.service.attachments.db.execute(
            """SELECT request_id,item,attachment_id FROM content_attachments
            WHERE tenant_id=? AND status='pending'
              AND media_type IN ('image/png','image/jpeg','image/webp')
            ORDER BY created_at DESC,attachment_id DESC LIMIT 501""",
            (tenant,)).fetchall()
        if len(rows)>500:
            raise ValueError('Pending media list too large')
        request_cache={}
        statuses={}
        for request_id,item,attachment_id in rows:
            if request_id not in request_cache:
                request_cache[request_id]=self.service.requests.get(
                    tenant_id=tenant,request_id=request_id)
            draft=request_cache[request_id]
            if (draft is None or draft['status']!='needs_content'
                    or item not in draft['required_items']
                    or item in draft['provided_items']):
                continue
            try:
                info=os.lstat(self.root/(attachment_id+'.pending'))
                received=(stat.S_ISREG(info.st_mode)
                    and info.st_size>0 and info.st_nlink==1
                    and (os.name!='posix' or
                         stat.S_IMODE(info.st_mode)&0o077==0))
            except FileNotFoundError:
                received=False
            state='pending_scan' if received else 'awaiting_file'
            key=(request_id,item)
            if key not in statuses or state=='pending_scan':
                statuses[key]=state
        return {'tenant_id':tenant,
            'items':[{'request_id':rid,'item':item,'status':status}
                     for (rid,item),status in sorted(statuses.items())],
            'media_verified':False,'publishing_enabled':False}


    def discard(self,*,token,request_id,item,now):
        """Explicitly discard pending private images for one required item.

        This never affects verified media, approval, published work or another
        business. File unlink precedes metadata deletion to avoid declaring
        private bytes removed when disk removal actually failed.
        """
        if (type(request_id) is not str or _ID.fullmatch(request_id) is None
                or type(item) is not str or not item.strip()
                or item!=item.strip() or len(item)>80):
            raise ValueError('Required content item and request ID needed')
        session=self.service.sessions.resolve_current(
            token,directory=self.service.directory,now=now)
        if session is None:
            raise PermissionError('Current BAM session required')
        tenant=session.principal.tenant_id
        self.service._authorize(token=token,tenant_id=tenant,
                                action=Action.EDIT_DRAFT,now=now)
        request=self.service.requests.get(
            tenant_id=tenant,request_id=request_id)
        if request is None:
            raise KeyError('Business content request not found')
        if item not in request['required_items']:
            raise ValueError('Item is not part of this content request')
        rows=self.service.attachments.db.execute(
            """SELECT attachment_id FROM content_attachments
               WHERE tenant_id=? AND request_id=? AND item=?
                 AND status='pending' AND
                 media_type IN ('image/png','image/jpeg','image/webp')
               ORDER BY attachment_id LIMIT 201""",
            (tenant,request_id,item)).fetchall()
        if len(rows)>200:
            raise ValueError('Too many pending media attachments')
        paths=[]
        for (attachment_id,) in rows:
            if _ID.fullmatch(attachment_id) is None:
                raise RuntimeError('Unsafe stored attachment ID')
            path=self.root/(attachment_id+'.pending')
            try:
                info=os.lstat(path)
            except FileNotFoundError:
                continue
            if not (stat.S_ISREG(info.st_mode) and info.st_nlink==1 or
                    stat.S_ISLNK(info.st_mode)):
                raise PermissionError('Unsafe pending media object')
            paths.append(path)
        # Unlink the expected private files, never follow symbolic links.
        for path in paths:
            path.unlink(missing_ok=True)
        if rows:
            identifiers=[record[0] for record in rows]
            with self.service.attachments.db:
                self.service.attachments.db.executemany(
                    """DELETE FROM content_attachments
                       WHERE tenant_id=? AND request_id=? AND item=?
                         AND attachment_id=? AND status='pending'""",
                    [(tenant,request_id,item,attachment_id)
                     for attachment_id in identifiers])
        return {'tenant_id':tenant,'request_id':request_id,
                'item':item,'removed':len(rows),
                'media_verified':False,'publishing_enabled':False}

    def receive(self,*,token,attachment_id,content,now):
        slot=self.authorize_slot(
            token=token,attachment_id=attachment_id,now=now)
        if (type(content) is not bytes or not 0<len(content)
                <=slot['max_bytes']):
            raise ValueError('Invalid image size or bytes')
        # Hash, declared type and file signature must match; this is not a
        # malware scan, decoded-image inspection or owner-permission proof.
        self.inspector.inspect(
            content=content,media_type=slot['media_type'],
            expected_sha256=slot['sha256'])
        target=self.root/(attachment_id+'.pending')
        if target.exists():
            raise FileExistsError('Attachment already received')
        staged=list(self.root.glob('*.pending'))
        if (len(staged)>=_MAX_STAGED_FILES
                or sum(p.stat().st_size for p in staged)+len(content)
                    >_MAX_STAGED_BYTES):
            raise ValueError('Pending storage quota exceeded')
        flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
        if hasattr(os,'O_NOFOLLOW'):
            flags|=os.O_NOFOLLOW
        fd=os.open(target,flags,0o600)
        try:
            with os.fdopen(fd,'wb') as sink:
                sink.write(content)
                sink.flush()
                os.fsync(sink.fileno())
        except Exception:
            target.unlink(missing_ok=True)
            raise
        # Registry intentionally stays 'pending'. A separate scanner,
        # consent verifier and explicit content-review flow are mandatory.
        return {'tenant_id':slot['tenant_id'],
                'attachment_id':attachment_id,'status':'pending_scan',
                'bytes_received':len(content),'media_verified':False,
                'publishing_enabled':False}
