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
from neon_ai_budget_schema import BUDGET_TABLE_NAMES,ai_budget_ddl_preview
from neon_business_analytics_schema import BUSINESS_ANALYTICS_TABLES
from neon_tenant_content_schema import TENANT_CONTENT_TABLES
from neon_review_security_schema import REVIEW_SECURITY_TABLES
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
            REVIEW_SECURITY_TABLES)+' CASCADE')
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

    def test_ci_schema_migration_journal_is_idempotent(self):
        self.assertEqual(self.migration_result['versions_present'],7)
        self.assertEqual(self.migration_result['versions_applied'],[1,2,3,4,5,6,7])
        reread=apply_ephemeral_ci_migrations(self.conn)
        self.assertEqual(reread['versions_applied'],[])
        self.assertFalse(reread['migration_production_ready'])
        self.assertFalse(reread['customer_records_migrated'])
        self.assertFalse(reread['neon_connected'])
        self.assertFalse(reread['social_publishing_enabled'])
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM bam_ci_migration_journal').fetchone()[0],7)

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



if __name__=='__main__':
    unittest.main()
