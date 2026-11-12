import sqlite3
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
