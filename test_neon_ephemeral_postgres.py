"""Real PostgreSQL *ephemeral GitHub CI* integration, never customer Neon.

Runs only when BAM_EPHEMERAL_PG_TEST=1. Refuses any non-loopback endpoint or
unexpected database name/user. This does not implement or authorize production
credentials, migration, persistence, public hosting, or scheduled publication.
"""
import os
import threading
import unittest

from neon_schema_blueprint import ddl_preview,TABLE_NAMES
from neon_collaboration_schema import (
    COLLABORATION_NAMES,collaboration_ddl_preview)
from neon_identity_provider_schema import EXTRA_TABLE_NAMES
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
            TABLE_NAMES+COLLABORATION_NAMES+EXTRA_TABLE_NAMES)+' CASCADE')
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

    def test_ci_schema_migration_journal_is_idempotent(self):
        self.assertEqual(self.migration_result['versions_present'],3)
        self.assertEqual(self.migration_result['versions_applied'],[1,2,3])
        reread=apply_ephemeral_ci_migrations(self.conn)
        self.assertEqual(reread['versions_applied'],[])
        self.assertFalse(reread['migration_production_ready'])
        self.assertFalse(reread['customer_records_migrated'])
        self.assertFalse(reread['neon_connected'])
        self.assertFalse(reread['social_publishing_enabled'])
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM bam_ci_migration_journal').fetchone()[0],3)

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
                             ('bam_ci_migration_journal',)))
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


if __name__=='__main__':
    unittest.main()
