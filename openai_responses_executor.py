"""Strict OpenAI Responses API adapter with an injected HTTPS transport.

This module does NOT read environment variables, load API keys, or make network
requests by itself. A production-only trusted transport supplies credentials,
TLS verification, timeouts, request IDs, retries and cost accounting.
"""
import json
import hashlib
import re

DEFAULT_MODEL='gpt-4.1-mini'
_ALLOWED_MODELS=frozenset(('gpt-4.1-mini','gpt-4.1','gpt-5-mini'))
_MAX_INPUT_BYTES=32768
_MAX_RESPONSE_BYTES=65536
_PROVIDER_ID=re.compile(r'resp_[A-Za-z0-9_-]{8,200}\Z')

class OpenAIResponsesExecutor:
    """Callable adapter accepted by AIDraftGenerationWorkflow."""

    def __init__(self, *, transport, model=DEFAULT_MODEL,
                 usage_observer=None):
        if not callable(transport):
            raise TypeError('Trusted transport required')
        if model not in _ALLOWED_MODELS:
            raise ValueError('Model must be explicitly approved')
        if usage_observer is not None and not callable(usage_observer):
            raise TypeError('Trusted usage observer required')
        self.transport=transport
        self.model=model
        self.usage_observer=usage_observer

    def __call__(self, *, request, max_output_tokens):
        if type(request) is not dict or request.get('provider')!='openai' or (
            request.get('output_type')!='unpublished_draft' or
            request.get('publishing_enabled') is not False):
            raise ValueError('Only unpublished OpenAI draft requests allowed')
        if request.get('mode')!='bam_sponsored':
            raise PermissionError('Personal-key mode requires separate executor')
        if type(max_output_tokens) is not int or not 1<=max_output_tokens<=16384:
            raise ValueError('Invalid reserved token limit')
        instructions=request.get('instructions')
        input_json=request.get('input_json')
        if (type(instructions) is not str or not instructions.strip() or
            type(input_json) is not str or not input_json.strip() or
            len((instructions+input_json).encode('utf-8'))>_MAX_INPUT_BYTES):
            raise ValueError('Invalid prompt')
        # The user-supplied content is isolated in a user message, not
        # concatenated into the developer instruction hierarchy.
        try:
            input_data=json.loads(input_json)
        except json.JSONDecodeError as exc:
            raise ValueError('Invalid structured input') from exc
        if type(input_data) is not dict:
            raise ValueError('Structured input object required')
        schema={
            'type':'object',
            'properties':{
                'post_text':{'type':'string'},
                'image_prompt':{'type':['string','null']}},
            'required':['post_text','image_prompt'],
            'additionalProperties':False}
        payload={
            'model':self.model,
            'instructions':instructions,
            'input':[{'role':'user','content':[{
                'type':'input_text',
                'text':json.dumps(input_data,ensure_ascii=False,sort_keys=True)
            }]}],
            'text':{'format':{'type':'json_schema','name':'bam_draft',
                'strict':True,'schema':schema}},
            'max_output_tokens':max_output_tokens,
            'store':False,
            'tools':[],
            'parallel_tool_calls':False}
        response=self.transport(payload)
        # Meter a trusted provider's reported token usage BEFORE checking
        # whether its text is suitable for staging. A refused, incomplete
        # or malformed generated draft may still represent costly tokens;
        # don't silently undercount those attempts in the local ledger.
        if self.usage_observer is not None:
            if type(response) is not dict:
                raise ValueError('Structured provider usage required')
            provider_id=response.get('id')
            if (type(provider_id) is not str or
                    _PROVIDER_ID.fullmatch(provider_id) is None):
                raise ValueError('Trusted provider response identifier required')
            # A stable 128-bit truncated SHA-256 reference is sufficient for
            # local deduplication; the raw provider ID is not exposed to the
            # ledger or the response. No claim of verified billing is made.
            usage_ref=hashlib.sha256(
                provider_id.encode('ascii')).hexdigest()[:32]
            usage=response.get('usage')
            if type(usage) is not dict or any(
                type(usage.get(key)) is not int or
                not 0<=usage[key]<=100000000
                for key in ('input_tokens','output_tokens')):
                raise ValueError('Provider token usage required for accounting')
            self.usage_observer(tenant_id=request['tenant_id'],
                subject_id=request['subject_id'],model=self.model,
                input_tokens=usage['input_tokens'],
                output_tokens=usage['output_tokens'],
                usage_ref=usage_ref)
        return self._extract(response)

    @staticmethod
    def _extract(response):
        if type(response) is str:
            if len(response.encode('utf-8'))>_MAX_RESPONSE_BYTES:
                raise ValueError('Provider response too large')
            try:
                response=json.loads(response)
            except json.JSONDecodeError as exc:
                raise ValueError('Invalid provider JSON') from exc
        if type(response) is not dict:
            raise ValueError('Invalid provider response')
        if response.get('status')!='completed' or response.get('error') is not None or (
            response.get('incomplete_details') is not None):
            raise ValueError('Provider response incomplete')
        output=response.get('output')
        if type(output) is not list or not 1<=len(output)<=12:
            raise ValueError('Missing provider output')
        texts=[]
        for item in output:
            if type(item) is not dict or item.get('type')!='message' or (
                item.get('role')!='assistant' or item.get('status')!='completed'):
                raise ValueError('Unexpected provider output type')
            contents=item.get('content')
            if type(contents) is not list or not 1<=len(contents)<=8:
                raise ValueError('Invalid provider content')
            for part in contents:
                if type(part) is not dict or part.get('type')!='output_text' or (
                    type(part.get('text')) is not str):
                    raise ValueError('Unexpected provider content')
                texts.append(part['text'])
        if len(texts)!=1 or len(texts[0].encode('utf-8'))>_MAX_RESPONSE_BYTES:
            raise ValueError('Expected exactly one structured response')
        try:
            parsed=json.loads(texts[0])
        except json.JSONDecodeError as exc:
            raise ValueError('Invalid generated JSON') from exc
        if type(parsed) is not dict or set(parsed)!={'post_text','image_prompt'}:
            raise ValueError('Invalid structured draft fields')
        return parsed
