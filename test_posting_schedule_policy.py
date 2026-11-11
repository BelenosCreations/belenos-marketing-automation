import unittest
from datetime import datetime, timezone
from posting_schedule_policy import SchedulePreferences,PostContext,SchedulingPlanner

class SchedulingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.planner=SchedulingPlanner()
        self.start=datetime(2026,11,10,15,0,tzinfo=timezone.utc)
        self.post=PostContext(subject='New product',audience='local families',
                              platform='facebook',ready_for_review=True,approved=True)
        self.manual=SchedulePreferences(mode='manual',timezone_name='America/New_York',
            manual_weekly={1:['11:17'],3:['12:00']})
        self.smart=SchedulePreferences(mode='smart',timezone_name='America/New_York',
            manual_weekly={})

    def test_manual_exact_minutes(self):
        result=self.planner.suggest(prefs=self.manual,post=self.post,start_utc=self.start)
        self.assertEqual(result['scheduled_at'],'2026-11-10T11:17:00-05:00')

    def test_manual_no_automatic_move(self):
        result=self.planner.suggest(prefs=self.manual,post=self.post,start_utc=self.start,
            engagement_by_hour={19:1000})
        self.assertEqual(result['scheduled_at'],'2026-11-10T11:17:00-05:00')

    def test_manual_next_week_if_slot_passed(self):
        result=self.planner.suggest(prefs=self.manual,post=self.post,
            start_utc=datetime(2026,11,10,17,0,tzinfo=timezone.utc))
        self.assertEqual(result['scheduled_at'],'2026-11-12T12:00:00-05:00')

    def test_smart_proposes_not_publishes(self):
        result=self.planner.suggest(prefs=self.smart,post=self.post,start_utc=self.start)
        self.assertEqual(result['status'],'proposed')
        self.assertIn('Smart suggestion',result['reason'])

    def test_smart_uses_supplied_engagement(self):
        result=self.planner.suggest(prefs=self.smart,post=self.post,
            start_utc=self.start,engagement_by_hour={20:50})
        self.assertIn('T20:00:00',result['scheduled_at'])

    def test_explicit_override_wins(self):
        target=datetime(2026,11,11,7,45,tzinfo=timezone.utc)
        result=self.planner.suggest(prefs=self.smart,post=self.post,
            start_utc=self.start,override_local=target)
        self.assertEqual(result['scheduled_at'],'2026-11-11T02:45:00-05:00')

    def test_missing_content_holds(self):
        incomplete=PostContext('product','families','facebook',False,True)
        result=self.planner.suggest(prefs=self.manual,post=incomplete,
            start_utc=self.start)
        self.assertEqual(result['status'],'held')
        self.assertIsNone(result['scheduled_at'])

    def test_unapproved_holds_even_with_override(self):
        unapproved=PostContext('product','families','facebook',True,False)
        result=self.planner.suggest(prefs=self.smart,post=unapproved,
            start_utc=self.start,override_local=datetime(2026,11,11,tzinfo=timezone.utc))
        self.assertEqual(result['status'],'held')

    def test_invalid_manual_time(self):
        with self.assertRaises(ValueError):
            SchedulePreferences('manual','America/New_York',{0:['25:00']})

    def test_no_manual_slot(self):
        empty=SchedulePreferences('manual','America/New_York',{})
        self.assertEqual(self.planner.suggest(prefs=empty,post=self.post,
            start_utc=self.start)['status'],'no_slot')

    def test_invalid_engagement(self):
        with self.assertRaises(ValueError):
            self.planner.suggest(prefs=self.smart,post=self.post,
                start_utc=self.start,engagement_by_hour={12:float('nan')})

    def test_naive_start_rejected(self):
        with self.assertRaises(ValueError):
            self.planner.suggest(prefs=self.smart,post=self.post,
                start_utc=datetime(2026,11,10))

if __name__=='__main__':unittest.main()
