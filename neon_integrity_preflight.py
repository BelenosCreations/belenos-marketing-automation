"""Metadata-only SQLite data-integrity preflight before future Neon migration.

Do not use this as an exporter, migration runner or production acceptance
check. It reports aggregate issue counts only; never row values, identities,
emails, tokens, hashes or draft text. DB connection must be trusted/offline.
"""
import sqlite3

_CHECKS={
 'orphan_memberships': """SELECT COUNT(*) FROM members m
    LEFT JOIN bam_identities i ON i.subject_id=m.subject_id
    WHERE i.subject_id IS NULL""",
 'orphan_password_credentials': """SELECT COUNT(*)
    FROM bam_password_credentials p
    LEFT JOIN bam_identities i ON i.subject_id=p.subject_id
    WHERE i.subject_id IS NULL""",
 'orphan_google_bindings': """SELECT COUNT(*) FROM bam_google_identities g
    LEFT JOIN bam_identities i ON i.subject_id=g.subject_id
    WHERE i.subject_id IS NULL""",
 'orphan_sessions': """SELECT COUNT(*) FROM sessions s
    LEFT JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE i.subject_id IS NULL""",
 'stale_or_revoked_memberships_with_live_sessions': """SELECT COUNT(*)
    FROM sessions s LEFT JOIN members m
    ON m.tenant_id=s.tenant_id AND m.subject_id=s.subject_id
    WHERE s.revoked_at IS NULL AND
    (m.subject_id IS NULL OR m.active<>1 OR m.role<>s.role)""",
 'disabled_identities_with_live_sessions': """SELECT COUNT(*)
    FROM sessions s JOIN bam_identities i ON i.subject_id=s.subject_id
    WHERE s.revoked_at IS NULL AND i.active<>1""",
 'orphan_calendar_proposals': """SELECT COUNT(*) FROM bam_calendar_proposals p
    LEFT JOIN content_requests c ON c.tenant_id=p.tenant_id
       AND c.request_id=p.request_id WHERE c.request_id IS NULL""",
 'duplicate_casefold_emails': """SELECT COALESCE(SUM(n-1),0) FROM (
    SELECT COUNT(*) n FROM bam_identities
    GROUP BY LOWER(email) HAVING COUNT(*)>1)""",
 'invalid_session_token_digests': """SELECT COUNT(*) FROM sessions
    WHERE length(token_hash)<>64 OR token_hash GLOB '*[^0-9a-f]*'""",
 'invalid_active_member_roles': """SELECT COUNT(*) FROM members
    WHERE active=1 AND role NOT IN
    ('owner','marketing_manager','content_creator','employee','viewer')""",
}


def inspect_offline_integrity(db):
    """Read-only, bounded-shape aggregate preflight; always beta-blocked."""
    if not isinstance(db,sqlite3.Connection):
        raise TypeError('Trusted offline SQLite connection required')
    # SQLite may contain damaged pages, but do not propagate file content or
    # account-specific details into output. The caller controls DB access.
    integrity=db.execute('PRAGMA integrity_check(1)').fetchone()
    integrity_ok=bool(integrity and integrity[0]=='ok')
    foreign_key_count=sum(1 for _ in db.execute('PRAGMA foreign_key_check'))
    counts={}
    for label,statement in _CHECKS.items():
        result=db.execute(statement).fetchone()
        count=result[0] if result is not None else None
        if type(count) is not int or count<0:
            raise ValueError('Unexpected aggregate preflight count')
        counts[label]=count
    flagged=sum(counts.values())+foreign_key_count
    return {'status':'local_integrity_preflight_only',
            'integrity_check_ok':integrity_ok,
            'foreign_key_issue_count':foreign_key_count,
            'aggregate_issue_counts':counts,
            'issue_count_total':flagged,
            'migration_fixture_issues_found':flagged>0 or not integrity_ok,
            'customer_rows_exported':False,
            'secrets_exported':False,
            'postgres_connection_attempted':False,
            'production_ready':False,
            'publishing_enabled':False}


def require_clean_offline_fixture(db):
    """Test helper: no finding does NOT authorize production migration."""
    result=inspect_offline_integrity(db)
    if result['migration_fixture_issues_found']:
        raise ValueError('Offline migration fixture contains integrity findings')
    return result
