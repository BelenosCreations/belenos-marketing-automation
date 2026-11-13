# AI draft request recovery design

Source review baseline: `d3bffa1cf935d6ed15090f8cfb8f06b7bbf4a886`.
The [alternate writer inventory](MIGRATION_ALTERNATE_WRITER_INVENTORY.md)
records the surrounding repository entry points. This design and the
disposable tests leave the application schema, workflows and provider
configuration untouched.

## Current store boundaries

| Step | Existing implementation | Recovery evidence and gap |
| --- | --- | --- |
| Claim | [AIGenerationIdempotency](ai_generation_idempotency.py) commits the request key and fingerprint under `(tenant_id, subject_id, request_key)`. Initial status is `in_progress`. Both generation and targeted revision share the table. | Matching replays are held. The row has no operation kind, admission generation, dispatch reference or output receipt. |
| Reserve | [SponsoredAIQuota](ai_sponsorship.py) reserves monthly user, business and operator counters in one SQLite transaction. | The counters have no per-request reservation identity. Their values cannot attribute a particular reservation or provider charge to a claimed request. |
| Dispatch and observe | [OpenAIResponsesExecutor](openai_responses_executor.py) may send usage to an injected observer before validating draft output. [AICostLedger](ai_cost_ledger.py) can deduplicate observed usage by a scoped, hashed reference. The [disabled factory](bam_ai_offline_factory.py) supplies a disabled transport and leaves the observer unwired. | The observer reference derives from a provider response ID, and the request row has no corresponding reference. An absent response, malformed output, or timeout can leave the provider outcome unresolved. A usage entry records estimated cost and reported tokens. |
| Write output | [Generation](ai_generation_workflow.py) inserts a draft with a random ID through [AIContentDraftStore](ai_content_drafts.py). [Targeted revision](ai_targeted_revision_workflow.py) updates an existing draft by revision compare-and-swap and can invalidate its verified media link. Both commit before the workflow finishes the request. | The draft primary key is `(tenant_id, subject_id, draft_id)`. Drafts lack a link to the claim or a historical receipt for the revision applied by the request. |
| Finalize | `finish` uses the current editor principal and updates the request only while it is `in_progress`. It stores a draft ID for completion. | The store does not verify a matching output receipt or reference the draft by foreign key. A worker can lose its session or exit after saving output but before recording completion. |

## Proposed transaction and operator boundaries

1. Assign a server-owned operation ID at claim. Persist the request scope,
   operation kind, fingerprint and admitted generation. Record a uniquely
   scoped reservation in the quota transaction before any possible dispatch.
   Keep any future provider correlation ID private and bind it to the
   operation before transport where supported. Retain independently
   attributable provider evidence before deciding whether to reconcile a charge.
2. Store the draft and its immutable receipt in the same fenced transaction.
   Bind the receipt to the tenant, subject, request key, operation kind,
   fingerprint, admitted generation, draft ID and resulting revision. For
   targeted revision, include the expected prior revision, affected component
   and any media-link invalidation in the atomic write. Preserve original
   receipt evidence when later manual edits advance the draft revision.
3. In PostgreSQL, acquire a shared row lock on the persistent generation
   authority and verify the expected generation and open mode inside every
   normal write transaction. Freeze and resume use a conflicting update of
   that same authority row and advance the generation. Order any request,
   draft and receipt locks after the authority check. A timeout, failed lock,
   stale generation or missing authority aborts the write. When practical,
   commit the receipt, draft and request completion together. A separate
   completion step must compare and set the status from the matching receipt.
   A database lock can order local commits. External dispatch, retries and
   file writes need separately verified drain and admission controls.
4. Recovery uses a dedicated authenticated operator principal with narrowly
   scoped authority, separate from business editor sessions and application
   writer credentials. Bind an auditable decision to the current independently
   pinned authority head, operation scope, expected receipt and expiry. Check
   operator authorization, head and request state again in the transaction.
   A matching committed receipt permits only request finalization. Record
   the operator decision atomically with that change so the same approval
   cannot be replayed for another request or generation. An already
   completed request with matching evidence is a read-only result.

## Interruption outcomes

| Observed state | Proposed disposition |
| --- | --- |
| Draft and receipt transaction was abandoned before commit | Both roll back. A committed claim or reservation remains. Hold the operation and determine dispatch state from independently attributable evidence. |
| Matching draft receipt committed, request still in progress | Authorized recovery can finalize the original request without generating or revising another draft. Reconcile any provider usage separately. |
| Provider timed out or may have accepted a request, with no durable output receipt | Hold for reconciliation. Preserve the reservation and prohibit automatic retries or refunds. Record a terminal disposition only from reviewed provider and local evidence. |
| Request predates receipts, or a receipt conflicts with scope, input or history | Hold for operator investigation. Draft text, timestamp, aggregate quota, and matching business alone cannot establish provenance. |

## Rehearsal and remaining evidence

`test_ai_generation_idempotency` exercises the current SQLite stores with
synthetic interruptions before draft staging and after its commit. Both
requests stay in progress and retries leave the executor call count unchanged.
The PostgreSQL integration suite uses the existing preview tables and
test-only receipt and authority tables. It checks rollback before the receipt,
atomic receipt visibility, scoped foreign keys and duplicate denial. A second
connection tests that freeze conflicts with an admitted write, and that frozen
or stale generations cannot insert a new request.

Additional PostgreSQL fixtures exercise receipt-based finalization after a
generation change. The statement compares the approved scope, fingerprint,
draft, revision and receipt generation under the authority lock, then commits
request status and the operator audit row together. An expired decision, stale
head, mismatched receipt or missing receipt leaves the request held. Repeating
successful recovery does not add another audit row, draft or quota entry.
Fixture inputs represent a preverified approval and trusted clock.

The targeted revision rehearsal rolls back the prompt edit and media-link
removal when the receipt fails to insert. A successful receipt retains the
resulting revision after a later manual edit. A separate resume rehearsal
reopens the database connection after committing a pending transition,
requires the expected head before admitting writes, and substitutes the
older authority row to model a stale restore. Independent head custody and
operational restore remain outside this test.

## Authority after interruption or restore

The database generation orders local transactions. Keep the latest approved
transition head and its verification keys in independent custody so a restored
database cannot make an old open generation current again. Start recovered
workers with write admission closed. Compare the restored authority and audit
chain with the independently held head before opening a new generation. An
unavailable, stale or divergent head leaves workers closed pending operator
review. Never reuse an earlier generation after rollback.

An operator transition should name the intended environment, previous
generation and mode, new generation and mode, previous decision head, and
the expected evidence. Restrict the role that can change the authority row.
Advance the database generation and record the authorized transition in one
transaction. Freeze immediately denies normal writes. A resume transition
records a pending generation with writes still denied. Publish and confirm
the new head independently, then admit writes with a separate transaction
that compares that confirmation to the pending generation and recorded head.
If confirmation is interrupted, workers stay closed. On restart, verify and
reconcile the committed transition before allowing writes. A stale
acknowledgement cannot reopen a prior generation.

| Evidence required before activation | Verification |
| --- | --- |
| Independent operator identity and transition authority | Reject expired, replayed, revoked and wrong-environment approvals, including during role changes. Verify that ordinary app credentials cannot change the generation or run recovery. |
| Independently held latest head and verification keys | Restore an older open generation from a disposable snapshot. Confirm that missing or mismatched head evidence blocks writes and that the next approved generation is newer than the independently witnessed head. |
| Request recovery authorization | Verify the scoped request, operation kind, fingerprint, admitted generation, receipt and current request status while holding the transaction locks. Confirm recovery cannot stage output, call a provider or adjust quota. |
| Deployment inventory and drain | Reconcile running instances, worker versions, ingress routes, scheduled and retry jobs, provider callbacks and storage writers against independently reviewed runtime evidence. Verify each principal's write path and the outcome for stale work. |

## AI store migration mapping review

The [identity and provider preview](neon_identity_provider_schema.py) and
[AI budget preview](neon_ai_budget_schema.py) describe the target shapes.
The following review is based on their DDL and the current store methods.
It records decisions to validate using synthetic rows before proposing
transformations. No customer rows were inspected.

| Fields or relationship | Proposed mapping and verification |
| --- | --- |
| Facts and memories | Keep JSON as text for the initial mapping. Validate the bounded string-object shape and UTF-8 limits from the existing stores, including duplicate keys. Preserve the text used by memory compare-and-swap. Flag malformed or noncanonical legacy text for a reviewed normalization decision. An absent facts row and an empty memory object have different meanings. |
| Request status and draft reference | Preserve the composite tenant, subject and request key and exact fingerprint. Validate a completed request's scoped draft ID. Keep `draft_id` null for held or failed requests. Legacy requests lack receipts and must enter reconciliation without fabricated generation, dispatch or provider evidence. |
| Draft revision and verified media | Preserve nullable image prompts, positive revisions and the existing integer media flag, rejecting values outside its accepted range. Verify the full tenant, subject and draft association and the underlying attachment evidence. Report orphaned or mismatched links for review before adding constraints. Later edits must leave historical receipt revisions intact. |
| Tenant and subject ownership | Map exact opaque IDs and validate references against the reviewed identity and tenant inventories. Establish how inactive or removed memberships and historical authors are retained before adding live membership foreign keys or deletion rules. Report unknown or ambiguous identities. |
| Quota and estimated cost | Preserve counts and micro-USD integers within target bounds. Historical accepted requests from before cost accounting require the existing unpriced backfill rule, which must be reviewed for each source version. A null usage hash preserves legacy lack of deduplication. Never reconstruct a provider charge from aggregate counters or default an unknown reservation to priced zero. |
| Operator control and vault references | Keep target staging paused. Preserve an absent credential reference as null. References alone need independent validation against the intended vault and scope before use. There are no generated numeric identities in these AI tables. Preserve the source-issued keys and validate uniqueness within each declared scope. |

Before any activation, independently identify the deployed WSGI, callback,
worker, scheduler, retry, admin and storage writer identities and bindings.
Review provider behavior using authorized evidence, establish operator identity
and independent head and key custody, and prove that all writers are fenced.
The disposable tests cover selected database boundaries. They do not authorize
provider activity, real recovery, customer migration, or private Beta.

### Disposable SQLite-to-PostgreSQL mapping results

- Canonical and noncanonical memory JSON text round-trips byte for byte. The
  existing compare-and-swap uses a canonical encoding of the previously read
  map. A valid legacy spelling with different whitespace, key order or
  Unicode escaping still fails that comparison after an exact transfer.
  Preserve the original text for review before deciding how to repair it.
  Reject duplicate keys before validating decoded objects. Keep an absent
  facts row distinct from a stored empty personal memory.
- Legacy request keys, fingerprints, status and nullable draft IDs transfer
  unchanged. A completed request requires a matching tenant, subject and
  draft. Even a matching row cannot establish a receipt or provider outcome.
  Held and failed rows with a draft reference require review.
- The stage-eight PostgreSQL attachment foreign key references
  `content_requests(tenant_id, request_id)`. SQLite's AI draft workflow can
  store that same attachment key under an AI draft ID with no content-request
  row. PostgreSQL rejects this source-valid case. A matching attachment
  metadata row also lacks a subject and can be ambiguous if two draft owners
  share an ID within the same tenant. Review explicit parent type, subject
  scope, namespace collisions and historical membership before selecting a
  schema change. Do not synthesize a content request to satisfy the constraint.
- Counts-only quota rows acquire `reserved_micro_usd=0` and
  `unpriced_requests=accepted` through the existing SQLite upgrade. A
  synthetic intermediate schema with only the reserved-cost column retains
  that cost but also marks all accepted requests unpriced. Current rows
  preserve both accounting fields. This holds across user, tenant and
  operator rows and a repeated initializer. The PostgreSQL zero defaults
  cannot replace the legacy backfill.

These tests copy only hand-seeded fixtures into the disposable preview and
leave production transforms, receipt creation and media trust decisions gated.
