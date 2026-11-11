"""Minimal read-only WSGI adapter for BAM's authenticated dashboard.

Requires HTTPS at the WSGI boundary. In production the reverse proxy must
terminate TLS and set wsgi.url_scheme safely; never trust client X-Forwarded-Proto.
No CORS, cookies, write endpoints, social publishing or public server startup.
"""
import json
import time

class BAMReadWSGI:
    def __init__(self,api,clock=None):
        self.api=api
        self.clock=clock if clock is not None else time.time

    @staticmethod
    def _response(start_response,status,body):
        encoded=json.dumps(body,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        start_response(status,[
            ('Content-Type','application/json; charset=utf-8'),
            ('Content-Length',str(len(encoded))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('Content-Security-Policy',"default-src 'none'; frame-ancestors 'none'"),
        ])
        return [encoded]

    def __call__(self,environ,start_response):
        if environ.get('wsgi.url_scheme')!='https':
            return self._response(start_response,'403 Forbidden',
                {'error':'HTTPS required'})
        if environ.get('REQUEST_METHOD')!='GET':
            return self._response(start_response,'405 Method Not Allowed',
                {'error':'Read-only API'})
        path=environ.get('PATH_INFO')
        if path not in ('/api/v1/dashboard','/api/v1/drafts',
                        '/api/v1/posting-preferences','/api/v1/ai-drafts',
                        '/api/v1/ai-settings','/api/v1/ai-business-facts',
                        '/api/v1/ai-cost-summary'):
            return self._response(start_response,'404 Not Found',
                {'error':'Not found'})
        auth=environ.get('HTTP_AUTHORIZATION','')
        if (not isinstance(auth,str) or not auth.startswith('Bearer ')
                or len(auth)>2060):
            return self._response(start_response,'401 Unauthorized',
                {'error':'Authentication required'})
        token=auth[7:]
        if not token or token!=token.strip():
            return self._response(start_response,'401 Unauthorized',
                {'error':'Authentication required'})
        try:
            now=int(self.clock())
            if path=='/api/v1/dashboard':
                body=self.api.get_dashboard_view(
                    session_token=token,server_now=now)
            elif path=='/api/v1/drafts':
                body=self.api.list_held_drafts(
                    session_token=token,server_now=now)
            elif path=='/api/v1/ai-cost-summary':
                body=self.api.get_ai_cost_summary(
                    session_token=token,server_now=now)
            elif path=='/api/v1/ai-business-facts':
                body=self.api.get_ai_business_facts(
                    session_token=token,server_now=now)
            elif path=='/api/v1/ai-settings':
                body=self.api.get_ai_settings(
                    session_token=token,server_now=now)
            elif path=='/api/v1/ai-drafts':
                body=self.api.list_ai_content_drafts(
                    session_token=token,server_now=now)
            else:
                body=self.api.get_posting_preferences(
                    session_token=token,server_now=now)
        except PermissionError:
            return self._response(start_response,'401 Unauthorized',
                {'error':'Authentication required'})
        except Exception:
            # Do not disclose token, SQL, private drafts, or internal details.
            return self._response(start_response,'503 Service Unavailable',
                {'error':'Service unavailable'})
        return self._response(start_response,'200 OK',body)
