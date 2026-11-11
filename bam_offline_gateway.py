"""Offline-only composition root for BAM's verified sign-in and read APIs.

Purpose: exercise real SQLite identity, membership, dashboard and AI read
services through a single WSGI application before production integration.
No HTTP listener, hosting, provider calls, account signup or publishing.
The app is disabled by default and must never be mounted publicly.
"""
import json
import time

from account_dashboard import AccountDashboard
from account_read_api import AccountReadAPI
from accounts import AccountDirectory
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_content_drafts import AIContentDraftStore
from ai_cost_ledger import AICostLedger
from auth_login_api import AuthLoginAPI
from bam_auth_wsgi import BAMAuthWSGI
from bam_business_switch_wsgi import BAMBusinessSwitchWSGI
from bam_content_write_wsgi import BAMContentWriteWSGI
from bam_posting_preferences_wsgi import BAMPostingPreferencesWSGI
from bam_upload_preflight_wsgi import BAMUploadPreflightWSGI
from bam_ai_facts_write_wsgi import BAMAIFactsWriteWSGI
from bam_local_draft_wsgi import BAMLocalProductDraftWSGI
from bam_signed_in_assets_wsgi import BAMSignedInAssetsWSGI
from bam_ai_draft_edit_wsgi import BAMAIDraftEditWSGI
from bam_read_wsgi import BAMReadWSGI
from business_curation import BusinessCuration
from business_switcher import BusinessSwitcher
from content_attachments import AttachmentRegistry
from content_request_service import ContentRequestService
from content_requests import ContentRequests
from google_login_challenges import GoogleLoginChallenges
from identity_auth import IdentityAuth
from login_throttle import LoginThrottle
from posting_preferences import PostingPreferences
from provider_connection_registry import ProviderConnectionRegistry
from sessions import SessionStore
from social_connection_directory import SocialConnectionDirectory

_AUTH_PATHS = frozenset((
    '/api/v1/auth/password', '/api/v1/auth/google-challenge',
    '/api/v1/auth/google', '/api/v1/auth/logout',
    '/api/v1/auth/logout-everywhere'))
_READ_PATHS = frozenset((
    '/api/v1/dashboard', '/api/v1/drafts',
    '/api/v1/posting-preferences', '/api/v1/ai-drafts',
    '/api/v1/ai-settings', '/api/v1/ai-business-facts',
    '/api/v1/ai-cost-summary'))


class _DisabledGoogleVerifier:
    def verify(self, **kwargs):
        raise PermissionError('Google verification not configured')


class BAMOfflineGateway:
    """Trusted test fixture composition. Provision fixtures via Python only.

    `enabled=True` permits WSGI direct-call tests; it does NOT mean that
    external HTTP/TLS hosting, production enrollment, or publishing is safe.
    """

    def __init__(self, db, *, enabled=False, clock=None, google_verifier=None,
                 serve_browser_assets=False):
        if type(enabled) is not bool:
            raise ValueError('Boolean integration switch required')
        if type(serve_browser_assets) is not bool:
            raise ValueError('Boolean browser-assets switch required')
        self.enabled = enabled
        self.serve_browser_assets = serve_browser_assets
        self.clock = time.time if clock is None else clock
        if not callable(self.clock):
            raise ValueError('Trusted server clock required')
        self.directory = AccountDirectory(db)
        self.sessions = SessionStore(db)
        self.identities = IdentityAuth(db, self.sessions, self.directory)
        self.curation = BusinessCuration(db)
        self.connections = ProviderConnectionRegistry(db)
        self.requests = ContentRequests(db)
        self.attachments = AttachmentRegistry(db)
        self.ai_policy = AIPolicyStore(
            db=db, sessions=self.sessions, directory=self.directory)
        self.ai_business_facts = AIBusinessFacts(
            db=db, policy_store=self.ai_policy)
        self.ai_drafts = AIContentDraftStore(
            db=db, policy_store=self.ai_policy)
        self.ai_costs = AICostLedger(db)
        self.preferences = PostingPreferences(
            db=db, sessions=self.sessions, directory=self.directory)
        self.dashboard = AccountDashboard(
            sessions=self.sessions,
            directory=self.directory,
            switcher=BusinessSwitcher(db, self.sessions, self.directory),
            social_connections=SocialConnectionDirectory(
                registry=self.connections, directory=self.directory,
                sessions=self.sessions),
            content_service=ContentRequestService(
                requests=self.requests, sessions=self.sessions,
                directory=self.directory, attachments=self.attachments))
        self.read_api = AccountReadAPI(
            self.dashboard, posting_preferences=self.preferences,
            ai_content_drafts=self.ai_drafts, ai_policy=self.ai_policy,
            ai_business_facts=self.ai_business_facts,
            ai_cost_ledger=self.ai_costs)
        self.login_api = AuthLoginAPI(
            auth=self.identities, challenges=GoogleLoginChallenges(db),
            google_verifier=(google_verifier if google_verifier is not None
                             else _DisabledGoogleVerifier()),
            throttle=LoginThrottle(db))
        self.auth_wsgi = BAMAuthWSGI(
            self.login_api, enabled=enabled, clock=self.clock,
            logout_api=self.read_api)
        self.read_wsgi = BAMReadWSGI(self.read_api, clock=self.clock)
        self.assets_wsgi = BAMSignedInAssetsWSGI(enabled=enabled and serve_browser_assets)
        self.switch_wsgi = BAMBusinessSwitchWSGI(
            self.read_api, enabled=enabled, clock=self.clock)
        self.content_write_wsgi = BAMContentWriteWSGI(
            self.read_api, enabled=enabled, clock=self.clock)
        self.preference_write_wsgi = BAMPostingPreferencesWSGI(
            self.read_api, enabled=enabled, clock=self.clock)
        self.upload_preflight_wsgi = BAMUploadPreflightWSGI(
            self.read_api, enabled=enabled, clock=self.clock)
        self.facts_write_wsgi = BAMAIFactsWriteWSGI(
            registry=self.ai_business_facts,enabled=enabled,clock=self.clock)
        self.local_draft_wsgi = BAMLocalProductDraftWSGI(
            self.read_api,enabled=enabled,clock=self.clock)
        self.local_service_wsgi = BAMLocalProductDraftWSGI(
            self.read_api,enabled=enabled,clock=self.clock,template='service')
        self.ai_draft_edit_wsgi = BAMAIDraftEditWSGI(
            self.read_api,enabled=enabled,clock=self.clock)

    @staticmethod
    def _unavailable(start_response, status, message):
        raw=json.dumps({'error':message},separators=(',',':')).encode('utf-8')
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(raw))),
            ('Cache-Control','no-store, private'),
            ('X-Content-Type-Options','nosniff')])
        return [raw]

    def __call__(self, environ, start_response):
        if not self.enabled:
            return self._unavailable(
                start_response,'503 Service Unavailable',
                'BAM offline integration is disabled')
        path = environ.get('PATH_INFO')
        if self.serve_browser_assets and (path == '/' or
            (type(path) is str and (path.startswith('/ui/') or
                                    path.startswith('/branding/')))):
            return self.assets_wsgi(environ, start_response)
        if path in _AUTH_PATHS:
            return self.auth_wsgi(environ, start_response)
        if path == '/api/v1/posting-preferences' and environ.get('REQUEST_METHOD') == 'PUT':
            return self.preference_write_wsgi(environ, start_response)
        if path == '/api/v1/ai-business-facts' and environ.get('REQUEST_METHOD') == 'PUT':
            return self.facts_write_wsgi(environ, start_response)
        if path == '/api/v1/ai-drafts' and environ.get('REQUEST_METHOD') == 'PUT':
            return self.ai_draft_edit_wsgi(environ, start_response)
        if path in _READ_PATHS:
            return self.read_wsgi(environ, start_response)
        if path == '/api/v1/businesses/activate':
            return self.switch_wsgi(environ, start_response)
        if path in ('/api/v1/content/drafts','/api/v1/content/hold'):
            return self.content_write_wsgi(environ, start_response)
        if path == '/api/v1/ai/local-product-draft':
            return self.local_draft_wsgi(environ, start_response)
        if path == '/api/v1/ai/local-service-draft':
            return self.local_service_wsgi(environ, start_response)
        if path == '/api/v1/content/upload-preflight':
            return self.upload_preflight_wsgi(environ, start_response)
        return self._unavailable(
            start_response,'404 Not Found','Unknown BAM API route')
