import unittest
from dashboard_cards import build_dashboard_cards

class DashboardCardTests(unittest.TestCase):
    def test_counts_only_authorized_held_requests(self):
        overview={'tenant_id':'a','pending_content_requests':[
            {'status':'needs_content'},{'status':'needs_content'},
            {'status':'ready_for_review'}],'social_connections':[]}
        cards=build_dashboard_cards(overview)['cards']
        self.assertEqual(cards[1]['value'],1)
        self.assertEqual(cards[2]['value'],2)
        self.assertEqual(cards[3]['value'],0)

    def test_unknown_schedule_is_not_fake_zero(self):
        cards=build_dashboard_cards({'tenant_id':'a',
            'pending_content_requests':[],'social_connections':[]})['cards']
        self.assertIsNone(cards[0]['value'])
        self.assertEqual(cards[0]['availability'],'not_connected')

    def test_restricted_connection_count_is_not_exposed(self):
        cards=build_dashboard_cards({'tenant_id':'a',
            'pending_content_requests':[],'social_connections':None})['cards']
        self.assertIsNone(cards[3]['value'])
        self.assertEqual(cards[3]['availability'],'restricted')

    def test_publishing_disabled(self):
        result=build_dashboard_cards({'tenant_id':'a',
            'pending_content_requests':[],'social_connections':[]})
        self.assertFalse(result['publishing_enabled'])

    def test_invalid_overview_rejected(self):
        with self.assertRaises(ValueError):
            build_dashboard_cards({'tenant_id':'a','pending_content_requests':None})

if __name__=='__main__':unittest.main()
