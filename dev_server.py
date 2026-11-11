"""Explicit offline demo server for BAM account APIs.

Run locally: python dev_server.py
The printed demo bearer token is a disposable test credential only.
No real login, provider credentials, publishing or production deployment.
"""
import sqlite3
from access_policy import Principal,Role
from accounts import AccountDirectory
from account_dashboard import AccountDashboard
from account_read_api import AccountReadAPI
from business_curation import BusinessCuration
from business_switcher import BusinessSwitcher
from content_requests import ContentRequests
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from dev_http_gateway import create_loopback_server
from provider_connection_registry import ProviderConnectionRegistry
from sessions import SessionStore
from social_connection_directory import SocialConnectionDirectory

def create_demo():
    # Isolated in-memory data: never use this server for actual customer data.
    db=sqlite3.connect(':memory:',check_same_thread=False)
    directory=AccountDirectory(db)
    directory.bootstrap_owner('belenos_demo','demo_user')
    directory.bootstrap_owner('busy_b_demo','busy_b_owner')
    directory.set_member(Principal('busy_b_owner','busy_b_demo',Role.OWNER),
                         'demo_user',Role.MARKETING_MANAGER)
    curation=BusinessCuration(db)
    curation.create_profile('belenos_demo','Belenos Creations (Demo)',
                            'custom products',['3d_printing'])
    curation.create_profile('busy_b_demo','Busy B Cleaning (Demo)',
                            'commercial cleaning',['facility_care'])
    sessions=SessionStore(db)
    token=sessions.issue(Principal('demo_user','belenos_demo',Role.OWNER),
                         ttl_seconds=3600)
    registry=ProviderConnectionRegistry(db)
    requests=ContentRequests(db)
    import time
    now=int(time.time())
    requests.create(tenant_id='belenos_demo',channel='facebook',
        draft_text='See our latest custom creations!',
        suggestion='Take a photo of the finished item in good lighting.',
        required_items=['product_photo','photo_permission'],now=now)
    requests.create(tenant_id='busy_b_demo',channel='facebook',
        draft_text='A behind-the-scenes look at commercial cleaning.',
        suggestion='Provide an approved photo of the team or equipment.',
        required_items=['approved_team_photo'],now=now)
    content_service=ContentRequestService(requests=requests,
        sessions=sessions,directory=directory,
        attachments=AttachmentRegistry(db))
    dashboard=AccountDashboard(
        sessions=sessions,directory=directory,
        switcher=BusinessSwitcher(db,sessions,directory),
        social_connections=SocialConnectionDirectory(
            registry=registry,directory=directory,sessions=sessions),
        content_service=content_service)
    server=create_loopback_server(AccountReadAPI(dashboard))
    return db,server,token

def main():
    db,server,token=create_demo()
    try:
        print('BAM OFFLINE DEVELOPMENT DEMO — NO REAL LOGIN OR PUBLISHING')
        print('Local endpoint: http://127.0.0.1:%s/api/account/overview' % server.server_port)
        print('Disposable demo bearer token (expires in 1 hour):',token)
        print('Use Authorization: Bearer <token>. Ctrl+C to stop.')
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        db.close()

if __name__=='__main__':
    main()
