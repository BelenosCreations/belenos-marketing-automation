"""Real PostgreSQL *ephemeral GitHub CI* integration, never customer Neon.

Runs only when BAM_EPHEMERAL_PG_TEST=1. Refuses any non-loopback endpoint or
unexpected database name/user. This does not implement or authorize production
credentials, migration, persistence, public hosting, or scheduled publication.
"""
import hashlib
import json
import os
import sqlite3
import threading
import unittest
from contextlib import closing

from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_content_drafts import AIContentDraftStore
from ai_generation_idempotency import AIGenerationIdempotency
from ai_sponsorship import SponsoredAIQuota
from content_attachments import AttachmentRegistry

from neon_schema_blueprint import ddl_preview,TABLE_NAMES
from neon_collaboration_schema import (
    COLLABORATION_NAMES,collaboration_ddl_preview)
from neon_identity_provider_schema import EXTRA_TABLE_NAMES
from neon_ai_budget_schema import BUDGET_TABLE_NAMES,ai_budget_ddl_preview
from neon_business_analytics_schema import BUSINESS_ANALYTICS_TABLES
from neon_tenant_content_schema import TENANT_CONTENT_TABLES
from neon_review_security_schema import REVIEW_SECURITY_TABLES
from neon_media_schema import MEDIA_TABLE_NAMES,media_ddl_preview
from neon_scoped_review_facts import prepare_current_private_facts
from neon_authenticated_read_contract import (
    prepare_session_draft_read,prepare_session_calendar_read)
from neon_scoped_tenant_content import (prepare_tenant_post_review,
    prepare_tenant_schedule_read)
from neon_scoped_business_analytics import (prepare_business_sources_read,
    prepare_private_audience_read)
from neon_scoped_provider_queries import (
    prepare_connections_read,prepare_personal_ai_usage,
    safe_connection_preview)
from neon_scoped_collaboration_queries import prepare_pending_owner_invitations
from neon_ephemeral_ci_migrations import apply_ephemeral_ci_migrations
from neon_scoped_queries import (draft_select_for_verified_member,
    calendar_select_for_verified_member)
from neon_scoped_writes import (
    prepare_draft_priority_cas,priority_cas_result)

_SCHEMA='bam_ci_integration'

class NeonEphemeralPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('BAM_EPHEMERAL_PG_TEST')!='1':
            raise unittest.SkipTest('Ephemeral PostgreSQL CI flag not set')
        expected={'PGHOST':'127.0.0.1','PGPORT':'5432',
                  'PGDATABASE':'bam_ci_test','PGUSER':'bam_ci'}
        if any(os.environ.get(k)!=v for k,v in expected.items()):
            raise RuntimeError('Postgres integration permits CI loopback only')
        if not os.environ.get('PGPASSWORD'):
            raise RuntimeError('Ephemeral Postgres test credential missing')
        import psycopg
        cls.psycopg=psycopg
        cls._conn_args={'host':'127.0.0.1','port':5432,
             'dbname':'bam_ci_test','user':'bam_ci',
             'password':os.environ['PGPASSWORD'],'connect_timeout':5}
        cls.conn=cls._connect()
        cls.conn.execute('CREATE SCHEMA IF NOT EXISTS '+_SCHEMA)
        cls.migration_result=apply_ephemeral_ci_migrations(cls.conn)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'conn'):
            try:
                cls.conn.execute('DROP SCHEMA IF EXISTS '+_SCHEMA+' CASCADE')
            finally:
                cls.conn.close()

    @classmethod
    def _connect(cls):
        connection=cls.psycopg.connect(**cls._conn_args,autocommit=True)
        connection.execute('SET search_path TO '+_SCHEMA)
        return connection

    def setUp(self):
        self.conn.execute('TRUNCATE TABLE '+','.join(
            TABLE_NAMES+COLLABORATION_NAMES+EXTRA_TABLE_NAMES+
            tuple(name for name in BUDGET_TABLE_NAMES if
                name!='bam_ai_operator_control')+
            BUSINESS_ANALYTICS_TABLES+TENANT_CONTENT_TABLES+
            REVIEW_SECURITY_TABLES+MEDIA_TABLE_NAMES)+' CASCADE')
        self.conn.execute("""UPDATE bam_ai_operator_control
            SET paused=1,updated_at=0 WHERE control_id=1""")
        self.a='identityA'
        self.b='identityB'
        self.viewer='viewerC'
        self.rid_a='a'*32
        self.rid_b='b'*32
        self.priority_token='c'*32
        for subject in (self.a,self.b,self.viewer):
            self.conn.execute("""INSERT INTO bam_identities
                (subject_id,email,email_verified,active,created_at)
                VALUES (%s,%s,1,1,100)""",
                (subject,subject.lower()+'@example.test'))
        for tenant,subject,role in (
            ('shop-a',self.a,'owner'),('shop-b',self.b,'owner'),
            ('shop-a',self.viewer,'viewer')):
            self.conn.execute("""INSERT INTO members
                (tenant_id,subject_id,role,active,revision)
                VALUES (%s,%s,%s,1,1)""",(tenant,subject,role))
        for tenant,rid,copy in (
            ('shop-a',self.rid_a,'private tenant A copy'),
            ('shop-b',self.rid_b,'private tenant B copy')):
            self.conn.execute("""INSERT INTO content_requests
                (request_id,tenant_id,channel,draft_text,suggestion,
                 required_items,provided_items,status,priority,priority_token,
                 created_at,updated_at,revision)
                VALUES (%s,%s,'facebook',%s,'photo','["image"]','{}',
                        'needs_content',0,%s,100,100,1)""",
                (rid,tenant,copy,self.priority_token))




    def test_ci_restore_encrypts_each_table_before_copy_and_rejects_tamper(self):
        """All 47 synthetic tables cross an authenticated in-memory envelope."""
        from unittest.mock import patch
        import neon_ci_restore_probe as probe
        actual=probe.seal_disposable_backup
        fingerprints=[]
        def capture(**params):
            fingerprints.append(params['schema_fingerprint'])
            return actual(**params)
        with patch.object(probe,'seal_disposable_backup',side_effect=capture):
            result=probe.run_ephemeral_ci_logical_restore(self.conn)
        self.assertEqual(result['ephemeral_encryption_roundtrips_checked'],47)
        self.assertFalse(result['encrypted_backup_retained'])
        self.assertEqual(len(fingerprints),47)
        self.assertEqual(len(set(fingerprints)),47)
        def corrupt(**params):
            ciphertext=actual(**params)
            return ciphertext[:-1]+b'0'
        with patch.object(probe,'seal_disposable_backup',side_effect=corrupt):
            with self.assertRaises((ValueError,PermissionError)):
                probe.run_ephemeral_ci_logical_restore(self.conn)
        self.assertIsNone(self.conn.execute(
            "SELECT to_regnamespace('bam_ci_restore_probe')").fetchone()[0])

    def test_ci_restore_uses_one_snapshot_during_concurrent_source_edit(self):
        """A parallel edit after copying one table cannot split the restore."""
        from unittest.mock import patch
        import neon_ci_restore_probe as probe
        original_import=probe._import_csv
        interleaved=[]
        def import_then_change_source(conn,table,data):
            original_import(conn,table,data)
            if table=='bam_ci_restore_probe.content_requests':
                peer=self._connect()
                try:
                    changed=peer.execute("""UPDATE content_requests
                        SET draft_text=draft_text||'[parallel-ci-edit]'
                        WHERE request_id=%s""",(self.rid_a,))
                    self.assertEqual(changed.rowcount,1)
                finally:
                    peer.close()
                interleaved.append(True)
        with patch.object(probe,'_import_csv',
                          side_effect=import_then_change_source):
            report=probe.run_ephemeral_ci_logical_restore(self.conn)
        self.assertEqual(interleaved,[True])
        self.assertTrue(report['consistent_source_snapshot_used'])
        self.assertTrue(report['separate_schema_discarded'])
        self.assertFalse(report['production_restore_validated'])
        self.assertEqual(self.conn.execute("""SELECT draft_text
            FROM content_requests WHERE request_id=%s""",
            (self.rid_a,)).fetchone()[0],
            'private tenant A copy[parallel-ci-edit]')
        self.assertIsNone(self.conn.execute(
            "SELECT to_regnamespace('bam_ci_restore_probe')").fetchone()[0])

    def test_ci_restore_rejects_unreviewed_constraints_and_indexes(self):
        """Catalog drift must roll back target and allow clean retry."""
        from neon_ci_restore_probe import run_ephemeral_ci_logical_restore
        cases=(
            ('ALTER TABLE content_requests ADD CONSTRAINT '
             'ci_restore_unreviewed_check CHECK (revision>=0)',
             'ALTER TABLE content_requests '
             'DROP CONSTRAINT ci_restore_unreviewed_check'),
            ('CREATE INDEX ci_restore_unreviewed_idx '
             'ON content_requests(priority)',
             'DROP INDEX ci_restore_unreviewed_idx'),
        )
        for introduce,repair in cases:
            with self.subTest(introduce=introduce.split()[0]):
                self.conn.execute(introduce)
                try:
                    with self.assertRaisesRegex(ValueError,
                                                'constraint or index shape mismatch'):
                        run_ephemeral_ci_logical_restore(self.conn)
                    self.assertIsNone(self.conn.execute(
                        "SELECT to_regnamespace('bam_ci_restore_probe')"
                    ).fetchone()[0])
                    self.assertEqual(self.conn.execute(
                        'SELECT COUNT(*) FROM content_requests').fetchone()[0],2)
                finally:
                    self.conn.execute(repair)
                result=run_ephemeral_ci_logical_restore(self.conn)
                self.assertEqual(result['constraint_and_index_shapes_checked'],47)
                self.assertFalse(result['production_restore_validated'])

    def test_ci_restore_rejects_unreviewed_column_schema_drift(self):
        """A source table with a new/changed column must not restore as normal."""
        from neon_ci_restore_probe import run_ephemeral_ci_logical_restore
        self.conn.execute("""ALTER TABLE content_requests
            ADD COLUMN ci_unreviewed_column TEXT""")
        try:
            with self.assertRaisesRegex(ValueError,'column schema mismatch'):
                run_ephemeral_ci_logical_restore(self.conn)
            self.assertIsNone(self.conn.execute(
                "SELECT to_regnamespace('bam_ci_restore_probe')").fetchone()[0])
            self.assertEqual(self.conn.execute(
                'SELECT COUNT(*) FROM content_requests').fetchone()[0],2)
        finally:
            self.conn.execute("""ALTER TABLE content_requests
                DROP COLUMN ci_unreviewed_column""")
        report=run_ephemeral_ci_logical_restore(self.conn)
        self.assertEqual(report['column_shapes_checked'],47)
        self.assertEqual(report['reviewed_tables_rehearsed'],46)
        self.assertFalse(report['production_restore_validated'])
        self.assertFalse(report['publishing_enabled'])

    def test_restored_postgres_sessions_preserve_live_business_isolation(self):
        """Actual restored PostgreSQL must enforce current auth and revocation."""
        import hashlib
        from neon_ci_restore_probe import run_ephemeral_ci_logical_restore
        active_a='Synthetic_Restore_Active_A_Bearer_1234567890123456789'
        active_b='Synthetic_Restore_Active_B_Bearer_1234567890123456789'
        revoked='Synthetic_Restore_Revoked_Bearer_123456789012345678'
        for bearer,subject,tenant,revoked_at in (
                (active_a,self.a,'shop-a',None),
                (active_b,self.b,'shop-b',None),
                (revoked,self.a,'shop-a',100)):
            digest=hashlib.sha256(bearer.encode('ascii')).hexdigest()
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at,revoked_at)
                VALUES (%s,%s,%s,'owner',3600,%s)""",
                (digest,subject,tenant,revoked_at))
        def probe(bearer,tenant,rid,at,visible):
            return {'raw_session_token':bearer,'tenant_id':tenant,
                    'request_id':rid,'server_now':at,'visible':visible}
        checks=[
            probe(active_a,'shop-a',self.rid_a,101,True),
            probe(active_a,'shop-b',self.rid_b,101,False),
            probe(active_b,'shop-b',self.rid_b,101,True),
            probe(active_b,'shop-a',self.rid_a,101,False),
            probe(revoked,'shop-a',self.rid_a,101,False),
            probe(active_a,'shop-a',self.rid_a,3600,False),
            probe(active_a+'tampered','shop-a',self.rid_a,101,False),
        ]
        with self.assertRaises(ValueError):
            run_ephemeral_ci_logical_restore(self.conn,
                session_probes=[probe(active_a,'shop-b',self.rid_b,101,True)])
        self.assertIsNone(self.conn.execute(
            "SELECT to_regnamespace('bam_ci_restore_probe')").fetchone()[0])
        with self.assertRaises(ValueError):
            run_ephemeral_ci_logical_restore(self.conn,
                session_probes=[dict(checks[0],visible=1)])
        report=run_ephemeral_ci_logical_restore(self.conn,session_probes=checks)
        self.assertEqual(report['restored_session_checks_passed'],7)
        for secret in (active_a,active_b,revoked,self.a,self.b):
            self.assertNotIn(secret,str(report))
        self.assertFalse(report['production_restore_validated'])
        self.assertFalse(report['publishing_enabled'])
        self.assertIsNone(self.conn.execute(
            "SELECT to_regnamespace('bam_ci_restore_probe')").fetchone()[0])

    def test_ci_restore_rejects_interrupted_or_corrupted_copy_without_residue(self):
        """Injected CI-only faults cannot leak a partial replacement schema."""
        from neon_ci_restore_probe import run_ephemeral_ci_logical_restore
        before=self.conn.execute("""SELECT request_id,draft_text,revision
            FROM content_requests ORDER BY request_id""").fetchall()
        source_tables=self.conn.execute("""SELECT COUNT(*) FROM
            information_schema.tables
            WHERE table_schema='bam_ci_integration'""").fetchone()[0]
        with self.assertRaises(ValueError):
            run_ephemeral_ci_logical_restore(self.conn,fail_mode='unknown')
        with self.assertRaises(ValueError):
            run_ephemeral_ci_logical_restore(self.conn,fail_mode=True)
        for fault,error in (('abort_after_copy',RuntimeError),
                            ('corrupt_restored_draft',ValueError)):
            with self.subTest(fault=fault):
                with self.assertRaises(error):
                    run_ephemeral_ci_logical_restore(self.conn,fail_mode=fault)
                self.assertIsNone(self.conn.execute(
                    "SELECT to_regnamespace('bam_ci_restore_probe')"
                    ).fetchone()[0])
                self.assertEqual(self.conn.execute("""SELECT request_id,
                    draft_text,revision FROM content_requests
                    ORDER BY request_id""").fetchall(),before)
                self.assertEqual(self.conn.execute("""SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema='bam_ci_integration'
                    """).fetchone()[0],source_tables)
        # A repaired/retried run has no leftover schema and succeeds normally.
        result=run_ephemeral_ci_logical_restore(self.conn)
        self.assertTrue(result['separate_schema_discarded'])
        self.assertFalse(result['production_restore_validated'])
        self.assertFalse(result['publishing_enabled'])

    def test_full_preview_ci_copy_restore_rehearsal(self):
        """Restore all reviewed table rows to a second disposable PG schema."""
        import hashlib
        from unittest.mock import patch
        from neon_ci_restore_probe import run_ephemeral_ci_logical_restore
        secret='Synthetic_Revoked_Session_Restore_1234567890'
        digest=hashlib.sha256(secret.encode('ascii')).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at,revoked_at)
            VALUES (%s,%s,'shop-a','owner',500,101)""",(digest,self.a))
        self.conn.execute("""INSERT INTO bam_password_credentials
            (subject_id,salt,digest,iterations)
            VALUES (%s,%s,%s,210000)""",
            (self.a,b'fake-salt-for-tests',b'fake-digest-for-tests'))
        self.conn.execute("""INSERT INTO content_attachments
            (attachment_id,tenant_id,request_id,item,media_type,sha256,
             storage_key,status,created_at)
            VALUES (%s,'shop-a',%s,'image','image/png',%s,
                    'private/synthetic-only','pending',101)""",
            ('d'*32,self.rid_a,'e'*64))
        report=run_ephemeral_ci_logical_restore(self.conn)
        self.assertEqual(report['reviewed_tables_rehearsed'],46)
        self.assertTrue(report['migration_journal_rehearsed'])
        self.assertTrue(report['separate_schema_discarded'])
        self.assertFalse(report['backup_file_created'])
        self.assertFalse(report['production_restore_validated'])
        self.assertFalse(report['customer_records_exported'])
        self.assertFalse(report['publishing_enabled'])
        self.assertIsNone(self.conn.execute(
            "SELECT to_regnamespace('bam_ci_restore_probe')").fetchone()[0])
        self.assertEqual(self.conn.execute("""SELECT revoked_at
            FROM sessions WHERE token_hash=%s""",(digest,)).fetchone()[0],101)
        self.assertEqual(self.conn.execute("""SELECT status FROM content_attachments
            WHERE attachment_id=%s""",('d'*32,)).fetchone()[0],'pending')
        with self.assertRaises(TypeError):
            run_ephemeral_ci_logical_restore(object())
        with patch.dict(os.environ,{'BAM_EPHEMERAL_PG_TEST':'0'}):
            with self.assertRaises(PermissionError):
                run_ephemeral_ci_logical_restore(self.conn)

    def test_ci_schema_migration_journal_is_idempotent(self):
        self.assertEqual(self.migration_result['versions_present'],8)
        self.assertEqual(self.migration_result['versions_applied'],[1,2,3,4,5,6,7,8])
        reread=apply_ephemeral_ci_migrations(self.conn)
        self.assertEqual(reread['versions_applied'],[])
        self.assertFalse(reread['migration_production_ready'])
        self.assertFalse(reread['customer_records_migrated'])
        self.assertFalse(reread['neon_connected'])
        self.assertFalse(reread['social_publishing_enabled'])
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM bam_ci_migration_journal').fetchone()[0],8)

    def test_schema_digest_tamper_is_refused_without_changing_data(self):
        old=self.conn.execute('SELECT checksum FROM bam_ci_migration_journal '
                              'WHERE version=2').fetchone()[0]
        self.conn.execute("""UPDATE bam_ci_migration_journal SET checksum=%s
            WHERE version=2""",('x'*64,))
        try:
            with self.assertRaises(ValueError):
                apply_ephemeral_ci_migrations(self.conn)
            self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM members'
                              ).fetchone()[0],3)
        finally:
            self.conn.execute("""UPDATE bam_ci_migration_journal SET
                checksum=%s WHERE version=2""",(old,))

    def test_schema_drift_is_refused_even_if_journal_is_intact(self):
        self.conn.execute('DROP TABLE bam_review_feedback')
        try:
            with self.assertRaises(ValueError):
                apply_ephemeral_ci_migrations(self.conn)
        finally:
            self.conn.execute(collaboration_ddl_preview()[3])
        self.assertEqual(apply_ephemeral_ci_migrations(
            self.conn)['versions_applied'],[])

    def test_unknown_future_migration_is_refused(self):
        self.conn.execute("""INSERT INTO bam_ci_migration_journal
            (version,checksum,completed_at) VALUES (99,%s,0)""",
            ('f'*64,))
        try:
            with self.assertRaises(ValueError):
                apply_ephemeral_ci_migrations(self.conn)
        finally:
            self.conn.execute('DELETE FROM bam_ci_migration_journal '
                              'WHERE version=99')

    def test_migration_loader_refuses_non_psycopg_connections(self):
        with self.assertRaises(TypeError):
            apply_ephemeral_ci_migrations(object())

    def test_actual_postgresql_ddl_and_private_bytea_type(self):
        rows=self.conn.execute("""SELECT table_name
            FROM information_schema.tables
            WHERE table_schema=%s AND table_type='BASE TABLE'""",
            (_SCHEMA,)).fetchall()
        self.assertEqual({name for (name,) in rows},
                         set(TABLE_NAMES+COLLABORATION_NAMES+EXTRA_TABLE_NAMES+
                             BUDGET_TABLE_NAMES+BUSINESS_ANALYTICS_TABLES+
                             TENANT_CONTENT_TABLES+REVIEW_SECURITY_TABLES+
                             MEDIA_TABLE_NAMES+('bam_ci_migration_journal',)))
        values=self.conn.execute("""SELECT column_name,data_type FROM
            information_schema.columns
            WHERE table_schema=%s AND table_name='bam_password_credentials'
            ORDER BY ordinal_position""",(_SCHEMA,)).fetchall()
        self.assertIn(('salt','bytea'),values)
        self.assertIn(('digest','bytea'),values)

    def test_read_queries_check_actual_postgres_membership(self):
        sql,params=draft_select_for_verified_member(
            tenant_id='shop-a',request_id=self.rid_a,
            verified_subject_id=self.a)
        self.assertEqual(self.conn.execute(sql,params).fetchone()[2],
                         'private tenant A copy')
        sql,params=draft_select_for_verified_member(
            tenant_id='shop-b',request_id=self.rid_b,
            verified_subject_id=self.a)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        sql,params=draft_select_for_verified_member(
            tenant_id='shop-a',request_id=self.rid_a,
            verified_subject_id=self.viewer)
        self.assertIsNotNone(self.conn.execute(sql,params).fetchone())
        self.conn.execute("""UPDATE members SET active=0
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.viewer,))
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        self.conn.execute("""UPDATE bam_identities SET email_verified=0
            WHERE subject_id=%s""",(self.a,))
        sql,params=draft_select_for_verified_member(
            tenant_id='shop-a',request_id=self.rid_a,
            verified_subject_id=self.a)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())

    def test_postgres_calendar_is_non_executable_and_scoped(self):
        self.conn.execute("""INSERT INTO bam_calendar_proposals
           (tenant_id,request_id,draft_revision,utc_at,local_date,
            local_time,timezone,updated_at,updated_by,proposal_token)
           VALUES ('shop-a',%s,1,'2026-11-12T16:00:00+00:00',
                   '2026-11-12','11:00','America/New_York',100,%s,%s)""",
            (self.rid_a,self.a,'f'*32))
        sql,params=calendar_select_for_verified_member(
            tenant_id='shop-a',request_id=self.rid_a,
            verified_subject_id=self.a)
        self.assertEqual(self.conn.execute(sql,params).fetchone()[0],
                         self.rid_a)
        sql,params=calendar_select_for_verified_member(
            tenant_id='shop-a',request_id=self.rid_a,
            verified_subject_id=self.b)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())

    def test_priority_cas_is_atomic_on_real_postgres(self):
        sql,params=prepare_draft_priority_cas(
            tenant_id='shop-a',request_id=self.rid_a,
            verified_subject_id=self.a,
            expected_priority_token=self.priority_token,
            priority=7,server_now=101)
        row=self.conn.execute(sql,params).fetchone()
        receipt=priority_cas_result(row,expected_new_token=params[1])
        self.assertFalse(receipt['publishing_enabled'])
        self.assertEqual(receipt['draft_revision'],1)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        self.assertEqual(self.conn.execute("""SELECT priority,revision,
            draft_text FROM content_requests WHERE request_id=%s""",
            (self.rid_a,)).fetchone(),
            (7,1,'private tenant A copy'))

    def test_priority_cas_rejects_live_revocation_and_viewer(self):
        def statement(actor,token):
            return prepare_draft_priority_cas(
                tenant_id='shop-a',request_id=self.rid_a,
                verified_subject_id=actor,
                expected_priority_token=token,priority=5,server_now=101)
        self.assertIsNone(self.conn.execute(*statement(
            self.viewer,self.priority_token)).fetchone())
        self.conn.execute("""UPDATE members SET active=0
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.assertIsNone(self.conn.execute(*statement(
            self.a,self.priority_token)).fetchone())
        self.conn.execute("""UPDATE members SET active=1
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.conn.execute("""UPDATE bam_identities SET active=0
            WHERE subject_id=%s""",(self.a,))
        self.assertIsNone(self.conn.execute(*statement(
            self.a,self.priority_token)).fetchone())

    def test_ai_cost_receipt_deduplication_scoped_to_identity_business(self):
        self.conn.execute("""INSERT INTO bam_ai_cost_events
            (event_id,tenant_id,subject_id,provider,model,input_tokens,
             output_tokens,estimated_micro_usd,occurred_at,trusted_usage_hash)
            VALUES (%s,'shop-a',%s,'openai','test-model',10,20,2,101,%s)""",
            ('a'*32,self.a,'f'*64))
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            self.conn.execute("""INSERT INTO bam_ai_cost_events
                (event_id,tenant_id,subject_id,provider,model,input_tokens,
                output_tokens,estimated_micro_usd,occurred_at,trusted_usage_hash)
                VALUES (%s,'shop-a',%s,'openai','test-model',11,22,5,102,%s)""",
                ('b'*32,self.a,'f'*64))
        self.conn.execute("""INSERT INTO bam_ai_cost_events
            (event_id,tenant_id,subject_id,provider,model,input_tokens,
             output_tokens,estimated_micro_usd,occurred_at,trusted_usage_hash)
            VALUES (%s,'shop-b',%s,'openai','test-model',9,7,1,101,%s)""",
            ('c'*32,self.b,'f'*64))
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM bam_ai_cost_events WHERE tenant_id='shop-a'""").fetchone()[0],1)
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM bam_ai_cost_events WHERE tenant_id='shop-b'""").fetchone()[0],1)

    def _create_ai_receipt_fixture(self):
        # CI-only receipt shape using the actual migration preview tables.
        self.conn.execute("""CREATE TABLE ci_ai_output_receipt (
            tenant_id TEXT NOT NULL, subject_id TEXT NOT NULL,
            request_key TEXT NOT NULL, draft_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL, generation BIGINT NOT NULL,
            resulting_revision INTEGER NOT NULL,
            PRIMARY KEY (tenant_id, subject_id, request_key),
            FOREIGN KEY (tenant_id, subject_id, request_key)
                REFERENCES bam_ai_generation_requests,
            FOREIGN KEY (tenant_id, subject_id, draft_id)
                REFERENCES bam_ai_draft_components
        )""")
        self.addCleanup(self.conn.execute, "DROP TABLE ci_ai_output_receipt")

    def test_ai_draft_and_receipt_commit_or_rollback_together(self):
        scope = ('shop-a', self.a)
        request_key, draft_id = 'a'*32, 'b'*32
        request_insert = """INSERT INTO bam_ai_generation_requests
            (tenant_id,subject_id,request_key,request_fingerprint,status,created_at)
            VALUES (%s,%s,%s,%s,'in_progress',100)"""
        self.conn.execute(request_insert, (*scope, request_key, 'c'*64))
        self._create_ai_receipt_fixture()
        reader = self._connect()
        self.addCleanup(reader.close)
        draft_insert = """INSERT INTO bam_ai_draft_components
            (tenant_id,subject_id,draft_id,platform,post_text,needs_media,
             revision,created_at,updated_at)
            VALUES (%s,%s,%s,'facebook','Synthetic draft',0,1,100,100)"""
        receipt_insert = """INSERT INTO ci_ai_output_receipt
            VALUES (%s,%s,%s,%s,%s,1,1)"""
        receipt = (*scope, request_key, draft_id, 'c'*64)

        # A crash after writing the draft but before recording its receipt
        # rolls back the uncommitted draft when the worker connection closes.
        worker = self._connect()
        try:
            worker.execute("BEGIN")
            worker.execute(draft_insert, (*scope, draft_id))
        finally:
            worker.close()
        self.assertEqual(reader.execute(
            "SELECT count(*) FROM bam_ai_draft_components").fetchone(), (0,))

        # A receipt for a different subject cannot reference this draft.
        other_scope = ('shop-a', self.b)
        self.conn.execute(request_insert, (*other_scope, request_key, 'c'*64))
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation):
            with self.conn.transaction():
                self.conn.execute(draft_insert, (*scope, draft_id))
                self.conn.execute(receipt_insert, (*other_scope, *receipt[2:]))
        self.assertEqual(reader.execute(
            "SELECT count(*) FROM bam_ai_draft_components").fetchone(), (0,))

        with self.conn.transaction():
            self.conn.execute(draft_insert, (*scope, draft_id))
            self.conn.execute(receipt_insert, receipt)
            self.assertEqual(reader.execute(
                "SELECT count(*) FROM ci_ai_output_receipt").fetchone(), (0,))
        self.assertEqual(reader.execute("""SELECT r.status, d.draft_id
            FROM ci_ai_output_receipt AS o
            JOIN bam_ai_draft_components AS d USING (tenant_id,subject_id,draft_id)
            JOIN bam_ai_generation_requests AS r USING (tenant_id,subject_id,request_key)
            """).fetchall(), [('in_progress', draft_id)])
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            self.conn.execute(receipt_insert, receipt)

    def test_ai_recovery_finalizes_only_a_matching_committed_receipt_once(self):
        self._create_ai_receipt_fixture()
        self.conn.execute("""CREATE TABLE ci_ai_recovery_authority (
            id INTEGER PRIMARY KEY CHECK (id=1), generation BIGINT NOT NULL,
            head TEXT NOT NULL, mode TEXT NOT NULL CHECK (mode IN ('open','frozen'))
        )""")
        self.addCleanup(self.conn.execute, "DROP TABLE ci_ai_recovery_authority")
        self.conn.execute("INSERT INTO ci_ai_recovery_authority VALUES (1,3,'head-3','open')")
        self.conn.execute("""CREATE TABLE ci_ai_recovery_audit (
            decision_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            subject_id TEXT NOT NULL, request_key TEXT NOT NULL,
            generation BIGINT NOT NULL, head TEXT NOT NULL
        )""")
        self.addCleanup(self.conn.execute, "DROP TABLE ci_ai_recovery_audit")
        scope = ('shop-a', self.a)
        request_key, uncertain_key, draft_id = 'a'*32, 'b'*32, 'c'*32
        other_request_key, other_draft_id = 'd'*32, 'e'*32
        fingerprint = 'd'*64
        for key in (request_key, uncertain_key, other_request_key):
            self.conn.execute("""INSERT INTO bam_ai_generation_requests
                (tenant_id,subject_id,request_key,request_fingerprint,status,created_at)
                VALUES (%s,%s,%s,%s,'in_progress',100)""", (*scope, key, fingerprint))
        for key, output in ((request_key, draft_id), (other_request_key, other_draft_id)):
            with self.conn.transaction():
                self.conn.execute("""INSERT INTO bam_ai_draft_components
                    (tenant_id,subject_id,draft_id,platform,post_text,needs_media,
                     revision,created_at,updated_at)
                    VALUES (%s,%s,%s,'facebook','Synthetic draft',0,1,100,100)""",
                    (*scope, output))
                self.conn.execute("""INSERT INTO ci_ai_output_receipt
                    VALUES (%s,%s,%s,%s,%s,1,1)""",
                    (*scope, key, output, fingerprint))

        # The parameters stand in for a preverified operator approval. SQL
        # compares the approved scope, receipt and authority under the lock.
        finalize = """WITH authority AS (
            SELECT generation, head FROM ci_ai_recovery_authority
            WHERE id=1 AND generation=%s AND head=%s AND mode='open' FOR SHARE NOWAIT
        ), finalized AS (
            UPDATE bam_ai_generation_requests AS r
            SET status='completed', draft_id=o.draft_id
            FROM ci_ai_output_receipt AS o, authority AS a
            WHERE (r.tenant_id,r.subject_id,r.request_key) =
                  (o.tenant_id,o.subject_id,o.request_key)
              AND (r.tenant_id,r.subject_id,r.request_key) = (%s,%s,%s)
              AND r.status='in_progress' AND r.draft_id IS NULL
              AND r.request_fingerprint=o.fingerprint AND o.fingerprint=%s
              AND o.draft_id=%s AND o.resulting_revision=%s
              AND o.generation=%s AND o.generation<a.generation
              AND %s::bigint < %s::bigint
            RETURNING r.tenant_id,r.subject_id,r.request_key,a.generation,a.head
        )
        INSERT INTO ci_ai_recovery_audit
        SELECT %s, tenant_id, subject_id, request_key, generation, head
        FROM finalized"""
        operator = self._connect()
        self.addCleanup(operator.close)

        def recover(*, generation=3, head='head-3', tenant='shop-a',
                    subject=self.a, key=request_key, digest=fingerprint,
                    receipt_draft=draft_id, output_revision=1, origin=1, expires=120):
            return operator.execute(finalize, (
                generation, head, tenant, subject, key, digest, receipt_draft,
                output_revision, origin, 110, expires, 'decision-1',
            )).rowcount

        for rejected in (
            {'generation': 2}, {'head': 'old-head'}, {'expires': 110},
            {'tenant': 'shop-b'}, {'subject': self.b}, {'key': uncertain_key},
            {'digest': 'e'*64}, {'receipt_draft': 'f'*32},
            {'output_revision': 2}, {'origin': 2},
        ):
            with self.subTest(rejected=rejected):
                self.assertEqual(recover(**rejected), 0)
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM ci_ai_recovery_audit").fetchone(), (0,))
        freeze = """UPDATE ci_ai_recovery_authority SET generation=4,
            head='head-4',mode='frozen' WHERE id=1 AND generation=3"""
        # If freeze gets the row lock first, a previously approved recovery
        # fails before writing either the request or its audit row.
        with self.conn.transaction(force_rollback=True):
            self.assertEqual(self.conn.execute(freeze).rowcount, 1)
            with self.assertRaises(self.psycopg.errors.LockNotAvailable):
                recover()
            self.assertEqual(self.conn.execute(
                "SELECT count(*) FROM ci_ai_recovery_audit").fetchone(), (0,))
        # A recovery that already holds the authority row orders its audit
        # and request commits before a freeze can finish.
        with operator.transaction():
            self.assertEqual(recover(), 1)
            self.assertEqual(self.conn.execute(
                "SELECT count(*) FROM ci_ai_recovery_audit").fetchone(), (0,))
            with self.assertRaises(self.psycopg.errors.LockNotAvailable):
                with self.conn.transaction():
                    self.conn.execute("SET LOCAL lock_timeout = '250ms'")
                    self.conn.execute(freeze)
        self.assertEqual(recover(), 0)
        # An audit uniqueness failure rolls back even a valid status update.
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            recover(key=other_request_key, receipt_draft=other_draft_id)
        self.assertEqual(self.conn.execute("""SELECT request_key, status, draft_id
            FROM bam_ai_generation_requests ORDER BY request_key""").fetchall(),
            [(request_key, 'completed', draft_id), (uncertain_key, 'in_progress', None),
             (other_request_key, 'in_progress', None)])
        self.assertEqual(self.conn.execute("""SELECT tenant_id, subject_id,
            request_key, generation, head FROM ci_ai_recovery_audit""").fetchall(),
            [(*scope, request_key, 3, 'head-3')])
        self.assertEqual(self.conn.execute("""SELECT draft_id, revision, post_text
            FROM bam_ai_draft_components ORDER BY draft_id""").fetchall(),
            [(draft_id, 1, 'Synthetic draft'), (other_draft_id, 1, 'Synthetic draft')])
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM bam_ai_cost_events").fetchone(), (0,))
        for table in ('bam_ai_usage', 'bam_ai_tenant_usage', 'bam_ai_operator_usage'):
            self.assertEqual(self.conn.execute(
                "SELECT count(*) FROM " + table).fetchone(), (0,))
        self.assertEqual(self.conn.execute(freeze).rowcount, 1)
        self.assertEqual(recover(key=other_request_key, receipt_draft=other_draft_id), 0)
        self.assertEqual(recover(generation=4, head='head-4',
            key=other_request_key, receipt_draft=other_draft_id), 0)

    def test_ai_targeted_revision_media_and_receipt_roll_back_together(self):
        self._create_ai_receipt_fixture()
        scope = ('shop-a', self.a)
        request_key, draft_id = 'a'*32, 'b'*32
        draft_scope = (*scope, draft_id)
        where_draft = " WHERE tenant_id=%s AND subject_id=%s AND draft_id=%s"
        self.conn.execute("""INSERT INTO bam_ai_generation_requests
            (tenant_id,subject_id,request_key,request_fingerprint,status,created_at)
            VALUES (%s,%s,%s,%s,'in_progress',100)""", (*scope, request_key, 'c'*64))
        self.conn.execute("""INSERT INTO bam_ai_draft_components
            (tenant_id,subject_id,draft_id,platform,post_text,image_prompt,
             needs_media,revision,created_at,updated_at)
            VALUES (%s,%s,%s,'facebook','Synthetic draft','Old prompt',1,1,100,100)""",
            draft_scope)
        self.conn.execute("""INSERT INTO bam_ai_draft_verified_media
            (tenant_id,subject_id,draft_id,attachment_id,updated_at)
            VALUES (%s,%s,%s,'synthetic-link',100)""", draft_scope)
        revise = """UPDATE bam_ai_draft_components SET image_prompt='New prompt',
            revision=revision+1, updated_at=110""" + where_draft + " AND revision=1"
        unlink = "DELETE FROM bam_ai_draft_verified_media" + where_draft
        add_receipt = "INSERT INTO ci_ai_output_receipt VALUES (%s,%s,%s,%s,%s,1,2)"

        # A receipt failure after both mutations must undo both.
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation):
            with self.conn.transaction():
                self.assertEqual(self.conn.execute(revise, draft_scope).rowcount, 1)
                self.assertEqual(self.conn.execute(unlink, draft_scope).rowcount, 1)
                self.conn.execute(add_receipt, (*scope, 'd'*32, draft_id, 'c'*64))
        self.assertEqual(self.conn.execute("""SELECT revision, image_prompt
            FROM bam_ai_draft_components""" + where_draft, draft_scope).fetchone(),
            (1, 'Old prompt'))
        self.assertEqual(self.conn.execute("""SELECT attachment_id
            FROM bam_ai_draft_verified_media""" + where_draft, draft_scope).fetchone(),
            ('synthetic-link',))

        with self.conn.transaction():
            self.assertEqual(self.conn.execute(revise, draft_scope).rowcount, 1)
            self.assertEqual(self.conn.execute(unlink, draft_scope).rowcount, 1)
            self.conn.execute(add_receipt, (*scope, request_key, draft_id, 'c'*64))
        self.assertEqual(self.conn.execute("""SELECT d.revision, d.image_prompt,
            o.resulting_revision FROM bam_ai_draft_components AS d
            JOIN ci_ai_output_receipt AS o USING (tenant_id,subject_id,draft_id)
            """).fetchone(), (2, 'New prompt', 2))
        self.assertEqual(self.conn.execute(
            "SELECT count(*) FROM bam_ai_draft_verified_media").fetchone(), (0,))
        self.assertEqual(self.conn.execute(revise, draft_scope).rowcount, 0)
        self.conn.execute("""UPDATE bam_ai_draft_components
            SET revision=3, image_prompt='Later manual edit'""" + where_draft,
            draft_scope)
        self.assertEqual(self.conn.execute("""SELECT resulting_revision
            FROM ci_ai_output_receipt""").fetchone(), (2,))

    def test_ai_epoch_lock_orders_writes_against_freeze(self):
        self.conn.execute("""CREATE TABLE ci_ai_epoch (
            id INTEGER PRIMARY KEY CHECK (id=1), generation BIGINT NOT NULL,
            frozen BOOLEAN NOT NULL
        )""")
        self.addCleanup(self.conn.execute, "DROP TABLE ci_ai_epoch")
        self.conn.execute("INSERT INTO ci_ai_epoch VALUES (1,1,FALSE)")
        operator = self._connect()
        self.addCleanup(operator.close)
        admit_and_write = """WITH admission AS (
            SELECT id FROM ci_ai_epoch
            WHERE id=1 AND generation=%s AND NOT frozen FOR SHARE NOWAIT
        )
        INSERT INTO bam_ai_generation_requests
            (tenant_id,subject_id,request_key,request_fingerprint,status,created_at)
        SELECT 'shop-a',%s,%s,%s,'in_progress',100 FROM admission"""
        freeze = "UPDATE ci_ai_epoch SET generation=2, frozen=TRUE WHERE id=1"

        # A pre-existing admitted writer holds the shared row lock until
        # its transaction ends. The freeze cannot commit past that lock.
        with self.conn.transaction():
            self.assertEqual(self.conn.execute(
                admit_and_write, (1, self.a, 'a'*32, 'c'*64)).rowcount, 1)
            with self.assertRaises(self.psycopg.errors.LockNotAvailable):
                with operator.transaction():
                    operator.execute("SET LOCAL lock_timeout = '250ms'")
                    operator.execute(freeze)

        # If the operator obtains the conflicting lock first, a worker
        # cannot admit itself using the previously visible generation.
        with operator.transaction():
            operator.execute(freeze)
            with self.assertRaises(self.psycopg.errors.LockNotAvailable):
                self.conn.execute(admit_and_write, (1, self.a, 'b'*32, 'c'*64))
        self.assertEqual(self.conn.execute(
            admit_and_write, (2, self.a, 'b'*32, 'c'*64)).rowcount, 0)
        operator.execute("UPDATE ci_ai_epoch SET generation=3, frozen=FALSE WHERE id=1")
        self.assertEqual(self.conn.execute(
            admit_and_write, (1, self.a, 'b'*32, 'c'*64)).rowcount, 0)
        self.assertEqual(self.conn.execute(
            admit_and_write, (3, self.a, 'b'*32, 'c'*64)).rowcount, 1)

    def test_ai_resume_requires_confirmed_head_after_interruption_and_restore(self):
        self.conn.execute("""CREATE TABLE ci_ai_resume_authority (
            id INTEGER PRIMARY KEY CHECK (id=1), generation BIGINT NOT NULL,
            head TEXT NOT NULL, mode TEXT NOT NULL
                CHECK (mode IN ('open','frozen','pending'))
        )""")
        self.addCleanup(self.conn.execute, "DROP TABLE ci_ai_resume_authority")
        self.conn.execute("INSERT INTO ci_ai_resume_authority VALUES (1,1,'head-1','open')")
        previous_snapshot = self.conn.execute("""SELECT generation, head, mode
            FROM ci_ai_resume_authority WHERE id=1""").fetchone()

        operator = self._connect()
        try:
            with operator.transaction():
                operator.execute("""UPDATE ci_ai_resume_authority
                    SET generation=2, head='head-2', mode='frozen' WHERE id=1""")
            with operator.transaction():
                operator.execute("""UPDATE ci_ai_resume_authority
                    SET generation=3, head='head-3', mode='pending'
                    WHERE id=1 AND generation=2 AND mode='frozen'""")
        finally:
            operator.close()

        # A replacement connection sees the committed pending transition.
        # The independently witnessed head is represented by fixture inputs.
        worker = self._connect()
        self.addCleanup(worker.close)
        admit = """WITH authority AS (
            SELECT id FROM ci_ai_resume_authority
            WHERE id=1 AND mode='open' AND generation=%s AND head=%s FOR SHARE NOWAIT
        )
        INSERT INTO bam_ai_generation_requests
            (tenant_id,subject_id,request_key,request_fingerprint,status,created_at)
        SELECT 'shop-a',%s,%s,%s,'in_progress',100 FROM authority"""
        confirm = """UPDATE ci_ai_resume_authority SET mode='open'
            WHERE id=1 AND mode='pending' AND generation=%s AND head=%s"""

        def admit_request(generation, head, request_key):
            return worker.execute(admit, (
                generation, head, self.a, request_key, 'f'*64,
            )).rowcount

        self.assertEqual(admit_request(3, 'head-3', 'a'*32), 0)
        self.assertEqual(self.conn.execute(confirm, (2, 'head-2')).rowcount, 0)
        self.assertEqual(self.conn.execute(confirm, (3, 'unrelated')).rowcount, 0)
        self.assertEqual(self.conn.execute(confirm, (3, 'head-3')).rowcount, 1)
        self.assertEqual(admit_request(3, 'head-3', 'a'*32), 1)

        # Simulate restoring the older database authority row. A restarted
        # writer still uses the independently witnessed generation and head.
        self.conn.execute("""UPDATE ci_ai_resume_authority
            SET generation=%s, head=%s, mode=%s WHERE id=1""", previous_snapshot)
        self.assertEqual(admit_request(3, 'head-3', 'b'*32), 0)
        self.assertEqual(admit_request(1, None, 'b'*32), 0)
        self.assertEqual(self.conn.execute(confirm, (1, 'head-1')).rowcount, 0)
        self.assertEqual(self.conn.execute(
            "SELECT request_key FROM bam_ai_generation_requests").fetchall(), [('a'*32,)])

    def test_ai_pending_resume_requires_signed_transition_and_independent_confirmation(self):
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        self.conn.execute("""CREATE TABLE ci_ai_signed_authority (
            id INTEGER PRIMARY KEY CHECK (id=1), generation BIGINT NOT NULL,
            head TEXT NOT NULL, mode TEXT NOT NULL CHECK (mode IN ('frozen','pending','open'))
        )""")
        self.addCleanup(self.conn.execute, "DROP TABLE ci_ai_signed_authority")
        self.conn.execute("INSERT INTO ci_ai_signed_authority VALUES (1,2,'head-2','frozen')")
        operator_key = Ed25519PrivateKey.generate()
        witness_key = Ed25519PrivateKey.generate()
        operator_verify = operator_key.public_key()
        witness_verify = witness_key.public_key()
        transition = {
            'purpose': 'bam-ci-resume-v1', 'environment': 'bam-ci-test',
            'previous_generation': 2, 'previous_head': 'head-2',
            'new_generation': 3, 'expires_at': 120,
        }

        def encode(value):
            return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')

        signed_transition = encode(transition)
        signature = operator_key.sign(signed_transition)
        head = hashlib.sha256(signed_transition + signature).hexdigest()

        def stage(value, signed, *, now=110):
            payload = encode(value)
            operator_verify.verify(signed, payload)
            if (value['purpose'] != 'bam-ci-resume-v1'
                    or value['environment'] != 'bam-ci-test'
                    or value['new_generation'] != value['previous_generation'] + 1
                    or now >= value['expires_at']):
                return 0
            transition_head = hashlib.sha256(payload + signed).hexdigest()
            return self.conn.execute("""UPDATE ci_ai_signed_authority
                SET generation=%s, head=%s, mode='pending'
                WHERE id=1 AND mode='frozen' AND generation=%s AND head=%s""",
                (value['new_generation'], transition_head,
                 value['previous_generation'], value['previous_head'])).rowcount

        with self.assertRaises(InvalidSignature):
            stage(dict(transition, new_generation=4), signature)
        with self.assertRaises(InvalidSignature):
            stage(transition, witness_key.sign(signed_transition))
        for changed in (
            {'environment': 'different-environment'}, {'purpose': 'different-purpose'},
            {'new_generation': 4}, {'previous_head': 'wrong-previous-head'},
        ):
            with self.subTest(changed=changed):
                rejected = dict(transition, **changed)
                self.assertEqual(stage(rejected, operator_key.sign(encode(rejected))), 0)
        self.assertEqual(stage(transition, signature, now=120), 0)
        self.assertEqual(stage(transition, signature), 1)
        self.assertEqual(stage(transition, signature), 0)

        acknowledgement = {'purpose': 'bam-ci-resume-confirmation-v1',
                           'environment': 'bam-ci-test', 'generation': 3, 'head': head}
        peer = self._connect()
        self.addCleanup(peer.close)

        def confirm(value, signed):
            witness_verify.verify(signed, encode(value))
            if (value['purpose'] != 'bam-ci-resume-confirmation-v1'
                    or value['environment'] != 'bam-ci-test'):
                return 0
            return peer.execute("""UPDATE ci_ai_signed_authority SET mode='open'
                WHERE id=1 AND mode='pending' AND generation=%s AND head=%s""",
                (value['generation'], value['head'])).rowcount

        acknowledgement_bytes = encode(acknowledgement)
        with self.assertRaises(InvalidSignature):
            confirm(acknowledgement, operator_key.sign(acknowledgement_bytes))
        for changed in (
            {'head': 'different-head'}, {'generation': 2},
            {'environment': 'different-environment'},
        ):
            with self.subTest(changed=changed):
                rejected = dict(acknowledgement, **changed)
                self.assertEqual(confirm(rejected, witness_key.sign(encode(rejected))), 0)
        self.assertEqual(peer.execute("SELECT mode FROM ci_ai_signed_authority").fetchone(),
                         ('pending',))
        witness_signature = witness_key.sign(acknowledgement_bytes)
        self.assertEqual(confirm(acknowledgement, witness_signature), 1)
        self.assertEqual(confirm(acknowledgement, witness_signature), 0)
        self.assertEqual(peer.execute("""SELECT generation, head, mode
            FROM ci_ai_signed_authority""").fetchone(), (3, head, 'open'))
        self.conn.execute("""UPDATE ci_ai_signed_authority
            SET generation=4, head='head-4', mode='frozen' WHERE id=1""")
        self.assertEqual(stage(transition, signature), 0)
        self.assertEqual(confirm(acknowledgement, witness_signature), 0)
        self.assertEqual(peer.execute("""SELECT generation, head, mode
            FROM ci_ai_signed_authority""").fetchone(), (4, 'head-4', 'frozen'))

    def test_ai_memory_and_facts_keep_exact_sqlite_text(self):
        def unique_object(pairs):
            result = dict(pairs)
            if len(result) != len(pairs):
                raise ValueError('Duplicate JSON key')
            return result

        memory = {'greeting': 'Café 🐝', 'tone': 'Friendly'}
        canonical = AIPolicyStore._encode_memory(memory)
        legacy = '{ "tone": "Friendly", "greeting": "Caf\\u00e9 \\ud83d\\udc1d" }'
        duplicate = '{"tone":"Wrong","tone":"Friendly"}'
        for value in (canonical, legacy):
            self.assertEqual(json.loads(value, object_pairs_hook=unique_object), memory)
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON key'):
            json.loads(duplicate, object_pairs_hook=unique_object)
        with self.assertRaises(ValueError):
            AIPolicyStore._encode_memory(json.loads('{"tone":42}'))
        with self.assertRaises(ValueError):
            AIBusinessFacts._validate({})

        with closing(sqlite3.connect(':memory:')) as source:
            policy = AIPolicyStore(db=source, sessions=None, directory=None)
            AIBusinessFacts(db=source, policy_store=policy)
            source.executemany('INSERT INTO bam_ai_memories VALUES (?,?,?,?)', (
                ('shop-a', self.a, canonical, 100),
                ('shop-b', self.a, legacy, 100),
                ('shop-a', self.viewer, '{}', 0),
            ))
            source.execute('INSERT INTO bam_ai_business_facts VALUES (?,?,?,?,?)',
                           ('shop-a', AIBusinessFacts._validate({'store': 'Café 🐝'}),
                            4, self.a, 100))
            for table, placeholders in (
                ('bam_ai_memories', '%s,%s,%s,%s'),
                ('bam_ai_business_facts', '%s,%s,%s,%s,%s'),
            ):
                select = f'SELECT * FROM {table} ORDER BY 1,2'
                source_rows = source.execute(select).fetchall()
                for row in source_rows:
                    self.conn.execute(f'INSERT INTO {table} VALUES ({placeholders})', row)
                self.assertEqual(self.conn.execute(select).fetchall(), source_rows)
        self.assertEqual(self.conn.execute("""SELECT
            convert_to(memory_json,'UTF8') FROM bam_ai_memories
            WHERE tenant_id='shop-b' AND subject_id=%s""", (self.a,)).fetchone(),
            (legacy.encode('utf-8'),))

        compare_and_swap = """UPDATE bam_ai_memories SET memory_json=%s
            WHERE tenant_id=%s AND subject_id=%s AND memory_json=%s"""
        replacement = AIPolicyStore._encode_memory({'tone': 'Direct'})
        self.assertEqual(self.conn.execute(compare_and_swap,
            (replacement, 'shop-b', self.a, canonical)).rowcount, 0)
        self.assertEqual(self.conn.execute(compare_and_swap,
            (replacement, 'shop-a', self.a, canonical)).rowcount, 1)
        self.assertEqual(self.conn.execute(compare_and_swap,
            (canonical, 'shop-a', self.a, canonical)).rowcount, 0)
        self.assertEqual(self.conn.execute("""SELECT memory_json FROM bam_ai_memories
            WHERE tenant_id='shop-b' AND subject_id=%s""", (self.a,)).fetchone(), (legacy,))

    def test_ai_legacy_requests_and_media_require_full_scope(self):
        draft_id, shared_id, ai_only_id, missing_id = self.rid_a, self.rid_b, 'c'*32, 'd'*32
        prompt = 'Synthetic image prompt'
        drafts = (
            ('shop-a', self.a, draft_id, 'facebook', 'Synthetic copy', prompt, 1, 4, 100, 102),
            ('shop-b', self.a, draft_id, 'facebook', 'Synthetic copy', None, 0, 1, 100, 100),
            ('shop-b', self.a, shared_id, 'facebook', 'Synthetic copy', prompt, 1, 1, 100, 100),
            ('shop-b', self.b, shared_id, 'facebook', 'Synthetic copy', prompt, 1, 1, 100, 100),
            ('shop-a', self.a, ai_only_id, 'facebook', 'Synthetic copy', prompt, 1, 1, 100, 100),
        )
        request_cases = (
            ('shop-a', self.a, 'completed', draft_id, True),
            ('shop-a', self.viewer, 'completed', draft_id, False),
            ('shop-b', self.a, 'completed', ai_only_id, False),
            ('shop-a', self.a, 'completed', None, False),
            ('shop-a', self.a, 'in_progress', None, True),
            ('shop-a', self.a, 'failed', None, True),
            ('shop-a', self.a, 'in_progress', draft_id, False),
            ('shop-b', self.a, 'failed', draft_id, False),
        )
        requests = [
            (tenant, subject, f'{index:032x}', 'f'*64, status, draft, 100)
            for index, (tenant, subject, status, draft, _) in enumerate(request_cases)
        ]
        attachments = [
            (f'{index:032x}', tenant, draft, item, 'image/png', 'f'*64,
             f'ci-object-{index}', status, 100)
            for index, (tenant, draft, item, status) in enumerate((
                ('shop-a', draft_id, 'image', 'verified'),
                ('shop-b', shared_id, 'image', 'verified'),
                ('shop-a', ai_only_id, 'image', 'verified'),
                ('shop-b', shared_id, 'image', 'pending'),
                ('shop-a', draft_id, 'caption', 'verified'),
            ))
        ]
        with closing(sqlite3.connect(':memory:')) as source:
            AIContentDraftStore(db=source, policy_store=None)
            AIGenerationIdempotency(db=source, policy_store=None)
            AttachmentRegistry(source)
            for table, rows in (
                ('bam_ai_draft_components', drafts),
                ('bam_ai_generation_requests', requests),
            ):
                sqlite_params = ','.join('?' for _ in rows[0])
                pg_params = ','.join('%s' for _ in rows[0])
                source.executemany(f'INSERT INTO {table} VALUES ({sqlite_params})', rows)
                for row in source.execute(f'SELECT * FROM {table}'):
                    self.conn.execute(f'INSERT INTO {table} VALUES ({pg_params})', row)
            source.executemany('INSERT INTO content_attachments VALUES (?,?,?,?,?,?,?,?,?)',
                               attachments)
            insert_attachment = 'INSERT INTO content_attachments VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)'
            for row in source.execute('SELECT * FROM content_attachments ORDER BY attachment_id'):
                if row[2] == ai_only_id:
                    # SQLite accepted this AI draft parent. The stage-eight
                    # target constraint points exclusively to content_requests.
                    with self.assertRaises(self.psycopg.errors.ForeignKeyViolation) as rejected:
                        self.conn.execute(insert_attachment, row)
                    self.assertEqual(rejected.exception.diag.constraint_name,
                                     'content_attachments_tenant_request_fkey')
                else:
                    self.conn.execute(insert_attachment, row)

        # A structurally matching historical draft still cannot prove an output
        # receipt, a provider outcome, or which revision a request produced.
        request_review = self.conn.execute("""SELECT r.request_key, r.status,
            r.draft_id, r.request_fingerprint, CASE WHEN r.status='completed'
                THEN d.draft_id IS NOT NULL ELSE r.draft_id IS NULL END
            FROM bam_ai_generation_requests AS r
            LEFT JOIN bam_ai_draft_components AS d USING (tenant_id,subject_id,draft_id)
            ORDER BY r.request_key""").fetchall()
        self.assertEqual(request_review, [
            (row[2], row[4], row[5], row[3], case[4])
            for row, case in zip(requests, request_cases)
        ])
        self.assertEqual(self.conn.execute("""SELECT subject_id, image_prompt,
            needs_media, revision FROM bam_ai_draft_components WHERE draft_id=%s
            ORDER BY tenant_id""", (draft_id,)).fetchall(),
            [(self.a, prompt, 1, 4), (self.a, None, 0, 1)])

        # The legacy attachment key has no subject. A second same-tenant
        # draft owner with the same ID makes attribution ambiguous.
        media_cases = (
            ('shop-a', self.a, draft_id, 0, (True, 1, True, 1)),
            ('shop-b', self.a, shared_id, 1, (True, 1, True, 2)),
            ('shop-b', self.a, draft_id, 0, (True, 0, False, 1)),
            ('shop-a', self.a, ai_only_id, 2, (True, 1, False, 1)),
            ('shop-b', self.a, shared_id, 3, (True, 1, False, 2)),
            ('shop-a', self.a, draft_id, 4, (True, 1, False, 1)),
            ('shop-a', self.viewer, draft_id, 0, (False, None, True, 1)),
            ('shop-a', self.a, missing_id, 0, (False, None, False, 0)),
        )
        for tenant, subject, draft, index, expected in media_cases:
            with self.subTest(tenant=tenant, subject=subject, draft=draft, index=index):
                # The same composite link is reused only within this transaction.
                with self.conn.transaction(force_rollback=True):
                    self.conn.execute("""INSERT INTO bam_ai_draft_verified_media
                        VALUES (%s,%s,%s,%s,103)""",
                        (tenant, subject, draft, attachments[index][0]))
                    self.assertEqual(self.conn.execute("""SELECT d.draft_id IS NOT NULL,
                        d.needs_media, a.attachment_id IS NOT NULL,
                        (SELECT count(*) FROM bam_ai_draft_components AS candidate
                         WHERE candidate.tenant_id=l.tenant_id AND candidate.draft_id=l.draft_id)
                        FROM bam_ai_draft_verified_media AS l
                        LEFT JOIN bam_ai_draft_components AS d
                            USING (tenant_id,subject_id,draft_id)
                        LEFT JOIN content_attachments AS a
                            ON a.tenant_id=l.tenant_id AND a.request_id=l.draft_id
                           AND a.item='image' AND a.attachment_id=l.attachment_id
                           AND a.status='verified'""").fetchone(),
                        expected)

    def test_ai_monthly_usage_preserves_unpriced_counts_across_source_versions(self):
        scopes = (
            ('bam_ai_usage', ('shop-a', self.a)),
            ('bam_ai_tenant_usage', ('shop-a',)),
            ('bam_ai_operator_usage', ()),
        )
        for version, values, expected in (
            ('counts-only', (3,), (3, 0, 3)),
            ('reserved-only', (5, 120), (5, 120, 5)),
            ('current', (7, 260, 2), (7, 260, 2)),
        ):
            with self.subTest(version=version), closing(sqlite3.connect(':memory:')) as source:
                policy = AIPolicyStore(db=source, sessions=None, directory=None)
                source.execute("""CREATE TABLE bam_ai_tenant_usage (
                    tenant_id TEXT NOT NULL, month TEXT NOT NULL, accepted INTEGER NOT NULL,
                    PRIMARY KEY (tenant_id,month))""")
                source.execute("""CREATE TABLE bam_ai_operator_usage (
                    month TEXT PRIMARY KEY, accepted INTEGER NOT NULL)""")
                for table, scope in scopes:
                    if len(values) >= 2:
                        source.execute(f'ALTER TABLE {table} ADD COLUMN reserved_micro_usd '
                                       'INTEGER NOT NULL DEFAULT 0')
                    if len(values) == 3:
                        source.execute(f'ALTER TABLE {table} ADD COLUMN unpriced_requests '
                                       'INTEGER NOT NULL DEFAULT 0')
                    row = (*scope, '2026-11', *values)
                    placeholders = ','.join('?' for _ in row)
                    source.execute(f'INSERT INTO {table} VALUES ({placeholders})', row)
                SponsoredAIQuota(db=source, policy_store=policy)
                SponsoredAIQuota(db=source, policy_store=policy)
                with self.conn.transaction(force_rollback=True):
                    for table, scope in scopes:
                        row = source.execute(f'SELECT * FROM {table}').fetchone()
                        self.assertEqual(row, (*scope, '2026-11', *expected))
                        placeholders = ','.join('%s' for _ in row)
                        self.conn.execute(f'INSERT INTO {table} VALUES ({placeholders})', row)
                        self.assertEqual(self.conn.execute(f'SELECT * FROM {table}').fetchone(),
                                         row)

    def test_ai_budget_state_never_unpauses_or_approves_paid_ai(self):
        self.assertEqual(self.conn.execute("""SELECT paused
            FROM bam_ai_operator_control WHERE control_id=1"""
            ).fetchone()[0],1)
        columns={row[0] for row in self.conn.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema=%s AND table_name='bam_ai_usage'""",
            (_SCHEMA,)).fetchall()}
        self.assertTrue({'reserved_micro_usd','unpriced_requests'}<=columns)
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.conn.execute("""INSERT INTO bam_ai_operator_control
                (control_id,paused,updated_at) VALUES (2,0,101)""")
        self.assertEqual(self.conn.execute("""SELECT paused
            FROM bam_ai_operator_control WHERE control_id=1"""
            ).fetchone()[0],1)

    def test_session_backed_draft_read_has_live_authentication_guards(self):
        import hashlib
        token='Synthetic_Session_Token_For_One_Business_Only_123'
        token_hash=hashlib.sha256(token.encode('ascii')).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at,revoked_at)
            VALUES (%s,%s,'shop-a','owner',3600,NULL)""",
            (token_hash,self.a))
        def query(tenant='shop-a',rid=None,now=101):
            sql,params=prepare_session_draft_read(
                raw_session_token=token,tenant_id=tenant,
                request_id=self.rid_a if rid is None else rid,
                server_now=now)
            self.assertNotIn(token,sql)
            self.assertNotIn(token,str(params))
            return self.conn.execute(sql,params).fetchone()
        self.assertEqual(query()[2],'private tenant A copy')
        self.assertIsNone(query(tenant='shop-b',rid=self.rid_b))
        self.assertIsNone(query(now=3600))
        self.conn.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.assertIsNone(query())
        self.conn.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.conn.execute("""UPDATE sessions SET revoked_at=105
            WHERE token_hash=%s""",(token_hash,))
        self.assertIsNone(query())
        self.conn.execute("""UPDATE sessions SET revoked_at=NULL
            WHERE token_hash=%s""",(token_hash,))
        self.conn.execute("""UPDATE bam_identities SET active=0
            WHERE subject_id=%s""",(self.a,))
        self.assertIsNone(query())

    def test_session_backed_calendar_stays_a_nonexecuting_proposal(self):
        import hashlib
        token='Synthetic_BAM_Calendar_Read_Token_1234567890'
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",
            (hashlib.sha256(token.encode()).hexdigest(),self.a))
        self.conn.execute("""INSERT INTO bam_calendar_proposals
            (tenant_id,request_id,draft_revision,utc_at,
             local_date,local_time,timezone,updated_at,updated_by,
             proposal_token)
            VALUES ('shop-a',%s,1,'2026-11-12T16:00:00+00:00',
             '2026-11-12','11:00','America/New_York',101,%s,%s)""",
            (self.rid_a,self.a,'f'*32))
        sql,params=prepare_session_calendar_read(
            raw_session_token=token,tenant_id='shop-a',
            request_id=self.rid_a,server_now=101)
        self.assertEqual(self.conn.execute(sql,params).fetchone()[0],
                         self.rid_a)
        sql,params=prepare_session_calendar_read(
            raw_session_token=token,tenant_id='shop-b',
            request_id=self.rid_b,server_now=101)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        self.conn.execute("""UPDATE sessions SET revoked_at=102
            WHERE token_hash=%s""",(
                hashlib.sha256(token.encode()).hexdigest(),))
        sql,params=prepare_session_calendar_read(
            raw_session_token=token,tenant_id='shop-a',
            request_id=self.rid_a,server_now=103)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())

    def test_private_approved_facts_do_not_leak_to_other_tenants(self):
        self.conn.execute("""INSERT INTO truthguard_facts
            (tenant_id,fact_id,claim_key,value,source,approved_by,
             approved_at,expires_at)
            VALUES ('shop-a','fact-1','hours','Synthetic test fact',
                    'internal-fixture',%s,101,150)""",(self.a,))
        self.conn.execute("""INSERT INTO truthguard_facts
            (tenant_id,fact_id,claim_key,value,source,approved_by,
             approved_at,expires_at)
            VALUES ('shop-b','fact-1','hours','Other business private fact',
                    'internal-fixture',%s,101,150)""",(self.b,))
        sql,params=prepare_current_private_facts(
            tenant_id='shop-a',verified_subject_id=self.a,server_now=120)
        rows=self.conn.execute(sql,params).fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][2],'Synthetic test fact')
        for tenant,actor in (
            ('shop-a',self.viewer),('shop-b',self.a)):
            sql,params=prepare_current_private_facts(
                tenant_id=tenant,verified_subject_id=actor,server_now=120)
            self.assertEqual(self.conn.execute(sql,params).fetchall(),[])
        sql,params=prepare_current_private_facts(
            tenant_id='shop-a',verified_subject_id=self.a,server_now=151)
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])
        self.conn.execute("""UPDATE truthguard_facts SET revoked_at=110
            WHERE tenant_id='shop-a' AND fact_id='fact-1'""")
        sql,params=prepare_current_private_facts(
            tenant_id='shop-a',verified_subject_id=self.a,server_now=120)
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])

    def test_editorial_and_email_states_do_not_authorize_publishing(self):
        self.conn.execute("""INSERT INTO editorial_inbox
            (tenant_id,platform,account_id,original_url,topic,summary,
             status,reason,candidate_digest)
            VALUES ('shop-a','facebook','page','https://example.invalid/x',
                    'events','synthetic item','review','needs-review',%s)""",
                    ('a'*64,))
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.conn.execute("""UPDATE editorial_inbox SET status='published'
                WHERE tenant_id='shop-a'""")
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.conn.execute("""INSERT INTO creator_identities
                (tenant_id,platform,account_id,status,reason)
                VALUES ('shop-a','facebook','page','published','bad')""")
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.conn.execute("""INSERT INTO bam_email_actions
                (token_hash,subject_id,purpose,expires_at)
                VALUES (%s,%s,'send_marketing',200)""",
                ('f'*64,self.a))
        self.assertEqual(self.conn.execute("""SELECT status
            FROM editorial_inbox WHERE tenant_id='shop-a'""").fetchone(),
            ('review',))

    def test_manual_tenant_post_approval_fk_does_not_publish(self):
        for tenant in ('shop-a','shop-b'):
            self.conn.execute("""INSERT INTO tenant_posts
               (tenant_id,post_id,content,category,status)
               VALUES (%s,'draft-1',%s,'marketing','approval_required')""",
               (tenant,'private '+tenant))
        self.conn.execute("""INSERT INTO tenant_approvals
            (tenant_id,post_id,actor_id,decision)
            VALUES ('shop-a','draft-1',%s,'approved')""",(self.a,))
        sql,params=prepare_tenant_post_review(
            tenant_id='shop-a',post_id='draft-1',
            verified_subject_id=self.a)
        row=self.conn.execute(sql,params).fetchone()
        self.assertEqual(row[1],'private shop-a')
        self.assertEqual(row[3],'approval_required')
        self.assertEqual(row[4],'approved')
        sql,params=prepare_tenant_post_review(
            tenant_id='shop-b',post_id='draft-1',
            verified_subject_id=self.a)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation):
            self.conn.execute("""INSERT INTO tenant_approvals
                (tenant_id,post_id,actor_id,decision)
                VALUES ('shop-b','missing-post',%s,'approved')""",
                (self.b,))
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.conn.execute("""UPDATE tenant_posts SET status='published'
                WHERE tenant_id='shop-a' AND post_id='draft-1'""")
        self.conn.execute("""UPDATE members SET active=0
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        sql,params=prepare_tenant_post_review(
            tenant_id='shop-a',post_id='draft-1',
            verified_subject_id=self.a)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())

    def test_schedule_preferences_are_private_and_not_executable(self):
        for tenant in ('shop-a','shop-b'):
            self.conn.execute("""INSERT INTO scheduling_settings
                (tenant_id,mode,timezone_name,weekly_json,
                 preferred_hours_json,revision)
                VALUES (%s,'manual','America/New_York','{}','[]',1)""",
                (tenant,))
        sql,params=prepare_tenant_schedule_read(
            tenant_id='shop-a',verified_subject_id=self.a)
        self.assertEqual(self.conn.execute(sql,params).fetchone()[0],'manual')
        sql,params=prepare_tenant_schedule_read(
            tenant_id='shop-b',verified_subject_id=self.a)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        sql,params=prepare_tenant_schedule_read(
            tenant_id='shop-a',verified_subject_id=self.viewer)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        self.conn.execute("""UPDATE bam_identities SET active=0
            WHERE subject_id=%s""",(self.a,))
        sql,params=prepare_tenant_schedule_read(
            tenant_id='shop-a',verified_subject_id=self.a)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())

    def test_business_research_fk_and_private_tenant_read(self):
        for tenant in ('shop-a','shop-b'):
            self.conn.execute("""INSERT INTO business_profiles
                (tenant_id,display_name,industry) VALUES (%s,%s,'retail')""",
                (tenant,'Business '+tenant))
            self.conn.execute("""INSERT INTO business_topics
                (tenant_id,topic) VALUES (%s,'merch')""",(tenant,))
            self.conn.execute("""INSERT INTO business_sources
                (tenant_id,source_url,source_name,topic,approved)
                VALUES (%s,%s,'Private source','merch',1)""",
                (tenant,'https://source.invalid/'+tenant))
        sql,params=prepare_business_sources_read(
            tenant_id='shop-a',verified_subject_id=self.a)
        rows=self.conn.execute(sql,params).fetchall()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0][0],'https://source.invalid/shop-a')
        sql,params=prepare_business_sources_read(
            tenant_id='shop-b',verified_subject_id=self.a)
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])
        sql,params=prepare_business_sources_read(
            tenant_id='shop-a',verified_subject_id=self.viewer)
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])
        with self.assertRaises(self.psycopg.errors.ForeignKeyViolation):
            self.conn.execute("""INSERT INTO business_sources
                (tenant_id,source_url,source_name,topic,approved)
                VALUES ('shop-a','https://bad.invalid','bad','not-a-topic',1)""")
        self.conn.execute("""UPDATE members SET active=0
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        sql,params=prepare_business_sources_read(
            tenant_id='shop-a',verified_subject_id=self.a)
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])

    def test_private_audience_data_requires_current_owner(self):
        for tenant in ('shop-a','shop-b'):
            self.conn.execute("""INSERT INTO audience_observations
                (tenant_id,platform,source_post_id,candidate,
                 engagement_rate,measured_at,source_name)
                VALUES (%s,'facebook',%s,'evening',0.4,101,'fixture')""",
                (tenant,'post-'+tenant))
        sql,params=prepare_private_audience_read(tenant_id='shop-a',
            platform='facebook',verified_subject_id=self.a)
        self.assertEqual(self.conn.execute(sql,params).fetchone()[0],
                         'post-shop-a')
        sql,params=prepare_private_audience_read(tenant_id='shop-b',
            platform='facebook',verified_subject_id=self.a)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        sql,params=prepare_private_audience_read(tenant_id='shop-a',
            platform='facebook',verified_subject_id=self.viewer)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        self.conn.execute("""UPDATE bam_identities SET email_verified=0
            WHERE subject_id=%s""",(self.a,))
        sql,params=prepare_private_audience_read(tenant_id='shop-a',
            platform='facebook',verified_subject_id=self.a)
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM audience_observations""").fetchone()[0],2)

    def test_provider_metadata_stays_tenant_private_without_vault_reference(self):
        self.conn.execute("""INSERT INTO provider_connections
           (tenant_id,platform,account_id,vault_reference,scope,state,
            expires_at,updated_at)
           VALUES ('shop-a','facebook','page-a','vault:synthetic-only',
             'read_insights','pending',NULL,101)""")
        self.conn.execute("""INSERT INTO provider_connections
           (tenant_id,platform,account_id,vault_reference,scope,state,
            expires_at,updated_at)
           VALUES ('shop-b','facebook','page-b','vault:other-synthetic',
             'read_insights','pending',NULL,101)""")
        sql,params=prepare_connections_read(tenant_id='shop-a',
            verified_subject_id=self.a)
        rows=self.conn.execute(sql,params).fetchall()
        self.assertEqual(len(rows),1)
        preview=safe_connection_preview(rows[0])
        self.assertEqual(preview['account_id'],'page-a')
        self.assertNotIn('vault:synthetic-only',str(preview))
        self.assertFalse(preview['publishing_enabled'])
        sql,params=prepare_connections_read(tenant_id='shop-b',
            verified_subject_id=self.a)
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])
        self.conn.execute("""UPDATE members SET role='content_creator'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        sql,params=prepare_connections_read(tenant_id='shop-a',
            verified_subject_id=self.a)
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])

    def test_ai_usage_private_by_identity_and_business(self):
        self.conn.execute("""INSERT INTO bam_ai_usage
            (tenant_id,subject_id,month,accepted)
            VALUES ('shop-a',%s,'2026-11',8)""",(self.a,))
        self.conn.execute("""INSERT INTO bam_ai_usage
            (tenant_id,subject_id,month,accepted)
            VALUES ('shop-b',%s,'2026-11',3)""",(self.b,))
        sql,params=prepare_personal_ai_usage(
            tenant_id='shop-a',verified_subject_id=self.a,month='2026-11')
        self.assertEqual(self.conn.execute(sql,params).fetchone(),(8,))
        sql,params=prepare_personal_ai_usage(
            tenant_id='shop-b',verified_subject_id=self.a,month='2026-11')
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        self.conn.execute("""UPDATE bam_identities SET active=0
            WHERE subject_id=%s""",(self.a,))
        sql,params=prepare_personal_ai_usage(
            tenant_id='shop-a',verified_subject_id=self.a,month='2026-11')
        self.assertIsNone(self.conn.execute(sql,params).fetchone())

    def test_collaboration_schema_and_owner_invitation_privacy(self):
        columns=self.conn.execute("""SELECT column_name,data_type
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name='bam_business_invitation_events'
            ORDER BY ordinal_position""",(_SCHEMA,)).fetchall()
        self.assertIn(('event_id','bigint'),columns)
        self.conn.execute("""INSERT INTO bam_business_invitations
            (token_hash,tenant_id,email,role,expires_at,created_by,
             invitation_id,delivery_state)
            VALUES (%s,'shop-a','guest@private.test','viewer',500,%s,%s,
                    'delivered')""",('1'*64,self.a,'e'*32))
        sql,params=prepare_pending_owner_invitations(tenant_id='shop-a',
            verified_subject_id=self.a,server_now=101)
        row=self.conn.execute(sql,params).fetchone()
        self.assertEqual(row[0],'e'*32)
        self.assertEqual(row[1],'guest@private.test')
        self.assertEqual(len(row),4)
        self.assertNotIn('1'*64,str(row))
        for actor,tenant in (
            (self.viewer,'shop-a'),(self.b,'shop-a'),(self.a,'shop-b')):
            sql,params=prepare_pending_owner_invitations(tenant_id=tenant,
                verified_subject_id=actor,server_now=101)
            self.assertEqual(self.conn.execute(sql,params).fetchall(),[])
        self.conn.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        sql,params=prepare_pending_owner_invitations(tenant_id='shop-a',
            verified_subject_id=self.a,server_now=101)
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])
        self.conn.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.conn.execute("""UPDATE bam_business_invitations SET consumed_at=101
            WHERE invitation_id=%s""",('e'*32,))
        self.assertEqual(self.conn.execute(sql,params).fetchall(),[])

    def test_collaboration_indexes_and_constraints(self):
        self.conn.execute("""INSERT INTO bam_business_invitations
            (token_hash,tenant_id,email,role,expires_at,created_by,
             invitation_id,delivery_state)
            VALUES (%s,'shop-a','guest@private.test','viewer',500,%s,%s,
                   'delivered')""",('2'*64,self.a,'f'*32))
        with self.assertRaises(self.psycopg.errors.UniqueViolation):
            self.conn.execute("""INSERT INTO bam_business_invitations
                (token_hash,tenant_id,email,role,expires_at,created_by,
                 invitation_id,delivery_state)
                VALUES (%s,'shop-b','guest2@private.test','viewer',500,%s,%s,
                        'delivered')""",('3'*64,self.b,'f'*32))
        self.conn.execute("""INSERT INTO bam_business_invitation_events
            (tenant_id,invitation_id,action,actor_id,occurred_at)
            VALUES ('shop-a',%s,'delivered',%s,100)""",
            ('f'*32,self.a))
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM bam_business_invitation_events
            WHERE tenant_id='shop-a'""").fetchone()[0],1)
        with self.assertRaises(self.psycopg.errors.CheckViolation):
            self.conn.execute("""INSERT INTO bam_review_feedback_events
                (event_id,tenant_id,request_id,action,draft_revision,
                 occurred_at,actor_id) VALUES (%s,'shop-a',%s,
                 'published',1,101,%s)""",
                ('e'*32,self.rid_a,self.a))

    def test_two_independent_postgres_clients_cannot_both_write_stale_token(self):
        barrier=threading.Barrier(2)
        results=[]
        errors=[]
        def write(priority):
            try:
                con=self._connect()
                try:
                    sql,params=prepare_draft_priority_cas(
                        tenant_id='shop-a',request_id=self.rid_a,
                        verified_subject_id=self.a,
                        expected_priority_token=self.priority_token,
                        priority=priority,server_now=102)
                    barrier.wait(timeout=15)
                    row=con.execute(sql,params).fetchone()
                    results.append(row is not None)
                finally:
                    con.close()
            except Exception as exc:
                errors.append(type(exc).__name__)
        one=threading.Thread(target=write,args=(1,))
        two=threading.Thread(target=write,args=(2,))
        one.start()
        two.start()
        one.join(timeout=20)
        two.join(timeout=20)
        self.assertFalse(one.is_alive() or two.is_alive())
        self.assertEqual(errors,[])
        self.assertEqual(sorted(results),[False,True])
        current=self.conn.execute("""SELECT priority,revision
            FROM content_requests WHERE request_id=%s""",
            (self.rid_a,)).fetchone()
        self.assertIn(current[0],(1,2))
        self.assertEqual(current[1],1)


    def test_pg_session_bound_priority_edit_is_tenant_scoped_and_revocable(self):
        import hashlib
        from neon_session_write_contract import prepare_session_priority_cas
        token='Synthetic_Postgres_Authenticated_Edit_Token_123'
        digest=hashlib.sha256(token.encode()).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",(digest,self.a))
        def prepare(tenant='shop-a',rid=None,expected=None,now=101):
            return prepare_session_priority_cas(
                raw_session_token=token,tenant_id=tenant,
                request_id=self.rid_a if rid is None else rid,
                expected_priority_token=self.priority_token if expected is None
                    else expected,priority=6,server_now=now)
        sql,params=prepare()
        self.assertNotIn(token,sql+str(params))
        self.assertNotIn(self.a,sql+str(params))
        self.assertIsNone(self.conn.execute(*prepare(
            tenant='shop-b',rid=self.rid_b)).fetchone())
        self.assertIsNone(self.conn.execute(*prepare(now=3600)).fetchone())
        self.conn.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.assertIsNone(self.conn.execute(*prepare()).fetchone())
        self.conn.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        receipt=priority_cas_result(self.conn.execute(sql,params).fetchone(),
                                    expected_new_token=params[1])
        self.assertFalse(receipt['publishing_enabled'])
        self.assertIsNone(self.conn.execute(sql,params).fetchone())
        self.assertEqual(self.conn.execute("""SELECT priority,revision,draft_text
            FROM content_requests WHERE request_id=%s""",(self.rid_a,)
            ).fetchone(),(6,1,'private tenant A copy'))
        self.conn.execute("""UPDATE sessions SET revoked_at=102
            WHERE token_hash=%s""",(digest,))
        self.assertIsNone(self.conn.execute(*prepare(
            expected=params[1],now=103)).fetchone())

    def test_pg_two_session_bound_concurrent_cas_only_one_wins(self):
        import hashlib
        from neon_session_write_contract import prepare_session_priority_cas
        token='Synthetic_Postgres_Concurrent_Edit_Token_123456'
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",
            (hashlib.sha256(token.encode()).hexdigest(),self.a))
        barrier=threading.Barrier(2)
        results=[]
        errors=[]
        def worker(priority):
            conn=self._connect()
            try:
                sql,params=prepare_session_priority_cas(
                    raw_session_token=token,tenant_id='shop-a',
                    request_id=self.rid_a,
                    expected_priority_token=self.priority_token,
                    priority=priority,server_now=101)
                barrier.wait(timeout=15)
                results.append(conn.execute(sql,params).fetchone() is not None)
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                conn.close()
        threads=[threading.Thread(target=worker,args=(v,)) for v in (2,9)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors,[])
        self.assertEqual(sorted(results),[False,True])



    def test_pg_session_bound_owner_invite_read_excludes_other_business(self):
        import hashlib
        from neon_session_collaboration_contract import (
            prepare_session_pending_owner_invitations)
        token='Synthetic_Postgres_Owner_Invitation_Session_1234'
        digest=hashlib.sha256(token.encode()).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",(digest,self.a))
        for tenant,actor,email,iid in (
            ('shop-a',self.a,'guest@private.test','c'*32),
            ('shop-b',self.b,'other@private.test','d'*32)):
            self.conn.execute("""INSERT INTO bam_business_invitations
                (token_hash,tenant_id,email,role,expires_at,
                 created_by,invitation_id,delivery_state)
                VALUES (%s,%s,%s,'viewer',500,%s,%s,'delivered')""",
                (('a' if tenant=='shop-a' else 'b')*64,
                 tenant,email,actor,iid))
        def query(tenant='shop-a',now=101):
            sql,params=prepare_session_pending_owner_invitations(
                raw_session_token=token,tenant_id=tenant,server_now=now)
            self.assertNotIn(token,sql+str(params))
            self.assertNotIn('v.token_hash',sql)
            return self.conn.execute(sql,params).fetchall()
        self.assertEqual(query(),
            [('c'*32,'guest@private.test','viewer',500)])
        self.assertEqual(query('shop-b'),[])
        self.assertEqual(query(now=500),[])
        self.conn.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.assertEqual(query(),[])
        self.conn.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.conn.execute("""UPDATE bam_identities SET active=0
            WHERE subject_id=%s""",(self.a,))
        self.assertEqual(query(),[])
        self.conn.execute("""UPDATE bam_identities SET active=1
            WHERE subject_id=%s""",(self.a,))
        self.conn.execute("""UPDATE sessions SET revoked_at=101
            WHERE token_hash=%s""",(digest,))
        self.assertEqual(query(),[])



    def test_ci_psycopg_session_facade_executes_real_nonpublishing_io(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_CI_Psycopg_Adapter_Authenticated_Session_1234'
        digest=hashlib.sha256(token.encode()).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",(digest,self.a))
        owner=EphemeralSessionPostgres(self.conn)
        args={'raw_session_token':token,'tenant_id':'shop-a',
              'request_id':self.rid_a,'server_now':101}
        draft=owner.read_held_draft(**args)
        self.assertEqual(draft['draft_text'],'private tenant A copy')
        self.assertFalse(draft['publishing_enabled'])
        self.assertEqual(draft['posts_scheduled'],0)
        self.assertIsNone(owner.read_held_draft(
            raw_session_token=token,tenant_id='shop-b',
            request_id=self.rid_b,server_now=101))
        self.assertIsNone(owner.read_calendar_proposal(**args))
        with self.assertRaises(PermissionError):
            owner.update_draft_priority(
                **args,expected_priority_token='f'*32,priority=6)
        receipt=owner.update_draft_priority(
            **args,expected_priority_token=self.priority_token,priority=6)
        self.assertEqual(receipt['priority'],6)
        self.assertFalse(receipt['publishing_enabled'])
        self.assertEqual(receipt['draft_revision'],1)
        self.assertEqual(self.conn.execute("""SELECT draft_text,revision
            FROM content_requests WHERE tenant_id='shop-a'
            AND request_id=%s""",(self.rid_a,)
            ).fetchone(),('private tenant A copy',1))
        with self.assertRaises(PermissionError):
            owner.update_draft_priority(
                **args,expected_priority_token=self.priority_token,priority=9)
        self.conn.execute("""INSERT INTO bam_business_invitations
            (token_hash,tenant_id,email,role,expires_at,
             created_by,invitation_id,delivery_state)
            VALUES (%s,'shop-a','guest@private.test','viewer',
                    500,%s,%s,'delivered')""",('a'*64,self.a,'c'*32))
        invitations=owner.read_owner_pending_invitations(
            raw_session_token=token,tenant_id='shop-a',server_now=101)
        self.assertEqual(invitations['items'],[{
            'invitation_id':'c'*32,'email':'guest@private.test',
            'role':'viewer','expires_at':500}])
        self.assertNotIn('a'*64,str(invitations))
        self.assertFalse(invitations['publishing_enabled'])
        second=self._connect()
        try:
            separate=EphemeralSessionPostgres(second)
            self.conn.execute("""UPDATE sessions SET revoked_at=102
                WHERE token_hash=%s""",(digest,))
            self.assertIsNone(separate.read_held_draft(
                raw_session_token=token,tenant_id='shop-a',
                request_id=self.rid_a,server_now=103))
            self.assertEqual(separate.read_owner_pending_invitations(
                raw_session_token=token,tenant_id='shop-a',
                server_now=103)['items'],[])
            with self.assertRaises(PermissionError):
                separate.update_draft_priority(
                    raw_session_token=token,tenant_id='shop-a',
                    request_id=self.rid_a,
                    expected_priority_token=receipt['priority_token'],
                    priority=2,server_now=103)
        finally:
            second.close()

    def test_ci_psycopg_session_facade_refuses_untrusted_connection(self):
        from neon_ci_session_adapter import EphemeralSessionPostgres
        with self.assertRaises(TypeError):
            EphemeralSessionPostgres(object())
        second=self._connect()
        try:
            second.execute('SET search_path TO public')
            with self.assertRaises(PermissionError):
                EphemeralSessionPostgres(second)
        finally:
            second.close()



    def test_ci_psycopg_session_inbox_pages_and_business_isolation(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_CI_Inbox_Session_1234567890123456789012'
        digest=hashlib.sha256(token.encode('ascii')).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",(digest,self.a))
        for rid,created,status,copy in (
            ('e'*32,100,'ready_for_review','shop A review'),
            ('f'*32,100,'postponed','shop A postponed'),
            ('9'*32,101,'unavailable','shop A unavailable')):
            self.conn.execute("""INSERT INTO content_requests
                (request_id,tenant_id,channel,draft_text,suggestion,
                 required_items,provided_items,status,priority_token,
                 created_at,updated_at)
                VALUES (%s,'shop-a','facebook',%s,'photo','[]',
                        '{}',%s,%s,%s,%s)""",
                (rid,copy,status,'c'*32,created,created))
        adapter=EphemeralSessionPostgres(self.conn)
        params={'raw_session_token':token,'tenant_id':'shop-a',
                'server_now':101,'limit':2}
        first=adapter.read_held_inbox_page(**params)
        self.assertEqual([x['request_id'] for x in first['items']],
                         [self.rid_a,'e'*32])
        self.assertEqual(first['next_cursor'],
                         {'created_at':100,'request_id':'e'*32})
        self.assertTrue(first['has_more'])
        second=adapter.read_held_inbox_page(
            **params,**{'after_created_at':100,'after_request_id':'e'*32})
        self.assertEqual([x['request_id'] for x in second['items']],
                         ['f'*32,'9'*32])
        self.assertFalse(second['has_more'])
        self.assertIsNone(second['next_cursor'])
        only_review=adapter.read_held_inbox_page(
            raw_session_token=token,tenant_id='shop-a',
            server_now=101,limit=50,status='ready_for_review')
        self.assertEqual([x['draft_text'] for x in only_review['items']],
                         ['shop A review'])
        cross=adapter.read_held_inbox_page(
            raw_session_token=token,tenant_id='shop-b',server_now=101)
        self.assertEqual(cross['items'],[])
        self.assertEqual(first['posts_scheduled'],0)
        self.assertFalse(first['publishing_enabled'])
        self.assertNotIn('private tenant B copy',str(first))

    def test_ci_psycopg_session_inbox_revocation_and_live_access(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_Inbox_Viewer_Permission_Token_123456789'
        digest=hashlib.sha256(token.encode('ascii')).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','viewer',3600)""",
            (digest,self.viewer))
        separate=self._connect()
        try:
            adapter=EphemeralSessionPostgres(separate)
            args={'raw_session_token':token,'tenant_id':'shop-a',
                  'server_now':101}
            self.assertEqual(
                len(adapter.read_held_inbox_page(**args)['items']),1)
            self.conn.execute("""UPDATE members SET role='owner'
                WHERE tenant_id='shop-a' AND subject_id=%s""",
                (self.viewer,))
            self.assertEqual(
                adapter.read_held_inbox_page(**args)['items'],[])
            self.conn.execute("""UPDATE members SET role='viewer'
                WHERE tenant_id='shop-a' AND subject_id=%s""",
                (self.viewer,))
            self.conn.execute("""UPDATE bam_identities SET active=0
                WHERE subject_id=%s""",(self.viewer,))
            self.assertEqual(
                adapter.read_held_inbox_page(**args)['items'],[])
            self.conn.execute("""UPDATE bam_identities SET active=1
                WHERE subject_id=%s""",(self.viewer,))
            self.conn.execute("""UPDATE sessions SET revoked_at=101
                WHERE token_hash=%s""",(digest,))
            self.assertEqual(
                adapter.read_held_inbox_page(**args)['items'],[])
            with self.assertRaises(ValueError):
                adapter.read_held_inbox_page(
                    **args,limit=51)
        finally:
            separate.close()


    def test_ci_psycopg_owner_team_roster_authentication_and_privacy(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        owner_token='Synthetic_PG_Owner_Team_Roster_123456789012345'
        viewer_token='Synthetic_PG_Viewer_Team_Roster_12345678901234'
        owner_digest=hashlib.sha256(owner_token.encode('ascii')).hexdigest()
        viewer_digest=hashlib.sha256(viewer_token.encode('ascii')).hexdigest()
        for digest,subject,role in (
            (owner_digest,self.a,'owner'),
            (viewer_digest,self.viewer,'viewer')):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (%s,%s,'shop-a',%s,3600)""",
                (digest,subject,role))
        separate=self._connect()
        try:
            adapter=EphemeralSessionPostgres(separate)
            args={'raw_session_token':owner_token,'tenant_id':'shop-a',
                  'server_now':101}
            roster=adapter.read_owner_team_roster(**args)
            self.assertEqual(roster['status'],'private_team_preview')
            self.assertEqual([m['member_id'] for m in roster['members']],
                             [self.a,self.viewer])
            self.assertTrue(roster['members'][0]['is_self'])
            self.assertEqual(roster['members'][0]['role'],'owner')
            self.assertTrue(roster['members'][1]['active'])
            self.assertFalse(roster['members'][1]['is_self'])
            self.assertFalse(roster['publishing_enabled'])
            self.assertNotIn(self.b,str(roster))
            with self.assertRaises(PermissionError):
                adapter.read_owner_team_roster(
                    raw_session_token=owner_token,
                    tenant_id='shop-b',server_now=101)
            with self.assertRaises(PermissionError):
                adapter.read_owner_team_roster(
                    raw_session_token=viewer_token,
                    tenant_id='shop-a',server_now=101)
            self.conn.execute("""UPDATE bam_identities SET email_verified=0
                WHERE subject_id=%s""",(self.viewer,))
            self.assertIsNone(
                adapter.read_owner_team_roster(**args)['members'][1]['email'])
            self.conn.execute("""UPDATE members SET active=0,revision=2
                WHERE subject_id=%s AND tenant_id='shop-a'""",
                (self.viewer,))
            inactive=adapter.read_owner_team_roster(**args)['members'][1]
            self.assertFalse(inactive['active'])
            self.assertEqual(inactive['revision'],2)
            self.conn.execute("""UPDATE members SET role='viewer'
                WHERE subject_id=%s AND tenant_id='shop-a'""",
                (self.a,))
            with self.assertRaises(PermissionError):
                adapter.read_owner_team_roster(**args)
            self.conn.execute("""UPDATE members SET role='owner'
                WHERE subject_id=%s AND tenant_id='shop-a'""",
                (self.a,))
            self.conn.execute("""UPDATE sessions SET revoked_at=101
                WHERE token_hash=%s""",(owner_digest,))
            with self.assertRaises(PermissionError):
                adapter.read_owner_team_roster(**args)
        finally:
            separate.close()


    def test_pg_authenticated_create_and_revise_held_draft(self):
        import hashlib
        import json
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Draft_Create_Owner_Session_123456789'
        viewer='Synthetic_PG_Draft_Create_Viewer_Session_12345678'
        for bearer,actor,role in ((token,self.a,'owner'),
                                  (viewer,self.viewer,'viewer')):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (%s,%s,'shop-a',%s,3600)""",
                (hashlib.sha256(bearer.encode('ascii')).hexdigest(),
                 actor,role))
        owner=EphemeralSessionPostgres(self.conn)
        base={'raw_session_token':token,'tenant_id':'shop-a',
              'channel':'facebook','draft_text':'New held copy',
              'suggestion':'Use approved artwork',
              'required_items':['image','alt_text'],'server_now':101}
        with self.assertRaises(PermissionError):
            owner.create_held_draft(**(base|{'tenant_id':'shop-b'}))
        with self.assertRaises(PermissionError):
            owner.create_held_draft(
                **(base|{'raw_session_token':viewer}))
        created=owner.create_held_draft(**base,priority=3)
        rid=created['request_id']
        self.assertEqual(len(rid),32)
        self.assertEqual(created['revision'],1)
        self.assertFalse(created['publishing_enabled'])
        self.assertEqual(created['posts_scheduled'],0)
        row=self.conn.execute("""SELECT tenant_id,status,priority,revision,
            provided_items,required_items,draft_text,suggestion
            FROM content_requests WHERE request_id=%s""",(rid,)).fetchone()
        self.assertEqual(row[:5],('shop-a','needs_content',3,1,'{}'))
        self.assertEqual(json.loads(row[5]),['image','alt_text'])
        self.assertEqual(row[6:],
                         ('New held copy','Use approved artwork'))
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM bam_calendar_proposals""").fetchone()[0],0)
        edited=owner.revise_held_draft(
            raw_session_token=token,tenant_id='shop-a',
            request_id=rid,target='draft_text',
            revised_text='Revision two',expected_revision=1,
            server_now=102)
        self.assertEqual(edited['draft_text'],'Revision two')
        self.assertEqual(edited['suggestion'],'Use approved artwork')
        self.assertEqual(edited['revision'],2)
        self.assertFalse(edited['publishing_enabled'])
        with self.assertRaises(PermissionError):
            owner.revise_held_draft(
                raw_session_token=token,tenant_id='shop-a',
                request_id=rid,target='draft_text',
                revised_text='Stale overwrite',expected_revision=1,
                server_now=103)
        with self.assertRaises(PermissionError):
            owner.revise_held_draft(
                raw_session_token=viewer,tenant_id='shop-a',
                request_id=rid,target='suggestion',
                revised_text='Viewer overwrite',expected_revision=2,
                server_now=103)
        other=owner.revise_held_draft(
            raw_session_token=token,tenant_id='shop-a',
            request_id=rid,target='suggestion',
            revised_text='Updated guidance',expected_revision=2,
            server_now=104)
        self.assertEqual(other['revision'],3)
        self.assertEqual(other['status'],'needs_content')
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM tenant_posts').fetchone()[0],0)

    def test_pg_authenticated_write_session_change_and_revocation(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Create_Draft_Revocation_1234567890'
        digest=hashlib.sha256(token.encode('ascii')).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",
            (digest,self.a))
        second=self._connect()
        try:
            adapter=EphemeralSessionPostgres(second)
            base={'raw_session_token':token,'tenant_id':'shop-a',
                  'channel':'facebook','draft_text':'Private copy',
                  'suggestion':'Original photo',
                  'required_items':['image'],'server_now':101}
            created=adapter.create_held_draft(**base)
            self.conn.execute("""UPDATE members SET role='viewer'
                WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
            with self.assertRaises(PermissionError):
                adapter.create_held_draft(**base)
            with self.assertRaises(PermissionError):
                adapter.revise_held_draft(
                    raw_session_token=token,tenant_id='shop-a',
                    request_id=created['request_id'],target='suggestion',
                    revised_text='No access',expected_revision=1,
                    server_now=102)
            self.conn.execute("""UPDATE members SET role='owner'
                WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
            self.conn.execute("""UPDATE bam_identities SET email_verified=0
                WHERE subject_id=%s""",(self.a,))
            with self.assertRaises(PermissionError):
                adapter.create_held_draft(**base)
            self.conn.execute("""UPDATE bam_identities SET email_verified=1
                WHERE subject_id=%s""",(self.a,))
            with self.assertRaises(PermissionError):
                adapter.create_held_draft(
                    **(base|{'server_now':3600}))
            self.conn.execute("""UPDATE sessions SET revoked_at=103
                WHERE token_hash=%s""",(digest,))
            with self.assertRaises(PermissionError):
                adapter.create_held_draft(
                    **(base|{'server_now':104}))
            with self.assertRaises(PermissionError):
                adapter.revise_held_draft(
                    raw_session_token=token,tenant_id='shop-a',
                    request_id=created['request_id'],target='draft_text',
                    revised_text='No access',expected_revision=1,
                    server_now=104)
            self.assertEqual(self.conn.execute("""SELECT revision
                FROM content_requests WHERE request_id=%s""",
                (created['request_id'],)).fetchone()[0],1)
        finally:
            second.close()

    def test_pg_two_clients_only_one_held_revision_wins(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Concurrent_Held_Revision_123456789'
        digest=hashlib.sha256(token.encode('ascii')).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",(digest,self.a))
        adapter=EphemeralSessionPostgres(self.conn)
        created=adapter.create_held_draft(
            raw_session_token=token,tenant_id='shop-a',channel='facebook',
            draft_text='Unchanged original',suggestion='Owned photo',
            required_items=['image'],server_now=101)
        barrier=threading.Barrier(2)
        successes=[]
        errors=[]
        def writer(copy):
            client=self._connect()
            try:
                gateway=EphemeralSessionPostgres(client)
                barrier.wait(timeout=15)
                try:
                    result=gateway.revise_held_draft(
                        raw_session_token=token,tenant_id='shop-a',
                        request_id=created['request_id'],
                        target='draft_text',revised_text=copy,
                        expected_revision=1,server_now=102)
                    successes.append(result['draft_text'])
                except PermissionError:
                    errors.append('stale')
            finally:
                client.close()
        workers=[threading.Thread(target=writer,args=(copy,))
                 for copy in ('Editor A','Editor B')]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=20)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertEqual(len(successes),1)
        self.assertEqual(errors,['stale'])
        row=self.conn.execute("""SELECT draft_text,revision,status
            FROM content_requests WHERE request_id=%s""",
            (created['request_id'],)).fetchone()
        self.assertEqual(row,(successes[0],2,'needs_content'))


    def test_pg_authenticated_review_feedback_and_audit(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        owner='Synthetic_PG_Feedback_Owner_123456789012345678'
        manager='Synthetic_PG_Feedback_Manager_12345678901234567'
        viewer='Synthetic_PG_Feedback_Viewer_123456789012345678'
        self.conn.execute("""INSERT INTO bam_identities
            (subject_id,email,email_verified,active,created_at)
            VALUES ('managerX','managerx@example.test',1,1,100)""")
        self.conn.execute("""INSERT INTO members
            (tenant_id,subject_id,role,active,revision)
            VALUES ('shop-a','managerX','marketing_manager',1,1)""")
        for bearer,actor,role in (
            (owner,self.a,'owner'),
            (manager,'managerX','marketing_manager'),
            (viewer,self.viewer,'viewer')):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (%s,%s,'shop-a',%s,3600)""",
                (hashlib.sha256(bearer.encode()).hexdigest(),actor,role))
        gateway=EphemeralSessionPostgres(self.conn)
        opts={'raw_session_token':owner,'tenant_id':'shop-a',
              'request_id':self.rid_a,'expected_revision':1,
              'expected_feedback_token':None,
              'note':'Check image rights before publication.',
              'server_now':101}
        with self.assertRaises(PermissionError):
            gateway.save_review_feedback(
                **(opts|{'raw_session_token':viewer}))
        with self.assertRaises(PermissionError):
            gateway.save_review_feedback(
                **(opts|{'tenant_id':'shop-b'}))
        receipt=gateway.save_review_feedback(**opts)
        self.assertEqual(receipt['status'],'feedback_only')
        self.assertFalse(receipt['approval_granted'])
        self.assertFalse(receipt['publishing_enabled'])
        read=gateway.read_review_feedback(
            raw_session_token=viewer,tenant_id='shop-a',server_now=102)
        self.assertEqual(len(read['items']),1)
        self.assertFalse(read['items'][0]['stale'])
        self.assertEqual(read['items'][0]['note'],
                         'Check image rights before publication.')
        self.assertFalse(read['approval_granted'])
        self.assertEqual(gateway.read_review_feedback(
            raw_session_token=owner,tenant_id='shop-b',
            server_now=102)['items'],[])
        with self.assertRaises(PermissionError):
            gateway.save_review_feedback(
                **(opts|{'raw_session_token':manager,
                         'expected_feedback_token':'f'*32}))
        updated=gateway.save_review_feedback(
            **(opts|{'raw_session_token':manager,
                     'expected_feedback_token':receipt['feedback_token'],
                     'note':'Permission verified, needs final owner review.',
                     'server_now':103}))
        self.assertNotEqual(updated['feedback_token'],
                            receipt['feedback_token'])
        events=self.conn.execute("""SELECT action,actor_id
            FROM bam_review_feedback_events
            WHERE tenant_id='shop-a' ORDER BY occurred_at""").fetchall()
        self.assertEqual(events,[('created',self.a),
                                 ('updated','managerX')])
        self.assertEqual(self.conn.execute("""SELECT status,revision,draft_text
            FROM content_requests WHERE request_id=%s""",
            (self.rid_a,)).fetchone(),
            ('needs_content',1,'private tenant A copy'))
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM bam_calendar_proposals').fetchone()[0],0)
        self.conn.execute("""UPDATE content_requests SET revision=2
            WHERE request_id=%s""",(self.rid_a,))
        read=gateway.read_review_feedback(
            raw_session_token=owner,tenant_id='shop-a',server_now=104)
        self.assertTrue(read['items'][0]['stale'])
        self.assertEqual(read['items'][0]['current_revision'],2)
        with self.assertRaises(PermissionError):
            gateway.save_review_feedback(
                **(opts|{'expected_feedback_token':updated['feedback_token'],
                         'server_now':104}))

    def test_pg_feedback_concurrency_and_live_revocation(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Concurrent_Feedback_12345678901234'
        digest=hashlib.sha256(token.encode()).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",(digest,self.a))
        gate=threading.Barrier(2)
        successes=[]
        failures=[]
        errors=[]
        def save(note):
            conn=self._connect()
            try:
                app=EphemeralSessionPostgres(conn)
                gate.wait(timeout=15)
                try:
                    result=app.save_review_feedback(
                        raw_session_token=token,tenant_id='shop-a',
                        request_id=self.rid_a,expected_revision=1,
                        expected_feedback_token=None,note=note,
                        server_now=101)
                    successes.append(result)
                except PermissionError:
                    failures.append('already exists')
            except Exception as error:
                errors.append(type(error).__name__)
            finally:
                conn.close()
        threads=[threading.Thread(target=save,args=(note,))
                 for note in ('Editor one review','Editor two review')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors,[])
        self.assertEqual(len(successes),1)
        self.assertEqual(failures,['already exists'])
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM bam_review_feedback_events""").fetchone()[0],1)
        self.assertFalse(successes[0]['publishing_enabled'])
        second=self._connect()
        try:
            app=EphemeralSessionPostgres(second)
            self.conn.execute("""UPDATE members SET role='viewer'
                WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
            with self.assertRaises(PermissionError):
                app.save_review_feedback(
                    raw_session_token=token,tenant_id='shop-a',
                    request_id=self.rid_a,expected_revision=1,
                    expected_feedback_token=successes[0]['feedback_token'],
                    note='Unauthorized edit',server_now=102)
            self.conn.execute("""UPDATE members SET role='owner'
                WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
            self.conn.execute("""UPDATE sessions SET revoked_at=102
                WHERE token_hash=%s""",(digest,))
            with self.assertRaises(PermissionError):
                app.save_review_feedback(
                    raw_session_token=token,tenant_id='shop-a',
                    request_id=self.rid_a,expected_revision=1,
                    expected_feedback_token=successes[0]['feedback_token'],
                    note='Revoked edit',server_now=103)
            self.assertEqual(app.read_review_feedback(
                raw_session_token=token,tenant_id='shop-a',
                server_now=103)['items'],[])
        finally:
            second.close()
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM bam_review_feedback_events").fetchone()[0],1)



    def test_pg_review_feedback_removal_and_private_history(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        owner='Synthetic_PG_Feedback_History_Owner_12345678'
        manager='Synthetic_PG_Feedback_History_Manager_1234567'
        viewer='Synthetic_PG_Feedback_History_Viewer_12345678'
        self.conn.execute("""INSERT INTO bam_identities
            (subject_id,email,email_verified,active,created_at)
            VALUES ('historyManager','historymanager@example.test',1,1,100)""")
        self.conn.execute("""INSERT INTO members
            (tenant_id,subject_id,role,active,revision)
            VALUES ('shop-a','historyManager','marketing_manager',1,1)""")
        for token,subject,role in (
            (owner,self.a,'owner'),
            (manager,'historyManager','marketing_manager'),
            (viewer,self.viewer,'viewer')):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (%s,%s,'shop-a',%s,3600)""",
                (hashlib.sha256(token.encode('ascii')).hexdigest(),
                 subject,role))
        app=EphemeralSessionPostgres(self.conn)
        opts={'raw_session_token':owner,'tenant_id':'shop-a',
              'request_id':self.rid_a,'expected_revision':1,
              'expected_feedback_token':None,'note':'Check photo rights',
              'server_now':101}
        created=app.save_review_feedback(**opts)
        edited=app.save_review_feedback(
            **(opts|{'raw_session_token':manager,
                     'expected_feedback_token':created['feedback_token'],
                     'note':'Rights still need owner review',
                     'server_now':102}))
        self.assertEqual(app.read_review_feedback_history(
            raw_session_token=viewer,tenant_id='shop-a',
            server_now=103)['events'],[])
        self.assertEqual(app.read_review_feedback_history(
            raw_session_token=owner,tenant_id='shop-b',
            server_now=103)['events'],[])
        with self.assertRaises(PermissionError):
            app.remove_review_feedback(
                raw_session_token=viewer,tenant_id='shop-a',
                request_id=self.rid_a,
                expected_feedback_token=edited['feedback_token'],
                server_now=103)
        with self.assertRaises(PermissionError):
            app.remove_review_feedback(
                raw_session_token=owner,tenant_id='shop-b',
                request_id=self.rid_a,
                expected_feedback_token=edited['feedback_token'],
                server_now=103)
        with self.assertRaises(PermissionError):
            app.remove_review_feedback(
                raw_session_token=owner,tenant_id='shop-a',
                request_id=self.rid_a,
                expected_feedback_token=created['feedback_token'],
                server_now=103)
        result=app.remove_review_feedback(
            raw_session_token=manager,tenant_id='shop-a',
            request_id=self.rid_a,
            expected_feedback_token=edited['feedback_token'],
            server_now=103)
        self.assertEqual(result['removed'],1)
        self.assertFalse(result['approval_granted'])
        self.assertFalse(result['publishing_enabled'])
        self.assertEqual(app.read_review_feedback(
            raw_session_token=viewer,tenant_id='shop-a',
            server_now=103)['items'],[])
        history=app.read_review_feedback_history(
            raw_session_token=owner,tenant_id='shop-a',server_now=103)
        self.assertEqual([e['action'] for e in history['events']],
                         ['removed','updated','created'])
        self.assertFalse(history['truncated'])
        self.assertFalse(history['approval_granted'])
        self.assertFalse(history['publishing_enabled'])
        self.assertNotIn('Rights still need owner review',str(history))
        self.assertEqual(self.conn.execute("""SELECT status,revision,
            draft_text FROM content_requests WHERE request_id=%s""",
            (self.rid_a,)).fetchone(),
            ('needs_content',1,'private tenant A copy'))
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM bam_calendar_proposals').fetchone()[0],0)
        with self.assertRaises(PermissionError):
            app.remove_review_feedback(
                raw_session_token=owner,tenant_id='shop-a',
                request_id=self.rid_a,
                expected_feedback_token=edited['feedback_token'],
                server_now=104)

    def test_pg_feedback_remove_audit_failure_rolls_back(self):
        import hashlib
        from unittest.mock import patch
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Feedback_Rollback_Owner_12345678'
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",
            (hashlib.sha256(token.encode()).hexdigest(),self.a))
        app=EphemeralSessionPostgres(self.conn)
        original=app.save_review_feedback(
            raw_session_token=token,tenant_id='shop-a',
            request_id=self.rid_a,expected_revision=1,
            expected_feedback_token=None,note='Keep review note',
            server_now=101)
        with patch('neon_ci_session_adapter.prepare_session_feedback_removal_event',
                   return_value=('SELECT %s::text WHERE FALSE',
                                 ('f'*32,))):
            with self.assertRaises(PermissionError):
                app.remove_review_feedback(
                    raw_session_token=token,tenant_id='shop-a',
                    request_id=self.rid_a,
                    expected_feedback_token=original['feedback_token'],
                    server_now=102)
        self.assertEqual(self.conn.execute(
            'SELECT note FROM bam_review_feedback').fetchone()[0],
            'Keep review note')
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM bam_review_feedback_events').fetchone()[0],1)
        self.conn.execute("""UPDATE sessions SET revoked_at=102
            WHERE token_hash=%s""",
            (hashlib.sha256(token.encode()).hexdigest(),))
        with self.assertRaises(PermissionError):
            app.remove_review_feedback(
                raw_session_token=token,tenant_id='shop-a',
                request_id=self.rid_a,
                expected_feedback_token=original['feedback_token'],
                server_now=103)
        self.assertEqual(app.read_review_feedback_history(
            raw_session_token=token,tenant_id='shop-a',
            server_now=103)['events'],[])

    def test_pg_two_clients_only_one_feedback_removal_wins(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Concurrent_Feedback_Delete_1234567'
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",
            (hashlib.sha256(token.encode()).hexdigest(),self.a))
        app=EphemeralSessionPostgres(self.conn)
        saved=app.save_review_feedback(
            raw_session_token=token,tenant_id='shop-a',
            request_id=self.rid_a,expected_revision=1,
            expected_feedback_token=None,note='One original review',
            server_now=101)
        gate=threading.Barrier(2)
        successes=[]
        denials=[]
        errors=[]
        def delete_note():
            connection=self._connect()
            try:
                client=EphemeralSessionPostgres(connection)
                gate.wait(timeout=15)
                try:
                    result=client.remove_review_feedback(
                        raw_session_token=token,tenant_id='shop-a',
                        request_id=self.rid_a,
                        expected_feedback_token=saved['feedback_token'],
                        server_now=102)
                    successes.append(result['removed'])
                except PermissionError:
                    denials.append('stale')
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                connection.close()
        threads=[threading.Thread(target=delete_note) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors,[])
        self.assertEqual(successes,[1])
        self.assertEqual(denials,['stale'])
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM bam_review_feedback').fetchone()[0],0)
        actions=self.conn.execute("""SELECT action
            FROM bam_review_feedback_events ORDER BY occurred_at""").fetchall()
        self.assertEqual(actions,[('created',),('removed',)])


    def test_pg_session_scheduling_preferences_roundtrip(self):
        import hashlib
        from posting_schedule_policy import SchedulePreferences
        from neon_ci_session_adapter import EphemeralSessionPostgres
        owner='Synthetic_PG_Scheduling_Owner_Session_12345678'
        viewer='Synthetic_PG_Scheduling_Viewer_Session_1234567'
        manager='Synthetic_PG_Scheduling_Manager_Session_123456'
        self.conn.execute("""INSERT INTO bam_identities
            (subject_id,email,email_verified,active,created_at)
            VALUES ('scheduleManager','schedulemanager@example.test',1,1,100)""")
        self.conn.execute("""INSERT INTO members
            (tenant_id,subject_id,role,active,revision)
            VALUES ('shop-a','scheduleManager','marketing_manager',1,1)""")
        for token,subject,role in (
            (owner,self.a,'owner'),
            (viewer,self.viewer,'viewer'),
            (manager,'scheduleManager','marketing_manager')):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (%s,%s,'shop-a',%s,3600)""",
                (hashlib.sha256(token.encode()).hexdigest(),subject,role))
        app=EphemeralSessionPostgres(self.conn)
        manual=SchedulePreferences(
            'manual','America/New_York',
            {1:['10:00','11:17'],4:['18:30']},
            preferred_hours=(9,12,17,19))
        self.assertIsNone(app.read_scheduling_settings(
            raw_session_token=owner,tenant_id='shop-a',server_now=101))
        with self.assertRaises(PermissionError):
            app.save_scheduling_settings(
                raw_session_token=viewer,tenant_id='shop-a',
                preferences=manual,expected_revision=0,server_now=101)
        with self.assertRaises(PermissionError):
            app.save_scheduling_settings(
                raw_session_token=owner,tenant_id='shop-b',
                preferences=manual,expected_revision=0,server_now=101)
        receipt=app.save_scheduling_settings(
            raw_session_token=owner,tenant_id='shop-a',
            preferences=manual,expected_revision=0,server_now=101)
        self.assertEqual(receipt['revision'],1)
        self.assertFalse(receipt['publishing_enabled'])
        self.assertEqual(receipt['posts_scheduled'],0)
        owner_result=app.read_scheduling_settings(
            raw_session_token=owner,tenant_id='shop-a',server_now=102)
        viewer_result=app.read_scheduling_settings(
            raw_session_token=viewer,tenant_id='shop-a',server_now=102)
        self.assertEqual(viewer_result,owner_result)
        self.assertEqual(owner_result['preferences'].manual_weekly,
                         manual.manual_weekly)
        self.assertIsNone(app.read_scheduling_settings(
            raw_session_token=owner,tenant_id='shop-b',server_now=102))
        smart=SchedulePreferences('smart','America/Chicago',{},
                                  preferred_hours=(9,15,20))
        update=app.save_scheduling_settings(
            raw_session_token=manager,tenant_id='shop-a',
            preferences=smart,expected_revision=1,server_now=103)
        self.assertEqual(update['revision'],2)
        self.assertEqual(app.read_scheduling_settings(
            raw_session_token=owner,tenant_id='shop-a',
            server_now=103)['preferences'],smart)
        with self.assertRaises(PermissionError):
            app.save_scheduling_settings(
                raw_session_token=owner,tenant_id='shop-a',
                preferences=manual,expected_revision=1,server_now=104)
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM bam_calendar_proposals""").fetchone()[0],0)
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM tenant_posts""").fetchone()[0],0)

    def test_pg_scheduling_settings_concurrent_edits_and_revocation(self):
        import hashlib
        from posting_schedule_policy import SchedulePreferences
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Concurrent_Scheduling_Session_12345'
        digest=hashlib.sha256(token.encode()).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",
            (digest,self.a))
        app=EphemeralSessionPostgres(self.conn)
        original=SchedulePreferences('smart','America/New_York',{},
                                      preferred_hours=(9,12))
        app.save_scheduling_settings(
            raw_session_token=token,tenant_id='shop-a',
            preferences=original,expected_revision=0,server_now=101)
        barrier=threading.Barrier(2)
        successes=[]
        denials=[]
        errors=[]
        def writer(zone):
            conn=self._connect()
            try:
                client=EphemeralSessionPostgres(conn)
                prefs=SchedulePreferences('smart',zone,{},
                                          preferred_hours=(10,18))
                barrier.wait(timeout=15)
                try:
                    result=client.save_scheduling_settings(
                        raw_session_token=token,tenant_id='shop-a',
                        preferences=prefs,expected_revision=1,
                        server_now=102)
                    successes.append((result['revision'],zone))
                except PermissionError:
                    denials.append(zone)
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                conn.close()
        threads=[threading.Thread(target=writer,args=(z,))
                 for z in ('America/Chicago','America/Denver')]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)
        self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertEqual(errors,[])
        self.assertEqual(len(successes),1)
        self.assertEqual(successes[0][0],2)
        self.assertEqual(len(denials),1)
        self.assertEqual(app.read_scheduling_settings(
            raw_session_token=token,tenant_id='shop-a',
            server_now=103)['preferences'].timezone_name,
            successes[0][1])
        self.conn.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        with self.assertRaises(PermissionError):
            app.save_scheduling_settings(
                raw_session_token=token,tenant_id='shop-a',
                preferences=original,expected_revision=2,server_now=103)
        self.conn.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.conn.execute("""UPDATE sessions SET revoked_at=104
            WHERE token_hash=%s""",(digest,))
        with self.assertRaises(PermissionError):
            app.save_scheduling_settings(
                raw_session_token=token,tenant_id='shop-a',
                preferences=original,expected_revision=2,server_now=105)
        self.assertIsNone(app.read_scheduling_settings(
            raw_session_token=token,tenant_id='shop-a',server_now=105))
        self.assertEqual(self.conn.execute(
            "SELECT revision FROM scheduling_settings").fetchone()[0],2)


    def test_ci_private_media_metadata_no_storage_path(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Thumbnail_Metadata_Owner_123456789'
        viewer='Synthetic_PG_Thumbnail_Metadata_Viewer_12345678'
        for bearer,subject,role in ((token,self.a,'owner'),
                                    (viewer,self.viewer,'viewer')):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (%s,%s,'shop-a',%s,3600)""",
                (hashlib.sha256(bearer.encode('ascii')).hexdigest(),
                 subject,role))
        a_id='d'*32
        b_id='e'*32
        for aid,tenant,rid,state,when,secret in (
            (a_id,'shop-a',self.rid_a,'pending',103,'private-shop-a-path'),
            (b_id,'shop-b',self.rid_b,'verified',102,'private-shop-b-path')):
            self.conn.execute("""INSERT INTO content_attachments
                (attachment_id,tenant_id,request_id,item,media_type,sha256,
                 storage_key,status,created_at)
                VALUES (%s,%s,%s,'image','image/png',%s,%s,%s,%s)""",
                (aid,tenant,rid,'f'*64,secret,state,when))
        adapter=EphemeralSessionPostgres(self.conn)
        opts={'raw_session_token':token,'tenant_id':'shop-a',
              'request_id':self.rid_a,'server_now':104}
        own=adapter.read_attachment_statuses(**opts)
        self.assertEqual(own['status'],'attachment_metadata_only')
        self.assertEqual(own['items'],[{
            'attachment_id':a_id,'item':'image','media_type':'image/png',
            'status':'pending','created_at':103}])
        self.assertEqual(adapter.read_attachment_statuses(
            **(opts|{'raw_session_token':viewer})),own)
        self.assertEqual(adapter.read_attachment_statuses(
            **(opts|{'tenant_id':'shop-b','request_id':self.rid_b})
        )['items'],[])
        self.assertNotIn(b_id,str(own))
        for secret in ('private-shop-a-path','private-shop-b-path','f'*64):
            self.assertNotIn(secret,str(own))
        self.assertFalse(own['approval_granted'])
        self.assertFalse(own['publishing_enabled'])
        self.assertFalse(own['scanning_performed_by_adapter'])
        self.assertEqual(own['files_uploaded'],0)
        self.conn.execute("""UPDATE sessions SET revoked_at=105
            WHERE token_hash=%s""",
            (hashlib.sha256(token.encode('ascii')).hexdigest(),))
        self.assertEqual(adapter.read_attachment_statuses(
            **(opts|{'server_now':106}))['items'],[])

    def test_ci_media_schema_rejects_cross_tenant_and_invalid_state(self):
        import psycopg
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            self.conn.execute("""INSERT INTO content_attachments
                (attachment_id,tenant_id,request_id,item,media_type,
                 sha256,storage_key,status,created_at)
                VALUES (%s,'shop-b',%s,'image','image/png',
                        %s,'private/path','pending',101)""",
                ('1'*32,self.rid_a,'a'*64))
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute("""INSERT INTO content_attachments
                (attachment_id,tenant_id,request_id,item,media_type,
                 sha256,storage_key,status,created_at)
                VALUES (%s,'shop-a',%s,'image','image/png',
                        %s,'private/path','published',101)""",
                ('2'*32,self.rid_a,'a'*64))
        with self.assertRaises(psycopg.errors.CheckViolation):
            self.conn.execute("""INSERT INTO content_attachments
                (attachment_id,tenant_id,request_id,item,media_type,
                 sha256,storage_key,status,created_at)
                VALUES (%s,'shop-a',%s,'image','image/png',
                        'not-a-sha','private/path','pending',101)""",
                ('3'*32,self.rid_a))
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM content_attachments""").fetchone()[0],0)


    def test_pg_verified_media_binding_respects_scope_and_state(self):
        import hashlib
        import json
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Bind_Media_Owner_Session_123456789'
        viewer='Synthetic_PG_Bind_Media_Viewer_Session_12345678'
        for bearer,actor,role in ((token,self.a,'owner'),
                                  (viewer,self.viewer,'viewer')):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (%s,%s,'shop-a',%s,3600)""",
                (hashlib.sha256(bearer.encode()).hexdigest(),actor,role))
        aid='f'*32
        self.conn.execute("""INSERT INTO content_attachments
            (attachment_id,tenant_id,request_id,item,media_type,
             sha256,storage_key,status,created_at)
            VALUES (%s,'shop-a',%s,'image','image/png',%s,
                    'private/not-a-public-url','pending',101)""",
            (aid,self.rid_a,'a'*64))
        app=EphemeralSessionPostgres(self.conn)
        args={'raw_session_token':token,'tenant_id':'shop-a',
              'request_id':self.rid_a,'item':'image',
              'attachment_id':aid,'expected_revision':1,'server_now':102}
        with self.assertRaises(PermissionError):
            app.bind_verified_attachment(**args)
        self.conn.execute("""UPDATE content_attachments SET status='rejected'
            WHERE attachment_id=%s""",(aid,))
        with self.assertRaises(PermissionError):
            app.bind_verified_attachment(**args)
        self.conn.execute("""UPDATE content_attachments SET status='verified'
            WHERE attachment_id=%s""",(aid,))
        with self.assertRaises(PermissionError):
            app.bind_verified_attachment(
                **(args|{'raw_session_token':viewer}))
        with self.assertRaises(PermissionError):
            app.bind_verified_attachment(
                **(args|{'tenant_id':'shop-b','request_id':self.rid_b}))
        with self.assertRaises(PermissionError):
            app.bind_verified_attachment(
                **(args|{'attachment_id':'1'*32}))
        receipt=app.bind_verified_attachment(**args)
        self.assertEqual(receipt['revision'],2)
        self.assertEqual(receipt['status'],'ready_for_review')
        self.assertTrue(receipt['editorial_review_required'])
        self.assertFalse(receipt['approval_granted'])
        self.assertFalse(receipt['publishing_enabled'])
        self.assertEqual(receipt['posts_scheduled'],0)
        draft=self.conn.execute("""SELECT provided_items,status,revision
            FROM content_requests WHERE request_id=%s""",
            (self.rid_a,)).fetchone()
        self.assertEqual(json.loads(draft[0]),
                         {'image':'verified-attachment:'+aid})
        self.assertEqual(draft[1:],('ready_for_review',2))
        self.assertNotIn('private/not-a-public-url',str(receipt))
        self.assertNotIn('a'*64,str(receipt))
        with self.assertRaises(PermissionError):
            app.bind_verified_attachment(**args)
        self.conn.execute("""UPDATE content_requests SET status='postponed'
            WHERE request_id=%s""",(self.rid_a,))
        with self.assertRaises(PermissionError):
            app.bind_verified_attachment(
                **(args|{'expected_revision':2}))
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM bam_calendar_proposals""").fetchone()[0],0)
        self.assertEqual(self.conn.execute("""SELECT COUNT(*)
            FROM tenant_posts""").fetchone()[0],0)

    def test_pg_verified_media_binding_two_item_review_and_live_revocation(self):
        import hashlib
        import json
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Bind_Media_Two_Item_Session_1234567'
        digest=hashlib.sha256(token.encode()).hexdigest()
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",(digest,self.a))
        rid='9'*32
        self.conn.execute("""INSERT INTO content_requests
            (request_id,tenant_id,channel,draft_text,suggestion,
             required_items,provided_items,status,created_at,updated_at,
             revision)
            VALUES (%s,'shop-a','facebook','private copy','photo',
                    '["image","alt_text"]','{}','needs_content',100,100,1)""",
            (rid,))
        for item,aid in (('image','8'*32),('alt_text','7'*32)):
            self.conn.execute("""INSERT INTO content_attachments
                (attachment_id,tenant_id,request_id,item,media_type,
                 sha256,storage_key,status,created_at)
                VALUES (%s,'shop-a',%s,%s,'text/plain',%s,
                        'private/synthetic','verified',101)""",
                (aid,rid,item,'a'*64))
        adapter=EphemeralSessionPostgres(self.conn)
        opts={'raw_session_token':token,'tenant_id':'shop-a',
              'request_id':rid,'server_now':102}
        first=adapter.bind_verified_attachment(
            **opts,item='image',attachment_id='8'*32,expected_revision=1)
        self.assertEqual(first['status'],'needs_content')
        self.assertEqual(first['revision'],2)
        second=adapter.bind_verified_attachment(
            **opts,item='alt_text',attachment_id='7'*32,expected_revision=2)
        self.assertEqual(second['status'],'ready_for_review')
        self.assertEqual(second['revision'],3)
        draft=self.conn.execute("""SELECT provided_items FROM content_requests
            WHERE request_id=%s""",(rid,)).fetchone()[0]
        self.assertEqual(json.loads(draft),{
            'image':'verified-attachment:'+'8'*32,
            'alt_text':'verified-attachment:'+'7'*32})
        self.conn.execute("""UPDATE members SET role='viewer'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        with self.assertRaises(PermissionError):
            adapter.bind_verified_attachment(
                **opts,item='image',attachment_id='8'*32,
                expected_revision=3)
        self.conn.execute("""UPDATE members SET role='owner'
            WHERE tenant_id='shop-a' AND subject_id=%s""",(self.a,))
        self.conn.execute("""UPDATE sessions SET revoked_at=103
            WHERE token_hash=%s""",(digest,))
        with self.assertRaises(PermissionError):
            adapter.bind_verified_attachment(
                **(opts|{'server_now':104}),item='image',
                attachment_id='8'*32,expected_revision=3)
        self.assertEqual(self.conn.execute("""SELECT revision
            FROM content_requests WHERE request_id=%s""",(rid,)
        ).fetchone()[0],3)

    def test_pg_verified_media_binding_concurrent_revisions_one_wins(self):
        import hashlib
        import json
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Concurrent_Media_Binding_123456789'
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",
            (hashlib.sha256(token.encode()).hexdigest(),self.a))
        for aid in ('3'*32,'4'*32):
            self.conn.execute("""INSERT INTO content_attachments
                (attachment_id,tenant_id,request_id,item,media_type,
                 sha256,storage_key,status,created_at)
                VALUES (%s,'shop-a',%s,'image','image/png',%s,
                        'private/synthetic','verified',101)""",
                (aid,self.rid_a,'b'*64))
        gate=threading.Barrier(2)
        successes=[]
        failures=[]
        errors=[]
        def writer(aid):
            conn=self._connect()
            try:
                gateway=EphemeralSessionPostgres(conn)
                gate.wait(timeout=15)
                try:
                    result=gateway.bind_verified_attachment(
                        raw_session_token=token,tenant_id='shop-a',
                        request_id=self.rid_a,item='image',
                        attachment_id=aid,expected_revision=1,
                        server_now=102)
                    successes.append(result['attachment_id'])
                except PermissionError:
                    failures.append(aid)
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                conn.close()
        threads=[threading.Thread(target=writer,args=(aid,))
                 for aid in ('3'*32,'4'*32)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)
        self.assertTrue(all(not t.is_alive() for t in threads))
        self.assertEqual(errors,[])
        self.assertEqual(len(successes),1)
        self.assertEqual(len(failures),1)
        current=self.conn.execute("""SELECT provided_items,status,revision
            FROM content_requests WHERE request_id=%s""",
            (self.rid_a,)).fetchone()
        self.assertEqual(json.loads(current[0]),
                         {'image':'verified-attachment:'+successes[0]})
        self.assertEqual(current[1:],('ready_for_review',2))


    def test_pg_session_review_readiness_media_blockers(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Readiness_Owner_1234567890123456'
        viewer='Synthetic_PG_Readiness_Viewer_123456789012345'
        for bearer,subject,role in (
            (token,self.a,'owner'),(viewer,self.viewer,'viewer')):
            self.conn.execute("""INSERT INTO sessions
                (token_hash,subject_id,tenant_id,role,expires_at)
                VALUES (%s,%s,'shop-a',%s,3600)""",
                (hashlib.sha256(bearer.encode()).hexdigest(),subject,role))
        app=EphemeralSessionPostgres(self.conn)
        params={'raw_session_token':token,'tenant_id':'shop-a',
                'request_id':self.rid_a,'server_now':101}
        initial=app.read_review_readiness(**params)
        self.assertEqual(initial['status'],'review_preview_only')
        self.assertEqual(initial['held_count'],1)
        self.assertEqual(initial['editorial_material_complete_count'],0)
        self.assertEqual(initial['items'][0]['missing_items'],['image'])
        self.assertIn('social_publishing_disabled',
                      initial['items'][0]['blockers'])
        self.assertEqual(app.read_review_readiness(
            **(params|{'raw_session_token':viewer})),initial)
        self.assertEqual(app.read_review_readiness(
            **(params|{'tenant_id':'shop-b','request_id':self.rid_b})
        )['held_count'],0)
        aid='5'*32
        self.conn.execute("""INSERT INTO content_attachments
            (attachment_id,tenant_id,request_id,item,media_type,
             sha256,storage_key,status,created_at)
            VALUES (%s,'shop-a',%s,'image','image/png',%s,
                    'private/never-expose','pending',101)""",
            (aid,self.rid_a,'e'*64))
        with self.assertRaises(PermissionError):
            app.bind_verified_attachment(
                raw_session_token=token,tenant_id='shop-a',
                request_id=self.rid_a,item='image',attachment_id=aid,
                expected_revision=1,server_now=102)
        self.conn.execute("""UPDATE content_attachments SET status='verified'
            WHERE attachment_id=%s""",(aid,))
        bound=app.bind_verified_attachment(
            raw_session_token=token,tenant_id='shop-a',
            request_id=self.rid_a,item='image',attachment_id=aid,
            expected_revision=1,server_now=102)
        self.assertEqual(bound['status'],'ready_for_review')
        ready=app.read_review_readiness(
            **(params|{'server_now':103}))
        self.assertEqual(ready['editorial_material_complete_count'],1)
        self.assertTrue(ready['items'][0]['editorial_material_complete'])
        self.assertEqual(ready['items'][0]['blockers'],[
            'truthguard_review_required','owner_approval_not_implemented',
            'social_publishing_disabled'])
        self.assertEqual(ready['approved_count'],0)
        self.assertFalse(ready['publishing_enabled'])
        for secret in ('private/never-expose','e'*64):
            self.assertNotIn(secret,str(ready))
        self.conn.execute("""UPDATE content_attachments SET status='rejected'
            WHERE attachment_id=%s""",(aid,))
        revoked=app.read_review_readiness(
            **(params|{'server_now':104}))
        self.assertFalse(revoked['items'][0]['editorial_material_complete'])
        self.assertEqual(revoked['items'][0]['unverified_items'],['image'])
        self.conn.execute("""UPDATE content_requests SET status='postponed'
            WHERE request_id=%s""",(self.rid_a,))
        held=app.read_review_readiness(
            **(params|{'server_now':105}))
        self.assertIn('draft_held',held['items'][0]['blockers'])
        self.assertEqual(held['approved_count'],0)
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM bam_calendar_proposals').fetchone()[0],0)
        self.conn.execute("""UPDATE sessions SET revoked_at=106
            WHERE token_hash=%s""",
            (hashlib.sha256(token.encode()).hexdigest(),))
        self.assertEqual(app.read_review_readiness(
            **(params|{'server_now':107}))['held_count'],0)

    def test_pg_review_readiness_unexpected_items_fail_editorial_completion(self):
        import hashlib
        from neon_ci_session_adapter import EphemeralSessionPostgres
        token='Synthetic_PG_Readiness_Extra_Items_123456789'
        self.conn.execute("""INSERT INTO sessions
            (token_hash,subject_id,tenant_id,role,expires_at)
            VALUES (%s,%s,'shop-a','owner',3600)""",
            (hashlib.sha256(token.encode()).hexdigest(),self.a))
        aid='6'*32
        self.conn.execute("""INSERT INTO content_attachments
            (attachment_id,tenant_id,request_id,item,media_type,
             sha256,storage_key,status,created_at)
            VALUES (%s,'shop-a',%s,'image','image/png',%s,
                    'private/synthetic','verified',101)""",
            (aid,self.rid_a,'a'*64))
        self.conn.execute("""UPDATE content_requests
            SET status='ready_for_review',provided_items=%s
            WHERE request_id=%s""",
            ('{"image":"verified-attachment:'+aid+
             '","unexpected":"verified-attachment:'+aid+'"}',
             self.rid_a))
        gateway=EphemeralSessionPostgres(self.conn)
        result=gateway.read_review_readiness(
            raw_session_token=token,tenant_id='shop-a',
            request_id=self.rid_a,server_now=102)
        self.assertEqual(result['editorial_material_complete_count'],0)
        self.assertIn('unverified_or_unexpected_content',
                      result['items'][0]['blockers'])
        self.assertFalse(result['items'][0]['approved'])
        self.assertFalse(result['publishing_enabled'])


if __name__=='__main__':
    unittest.main()
