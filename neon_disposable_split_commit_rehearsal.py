"""CI-only recovery model for a draft committed before request finalization."""

from contextlib import contextmanager

from neon_disposable_generation_authority import (
    _CANARY, _ID, _TENANT, _DisposableGenerationAuthority, _epoch, _gate, _matches,
)

_SCHEMA = """
CREATE TABLE ci_draft_requests (
    operation_id TEXT PRIMARY KEY,
    tenant TEXT NOT NULL,
    generation INTEGER NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1))
);
CREATE TABLE ci_draft_outputs (
    operation_id TEXT PRIMARY KEY,
    tenant TEXT NOT NULL,
    generation INTEGER NOT NULL,
    marker TEXT NOT NULL
);
"""


class DisposableSplitCommitRehearsal(_DisposableGenerationAuthority):
    """Isolated SQLite only, with no BAM store, provider or operator integration."""

    def __init__(self):
        super().__init__()
        try:
            self._db.executescript(_SCHEMA)
        except BaseException:
            self.close()
            raise

    @contextmanager
    def _admitted_transaction(self, expected_epoch):
        _gate()
        _epoch(expected_epoch)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            if self._db.execute(
                "SELECT epoch, mode FROM ci_generation WHERE id=1"
            ).fetchone() != (expected_epoch, "open"):
                raise PermissionError("Stale or frozen rehearsal writer")
            yield
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise

    def claim(self, *, expected_epoch, operation_id, tenant):
        _matches(operation_id, _ID, "operation")
        _matches(tenant, _TENANT, "tenant")
        with self._admitted_transaction(expected_epoch):
            created = self._db.execute(
                "INSERT INTO ci_draft_requests(operation_id, tenant, generation)"
                " VALUES(?, ?, ?) ON CONFLICT(operation_id) DO NOTHING",
                (operation_id, tenant, expected_epoch),
            )
            if created.rowcount != 1:
                raise PermissionError("Existing rehearsal operation")

    def commit_output(self, *, expected_epoch, operation_id, tenant, marker):
        """Persist the draft with its operation receipt in the same row."""
        _matches(operation_id, _ID, "operation")
        _matches(tenant, _TENANT, "tenant")
        _matches(marker, _CANARY, "marker")
        with self._admitted_transaction(expected_epoch):
            created = self._db.execute(
                "INSERT INTO ci_draft_outputs(operation_id, tenant, generation, marker)"
                " SELECT operation_id, tenant, generation, ? FROM ci_draft_requests"
                " WHERE operation_id=? AND tenant=? AND generation=? AND completed=0"
                " ON CONFLICT(operation_id) DO NOTHING",
                (marker, operation_id, tenant, expected_epoch),
            )
            if created.rowcount != 1:
                raise PermissionError("Missing, stale or already persisted rehearsal operation")

    def finalize(self, *, expected_epoch, operation_id, tenant):
        """Normal continuation may finalize only its admitted generation."""
        return self._finalize(expected_epoch, operation_id, tenant, recover=False)

    def reconcile_committed_output(self, *, expected_epoch, operation_id, tenant):
        """Model a recovery-only action after resume, backed by a prior receipt.

        The caller represents an operator in the fixture. No identity or
        authorization is provided. This action can only update request status.
        """
        return self._finalize(expected_epoch, operation_id, tenant, recover=True)

    def _finalize(self, expected_epoch, operation_id, tenant, *, recover):
        _matches(operation_id, _ID, "operation")
        _matches(tenant, _TENANT, "tenant")
        with self._admitted_transaction(expected_epoch):
            receipt = self._db.execute(
                "SELECT request.generation, request.completed"
                " FROM ci_draft_requests AS request"
                " JOIN ci_draft_outputs AS output"
                " ON output.operation_id=request.operation_id"
                " AND output.tenant=request.tenant AND output.generation=request.generation"
                " WHERE request.operation_id=? AND request.tenant=?",
                (operation_id, tenant),
            ).fetchone()
            if receipt is None:
                raise PermissionError("No matching committed output receipt")
            admitted_epoch, completed = receipt
            matching_origin = (
                admitted_epoch < expected_epoch if recover else admitted_epoch == expected_epoch
            )
            if not matching_origin:
                raise PermissionError("Receipt belongs to a different generation")
            if completed:
                return False
            self._db.execute(
                "UPDATE ci_draft_requests SET completed=1 WHERE operation_id=?",
                (operation_id,),
            )
            return True
