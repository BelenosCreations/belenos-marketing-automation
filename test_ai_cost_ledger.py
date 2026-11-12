import sqlite3
import os
import tempfile
import threading
import unittest
from decimal import Decimal
from ai_cost_ledger import (AICostLedger,AITokenPricing,
                            conservative_request_cost_micro_usd)

class AICostLedgerTests(unittest.TestCase):
    def setUp(self):
        self.ledger=AICostLedger(sqlite3.connect(':memory:'))
        self.pricing=AITokenPricing(Decimal('0.15'),Decimal('0.60'))

    def test_explicit_pricing_and_tenant_scope(self):
        result=self.ledger.record_trusted(tenant_id='shop',
            subject_id='owner',model='gpt-4.1-mini',
            input_tokens=1000000,output_tokens=500000,
            pricing=self.pricing,now=100)
        self.assertEqual(result['estimated_micro_usd'],450000)
        self.assertFalse(result['actual_billing_verified'])
        first=self.ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')
        self.assertEqual(first['events'],1)
        self.assertEqual(first['estimated_micro_usd'],450000)
        other=self.ledger.summary_trusted(
            tenant_id='other',subject_id='owner')
        self.assertEqual(other['events'],0)
        self.assertEqual(other['estimated_micro_usd'],0)

    def test_conservative_cost_projection_requires_explicit_pricing(self):
        result=conservative_request_cost_micro_usd(
            pricing=self.pricing,max_input_tokens=10000,
            max_output_tokens=500)
        self.assertEqual(result,1800)
        # Fractional micro-USD is rounded upward to reserve conservatively,
        # not rounded down as provider estimates may be.
        self.assertEqual(conservative_request_cost_micro_usd(
            pricing=self.pricing,max_input_tokens=1,
            max_output_tokens=1),1)
        for bad in (0,-1,True,1.5,'100',1000001):
            with self.assertRaises(ValueError):
                conservative_request_cost_micro_usd(
                    pricing=self.pricing,max_input_tokens=bad,
                    max_output_tokens=100)
        for bad in (0,-1,True,16385):
            with self.assertRaises(ValueError):
                conservative_request_cost_micro_usd(
                    pricing=self.pricing,max_input_tokens=100,
                    max_output_tokens=bad)
        with self.assertRaises(ValueError):
            conservative_request_cost_micro_usd(
                pricing={'input':Decimal('0.15')},
                max_input_tokens=100,max_output_tokens=100)

    def test_trusted_usage_reference_is_idempotent_and_scope_private(self):
        kwargs=dict(tenant_id='shop',subject_id='owner',model='model-a',
            input_tokens=1200,output_tokens=200,pricing=self.pricing,
            now=100,usage_ref='a'*32)
        first=self.ledger.record_trusted(**kwargs)
        repeat=self.ledger.record_trusted(**{**kwargs,'now':101})
        self.assertFalse(first['replayed'])
        self.assertTrue(repeat['replayed'])
        self.assertEqual(repeat['event_id'],first['event_id'])
        self.assertEqual(self.ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],1)
        for altered in ({'input_tokens':1201},{'model':'model-b'},
                        {'pricing':AITokenPricing(
                            Decimal('0.16'),Decimal('0.60'))}):
            with self.assertRaisesRegex(ValueError,
                    'reference reused with different data'):
                self.ledger.record_trusted(**{**kwargs,**altered})
        self.assertEqual(self.ledger.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],1)
        separate=self.ledger.record_trusted(**{
            **kwargs,'tenant_id':'other'})
        self.assertNotEqual(separate['event_id'],first['event_id'])
        self.assertEqual(self.ledger.summary_trusted(
            tenant_id='other',subject_id='owner')['events'],1)
        for bad_ref in (True,123,'sk-secret','A'*32,'a'*31):
            with self.assertRaises(ValueError):
                self.ledger.record_trusted(**{**kwargs,'usage_ref':bad_ref})

    def test_old_sqlite_cost_events_migrate_without_inventing_refs(self):
        db=sqlite3.connect(':memory:')
        db.execute("""CREATE TABLE bam_ai_cost_events(
            event_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,subject_id TEXT NOT NULL,
            provider TEXT NOT NULL,model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,output_tokens INTEGER NOT NULL,
            estimated_micro_usd INTEGER NOT NULL,
            occurred_at INTEGER NOT NULL)""")
        db.execute("INSERT INTO bam_ai_cost_events VALUES(?,?,?,?,?,?,?,?,?)",
            ('d'*32,'shop','owner','openai','model-a',100,20,100,99))
        db.commit()
        migrated=AICostLedger(db)
        self.assertEqual(migrated.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],1)
        self.assertEqual(db.execute("""SELECT trusted_usage_hash FROM
            bam_ai_cost_events WHERE event_id=?""",('d'*32,)
            ).fetchone()[0],None)
        first=migrated.record_trusted(tenant_id='shop',subject_id='owner',
            model='model-a',input_tokens=100,output_tokens=20,
            pricing=self.pricing,now=100,usage_ref='e'*32)
        self.assertFalse(first['replayed'])
        repeated=migrated.record_trusted(tenant_id='shop',subject_id='owner',
            model='model-a',input_tokens=100,output_tokens=20,
            pricing=self.pricing,now=101,usage_ref='e'*32)
        self.assertTrue(repeated['replayed'])
        self.assertEqual(migrated.summary_trusted(
            tenant_id='shop',subject_id='owner')['events'],2)
        db.close()

    def test_independent_sqlite_connections_deduplicate_same_usage(self):
        with tempfile.TemporaryDirectory(prefix='bam-ai-ledger-') as tmp:
            path=os.path.join(tmp,'ledger.sqlite3')
            one=sqlite3.connect(path,timeout=10,check_same_thread=False)
            two=sqlite3.connect(path,timeout=10,check_same_thread=False)
            try:
                ledgers=[AICostLedger(one),AICostLedger(two)]
                barrier=threading.Barrier(3)
                outputs=[]
                def record(ledger):
                    try:
                        barrier.wait(timeout=8)
                        outputs.append(ledger.record_trusted(
                            tenant_id='shop',subject_id='owner',
                            model='model-a',input_tokens=100,
                            output_tokens=20,pricing=self.pricing,
                            now=100,usage_ref='f'*32))
                    except Exception as exc:
                        outputs.append(exc)
                workers=[threading.Thread(target=record,args=(ledger,),
                         daemon=True) for ledger in ledgers]
                for thread in workers:thread.start()
                barrier.wait(timeout=8)
                for thread in workers:thread.join(timeout=12)
                self.assertTrue(all(not t.is_alive() for t in workers))
                self.assertEqual(len(outputs),2)
                self.assertTrue(all(type(x) is dict for x in outputs),outputs)
                self.assertEqual(sum(x['replayed'] for x in outputs),1)
                self.assertEqual(ledgers[0].summary_trusted(
                    tenant_id='shop',subject_id='owner')['events'],1)
            finally:
                two.close()
                one.close()

    def test_invalid_usage_and_pricing_rejected(self):
        with self.assertRaises(ValueError):
            AITokenPricing(Decimal('-1'),Decimal('0.5'))
        with self.assertRaises(ValueError):
            AITokenPricing(Decimal('NaN'),Decimal('0.5'))
        for count in (-1,1.5,True):
            with self.assertRaises(ValueError):
                self.ledger.record_trusted(tenant_id='shop',
                    subject_id='owner',model='gpt-4.1-mini',
                    input_tokens=count,output_tokens=2,
                    pricing=self.pricing,now=100)

if __name__=='__main__':
    unittest.main()
