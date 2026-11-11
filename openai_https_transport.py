"""Disabled-by-default OpenAI HTTPS transport foundation.

No credentials are read from disk or environment. The production composition
root must inject a trusted key resolver and a TLS-verifying HTTP opener, then
explicitly enable this transport after deployment and cost review.
"""
import json
import re
from urllib.request import Request
from urllib.error import HTTPError,URLError

_API_URL='https://api.openai.com/v1/responses'
_MAX_BODY=65536

class OpenAITransport:
    def __init__(self, *, key_resolver, opener, enabled=False,
                 timeout_seconds=20):
        if not callable(key_resolver) or not callable(opener):
            raise TypeError('Trusted credential resolver and HTTPS opener required')
        if type(enabled) is not bool or type(timeout_seconds) is not int or (
            not 1<=timeout_seconds<=60):
            raise ValueError('Invalid transport configuration')
        self._resolve=key_resolver
        self._open=opener
        self._enabled=enabled
        self._timeout=timeout_seconds

    def __call__(self,payload):
        if not self._enabled:
            raise PermissionError('OpenAI requests disabled until deployment approval')
        if type(payload) is not dict or payload.get('store') is not False or (
            payload.get('tools')!=[] or
            payload.get('model') not in ('gpt-4.1-mini','gpt-4.1','gpt-5-mini') or
            type(payload.get('max_output_tokens')) is not int or
            not 1<=payload['max_output_tokens']<=16384 or
            type(payload.get('text')) is not dict or
            type(payload['text'].get('format')) is not dict or
            payload['text']['format'].get('type')!='json_schema'):
            raise ValueError('Unsupported OpenAI payload')
        body=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        if len(body)>32768:
            raise ValueError('OpenAI request too large')
        # Only the trusted server-side resolver can return the secret.
        secret=self._resolve()
        if type(secret) is not str or not re.fullmatch(
            r'sk-[A-Za-z0-9_-]{16,256}',secret):
            raise PermissionError('Server OpenAI credential unavailable')
        request=Request(_API_URL,data=body,method='POST',headers={
            'Authorization':'Bearer '+secret,
            'Content-Type':'application/json',
            'Accept':'application/json'})
        # Never log the Request object: it contains the Authorization header.
        try:
            with self._open(request,timeout=self._timeout) as response:
                if response.status!=200:
                    raise RuntimeError('OpenAI request failed')
                raw=response.read(_MAX_BODY+1)
        except (HTTPError,URLError,TimeoutError,OSError) as exc:
            # Do not expose provider errors, URLs, or request headers.
            raise RuntimeError('OpenAI request unavailable') from None
        if len(raw)>_MAX_BODY:
            raise ValueError('OpenAI response exceeds size limit')
        try:
            result=json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:
            raise ValueError('Invalid OpenAI response') from None
        if type(result) is not dict:
            raise ValueError('Invalid OpenAI response')
        return result
