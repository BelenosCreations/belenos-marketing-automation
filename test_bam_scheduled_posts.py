from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from bam_scheduled_posts import DEFAULT_FACTS, due_slots, generate_caption, initialize, read_facts, run_due


def slots(timestamp, facts=DEFAULT_FACTS):
    return [slot for _, slot in due_slots(datetime.fromisoformat(timestamp), facts)]


class ScheduledPostsTest(unittest.TestCase):
    def test_schedule_opening_cutoff_dst_and_exceptions(self):
        self.assertEqual(slots('2026-11-14T14:59:59+00:00'), [])
        self.assertEqual(slots('2026-11-14T15:00:00+00:00'), ['morning', 'opening'])
        self.assertEqual(slots('2026-11-14T23:30:00+00:00'), ['morning', 'evening'])
        self.assertEqual(slots('2026-11-16T23:30:00+00:00'), ['evening'])
        self.assertEqual(slots('2026-11-17T23:30:00+00:00'), ['morning'])
        self.assertEqual(slots('2026-12-12T15:00:00+00:00'), ['morning'])
        self.assertEqual(slots('2026-12-19T15:00:00+00:00'), ['morning'])
        self.assertEqual(slots('2027-07-03T14:00:00+00:00', {
            **DEFAULT_FACTS, 'hours_confirmed_through': '2027-07-03',
        }), ['morning', 'opening'])

    def test_failure_retry_and_success_are_persisted_per_slot(self):
        with tempfile.TemporaryDirectory() as folder:
            db_path = Path(folder) / 'drafts.sqlite3'
            now = datetime(2026, 11, 14, 15, tzinfo=timezone.utc)
            calls = []
            def generator(context):
                calls.append(context)
                if len(calls) == 1:
                    raise OSError('synthetic model unavailable')
                return context['focus']
            with closing(sqlite3.connect(db_path)) as db:
                initialize(db)
                run_due(db, now, DEFAULT_FACTS, generator)
                run_due(db, now, DEFAULT_FACTS, generator)
                self.assertEqual(len(calls), 2)
            with closing(sqlite3.connect(db_path)) as db:
                run_due(db, now.replace(minute=5), DEFAULT_FACTS, generator)
                run_due(db, now.replace(minute=6), DEFAULT_FACTS, generator)
                rows = db.execute('SELECT slot,caption,error FROM scheduled_post ORDER BY slot').fetchall()
            self.assertEqual(len(calls), 3)
            self.assertEqual(calls[1]['confirmed_hours_today'], 'noon–7 PM')
            self.assertIn(calls[1]['focus'], calls[2]['recent_posts_to_avoid_repeating'])
            self.assertEqual([row[0] for row in rows], ['morning', 'opening'])
            self.assertTrue(all(row[1] and row[2] is None for row in rows))

    def test_model_adapter_uses_loopback_and_validates_output(self):
        with patch('bam_scheduled_posts.http.client.HTTPConnection') as connect:
            connection = connect.return_value
            response = connection.getresponse.return_value
            response.status = 200
            def reply(text):
                response.read.return_value = json.dumps({
                    'done': True, 'done_reason': 'stop',
                    'message': {'content': json.dumps({'post_text': text, 'image_prompt': None})},
                }).encode()
            reply('Stop in today from noon–7 PM.')
            self.assertEqual(generate_caption({'confirmed_hours_today': 'noon–7 PM'}),
                             'Stop in today from noon–7 PM.')
            connect.assert_called_once_with('127.0.0.1', 11434, timeout=120)
            self.assertEqual(connection.request.call_args.args[:2], ('POST', '/api/chat'))
            reply('Come see our bees.')
            with self.assertRaisesRegex(ValueError, 'brand check'):
                generate_caption({})
            reply('We are open 9–5.')
            with self.assertRaisesRegex(ValueError, 'confirmed opening hours'):
                generate_caption({'confirmed_hours_today': 'noon–7 PM'})

    def test_explicit_closure_overrides_hours(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'marketing.json'
            path.write_text(json.dumps({'closed_dates': ['2026-11-14'],
                                        'hours_overrides': {'2026-11-14': '4–7 PM'}}))
            self.assertEqual(slots('2026-11-14T15:00:00+00:00', read_facts(path)), ['morning'])
