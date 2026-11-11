import unittest
from truthguard_risk_signals import scan_risk_signals

class RiskSignalTests(unittest.TestCase):
    def categories(self,text):
        return {s['category'] for s in scan_risk_signals(text)['signals']}

    def test_price(self):
        self.assertIn('price_or_discount',self.categories('Tumblers $18 each'))

    def test_discount(self):
        self.assertIn('price_or_discount',self.categories('25% off today'))

    def test_guarantee(self):
        self.assertIn('guarantee',self.categories('Waterproof forever'))

    def test_availability(self):
        self.assertIn('urgency_or_availability',self.categories('Same-day pickup'))

    def test_hours(self):
        self.assertIn('business_hours',self.categories('Open today'))

    def test_testimonial(self):
        self.assertIn('testimonial',self.categories('Customers love this'))

    def test_safe_sounding_post_not_verified(self):
        result=scan_risk_signals('See our custom creations')
        self.assertEqual(result['signals'],[])
        self.assertFalse(result['extraction_complete'])
        self.assertFalse(result['publishing_enabled'])

    def test_positions_match_source(self):
        text='Our tumblers are $18 today only'
        for signal in scan_risk_signals(text)['signals']:
            self.assertEqual(text[signal['start']:signal['end']],signal['text'])

    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            scan_risk_signals('')

    def test_oversize_rejected(self):
        with self.assertRaises(ValueError):
            scan_risk_signals('x'*20001)

if __name__=='__main__':unittest.main()
