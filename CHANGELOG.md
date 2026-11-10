# Changelog

## Phase 3.3 — 2026-11-10 (authorization foundation)

### Added
- Fail-closed, tenant-scoped role authorization policy for owner and future staff.
- 12 offline tests for role boundaries, tenant isolation, inactive identities, and privileged actions.

### Test status
- New tests committed; GitHub Actions result not yet verified.

### Known limitations
- Policy only: no authentication provider, token verification, user database, Android app, or API middleware yet.
- Existing prototype approval workflow is not yet wired to this policy.
- No live publishing or scheduling; publishing remains disabled.


## Phase 3.2 — 2026-11-10 (offline prototype imported to GitHub)

### Added
- Imported the offline policy engine, approval/audit workflow, and engagement optimizer.
- Imported 26 unit tests covering staging, approvals, dry runs, curation, and time ranking.
- Added GitHub Actions unit-test workflow and Python/credential-safe .gitignore.
- Created project documentation and version history.

### Test status
- All 26 tests passed locally against the original Phase 3.2 ZIP before import.
- GitHub Actions workflow is configured; remote run status has not yet been verified.

### Known limitations
- No authenticated approval service or real creator discovery.
- Trust and fact-verification flags are caller-supplied in the prototype.
- Content classification trusts caller-provided category; promotion authorization uses naive text matching.
- No live Metricool scheduling or Facebook publishing.
- Publishing remains disabled.

## Phase 3 — 2026-11-10 (offline prototype)
- Draft staging, authorization, audit, approval and dry-run workflow.
- Local test suite, with no network or publishing implementation.
