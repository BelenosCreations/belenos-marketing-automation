# Offline editorial and AI state writes

The CI source report ties these gateway delegates to pinned handler and service
files. If a pinned file changes, the report withdraws its reviewed write and
read classifications. The preceding [content and media review](MIGRATION_WSGI_WRITE_BOUNDARY_REVIEW.md)
and [identity review](MIGRATION_WSGI_IDENTITY_WRITE_REVIEW.md) cover other
groups. The report describes checked-in source and leaves deployment coverage
unverified.

| Offline entry point | Reviewed state change |
| --- | --- |
| `PUT /api/v1/posting-preferences` | The account API resolves the active business. [PostingPreferences.set](posting_preferences.py#L44-L76) upserts that business's posting preferences in one SQLite context. |
| `POST /api/v1/calendar-proposals` | [CalendarProposals.propose](calendar_proposals.py#L106-L174) inserts or updates a proposal. The write checks the held draft's revision and eligible status in SQL. Updates also check the previous proposal token. Manual preference slots are read before the write. |
| `DELETE /api/v1/calendar-proposals` | [CalendarProposals.discard](calendar_proposals.py#L259-L275) deletes the proposal only if its token still matches. |
| `PUT /api/v1/review-feedback` | [ReviewFeedback.save](review_feedback.py#L106-L159) inserts or updates a note and records its audit event in one connection context. The draft revision is re-read before mutation. The feedback update checks its own token. |
| `DELETE /api/v1/review-feedback` | [ReviewFeedback.discard](review_feedback.py#L161-L186) deletes the note and records its removal event in the same context. |
| `PUT /api/v1/ai-business-facts` | [AIBusinessFacts.confirm](ai_business_facts.py#L31-L53) checks the prior revision with a separate SELECT, then upserts the owner's facts. The upsert does not carry that expected revision as a SQL predicate. |
| `PUT /api/v1/ai-memory` | [AIPolicyStore.replace_memory_checked](ai_account_policy.py#L123-L146) conditionally initializes a user's business-scoped memory row, then compares and updates the previous JSON value in the same context. |
| `PUT /api/v1/ai-drafts` | [AIContentDraftStore.revise](ai_content_drafts.py#L92-L117) applies a revision-conditional draft update. If the image prompt changed, it also removes the previous verified-media association in the same context. |

The reviewed calendar GETs, feedback and history GETs, review readiness GET
and AI batch-preview POST read existing state. A batch preview builds proposed
request payloads without quota reservation, provider execution or draft
creation. No calendar proposal schedules a post. The source report's
no-direct-mutation classification applies only to the reviewed code path.

## Separate disabled AI composition

The [disabled AI factory](bam_ai_offline_factory.py#L38-L64) constructs
independent generation and targeted-revision adapters with a disabled
transport. Neither adapter is mounted in the checked-in offline gateway.
Their candidate write stages are documented here outside the gateway report.

| Stage | Boundary |
| --- | --- |
| Claim request | [AIGenerationIdempotency.claim](ai_generation_idempotency.py#L24-L48) inserts an in-progress record in its own transaction. |
| Reserve allowance | [SponsoredAIQuota.reserve](ai_sponsorship.py#L195-L291) uses `BEGIN IMMEDIATE` for user, tenant and operator counters and checks the operator pause under the write lock. |
| Invoke provider | [Generation](ai_generation_workflow.py#L84-L109) and [targeted revision](ai_targeted_revision_workflow.py#L86-L109) invoke an injected executor after quota reservation, outside the SQLite transaction. The factory leaves transport disabled. A separate pause read cannot recall a dispatched request or stop a race after the read. |
| Persist output | The generation workflow stages a draft and the revision workflow updates one. Each writes before the idempotency record is finalized. |
| Finalize request | [AIGenerationIdempotency.finish](ai_generation_idempotency.py#L67-L83) records completion or failure in a later transaction. |

The [trusted cost ledger](ai_cost_ledger.py#L73-L132) is a separate writer,
with optional trusted usage deduplication. The reviewed workflows do not
invoke it. Internal policy-mode changes, vault-reference removal, unchecked
memory replacement, trusted media association, operator pause changes, and
schema setup and backfills are additional source write surfaces. Inventory
their actual invocation and permissions before freeze. The source review
cannot resolve production provider callbacks, retries, queued jobs, external
vault actions or independent writers.

## Inactive freeze design

- For each SQLite-to-PostgreSQL mapping, put the generation check and write in
  one authoritative transaction. Evaluate optimistic revision and tenant
  predicates under that boundary. A connection context alone does not make a
  prior SELECT a write lock. Recheck invariants that depend on mutable
  preferences, fact revisions and draft state within the chosen boundary.
- Treat reservation, dispatch, output persistence and finalization as
  independently recoverable stages until the implementation can make them
  atomic where possible. If a worker crashes after committing a draft but
  before finalizing its request, an in-progress row cannot establish whether
  the output was already written. Require a durable operation identity and
  receipts that can reconcile a prior write without re-dispatch.
- Carry the original admitted generation through retries and revalidate it
  before each mutation. A preflight pause check alone cannot fence external
  requests. Independently verify worker drain and provider reconciliation
  before advancing a generation or taking a cutover snapshot.

This review changes CI evidence and documentation only. Live writer coverage,
persistent fencing, recovery rehearsal and hosted security remain open.
