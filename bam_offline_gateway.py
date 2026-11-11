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

    def __init__(self, db, *, enabled=False, clock=None, google_verifier=None):
        if type(enabled) is not bool:
            raise ValueError('Boolean integration switch required')
        self.enabled = enabled
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
        if path in _AUTH_PATHS:
            return self.auth_wsgi(environ, start_response)
        if path in _READ_PATHS:
            return self.read_wsgi(environ, start_response)
        return self._unavailable(
            start_response,'404 Not Found','Unknown BAM API route')
