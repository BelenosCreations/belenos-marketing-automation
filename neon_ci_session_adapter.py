"""Executable but STRICTLY disposable-CI-only PostgreSQL session facade.

This is the first end-to-end psycopg bridge for synthetic BAM drafts, held
calendar proposals and owner invitation metadata. It is NOT a production
database adapter: it refuses non-loopback connections, non-CI databases and
any actual customer Neon/Render connection. It opens no connections itself.
It has no provider, publication, AI, upload or scheduling operations.
"""
import os

from neon_authenticated_read_contract import (
    prepare_session_draft_read, prepare_session_calendar_read)
from neon_scoped_queries import (
    summarize_held_draft_row, summarize_calendar_row)
from neon_session_write_contract import prepare_session_priority_cas
from neon_scoped_writes import priority_cas_result
from neon_session_collaboration_contract import (
    prepare_session_pending_owner_invitations)
from neon_session_inbox_contract import (
    prepare_session_inbox_page,summarize_inbox_page)
from neon_session_team_contract import (
    prepare_session_owner_team_roster,summarize_owner_team_roster)
from neon_session_draft_write_contract import (
    prepare_session_held_draft_create,summarize_held_draft_create,
    prepare_session_held_draft_revision,summarize_held_draft_revision)
from neon_session_feedback_contract import (
    prepare_session_feedback_list,summarize_session_feedback_list,
    prepare_session_feedback_save,summarize_session_feedback_save,
    prepare_session_feedback_event,assert_feedback_event_saved,
    prepare_session_feedback_remove,summarize_session_feedback_remove,
    prepare_session_feedback_removal_event,
    prepare_session_feedback_history,summarize_session_feedback_history)
from neon_session_schedule_settings_contract import (
    prepare_session_schedule_settings_read,
    summarize_session_schedule_settings,
    prepare_session_schedule_settings_save,
    summarize_session_schedule_settings_save)
from neon_session_media_contract import (
    prepare_session_attachment_statuses,
    summarize_session_attachment_statuses)

_CI_SCHEMA='bam_ci_integration'


class EphemeralSessionPostgres:
    """Execution boundary for disposable local GitHub CI fixtures only."""

    def __init__(self,conn):
        if os.environ.get('BAM_EPHEMERAL_PG_TEST')!='1':
            raise PermissionError('Disposable PostgreSQL CI only')
        import psycopg
        if not isinstance(conn,psycopg.Connection):
            raise TypeError('Psycopg connection required')
        info=conn.info
        if (conn.closed or not conn.autocommit
                or info.host!='127.0.0.1'
                or int(info.port)!=5432
                or info.dbname!='bam_ci_test'
                or info.user!='bam_ci'):
            raise PermissionError('Dedicated loopback CI database required')
        scope=conn.execute(
            'SELECT current_schema(),current_database(),current_user').fetchone()
        if scope!=(_CI_SCHEMA,'bam_ci_test','bam_ci'):
            raise PermissionError('Unrecognized disposable PostgreSQL schema')
        self._conn=conn

    def read_held_draft(self,*,raw_session_token,tenant_id,request_id,
                        server_now):
        sql,params=prepare_session_draft_read(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            request_id=request_id,server_now=server_now)
        row=self._conn.execute(sql,params).fetchone()
        return summarize_held_draft_row(row)

    def read_held_inbox_page(self,*,raw_session_token,tenant_id,server_now,
                             limit=20,after_created_at=None,
                             after_request_id=None,status=None):
        sql,params=prepare_session_inbox_page(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            server_now=server_now,limit=limit,
            after_created_at=after_created_at,
            after_request_id=after_request_id,status=status)
        rows=self._conn.execute(sql,params).fetchall()
        return summarize_inbox_page(rows,limit=limit)

    def read_calendar_proposal(self,*,raw_session_token,tenant_id,request_id,
                               server_now):
        sql,params=prepare_session_calendar_read(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            request_id=request_id,server_now=server_now)
        return summarize_calendar_row(
            self._conn.execute(sql,params).fetchone())

    def read_owner_pending_invitations(self,*,raw_session_token,tenant_id,
                                       server_now):
        sql,params=prepare_session_pending_owner_invitations(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            server_now=server_now)
        rows=self._conn.execute(sql,params).fetchall()
        # The SQL bounds to 50 rows and never selects invitation token hashes.
        return {'status':'owner_private_pending_metadata',
                'items':[{'invitation_id':r[0],'email':r[1],
                          'role':r[2],'expires_at':r[3]} for r in rows],
                'publishing_enabled':False,'posts_scheduled':0}

    def read_owner_team_roster(self,*,raw_session_token,tenant_id,
                               server_now):
        sql,params=prepare_session_owner_team_roster(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            server_now=server_now)
        rows=self._conn.execute(sql,params).fetchall()
        return summarize_owner_team_roster(rows,tenant_id=tenant_id)

    def create_held_draft(self,*,raw_session_token,tenant_id,channel,
                          draft_text,suggestion,required_items,
                          priority=0,server_now):
        sql,params=prepare_session_held_draft_create(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            channel=channel,draft_text=draft_text,suggestion=suggestion,
            required_items=required_items,priority=priority,
            server_now=server_now)
        with self._conn.transaction():
            row=self._conn.execute(sql,params).fetchone()
            return summarize_held_draft_create(
                row,expected_id=params[0],tenant_id=tenant_id,
                expected_priority_token=params[7])

    def revise_held_draft(self,*,raw_session_token,tenant_id,request_id,
                          target,revised_text,expected_revision,server_now):
        sql,params=prepare_session_held_draft_revision(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            request_id=request_id,target=target,revised_text=revised_text,
            expected_revision=expected_revision,server_now=server_now)
        with self._conn.transaction():
            row=self._conn.execute(sql,params).fetchone()
            return summarize_held_draft_revision(
                row,request_id=request_id,expected_revision=expected_revision)

    def read_review_feedback(self,*,raw_session_token,tenant_id,
                             server_now):
        sql,params=prepare_session_feedback_list(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            server_now=server_now)
        rows=self._conn.execute(sql,params).fetchall()
        return summarize_session_feedback_list(rows,tenant_id=tenant_id)

    def save_review_feedback(self,*,raw_session_token,tenant_id,request_id,
                             expected_revision,expected_feedback_token,
                             note,server_now):
        sql,params,action,version=prepare_session_feedback_save(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            request_id=request_id,expected_revision=expected_revision,
            expected_feedback_token=expected_feedback_token,note=note,
            server_now=server_now)
        import psycopg
        try:
            with self._conn.transaction():
                row=self._conn.execute(sql,params).fetchone()
                receipt=summarize_session_feedback_save(
                    row,tenant_id=tenant_id,request_id=request_id,
                    expected_revision=expected_revision,
                    expected_new_token=version)
                audit_sql,audit_params=prepare_session_feedback_event(
                    raw_session_token=raw_session_token,tenant_id=tenant_id,
                    request_id=request_id,current_feedback_token=version,
                    action=action,server_now=server_now)
                event=self._conn.execute(audit_sql,audit_params).fetchone()
                assert_feedback_event_saved(
                    event,expected_event_id=audit_params[0])
                return receipt
        except psycopg.errors.UniqueViolation as exc:
            # A simultaneous new note already exists: never overwrite it.
            raise PermissionError(
                'Private feedback changed; refresh required') from exc

    def remove_review_feedback(self,*,raw_session_token,tenant_id,request_id,
                               expected_feedback_token,server_now):
        sql,params=prepare_session_feedback_remove(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            request_id=request_id,expected_feedback_token=expected_feedback_token,
            server_now=server_now)
        with self._conn.transaction():
            row=self._conn.execute(sql,params).fetchone()
            receipt,revision=summarize_session_feedback_remove(
                row,tenant_id=tenant_id,request_id=request_id)
            event_sql,event_params=prepare_session_feedback_removal_event(
                raw_session_token=raw_session_token,tenant_id=tenant_id,
                request_id=request_id,draft_revision=revision,
                server_now=server_now)
            event=self._conn.execute(event_sql,event_params).fetchone()
            assert_feedback_event_saved(event,expected_event_id=event_params[0])
            return receipt

    def read_review_feedback_history(self,*,raw_session_token,tenant_id,
                                     server_now):
        sql,params=prepare_session_feedback_history(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            server_now=server_now)
        rows=self._conn.execute(sql,params).fetchall()
        return summarize_session_feedback_history(rows,tenant_id=tenant_id)

    def read_scheduling_settings(self,*,raw_session_token,tenant_id,
                                server_now):
        sql,params=prepare_session_schedule_settings_read(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            server_now=server_now)
        row=self._conn.execute(sql,params).fetchone()
        return summarize_session_schedule_settings(row,tenant_id=tenant_id)

    def save_scheduling_settings(self,*,raw_session_token,tenant_id,
                                preferences,expected_revision,server_now):
        sql,params=prepare_session_schedule_settings_save(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            preferences=preferences,expected_revision=expected_revision,
            server_now=server_now)
        with self._conn.transaction():
            row=self._conn.execute(sql,params).fetchone()
            return summarize_session_schedule_settings_save(
                row,tenant_id=tenant_id,
                expected_revision=expected_revision)

    def read_attachment_statuses(self,*,raw_session_token,tenant_id,
                                 request_id,server_now):
        sql,params=prepare_session_attachment_statuses(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            request_id=request_id,server_now=server_now)
        rows=self._conn.execute(sql,params).fetchall()
        return summarize_session_attachment_statuses(
            rows,tenant_id=tenant_id,request_id=request_id)

    def update_draft_priority(self,*,raw_session_token,tenant_id,request_id,
                              expected_priority_token,priority,server_now):
        sql,params=prepare_session_priority_cas(
            raw_session_token=raw_session_token,tenant_id=tenant_id,
            request_id=request_id,expected_priority_token=expected_priority_token,
            priority=priority,server_now=server_now)
        with self._conn.transaction():
            row=self._conn.execute(sql,params).fetchone()
            # Denial/stale version raises, rolling back with no other writes.
            return priority_cas_result(row,expected_new_token=params[1])
