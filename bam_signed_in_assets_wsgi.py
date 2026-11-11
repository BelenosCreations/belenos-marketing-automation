"""Restricted same-origin browser asset adapter for BAM offline integration.

This module has NO HTTP listener and does not enable account enrollment,
publishing, external social providers or paid AI calls. It serves *only* the
script/CSS/image assets referenced by BAM's signed-in shell under an explicitly
enabled WSGI test composition. Do not deploy this offline gateway publicly.
"""
import base64
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import posixpath
from urllib.parse import urlsplit

_ROOT=Path(__file__).resolve().parent
_SHELL='/ui/bam_signed_in_shell.html'
_CONTENT_TYPES={
    '.html':'text/html; charset=utf-8',
    '.js':'text/javascript; charset=utf-8',
    '.css':'text/css; charset=utf-8',
    '.svg':'image/svg+xml',
}

class _AssetParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.assets=set()
        self.style_text=[]
        self._inside_style=False

    def handle_starttag(self,tag,attrs):
        items=dict(attrs)
        if tag=='style':
            self._inside_style=True
        if tag in ('script','img','link'):
            location=items.get('src') if tag!='link' else items.get('href')
            if location:
                self.assets.add(location)

    def handle_endtag(self,tag):
        if tag=='style':
            self._inside_style=False

    def handle_data(self,data):
        if self._inside_style:
            self.style_text.append(data)

class BAMSignedInAssetsWSGI:
    def __init__(self,*,enabled=False):
        if type(enabled) is not bool:
            raise ValueError('Explicit enabled switch required')
        self.enabled=enabled
        shell=(_ROOT/'ui'/'bam_signed_in_shell.html').read_bytes()
        parsed=_AssetParser()
        parsed.feed(shell.decode('utf-8'))
        if not parsed.style_text:
            raise RuntimeError('Expected BAM shell style')
        self._style_hash=base64.b64encode(hashlib.sha256(
            ''.join(parsed.style_text).encode('utf-8')).digest()).decode('ascii')
        self._assets={_SHELL:(_ROOT/'ui'/'bam_signed_in_shell.html')}
        for location in parsed.assets:
            if ('://' in location or location.startswith('//') or
                    '\\' in location or '?' in location or '#' in location):
                raise RuntimeError('Unapproved browser asset reference')
            # Browser-relative paths resolve against the shell's /ui/ directory.
            url=posixpath.normpath(urlsplit('/ui/'+location).path)
            path=(_ROOT/url.lstrip('/')).resolve()
            if (not path.is_relative_to(_ROOT)
                    or not path.is_file()
                    or path.suffix not in ('.js','.css','.svg')):
                raise RuntimeError('Unapproved or missing BAM browser resource')
            if url in self._assets:
                raise RuntimeError('Duplicate shell resource')
            self._assets[url]=path
        # A page with zero scripts or no original BAM icon is incomplete.
        if (_ROOT/'branding/source/app_icon.svg').resolve() not in self._assets.values():
            raise RuntimeError('Canonical BAM brand icon missing')
        if not any(path.suffix=='.js' for path in self._assets.values()):
            raise RuntimeError('Browser shell scripts missing')

    @staticmethod
    def _reply(start_response,status,body,headers=()):
        base=[
            ('Content-Type','text/plain; charset=utf-8'),
            ('Content-Length',str(len(body))),
            ('Cache-Control','no-store, private'),
            ('Pragma','no-cache'),
            ('X-Content-Type-Options','nosniff'),
            ('Referrer-Policy','no-referrer'),
            ('X-Frame-Options','DENY'),
            ('Cross-Origin-Resource-Policy','same-origin')]
        original={k for k,v in headers}
        start_response(status,[(k,v) for k,v in base if k not in original]+list(headers))
        return [body]

    def __call__(self,environ,start_response):
        respond=lambda status,body,headers=():self._reply(start_response,status,body,headers)
        if environ.get('wsgi.url_scheme')!='https':
            return respond('403 Forbidden',b'HTTPS required')
        if not self.enabled:
            return respond('503 Service Unavailable',b'BAM browser integration disabled')
        method=environ.get('REQUEST_METHOD')
        if method not in ('GET','HEAD'):
            return respond('405 Method Not Allowed',b'Read-only browser assets')
        if environ.get('QUERY_STRING'):
            return respond('404 Not Found',b'Unknown resource')
        requested=environ.get('PATH_INFO')
        if type(requested) is not str:
            return respond('404 Not Found',b'Unknown resource')
        if requested=='/':
            if method!='GET':
                return respond('405 Method Not Allowed',b'GET required')
            return respond('302 Found',b'',(
                ('Location',_SHELL),('Content-Length','0')))
        path=self._assets.get(requested)
        if path is None:
            return respond('404 Not Found',b'Unknown resource')
        data=path.read_bytes()
        content_type=_CONTENT_TYPES[path.suffix]
        if requested==_SHELL:
            policy=(
                "default-src 'none'; "
                "script-src 'self'; "
                "style-src 'self' 'sha256-"+self._style_hash+"'; "
                "img-src 'self'; connect-src 'self'; form-action 'self'; "
                "base-uri 'none'; object-src 'none'; frame-ancestors 'none'"
            )
        else:
            policy="default-src 'none'; script-src 'none'; object-src 'none'; frame-ancestors 'none'"
        return respond('200 OK',b'' if method=='HEAD' else data,(
            ('Content-Type',content_type),
            ('Content-Length',str(len(data))),
            ('Content-Security-Policy',policy)))
