"""Ephemeral SQLite backup/restore drills for BAM's offline Alpha state.

These tests run only in temporary directories. The database backup format is
NOT encrypted and MUST NOT be used as a production backup/export mechanism.
Real hosting needs encrypted backups, retention, access control and restore
rehearsals under the approved infrastructure before private beta.
"""
import os
import sqlite3
import tempfile
import unittest

from access_policy import Principal,Role
from bam_offline_gateway import BAMOfflineGateway


class OfflineSQLiteRestoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='bam-restore-test-')
        self.live=os.path.join(self.tmp.name,'live.sqlite3')
        self.snap=os.path.join(self.tmp.name,'snapshot.sqlite3')
        self.restored=os.path.join(self.tmp.name,'restored.sqlite3')
        self.db=sqlite3.connect(self.live)
        self.app=BAMOfflineGateway(self.db,enabled=True,clock=lambda:101)
        self.owner_id=self.app.identities.register_password(
            email='backup-owner@example.com',
            password='private backup test password',now=100)
        self.worker_id=self.app.identities.register_password(
            email='backup-worker@example.com',
            password='worker backup test password',now=100)
        for subject in (self.owner_id,self.worker_id):
            self.app.identities.set_email_verified_trusted(
                subject_id=subject,verified=True)
        self.app.directory.bootstrap_owner('shop',self.owner_id)
        self.app.directory.bootstrap_owner('other','other-owner')
        self.app.directory.set_member(
            Principal(self.owner_id,'shop',Role.OWNER),
            self.worker_id,Role.CONTENT_CREATOR)
        self.app.directory.set_member(
            Principal('other-owner','other',Role.OWNER),
            self.worker_id,Role.VIEWER)
        self.app.curation.create_profile(
            'shop','Backup Shop','retail',['custom projects'])
        self.app.curation.create_profile(
            'other','Separate Firm','services',['maintenance'])
        self.owner_token=self.app.sessions.issue(
            Principal(self.owner_id,'shop',Role.OWNER),now=100)
        self.worker_shop=self.app.sessions.issue(
            Principal(self.worker_id,'shop',Role.CONTENT_CREATOR),now=100)
        self.worker_other=self.app.sessions.issue(
            Principal(self.worker_id,'other',Role.VIEWER),now=100)
        self.draft_shop=self.app.requests.create(
            tenant_id='shop',channel='facebook',
            draft_text='Original shop draft',suggestion='Add private image',
            required_items=['image'],now=100)
        self.draft_other=self.app.requests.create(
            tenant_id='other',channel='facebook',
            draft_text='Unrelated firm draft',suggestion='Confirm permission',
            required_items=['permission'],now=100)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def snapshot(self):
        # SQLite's online backup API reads a consistent committed database,
        # unlike a naive file copy made while SQLite is writing.
        output=sqlite3.connect(self.snap)
        try:
            self.db.backup(output)
            self.assertEqual(output.execute(
                'PRAGMA integrity_check').fetchone()[0],'ok')
        finally:
            output.close()

    def restore(self):
        src=sqlite3.connect(self.snap)
        dest=sqlite3.connect(self.restored)
        try:
            src.backup(dest)
        finally:
            src.close()
        self.assertEqual(dest.execute(
            'PRAGMA integrity_check').fetchone()[0],'ok')
        return dest,BAMOfflineGateway(dest,enabled=True,clock=lambda:101)

    def test_snapshot_restores_business_isolation_and_original_draft_state(self):
        self.snapshot()
        self.app.requests.revise(
            tenant_id='shop',request_id=self.draft_shop,
            target='draft_text',revised_text='After backup change',
            expected_revision=1,now=101)
        self.app.directory.set_member(
            Principal(self.owner_id,'shop',Role.OWNER),
            self.worker_id,Role.VIEWER)
        self.assertEqual(self.app.requests.get(
            tenant_id='shop',request_id=self.draft_shop)['revision'],2)
        saved,restored=self.restore()
        try:
            old=restored.requests.get(
                tenant_id='shop',request_id=self.draft_shop)
            self.assertEqual(old['revision'],1)
            self.assertEqual(old['draft_text'],'Original shop draft')
            self.assertIsNone(restored.requests.get(
                tenant_id='other',request_id=self.draft_shop))
            self.assertEqual(restored.requests.get(
                tenant_id='other',request_id=self.draft_other)['draft_text'],
                'Unrelated firm draft')
            self.assertEqual(restored.directory.resolve(
                'shop',self.worker_id).role,Role.CONTENT_CREATOR)
            self.assertIsNotNone(restored.sessions.resolve_current(
                self.worker_shop,directory=restored.directory,now=101))
            self.assertIsNotNone(restored.sessions.resolve_current(
                self.worker_other,directory=restored.directory,now=101))
            self.assertIsNone(restored.sessions.resolve_current(
                self.owner_token+'tampered',
                directory=restored.directory,now=101))
            stored=saved.execute("""SELECT token_hash FROM sessions
                WHERE tenant_id='shop' AND subject_id=? LIMIT 1""",
                (self.owner_id,)).fetchone()[0]
            self.assertNotEqual(stored,self.owner_token)
            self.assertEqual(len(stored),64)
        finally:
            saved.close()

    def test_snapshot_restores_revocation_and_audit_without_cross_business_leak(self):
        changed=self.app.team_admin.change_current(
            token=self.owner_token,member_id=self.worker_id,
            action='deactivate',expected_revision=1,now=101)
        self.assertEqual(changed['sessions_revoked'],1)
        self.snapshot()
        restored_db,restored=self.restore()
        try:
            self.assertIsNone(restored.directory.resolve(
                'shop',self.worker_id))
            self.assertIsNone(restored.sessions.resolve_current(
                self.worker_shop,directory=restored.directory,now=101))
            self.assertIsNotNone(restored.sessions.resolve_current(
                self.worker_other,directory=restored.directory,now=101))
            activity=restored.team_admin.activity_current(
                token=self.owner_token,now=101)
            self.assertEqual(activity['events'][0]['action'],'deactivate')
            self.assertEqual(activity['events'][0]['actor_id'],self.owner_id)
            self.assertEqual(len(activity['events']),1)
            self.assertNotIn('backup-worker@example.com',str(activity))
            self.assertEqual(restored_db.execute(
                'PRAGMA integrity_check').fetchone()[0],'ok')
        finally:
            restored_db.close()


if __name__=='__main__':
    unittest.main()
