"""Static BAM browser shell is only accessible when explicitly opted in."""
import hashlib
import re
import unittest
from html.parser import HTMLParser
from bam_signed_in_assets_wsgi import BAMSignedInAssetsWSGI

class AssetsWSGITests(unittest.TestCase):
    def setUp(self):
        self.app=BAMSignedInAssetsWSGI(enabled=True)

    def call(self,path='/ui/bam_signed_in_shell.html',*,app=None,
             method='GET',scheme='https',extra=None):
        env={'wsgi.url_scheme':scheme,'PATH_INFO':path,
             'REQUEST_METHOD':method}
        if extra:env.update(extra)
        result={}
        output=b''.join((app or self.app)(env,lambda status,headers:
            result.update(status=status,headers=dict(headers))))
        return result,output

    def test_shell_and_all_dependent_assets_are_served(self):
        meta,html=self.call()
        self.assertEqual(meta['status'],'200 OK')
        self.assertEqual(meta['headers']['Content-Type'],
                         'text/html; charset=utf-8')
        self.assertEqual(meta['headers']['Cache-Control'],'no-store, private')
        policy=meta['headers']['Content-Security-Policy']
        self.assertIn("script-src 'self'",policy)
        self.assertIn("connect-src 'self'",policy)
        self.assertNotIn("'unsafe-eval'",policy)
        self.assertNotIn("'unsafe-inline'",policy)
        self.assertIn(b'Belenos Automatic Marketing',html)
        self.assertNotIn(b'<script src="https:',html)
        for asset in self.app._assets:
            with self.subTest(asset=asset):
                info,content=self.call(asset)
                self.assertEqual(info['status'],'200 OK')
                self.assertEqual(int(info['headers']['Content-Length']),
                                 len(content))
                self.assertNotIn(b'correct horse battery staple',content)
                if asset.endswith('.js'):
                    self.assertEqual(info['headers']['Content-Type'],
                                     'text/javascript; charset=utf-8')

    def test_headers_and_redirect_without_external_deployment(self):
        info,body=self.call('/')
        self.assertEqual(info['status'],'302 Found')
        self.assertEqual(info['headers']['Location'],
                         '/ui/bam_signed_in_shell.html')
        self.assertEqual(body,b'')
        info,body=self.call(method='HEAD')
        self.assertEqual(info['status'],'200 OK')
        self.assertEqual(body,b'')
        self.assertGreater(int(info['headers']['Content-Length']),len(body))

    def test_rejects_unlisted_or_untrusted_paths(self):
        for path in (
                '/ui/bam_dashboard_prototype.html',
                '/ui/../README.md','/README.md',
                '/.env','/ui/evil.js','/branding/source/other.svg',
                '/ui/dashboard_prototype.html','/api/v1/dashboard'):
            self.assertEqual(self.call(path)[0]['status'],'404 Not Found')
        self.assertEqual(self.call(extra={'QUERY_STRING':'debug=1'})[0]['status'],
                         '404 Not Found')
        self.assertEqual(self.call(method='POST')[0]['status'],
                         '405 Method Not Allowed')
        self.assertEqual(self.call(scheme='http',
            extra={'HTTP_X_FORWARDED_PROTO':'https'})[0]['status'],
            '403 Forbidden')
        self.assertEqual(self.call(app=BAMSignedInAssetsWSGI())[0]['status'],
                         '503 Service Unavailable')
        with self.assertRaises(ValueError):
            BAMSignedInAssetsWSGI(enabled=1)

if __name__=='__main__':unittest.main()
