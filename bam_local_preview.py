"""Opt-in, loopback-only HTTPS preview of BAM's offline authenticated shell.

This is intentionally NOT production hosting, public enrollment or a Render
entrypoint. The local WSGI service requires the user's own TLS certificate and
key and binds only 127.0.0.1. No social publishing or paid AI API is enabled.
Never put a preview SQLite database, credentials or TLS keys in this repo.
"""
import argparse
import getpass
import os
from pathlib import Path
from contextlib import closing
import sqlite3
import ssl
import stat
import time
from wsgiref.simple_server import WSGIRequestHandler, make_server

from bam_offline_gateway import BAMOfflineGateway
from access_policy import Role
from identity_auth import normalize_email

_SOURCE_ROOT=Path(__file__).resolve().parent

def _path(value,*,must_exist=False):
    if type(value) is not str or not value.strip():
        raise ValueError('Local file path required')
    candidate=Path(value).expanduser()
    if candidate.is_symlink():
        raise ValueError('Symlinked preview files are not allowed')
    path=candidate.resolve()
    if path.is_relative_to(_SOURCE_ROOT):
        raise ValueError('Preview files must be outside the source repository')
    if must_exist and not path.is_file():
        raise ValueError('Existing local file required')
    if path.is_dir():
        raise ValueError('A file path is required')
    return path

def _business_details(tenant_id,display_name,industry,topic):
    for value,limit in ((tenant_id,128),(display_name,200),
                        (industry,120),(topic,120)):
        if (type(value) is not str or not value.strip()
                or value!=value.strip() or len(value)>limit):
            raise ValueError('Invalid local preview business details')

def add_preview_business(db_path,*,email,password,existing_tenant_id,
                         new_tenant_id,display_name,industry,topic,now=None):
    """Add a second local preview business only after existing owner login.

    This is a trusted local CLI operation, never an HTTP route or a public
    self-service business enrollment. It cannot grant ownership to strangers.
    """
    path=_path(db_path,must_exist=True)
    normalize_email(email)
    if type(password) is not str or not 12<=len(password.encode('utf-8'))<=1024:
        raise ValueError('Valid password required')
    if type(existing_tenant_id) is not str or not existing_tenant_id.strip():
        raise ValueError('Existing business ID required')
    _business_details(new_tenant_id,display_name,industry,topic)
    timestamp=int(time.time()) if now is None else now
    if type(timestamp) is not int or timestamp<0:
        raise ValueError('Invalid local timestamp')
    if os.name=='posix' and stat.S_IMODE(path.stat().st_mode)&0o077:
        raise PermissionError('Local preview database must be private (chmod 600)')
    with closing(sqlite3.connect(path)) as db:
        db.execute('PRAGMA foreign_keys=ON')
        gateway=BAMOfflineGateway(db)
        token=gateway.identities.login_password(
            email=email,password=password,
            tenant_id=existing_tenant_id,now=timestamp)
        try:
            session=gateway.sessions.resolve_current(
                token,directory=gateway.directory,now=timestamp)
            if session is None or session.principal.role!=Role.OWNER:
                raise PermissionError('Existing local business owner required')
            if (db.execute('SELECT 1 FROM members WHERE tenant_id=?',
                (new_tenant_id,)).fetchone() or
                db.execute('SELECT 1 FROM business_profiles WHERE tenant_id=?',
                (new_tenant_id,)).fetchone()):
                raise PermissionError('Target business already exists')
            gateway.directory.bootstrap_owner(
                new_tenant_id,session.principal.subject_id)
            gateway.curation.create_profile(
                new_tenant_id,display_name,industry,[topic])
        finally:
            gateway.sessions.revoke(token,now=timestamp)
    return {'business_id':new_tenant_id,
            'preview_only':True,'publishing_enabled':False}

def provision_preview_owner(db_path,*,email,password,tenant_id,
                            display_name,industry,topic,now=None):
    """Local-only test owner enrollment; deliberately bypasses *real* email delivery.

    This function is NOT exposed through WSGI and must never be reused for
    production identity enrollment. It provisions a fresh SQLite preview DB.
    """
    path=_path(db_path)
    normalize_email(email)
    if type(password) is not str or not 12<=len(password.encode('utf-8'))<=1024:
        raise ValueError('Password must be 12–1024 UTF-8 bytes')
    _business_details(tenant_id,display_name,industry,topic)
    timestamp=int(time.time()) if now is None else now
    if type(timestamp) is not int or timestamp<0:
        raise ValueError('Invalid local setup time')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.exists():
        raise PermissionError('Preview database already exists; do not overwrite credentials')
    # Create with private permissions BEFORE SQLite writes any credentials.
    descriptor=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    os.close(descriptor)
    # Local-only database. Never fall back to shared, in-source production data.
    with closing(sqlite3.connect(path)) as db:
        db.execute('PRAGMA foreign_keys=ON')
        gateway=BAMOfflineGateway(db)
        for table in ('bam_identities','members','business_profiles'):
            count=db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
            if count:
                raise PermissionError('Preview already provisioned; preserve existing accounts')
        subject=gateway.identities.register_password(
            email=email,password=password,now=timestamp)
        # Trusted local preview shortcut ONLY: production requires email proof.
        gateway.identities.set_email_verified_trusted(
            subject_id=subject,verified=True)
        gateway.directory.bootstrap_owner(tenant_id,subject)
        gateway.curation.create_profile(
            tenant_id,display_name,industry,[topic])
    if os.name=='posix':
        os.chmod(path,0o600)
    return {'business_id':tenant_id,'preview_only':True,
            'publishing_enabled':False}

def _reject(start_response,status='403 Forbidden'):
    body=b'Local preview access denied'
    start_response(status,[
        ('Content-Type','text/plain; charset=utf-8'),
        ('Content-Length',str(len(body))),
        ('Cache-Control','no-store, private'),
        ('X-Content-Type-Options','nosniff')])
    return [body]

def make_loopback_application(gateway,port):
    """Prevent DNS rebinding, remote use and untrusted scheme forwarding.

    The real local TLS socket is the trusted HTTPS termination point.
    """
    if type(port) is not int or not 1024<=port<=65535:
        raise ValueError('Unprivileged local preview port required')
    def application(environ,start_response):
        address=environ.get('REMOTE_ADDR')
        host=environ.get('HTTP_HOST')
        if address not in ('127.0.0.1','::1') or host not in (
                '127.0.0.1:'+str(port),'localhost:'+str(port)):
            return _reject(start_response)
        trusted=dict(environ)
        trusted['wsgi.url_scheme']='https'
        # Ignore forwarded headers entirely; the listener terminates TLS.
        return gateway(trusted,start_response)
    return application

class _QuietHandler(WSGIRequestHandler):
    def log_message(self,format,*args):
        # Never log request paths, query strings, passwords or bearer tokens.
        pass

def run_loopback_preview(db_path,*,cert_path,key_path,port=8443,
                         explicit_opt_in=False,pending_media_dir=None):
    if explicit_opt_in is not True:
        raise PermissionError('Explicit local-only preview acknowledgement required')
    if type(port) is not int or not 1024<=port<=65535:
        raise ValueError('Invalid local preview port')
    dbpath=_path(db_path,must_exist=True)
    certificate=_path(cert_path,must_exist=True)
    key=_path(key_path,must_exist=True)
    media_path=(_path(pending_media_dir)
                if pending_media_dir is not None else None)
    if os.name=='posix' and stat.S_IMODE(key.stat().st_mode)&0o077:
        raise PermissionError('TLS private key must be accessible to owner only (chmod 600)')
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=str(certificate),keyfile=str(key))
    db=sqlite3.connect(dbpath)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=5000')
        gateway=BAMOfflineGateway(
            db,enabled=True,serve_browser_assets=True,
            pending_media_dir=(str(media_path) if media_path else None))
        count=db.execute('''SELECT COUNT(*) FROM bam_identities i
            JOIN members m ON i.subject_id=m.subject_id
            WHERE i.active=1 AND i.email_verified=1 AND m.active=1''').fetchone()[0]
        if not count:
            raise PermissionError('Provision a verified local preview owner before serving')
        app=make_loopback_application(gateway,port)
        with make_server('127.0.0.1',port,app,
                         handler_class=_QuietHandler) as server:
            server.socket=context.wrap_socket(server.socket,server_side=True)
            print('BAM local-only preview at https://localhost:'+str(port)+'/')
            print('No account signup, publishing, paid AI or social APIs are enabled.')
            server.serve_forever()
    finally:
        db.close()

def main(argv=None):
    parser=argparse.ArgumentParser(
        description='BAM local HTTPS preview. NEVER deploy this runner publicly.')
    sub=parser.add_subparsers(dest='command',required=True)
    setup=sub.add_parser('bootstrap',help='Local-only initial verified test owner')
    setup.add_argument('--db',required=True)
    setup.add_argument('--business-id',required=True)
    setup.add_argument('--display-name',required=True)
    setup.add_argument('--industry',required=True)
    setup.add_argument('--topic',required=True)
    add=sub.add_parser('add-business',help='Create a second preview business for an existing owner')
    add.add_argument('--db',required=True)
    add.add_argument('--existing-business-id',required=True)
    add.add_argument('--new-business-id',required=True)
    add.add_argument('--display-name',required=True)
    add.add_argument('--industry',required=True)
    add.add_argument('--topic',required=True)
    serve=sub.add_parser('serve',help='Run local-only HTTPS preview')
    serve.add_argument('--db',required=True)
    serve.add_argument('--cert',required=True)
    serve.add_argument('--key',required=True)
    serve.add_argument('--port',type=int,default=8443)
    serve.add_argument('--pending-media-dir',help='Private local image holding area, off by default')
    serve.add_argument('--i-understand-local-only',action='store_true')
    args=parser.parse_args(argv)
    if args.command in ('bootstrap','add-business'):
        email=input('Local BAM test owner email: ').strip()
        password=getpass.getpass('Local BAM password (12+ characters): ')
        if args.command=='bootstrap':
            confirmed=getpass.getpass('Confirm password: ')
            if password!=confirmed:
                parser.error('Passwords did not match')
            result=provision_preview_owner(args.db,email=email,password=password,
                tenant_id=args.business_id,display_name=args.display_name,
                industry=args.industry,topic=args.topic)
            print('Preview-only owner configured for business ID '+result['business_id'])
            print('Email ownership was NOT independently verified; never use this bootstrap in production.')
        else:
            result=add_preview_business(args.db,email=email,password=password,
                existing_tenant_id=args.existing_business_id,
                new_tenant_id=args.new_business_id,
                display_name=args.display_name,industry=args.industry,
                topic=args.topic)
            print('Additional local-only preview business configured: '+result['business_id'])
    else:
        run_loopback_preview(args.db,cert_path=args.cert,key_path=args.key,
            port=args.port,
            explicit_opt_in=args.i_understand_local_only,
            pending_media_dir=args.pending_media_dir)

if __name__=='__main__':
    main()
