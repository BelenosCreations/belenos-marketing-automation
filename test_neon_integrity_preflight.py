"""Privacy-safe migration preflight checks for local synthetic BAM data."""
import sqlite3
import unittest
from bam_offline_gateway import BAMOfflineGateway
from access_policy import Principal,Role
from neon_integrity_preflight import (
    inspect_offline_integrity,require_clean_offline_fixture)


class NeonIntegrityPreflightTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.app=BAMOfflineGateway(self.db,enabled=True,clock=lambda:101)
        self.subject=self.app.identities.register_password(
            email='fixture@example.com',password='test password phrase 123',
            now=100)
        self.app.identities.set_email_verified_trusted(
            subject_id=self.subject,verified=True)
        self.app.directory.bootstrap_owner('shop',self.subject)
        self.token=self.app.sessions.issue(
            Principal(self.subject,'shop',Role.OWNER),now=100)
        self.rid=self.app.requests.create(tenant_id='shop',channel='facebook',
            draft_text='fixture secret advertising copy',
            suggestion='supply photo',required_items=['image'],now=100)
    def tearDown(self):
        self.db.close()

    def test_clean_fixture_reports_no_issues_and_never_claims_ready(self):
        changes=self.db.total_changes
        report=require_clean_offline_fixture(self.db)
        self.assertEqual(report['issue_count_total'],0)
        self.assertEqual(report['foreign_key_issue_count'],0)
        self.assertTrue(report['integrity_check_ok'])
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['postgres_connection_attempted'])
        self.assertFalse(report['secrets_exported'])
        self.assertFalse(report['publishing_enabled'])
        self.assertEqual(self.db.total_changes,changes)
        for private in (self.token,self.subject,'fixture@example.com',
                        'fixture secret advertising copy','shop'):
            self.assertNotIn(private,str(report))

    def test_cross_business_orphan_and_dangling_session_are_counted(self):
        with self.db:
            self.db.execute("""INSERT INTO members
                (tenant_id,subject_id,role,active,revision)
                VALUES ('other','ghost','viewer',1,1)""")
            self.db.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at,revoked_at)
                VALUES (?,?,?,?,?,NULL)""",
                ('X'*64,'ghost','other','viewer',3600))
            self.db.execute("""INSERT INTO bam_calendar_proposals
                (tenant_id,request_id,draft_revision,utc_at,
                 local_date,local_time,timezone,updated_at,updated_by,
                 proposal_token)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                ('shop','a'*32,1,'2026-11-12T14:00:00+00:00',
                 '2026-11-12','09:00','America/New_York',100,self.subject,'b'*32))
        report=inspect_offline_integrity(self.db)
        counts=report['aggregate_issue_counts']
        self.assertEqual(counts['orphan_memberships'],1)
        self.assertEqual(counts['orphan_sessions'],1)
        self.assertEqual(counts['orphan_calendar_proposals'],1)
        self.assertEqual(counts['invalid_session_token_digests'],1)
        self.assertTrue(report['migration_fixture_issues_found'])
        with self.assertRaises(ValueError):
            require_clean_offline_fixture(self.db)
        self.assertNotIn('ghost',str(report))
        self.assertNotIn(self.subject,str(report))

    def test_detects_unverified_stale_permissions_and_disabled_identity(self):
        # Regression for situations a data migration must not silently carry
        # forward as usable sessions.
        with self.db:
            self.db.execute("""UPDATE members SET role='viewer'
                WHERE tenant_id='shop' AND subject_id=?""",(self.subject,))
            self.db.execute("""UPDATE bam_identities SET active=0
                WHERE subject_id=?""",(self.subject,))
        counts=inspect_offline_integrity(self.db)['aggregate_issue_counts']
        self.assertEqual(counts[
            'stale_or_revoked_memberships_with_live_sessions'],1)
        self.assertEqual(counts['disabled_identities_with_live_sessions'],1)

    def test_detects_casefold_duplicate_and_bad_role(self):
        with self.db:
            self.db.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,?,?,?)""",
                ('testcaseA','Mismatch@EXAMPLE.com',1,1,100))
            self.db.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (?,?,?,?,?)""",
                ('testcaseB','mismatch@example.COM',1,1,100))
            self.db.execute("""UPDATE members SET role='invalid'
                WHERE tenant_id='shop' AND subject_id=?""",(self.subject,))
        counts=inspect_offline_integrity(self.db)['aggregate_issue_counts']
        self.assertEqual(counts['duplicate_casefold_emails'],1)
        self.assertEqual(counts['invalid_active_member_roles'],1)

    def test_invalid_handle_refused(self):
        with self.assertRaises(TypeError):
            inspect_offline_integrity(object())


    def test_valid_private_media_metadata_keeps_preflight_clean(self):
        aid=self.app.attachments.register_pending(
            tenant_id='shop',request_id=self.rid,item='image',
            media_type='image/png',sha256='a'*64,
            storage_key='private/do-not-export',now=100)
        report=require_clean_offline_fixture(self.db)
        self.assertEqual(report['aggregate_issue_counts'][
            'orphan_or_cross_tenant_attachments'],0)
        self.assertEqual(report['aggregate_issue_counts'][
            'invalid_attachment_metadata'],0)
        for secret in (aid,'a'*64,'private/do-not-export',self.rid):
            self.assertNotIn(secret,str(report))
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['postgres_connection_attempted'])

    def test_cross_tenant_attachment_preflight_refuses_fixture(self):
        orphan=self.app.attachments.register_pending(
            tenant_id='shop',request_id='f'*32,item='image',
            media_type='image/png',sha256='b'*64,
            storage_key='private/orphan',now=100)
        cross=self.app.attachments.register_pending(
            tenant_id='another-shop',request_id=self.rid,item='image',
            media_type='image/png',sha256='c'*64,
            storage_key='private/cross-tenant',now=101)
        report=inspect_offline_integrity(self.db)
        counts=report['aggregate_issue_counts']
        self.assertEqual(counts['orphan_or_cross_tenant_attachments'],2)
        self.assertEqual(counts['invalid_attachment_metadata'],0)
        self.assertTrue(report['migration_fixture_issues_found'])
        with self.assertRaises(ValueError):
            require_clean_offline_fixture(self.db)
        for secret in (orphan,cross,'private/orphan',
                       'private/cross-tenant','b'*64,'c'*64):
            self.assertNotIn(secret,str(report))

    def test_invalid_media_metadata_is_counted_without_exporting_it(self):
        self.db.execute("""INSERT INTO content_attachments
            (attachment_id,tenant_id,request_id,item,media_type,
             sha256,storage_key,status,created_at)
            VALUES (?,?,?,'bad item','image/png',
                    'bad-sha','private/bad','pending',-1)""",
            ('e'*32,'shop',self.rid))
        report=inspect_offline_integrity(self.db)
        self.assertEqual(report['aggregate_issue_counts'][
            'orphan_or_cross_tenant_attachments'],0)
        self.assertEqual(report['aggregate_issue_counts'][
            'invalid_attachment_metadata'],1)
        self.assertTrue(report['migration_fixture_issues_found'])
        self.assertNotIn('bad-sha',str(report))
        self.assertNotIn('private/bad',str(report))
        with self.assertRaises(ValueError):
            require_clean_offline_fixture(self.db)



if __name__=='__main__':
    unittest.main()
