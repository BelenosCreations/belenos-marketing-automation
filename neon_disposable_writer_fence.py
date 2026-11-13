"""CI-only in-memory SQLite writer-fence and rollback semantics rehearsal.

This creates a disposable shared-memory database with synthetic canaries and
two independent connections. It never opens customer databases, provides
production application write fencing, or executes PostgreSQL cutover.
"""
import hashlib
import os
import sqlite3

_MODES = ("rollback", "abandoned_connection")


def rehearse_disposable_writer_fence(*, release_mode="rollback"):
    """Show a competing SQLite writer cannot commit while a fence lock is held.

    Real BAM writers, background jobs, provider callbacks and hosted PG
    transactions are NOT fenced. This is isolated SQLite engine behavior only.
    """
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("CI-only disposable write-fence rehearsal")
    if type(release_mode) is not str or release_mode not in _MODES:
        raise ValueError("Only explicitly reviewed synthetic release scenarios")
    # No caller-supplied path, URI, connection or SQL; memory-only unique name.
    uri = "file:bam_ci_fence_" + os.urandom(12).hex() + "?mode=memory&cache=shared"
    writer = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=0)
    competitor = None
    try:
        competitor = sqlite3.connect(uri, uri=True, isolation_level=None, timeout=0)
        writer.execute("""CREATE TABLE synthetic_fence_canary(
            id INTEGER PRIMARY KEY, state TEXT NOT NULL)""")
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("""INSERT INTO synthetic_fence_canary(id,state)
                          VALUES(1,'uncommitted')""")
        blocked = False
        try:
            competitor.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError:
            blocked = True
        else:
            # Unexpected success: clean up immediately, never report a fence.
            competitor.execute("ROLLBACK")
            raise AssertionError("Competing synthetic writer was not fenced")
        if not blocked:
            raise AssertionError("Synthetic writer lock did not hold")
        if release_mode == "rollback":
            writer.execute("ROLLBACK")
        else:
            # Abandoned connection closes uncommitted synthetic transaction.
            writer.close()
            writer = None
        competitor.execute("BEGIN IMMEDIATE")
        competitor.execute("""INSERT INTO synthetic_fence_canary(id,state)
                              VALUES(2,'post_release')""")
        competitor.execute("COMMIT")
        rows = competitor.execute(
            "SELECT id,state FROM synthetic_fence_canary ORDER BY id").fetchall()
        if rows != [(2, "post_release")]:
            raise AssertionError("Synthetic rollback/lock-release parity failed")
        evidence_sha = hashlib.sha256(
            ("bam-ci-fence-v1|" + release_mode + "|blocked|rolled-back|"
             "post-release-commit").encode("ascii")).hexdigest()
        return {
            "status": "disposable_sqlite_writer_fence_rehearsed",
            "release_mode": release_mode,
            "synthetic_competing_writer_blocked": True,
            "uncommitted_synthetic_row_rolled_back": True,
            "post_release_synthetic_writer_succeeded": True,
            "synthetic_evidence_sha256": evidence_sha,
            "temporary_in_memory_database_only": True,
            "customer_rows_read": False, "customer_database_opened": False,
            "real_application_write_fence_implemented": False,
            "background_workers_fenced": False,
            "postgres_transaction_started": False,
            "production_rollback_executable": False,
            "cutover_permitted": False,
            "production_ready": False, "publishing_enabled": False,
        }
    finally:
        if competitor is not None:
            competitor.close()
        if writer is not None:
            writer.close()
