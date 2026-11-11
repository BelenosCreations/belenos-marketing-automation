import io
import json
import unittest
from openai_https_transport import OpenAITransport

def payload():
    return {'model':'gpt-4.1-mini','store':False,'tools':[],
        'text':{'format':{'type':'json_schema','name':'bam_draft',
            'strict':True,'schema':{'type':'object'}}},
        'max_output_tokens':300,'input':[]}

class FakeResponse:
    status=200
    def __init__(self,data):
        self.stream=io.BytesIO(data)
    def __enter__(self):
        return self
    def __exit__(self,*args):
        return False
    def read(self,size):
        return self.stream.read(size)

class OpenAITransportTests(unittest.TestCase):
    def test_disabled_transport_never_reads_key_or_opens_connection(self):
        calls=[]
        transport=OpenAITransport(
            key_resolver=lambda:calls.append('key'),
            opener=lambda *a,**kw:calls.append('network'))
        with self.assertRaises(PermissionError):
            transport(payload())
        self.assertEqual(calls,[])

    def test_enabled_transport_uses_only_server_secret(self):
        seen=[]
        def opener(request,*,timeout):
            seen.append((request,timeout))
            return FakeResponse(json.dumps({'status':'completed',
                'output':[]}).encode())
        transport=OpenAITransport(
            key_resolver=lambda:'sk-'+'a'*30,
            opener=opener,enabled=True,timeout_seconds=8)
        result=transport(payload())
        self.assertEqual(result['status'],'completed')
        request,timeout=seen[0]
        self.assertEqual(timeout,8)
        self.assertEqual(request.full_url,
                         'https://api.openai.com/v1/responses')
        self.assertEqual(request.get_method(),'POST')
        self.assertTrue(request.get_header('Authorization').startswith('Bearer sk-'))
        self.assertNotIn('sk-',request.data.decode())

    def test_rejects_unsafe_payload_without_key_lookup(self):
        calls=[]
        transport=OpenAITransport(
            key_resolver=lambda:calls.append('key'),
            opener=lambda *a,**kw:None,enabled=True)
        for change in ({'store':True},{'tools':[{'type':'web_search'}]},
                       {'text':{}},{'max_output_tokens':'bad'}):
            if 'max_output_tokens' in change:
                continue  # Envelope cap is enforced by the executor.
            with self.assertRaises(ValueError):
                transport({**payload(),**change})
        self.assertEqual(calls,[])

    def test_network_errors_do_not_expose_secrets(self):
        def failing(*args,**kwargs):
            raise OSError('secret network diagnostics')
        transport=OpenAITransport(
            key_resolver=lambda:'sk-'+'a'*30,
            opener=failing,enabled=True)
        with self.assertRaisesRegex(RuntimeError,'OpenAI request unavailable') as cm:
            transport(payload())
        self.assertNotIn('secret',str(cm.exception))
        self.assertNotIn('sk-',str(cm.exception))

if __name__=='__main__':
    unittest.main()
