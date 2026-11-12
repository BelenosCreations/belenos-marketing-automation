import json
import hashlib
import sqlite3
from decimal import Decimal
from ai_cost_ledger import AICostLedger,AITokenPricing
import unittest
from openai_responses_executor import OpenAIResponsesExecutor

def response(text='{"post_text":"Custom tumblers","image_prompt":"A tumbler"}'):
    return {'status':'completed','error':None,'incomplete_details':None,
        'output':[{'type':'message','role':'assistant','status':'completed',
            'content':[{'type':'output_text','text':text}]}]}

def request():
    return {'provider':'openai','mode':'bam_sponsored',
        'output_type':'unpublished_draft','publishing_enabled':False,
        'tenant_id':'shop','subject_id':'owner',
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
                      {'input_json':'not json'},
                      {'tenant_id':None},{'subject_id':''},
                      {'tenant_id':True},{'subject_id':'s'*129}):
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

    def test_untrusted_provider_json_and_component_fields_fail_closed(self):
        for text in (
            '{"post_text":"First","post_text":"Override","image_prompt":null}',
            '{"post_text":"Hi","image_prompt":null,"image_prompt":"Oops"}',
            '{"post_text":[],"image_prompt":null}',
            '{"post_text":" ","image_prompt":null}',
            '{"post_text":"Hi","image_prompt":123}',
            '{"post_text":"Hi","image_prompt":" "}',
            json.dumps({'post_text':'P'*4001,'image_prompt':None}),
            json.dumps({'post_text':'OK','image_prompt':'I'*2001}),
        ):
            with self.subTest(text=text[:70]),self.assertRaises(ValueError):
                OpenAIResponsesExecutor._extract(response(text))
        raw=json.dumps(response())
        top_duplicate=raw.replace('"status": "completed"',
            '"status": "completed", "status": "completed"',1)
        with self.assertRaisesRegex(ValueError,'Duplicate provider JSON field'):
            OpenAIResponsesExecutor._extract(top_duplicate)

    def test_usage_is_observed_even_if_duplicate_generated_fields_are_rejected(self):
        raw=response('{"post_text":"A","post_text":"B","image_prompt":null}')
        raw['id']='resp_duplicate_output_12345678'
        raw['usage']={'input_tokens':45,'output_tokens':15}
        seen=[]
        executor=OpenAIResponsesExecutor(
            transport=lambda payload:raw,
            usage_observer=lambda **kwargs:seen.append(kwargs))
        with self.assertRaisesRegex(ValueError,'Duplicate provider JSON field'):
            executor(request=request(),max_output_tokens=250)
        self.assertEqual(len(seen),1)
        self.assertEqual(seen[0]['tenant_id'],'shop')

    def test_usage_observer_receives_scoped_provider_counts(self):
        observed=[]
        raw=response()
        raw['id']='resp_example_abcdefghijklmnop'
        raw['usage']={'input_tokens':300,'output_tokens':100}
        executor=OpenAIResponsesExecutor(
            transport=lambda payload:raw,
            usage_observer=lambda **kwargs:observed.append(kwargs))
        executor(request=request(),max_output_tokens=500)
        self.assertEqual(observed[0]['tenant_id'],'shop')
        self.assertEqual(observed[0]['input_tokens'],300)
        self.assertEqual(observed[0]['output_tokens'],100)
        self.assertEqual(observed[0]['usage_ref'],hashlib.sha256(
            raw['id'].encode('ascii')).hexdigest()[:32])
        del raw['usage']
        with self.assertRaises(ValueError):
            executor(request=request(),max_output_tokens=500)
        self.assertEqual(len(observed),1)

    def test_response_id_deduplicates_trusted_usage_estimates(self):
        db=sqlite3.connect(':memory:')
        ledger=AICostLedger(db)
        pricing=AITokenPricing(Decimal('0.15'),Decimal('0.60'))
        raw=response()
        raw['id']='resp_offline_1234567890abcdef'
        raw['usage']={'input_tokens':300,'output_tokens':100}
        executor=OpenAIResponsesExecutor(
            transport=lambda payload:raw,
            usage_observer=lambda **counts:ledger.record_trusted(
                **counts,pricing=pricing,now=103))
        for _ in range(2):
            self.assertEqual(executor(
                request=request(),max_output_tokens=500)['post_text'],
                'Custom tumblers')
        summary=ledger.summary_trusted(tenant_id='shop',subject_id='owner')
        self.assertEqual(summary['events'],1)
        self.assertEqual(summary['estimated_micro_usd'],105)
        # A purported replay of the same response with different usage is
        # rejected, not silently charged again or accepted as a new bill.
        raw['usage']['output_tokens']=101
        with self.assertRaisesRegex(ValueError,
                'reference reused with different data'):
            executor(request=request(),max_output_tokens=500)
        self.assertEqual(ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],1)
        # The same externally returned ID is still scoped independently to
        # different businesses and users.
        raw['usage']['output_tokens']=100
        executor(request={**request(),'tenant_id':'other'},
                 max_output_tokens=500)
        self.assertEqual(ledger.summary_trusted(
            tenant_id='other',subject_id='owner')['events'],1)
        self.assertEqual(ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],1)
        raw['id']='resp_second_1234567890abcdef'
        executor(request=request(),max_output_tokens=500)
        self.assertEqual(ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],2)
        stored=db.execute(
            'SELECT trusted_usage_hash FROM bam_ai_cost_events').fetchall()
        self.assertTrue(all(row[0] is not None for row in stored))
        self.assertNotIn('resp_offline_',str(stored))
        db.close()

    def test_failed_content_still_records_trusted_usage_once(self):
        db=sqlite3.connect(':memory:')
        ledger=AICostLedger(db)
        pricing=AITokenPricing(Decimal('0.20'),Decimal('0.80'))
        raw=response('{"post_text":"Hi","image_prompt":null,"published":true}')
        raw['id']='resp_invalid_copy_1234567890abcdef'
        raw['usage']={'input_tokens':300,'output_tokens':100}
        executor=OpenAIResponsesExecutor(
            transport=lambda payload:raw,
            usage_observer=lambda **usage:ledger.record_trusted(
                **usage,pricing=pricing,now=103))
        for _ in range(2):
            with self.assertRaises(ValueError):
                executor(request=request(),max_output_tokens=500)
        self.assertEqual(ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],1)
        self.assertEqual(ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')[
                'estimated_micro_usd'],140)
        # An explicitly incomplete response with valid usage is also
        # accounted for before being held out of the draft pipeline.
        raw['id']='resp_incomplete_1234567890abcdef'
        raw['status']='incomplete'
        with self.assertRaises(ValueError):
            executor(request=request(),max_output_tokens=500)
        self.assertEqual(ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],2)
        # Missing provider usage is an unresolved accounting event, NOT
        # evidence that no tokens were billed. It still cannot stage copy.
        raw['id']='resp_unknown_usage_1234567890abcdef'
        raw.pop('usage')
        with self.assertRaises(ValueError):
            executor(request=request(),max_output_tokens=500)
        self.assertEqual(ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],2)
        db.close()

    def test_usage_observer_fails_closed_on_missing_or_bad_provider_id(self):
        raw=response()
        raw['usage']={'input_tokens':300,'output_tokens':100}
        observed=[]
        executor=OpenAIResponsesExecutor(
            transport=lambda payload:raw,
            usage_observer=lambda **kwargs:observed.append(kwargs))
        for bad_id in (None,True,100,'x'*100,'resp_bad id',
                       'sk-a-secret-is-not-an-id'):
            if bad_id is None:
                raw.pop('id',None)
            else:
                raw['id']=bad_id
            with self.assertRaises(ValueError):
                executor(request=request(),max_output_tokens=500)
        self.assertEqual(observed,[])

    def test_model_allowlist(self):
        with self.assertRaises(ValueError):
            OpenAIResponsesExecutor(transport=lambda x:None,model='unknown')

if __name__=='__main__':
    unittest.main()
