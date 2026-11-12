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
# Explicit outbound request allowlist: prevent provider conversations, stored
# state, background requests, extra tools or unreviewed provider features.
_ALLOWED_FIELDS=frozenset((
    'model','instructions','input','text','max_output_tokens','store',
    'tools','parallel_tool_calls'))

class OpenAITransport:
    def __init__(self, *, key_resolver, opener, enabled=False,
                 timeout_seconds=20,dispatch_guard=None):
        if not callable(key_resolver) or not callable(opener):
            raise TypeError('Trusted credential resolver and HTTPS opener required')
        if type(enabled) is not bool or type(timeout_seconds) is not int or (
            not 1<=timeout_seconds<=60):
            raise ValueError('Invalid transport configuration')
        # Merely setting enabled=True can never bypass the operator
        # authorization guard. No implicit permissive default.
        if enabled and not callable(dispatch_guard):
            raise ValueError('Trusted operator dispatch guard required')
        if dispatch_guard is not None and not callable(dispatch_guard):
            raise ValueError('Trusted dispatch guard must be callable')
        self._resolve=key_resolver
        self._open=opener
        self._enabled=enabled
        self._timeout=timeout_seconds
        self._dispatch_guard=dispatch_guard

    def __call__(self,payload):
        if not self._enabled:
            raise PermissionError('OpenAI requests disabled until deployment approval')
        if type(payload) is not dict or set(payload)-_ALLOWED_FIELDS or (
            payload.get('parallel_tool_calls',False) is not False or
            ('instructions' in payload and (
                type(payload['instructions']) is not str or
                not payload['instructions'].strip())) or
            type(payload.get('input')) is not list or
            payload.get('store') is not False or
            payload.get('tools')!=[] or
            payload.get('model') not in ('gpt-4.1-mini','gpt-4.1','gpt-5-mini') or
            type(payload.get('max_output_tokens')) is not int or
            not 1<=payload['max_output_tokens']<=16384 or
            type(payload.get('text')) is not dict or
            type(payload['text'].get('format')) is not dict or
            payload['text']['format'].get('type')!='json_schema' or
            payload['text']['format'].get('strict') is not True or
            type(payload['text']['format'].get('schema')) is not dict):
            raise ValueError('Unsupported OpenAI payload')
        # Reject non-user messages and unsupported content even with tools=[].
        for message in payload['input']:
            if type(message) is not dict or set(message)!={'role','content'} or (
                message['role']!='user' or type(message['content']) is not list
                or not 1<=len(message['content'])<=4):
                raise ValueError('Unsupported OpenAI input')
            for part in message['content']:
                if type(part) is not dict or set(part)!={'type','text'} or (
                    part['type']!='input_text' or type(part['text']) is not str
                    or not part['text'].strip()):
                    raise ValueError('Unsupported OpenAI input')
        body=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        if len(body)>32768:
            raise ValueError('OpenAI request too large')
        # Check again *immediately* before credential access. An operator
        # pause can happen after quota admission while a request is queued.
        # The callback must be trusted server code, never a client flag.
        try:
            allowed=self._dispatch_guard()
        except Exception:
            raise PermissionError(
                'OpenAI dispatch authorization unavailable') from None
        if allowed is not True:
            raise PermissionError('OpenAI dispatch authorization unavailable')
        # Only the trusted server-side resolver can return the secret.
        secret=self._resolve()
        if type(secret) is not str or not re.fullmatch(
            r'sk-[A-Za-z0-9_-]{16,256}',secret):
            raise PermissionError('Server OpenAI credential unavailable')
        request=Request(_API_URL,data=body,method='POST',headers={
            'Authorization':'Bearer '+secret,
            'Content-Type':'application/json',
            'Accept':'application/json'})
        # A slow key-vault resolution must not bypass a newly activated
        # operator pause. Recheck immediately before the network opener.
        # This is still a point-in-time check, NOT atomic with the HTTP send.
        try:
            if self._dispatch_guard() is not True:
                raise PermissionError('OpenAI dispatch authorization unavailable')
        except Exception:
            raise PermissionError(
                'OpenAI dispatch authorization unavailable') from None
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
