"""Calendar proposals never become executable scheduled posts."""
import sqlite3
import unittest
from datetime import datetime
from access_policy import Principal,Role
from accounts import AccountDirectory
from sessions import SessionStore
from content_requests import ContentRequests
from content_request_service import ContentRequestService
from content_attachments import AttachmentRegistry
from posting_preferences import PostingPreferences
from calendar_proposals import CalendarProposals

def epoch(value):
    return int(datetime.fromisoformat(value).timestamp())

NOW=epoch('2026-11-11T12:00:00+00:00')
FIRST='2026-11-11T15:00:00+00:00'
SECOND='2026-11-11T23:30:00+00:00'

class CalendarProposalTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.directory=AccountDirectory(self.db)
        self.directory.bootstrap_owner('shop','owner')
        self.directory.bootstrap_owner('other','another')
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'creator',Role.CONTENT_CREATOR)
        self.directory.set_member(Principal('owner','shop',Role.OWNER),
                                  'viewer',Role.VIEWER)
        self.sessions=SessionStore(self.db)
        self.owner=self.sessions.issue(Principal('owner','shop',Role.OWNER),
                                       now=NOW-10)
        self.creator=self.sessions.issue(
            Principal('creator','shop',Role.CONTENT_CREATOR),now=NOW-10)
        self.viewer=self.sessions.issue(
            Principal('viewer','shop',Role.VIEWER),now=NOW-10)
        self.other=self.sessions.issue(
            Principal('another','other',Role.OWNER),now=NOW-10)
        self.requests=ContentRequests(self.db)
        self.service=ContentRequestService(
            requests=self.requests,sessions=self.sessions,
            directory=self.directory,
            attachments=AttachmentRegistry(self.db))
        self.prefs=PostingPreferences(
            db=self.db,sessions=self.sessions,directory=self.directory)
        self.prefs.set(token=self.owner,tenant_id='shop',
            mode='manual',timezone='America/New_York',
            manual_times=['10:00','18:30'],now=NOW-5)
        self.calendar=CalendarProposals(
            db=self.db,sessions=self.sessions,directory=self.directory,
            content_service=self.service,preferences=self.prefs)
        self.draft=self.service.create(
            token=self.owner,tenant_id='shop',channel='facebook',
            draft_text='New example product',suggestion='Need image',
            required_items=['image'],now=NOW-4)
    def propose(self,**changes):
        args={'token':self.owner,'now':NOW,
              'request_id':self.draft,
              'expected_revision':1,'utc_at':FIRST,
              'expected_proposal_token':None}
        args.update(changes)
        return self.calendar.propose(**args)

    def test_database_guard_rejects_stale_cached_draft_snapshot(self):
        # A stale in-memory service could return revision 1 even after a
        # second editor has committed revision 2. Only the current SQL
        # row is authoritative when a proposal is saved.
        stale=self.service.get(token=self.owner,tenant_id='shop',
            request_id=self.draft,now=NOW)
        self.service.revise(token=self.owner,tenant_id='shop',
            request_id=self.draft,target='draft_text',
            revised_text='Changed by other editor',
            expected_revision=1,now=NOW+1)
        class StaleRequests:
            @staticmethod
            def get(**kwargs):
                return stale
        class StaleService:
            requests=StaleRequests()
            @staticmethod
            def get(**kwargs):
                return stale
        calendar=CalendarProposals(
            db=self.db,sessions=self.sessions,directory=self.directory,
            content_service=StaleService(),preferences=self.prefs)
        with self.assertRaisesRegex(ValueError,'changed'):
            calendar.propose(token=self.owner,now=NOW+1,
                request_id=self.draft,expected_revision=1,
                utc_at=FIRST,expected_proposal_token=None)
        self.assertEqual(self.db.execute("""SELECT count(*) FROM
            bam_calendar_proposals WHERE tenant_id='shop'""").fetchone()[0],0)

    def test_existing_proposal_requires_exact_version_for_update(self):
        saved=self.propose()
        with self.assertRaisesRegex(ValueError,'changed'):
            self.propose(utc_at=SECOND,
                expected_proposal_token='a'*32)
        actual=self.calendar.list_mine_business(
            token=self.owner,now=NOW)['items'][0]
        self.assertEqual(actual['utc_at'],FIRST)
        self.assertEqual(actual['proposal_token'],saved['proposal_token'])
        moved=self.propose(utc_at=SECOND,
            expected_proposal_token=saved['proposal_token'])
        self.assertNotEqual(moved['proposal_token'],saved['proposal_token'])
        with self.assertRaisesRegex(ValueError,'changed'):
            self.propose(utc_at=FIRST,
                expected_proposal_token=saved['proposal_token'])
        self.assertEqual(self.calendar.list_mine_business(
            token=self.owner,now=NOW)['items'][0]['utc_at'],SECOND)

    def test_propose_is_durable_and_never_schedules(self):
        result=self.propose()
        self.assertEqual(result['status'],'proposal_only')
        self.assertEqual(result['posts_scheduled'],0)
        self.assertFalse(result['publishing_enabled'])
        entries=self.calendar.list_mine_business(token=self.owner,now=NOW)
        self.assertEqual(entries['tenant_id'],'shop')
        self.assertEqual(len(entries['items']),1)
        self.assertEqual(entries['items'][0]['request_id'],
                         self.draft)
        self.assertEqual(entries['items'][0]['utc_at'],FIRST)
        self.assertEqual(entries['items'][0]['local_time'],'10:00')
        self.assertTrue(entries['items'][0]['slot_current'])
        self.assertFalse(entries['items'][0]['content_changed'])
        self.assertEqual(entries['posts_scheduled'],0)
        reopened=CalendarProposals(
            db=self.db,sessions=self.sessions,directory=self.directory,
            content_service=self.service,preferences=self.prefs)
        self.assertEqual(len(reopened.list_mine_business(
            token=self.owner,now=NOW)['items']),1)
        self.assertEqual(len(reopened.list_mine_business(
            token=self.viewer,now=NOW)['items']),1)
        self.assertEqual(self.calendar.list_mine_business(
            token=self.other,now=NOW)['items'],[])

    def test_collision_and_draft_revision_safeguards(self):
        self.propose()
        another=self.service.create(
            token=self.owner,tenant_id='shop',channel='instagram',
            draft_text='Another product',suggestion='Need photo',
            required_items=['image'],now=NOW)
        with self.assertRaises(ValueError):
            self.propose(request_id=another)
        saved=self.calendar.list_mine_business(
            token=self.owner,now=NOW)['items'][0]
        self.assertEqual(self.propose(
            utc_at=SECOND,expected_proposal_token=saved['proposal_token']
            )['status'],'proposal_only')
        self.assertEqual(len(self.calendar.list_mine_business(
            token=self.owner,now=NOW)['items']),1)
        changed=self.service.revise(
            token=self.creator,tenant_id='shop',
            request_id=self.draft,target='draft_text',
            revised_text='Updated product copy',expected_revision=1,now=NOW+1)
        self.assertEqual(changed['revision'],2)
        item=self.calendar.list_mine_business(
            token=self.owner,now=NOW+1)['items'][0]
        self.assertTrue(item['content_changed'])
        with self.assertRaises(ValueError):
            self.propose(utc_at=FIRST,now=NOW+1)
        latest=self.calendar.list_mine_business(
            token=self.owner,now=NOW+1)['items'][0]
        restored=self.propose(utc_at=FIRST,now=NOW+1,
            expected_revision=2,
            expected_proposal_token=latest['proposal_token'])
        self.assertEqual(restored['posts_scheduled'],0)
        current=self.calendar.list_mine_business(
            token=self.owner,now=NOW+1)['items'][0]
        self.assertFalse(current['content_changed'])

    def test_configured_time_changes_invalidate_old_proposal(self):
        self.propose()
        self.prefs.set(token=self.owner,tenant_id='shop',
            mode='manual',timezone='America/New_York',
            manual_times=['18:30'],now=NOW+1)
        entry=self.calendar.list_mine_business(
            token=self.owner,now=NOW+2)['items'][0]
        self.assertFalse(entry['slot_current'])
        self.assertTrue(entry['publishing_enabled'] is False)

    def test_role_tenant_dst_and_no_arbitrary_clock(self):
        for token in (self.viewer,self.other,'no-session'):
            with self.assertRaises((PermissionError,KeyError)):
                self.propose(token=token)
        for clock in ('2026-11-11T12:00:00+00:00','bad',
                      '2026-11-11T15:00:00Z',
                      '2026-11-02T15:00:00+00:00'):
            with self.assertRaises(ValueError):
                self.propose(utc_at=clock)
        with self.assertRaises(ValueError):
            self.propose(expected_revision=True)
        self.prefs.set(token=self.owner,tenant_id='shop',
            mode='smart',timezone='America/New_York',
            manual_times=[],now=NOW+1)
        with self.assertRaises(ValueError):
            self.propose(now=NOW+2)

    def test_discard_is_private_idempotent_and_not_delete_content(self):
        self.propose()
        with self.assertRaises(PermissionError):
            self.calendar.discard(token=self.viewer,now=NOW,
                                  request_id=self.draft,
                                  expected_proposal_token='a'*32)
        current=self.calendar.list_mine_business(
            token=self.owner,now=NOW)['items'][0]
        version=current['proposal_token']
        removed=self.calendar.discard(token=self.creator,now=NOW,
            request_id=self.draft,expected_proposal_token=version)
        self.assertEqual(removed['removed'],1)
        self.assertEqual(removed['posts_scheduled'],0)
        with self.assertRaises(ValueError):
            self.calendar.discard(token=self.owner,now=NOW,
                request_id=self.draft,expected_proposal_token=version)
        self.assertIsNotNone(self.requests.get(
            tenant_id='shop',request_id=self.draft))

    def test_calendar_conflict_versions_prevent_stale_reassignment(self):
        original=self.propose()
        first_version=original['proposal_token']
        moved=self.propose(utc_at=SECOND,
            expected_proposal_token=first_version)
        self.assertNotEqual(first_version,moved['proposal_token'])
        with self.assertRaises(ValueError):
            self.propose(utc_at=FIRST,
                expected_proposal_token=first_version)
        with self.assertRaises(ValueError):
            self.calendar.discard(token=self.owner,now=NOW,
                request_id=self.draft,
                expected_proposal_token=first_version)
        self.assertEqual(self.calendar.discard(
            token=self.owner,now=NOW,request_id=self.draft,
            expected_proposal_token=moved['proposal_token'])['removed'],1)
        recreated=self.propose()
        self.assertNotEqual(recreated['proposal_token'],
                            first_version)
        with self.assertRaises(ValueError):
            self.calendar.discard(token=self.owner,now=NOW,
                request_id=self.draft,
                expected_proposal_token=first_version)
        self.assertEqual(len(self.calendar.list_mine_business(
            token=self.owner,now=NOW)['items']),1)

    def test_existing_sqlite_calendar_rows_migrate_without_loss(self):
        legacy=sqlite3.connect(':memory:')
        legacy.execute("""CREATE TABLE bam_calendar_proposals(
            tenant_id TEXT NOT NULL,request_id TEXT NOT NULL,
            draft_revision INTEGER NOT NULL,utc_at TEXT NOT NULL,
            local_date TEXT NOT NULL,local_time TEXT NOT NULL,
            timezone TEXT NOT NULL,updated_at INTEGER NOT NULL,
            updated_by TEXT NOT NULL,
            PRIMARY KEY(tenant_id,request_id),UNIQUE(tenant_id,utc_at))""")
        legacy.execute("""INSERT INTO bam_calendar_proposals VALUES(
            ?,?,?,?,?,?,?,?,?)""",('shop',self.draft,1,FIRST,
            '2026-11-11','10:00','America/New_York',NOW,'owner'))
        legacy.commit()
        CalendarProposals(db=legacy,sessions=self.sessions,
            directory=self.directory,content_service=self.service,
            preferences=self.prefs)
        first=legacy.execute(
            'SELECT proposal_token FROM bam_calendar_proposals').fetchone()[0]
        self.assertEqual(len(first),32)
        CalendarProposals(db=legacy,sessions=self.sessions,
            directory=self.directory,content_service=self.service,
            preferences=self.prefs)
        self.assertEqual(legacy.execute(
            'SELECT proposal_token FROM bam_calendar_proposals').fetchone()[0],
            first)
        legacy.close()

    def test_suggest_unassigned_is_read_only_and_collision_free(self):
        second=self.service.create(
            token=self.owner,tenant_id='shop',channel='instagram',
            draft_text='Second product preview',suggestion='Need image',
            required_items=['image'],priority=5,now=NOW-1)
        preview=self.calendar.suggest_unassigned(
            token=self.owner,now=NOW)
        self.assertEqual(preview['status'],'suggestion_preview_only')
        self.assertEqual(preview['preference_status'],'manual_preview')
        self.assertEqual(preview['unassigned_held_count'],2)
        self.assertEqual(preview['items'][0]['request_id'],second)
        self.assertEqual(preview['items'][0]['utc_at'],FIRST)
        self.assertEqual(preview['items'][1]['request_id'],self.draft)
        self.assertEqual(preview['items'][1]['utc_at'],SECOND)
        self.assertFalse(preview['publishing_enabled'])
        self.assertEqual(preview['posts_scheduled'],0)
        self.assertEqual(self.db.execute(
            'SELECT count(*) FROM bam_calendar_proposals').fetchone()[0],0)
        self.propose()
        after=self.calendar.suggest_unassigned(
            token=self.creator,now=NOW)
        self.assertEqual(after['unassigned_held_count'],1)
        self.assertEqual(len(after['items']),1)
        self.assertEqual(after['items'][0]['request_id'],second)
        self.assertEqual(after['items'][0]['utc_at'],SECOND)
        self.assertEqual(len(self.calendar.suggest_unassigned(
            token=self.viewer,now=NOW)['items']),1)
        self.assertEqual(self.calendar.suggest_unassigned(
            token=self.other,now=NOW)['items'],[])
        self.assertEqual(self.db.execute(
            'SELECT count(*) FROM bam_calendar_proposals').fetchone()[0],1)

    def test_suggestions_exclude_postponed_and_are_not_smart_claims(self):
        self.requests.set_hold(tenant_id='shop',request_id=self.draft,
                               status='postponed',now=NOW)
        first=self.calendar.suggest_unassigned(token=self.owner,now=NOW)
        self.assertEqual(first['unassigned_held_count'],0)
        self.assertEqual(first['items'],[])
        self.prefs.set(token=self.owner,tenant_id='shop',
            mode='smart',timezone='America/New_York',
            manual_times=[],now=NOW+1)
        smart=self.calendar.suggest_unassigned(
            token=self.owner,now=NOW+2)
        self.assertEqual(smart['preference_status'],'needs_audience_data')
        self.assertEqual(smart['items'],[])
        self.assertEqual(smart['available_slot_count'],0)
        with self.assertRaises(PermissionError):
            self.calendar.suggest_unassigned(token='fake',now=NOW)


if __name__=='__main__':
    unittest.main()
