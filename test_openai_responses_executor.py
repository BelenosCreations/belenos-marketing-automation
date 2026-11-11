import json
import unittest
from openai_responses_executor import OpenAIResponsesExecutor

def response(text='{"post_text":"Custom tumblers","image_prompt":"A tumbler"}'):
    return {'status':'completed','error':None,'incomplete_details':None,
        'output':[{'type':'message','role':'assistant','status':'completed',
            'content':[{'type':'output_text','text':text}]}]}

def request():
    return {'provider':'openai','mode':'bam_sponsored',
        'output_type':'unpublished_draft','publishing_enabled':False,
        'instructions':'Use only verified business facts.',
        'input_json':'{"topic":"Tumblers","verified_facts":{"name":"Shop"}}'}

class OpenAIResponsesExecutorTests(unittest.TestCase):
    def test_payload_and_valid_response(self):
        calls=[]
        def transport(payload):
            calls.append(payload)
            return response()
        executor=OpenAIResponsesExecutor(transport=transport)
        result=executor(request=request(),max_output_tokens=500)
        self.assertEqual(result['post_text'],'Custom tumblers')
        payload=calls[0]
        self.assertEqual(payload['model'],'gpt-4.1-mini')
        self.assertEqual(payload['max_output_tokens'],500)
        self.assertIs(payload['store'],False)
        self.assertEqual(payload['tools'],[])
        self.assertEqual(payload['text']['format']['type'],'json_schema')
        self.assertIs(payload['text']['format']['strict'],True)
        self.assertNotIn('api_key',json.dumps(payload))
        self.assertEqual(payload['input'][0]['role'],'user')

    def test_invalid_requests_never_reach_transport(self):
        calls=[]
        executor=OpenAIResponsesExecutor(
            transport=lambda payload:calls.append(payload))
        for patch in ({'mode':'own_openai_key'},
                      {'publishing_enabled':True},
                      {'provider':'third_party'},
                      {'input_json':'not json'}):
            with self.assertRaises((ValueError,PermissionError)):
                executor(request={**request(),**patch},max_output_tokens=100)
        with self.assertRaises(ValueError):
            executor(request=request(),max_output_tokens=20000)
        self.assertEqual(calls,[])

    def test_fail_closed_on_incomplete_or_unexpected_provider_data(self):
        cases=[
            {'status':'incomplete','output':[]},
            {'status':'completed','output':[]},
            response('{"post_text":"Hi","image_prompt":null,"published":true}'),
            {'**':'bad'},
            {'**':'bad'},
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    OpenAIResponsesExecutor._extract(raw)
        extra=response()
        extra['output'].append({'type':'function_call','name':'publish'})
        with self.assertRaises(ValueError):
            OpenAIResponsesExecutor._extract(extra)
        refusal=response()
        refusal['output'][0]['content']=[{'type':'refusal','refusal':'No'}]
        with self.assertRaises(ValueError):
            OpenAIResponsesExecutor._extract(refusal)

    def test_model_allowlist(self):
        with self.assertRaises(ValueError):
            OpenAIResponsesExecutor(transport=lambda x:None,model='unknown')

if __name__=='__main__':
    unittest.main()
