"""Independent SQLite-client races for non-executable BAM calendar proposals.

This verifies proposal safety only. No scheduled jobs or social provider APIs
are present, and the test databases are deleted after the run.
"""
import os
import sqlite3
import tempfile
import threading
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
SLOT='2026-11-11T15:00:00+00:00'


class TwoClientCalendarProposalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='bam-calendar-race-')
        self.path=os.path.join(self.tmp.name,'calendar.sqlite3')
        self.db1=sqlite3.connect(self.path,timeout=10,check_same_thread=False)
        self.directory1=AccountDirectory(self.db1)
        self.directory1.bootstrap_owner('shop','owner')
        self.sessions1=SessionStore(self.db1)
        self.owner=self.sessions1.issue(
            Principal('owner','shop',Role.OWNER),now=NOW-10)
        requests1=ContentRequests(self.db1)
        self.service1=ContentRequestService(
            requests=requests1,sessions=self.sessions1,
            directory=self.directory1,
            attachments=AttachmentRegistry(self.db1))
        prefs1=PostingPreferences(
            db=self.db1,sessions=self.sessions1,
            directory=self.directory1)
        prefs1.set(token=self.owner,tenant_id='shop',
            mode='manual',timezone='America/New_York',
            manual_times=['10:00','18:30'],now=NOW-5)
        self.first=CalendarProposals(
            db=self.db1,sessions=self.sessions1,
            directory=self.directory1,content_service=self.service1,
            preferences=prefs1)
        self.draft=self.service1.create(
            token=self.owner,tenant_id='shop',channel='facebook',
            draft_text='Original custom product announcement',
            suggestion='Add cleared original media',
            required_items=['photo'],now=NOW-4)
        self.db2=sqlite3.connect(self.path,timeout=10,check_same_thread=False)
        directory2=AccountDirectory(self.db2)
        sessions2=SessionStore(self.db2)
        requests2=ContentRequests(self.db2)
        service2=ContentRequestService(
            requests=requests2,sessions=sessions2,directory=directory2,
            attachments=AttachmentRegistry(self.db2))
        prefs2=PostingPreferences(
            db=self.db2,sessions=sessions2,directory=directory2)
        self.second=CalendarProposals(
            db=self.db2,sessions=sessions2,directory=directory2,
            content_service=service2,preferences=prefs2)

    def tearDown(self):
        self.db2.close()
        self.db1.close()
        self.tmp.cleanup()

    def race(self,functions):
        barrier=threading.Barrier(3)
        results=[None]*len(functions)
        def worker(index,fn):
            try:
                barrier.wait(timeout=8)
                results[index]=('ok',fn())
            except Exception as exc:
                results[index]=('error',exc)
        threads=[threading.Thread(target=worker,
                    args=(i,fn),daemon=True)
                 for i,fn in enumerate(functions)]
        for thread in threads:
            thread.start()
        barrier.wait(timeout=8)
        for thread in threads:
            thread.join(timeout=12)
        self.assertTrue(all(not thread.is_alive() for thread in threads),
            'Offline calendar race timed out')
        return results

    def propose(self,calendar,draft):
        return calendar.propose(
            token=self.owner,now=NOW,request_id=draft,
            expected_revision=1,utc_at=SLOT,
            expected_proposal_token=None)

    def test_simultaneous_first_assignment_creates_one_proposal(self):
        results=self.race([
            lambda:self.propose(self.first,self.draft),
            lambda:self.propose(self.second,self.draft)
        ])
        self.assertEqual(sum(k=='ok' for k,_ in results),1,results)
        self.assertEqual(sum(k=='error' and isinstance(v,ValueError)
                             for k,v in results),1,results)
        self.assertEqual(self.db1.execute("""SELECT count(*) FROM
            bam_calendar_proposals WHERE tenant_id='shop'""").fetchone()[0],1)
        for k,result in results:
            if k=='ok':
                self.assertEqual(result['posts_scheduled'],0)
                self.assertFalse(result['publishing_enabled'])

    def test_distinct_drafts_cannot_share_same_manual_slot(self):
        second_draft=self.service1.create(
            token=self.owner,tenant_id='shop',channel='instagram',
            draft_text='Independent product photo',
            suggestion='Attach verified image',
            required_items=['photo'],now=NOW-3)
        results=self.race([
            lambda:self.propose(self.first,self.draft),
            lambda:self.propose(self.second,second_draft)
        ])
        self.assertEqual(sum(k=='ok' for k,_ in results),1,results)
        self.assertEqual(sum(k=='error' and isinstance(v,ValueError)
                             for k,v in results),1,results)
        rows=self.db2.execute("""SELECT request_id,utc_at FROM
            bam_calendar_proposals WHERE tenant_id='shop'""").fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][1],SLOT)
        self.assertIn(rows[0][0],(self.draft,second_draft))


if __name__=='__main__':
    unittest.main()
