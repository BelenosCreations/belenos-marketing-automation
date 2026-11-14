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

The recovery fixture also tests both lock orders against freeze. If freeze
holds the authority row first, the recovery statement aborts before writing
the request or audit. If recovery holds the row first, freeze cannot finish
until the recovery transaction ends. The committed frozen generation denies
recovery even with its current generation and head.

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

An isolated PostgreSQL test signs the resume transition and the subsequent
confirmation with two independently generated test keys. The transition binds
the environment, purpose, prior generation and head, next generation and
expiry. Confirmation binds the pending generation and digest of the signed
transition under a distinct purpose and key. A new connection sees the
pending state. Tampered, expired, mis-scoped, wrong-key and replayed evidence
cannot reopen it. The keys, clock and database roles in this test are
synthetic. Operator identity, revocation, independent key and head custody,
and database grants still need operational verification.

The expanded disposable fixture keeps a confirmation deadline on the pending
authority row. Confirmation must be inside both the transition deadline and
the witness signature expiry. Revocation and confirmation take the same
authority lock first. The test verifies a lock conflict before the revocation
commits and denial afterward. An aborted stage transaction restores the
prior frozen row. These checks use a synthetic clock and revocation row.

PostgreSQL requires update privilege for a direct row-locking read. A
separate disposable grant fixture denied that read, direct authority changes
and direct canary inserts to the writer role. Its only write path was a
fixture function that checked the expected open generation under a row lock
before inserting. The operator could freeze but could not use that canary
path. A deployable design still needs a reviewed function owner and grants,
trusted generation, independent revocation and head custody, and equivalent
coverage at every real write path.

For the next grant rehearsal, use a dedicated non-login function owner with
only the table grants the function needs. Check who may create objects in
the function schema, who may replace the function, and whether a caller can
shadow any referenced object through its search path or temporary schema.
Test a clock read after lock acquisition and require a non-null deadline
for pending authority. Compare an independently held revocation head with
the restored database state before accepting a fresh confirmation.

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

### Proposed attachment parent review

An ordinary attachment would reference its tenant and content request. An
AI attachment would reference its tenant, subject and AI draft. Give each
association an explicit parent type and constrain it to exactly one parent.
Preserve the attachment ID and its storage metadata. Keep the existing
ordinary-request foreign key until a replacement design has been reviewed
against every reader and writer.

| Legacy evidence | Disposition to rehearse |
| --- | --- |
| Ordinary request matches and no AI parent or conflicting link exists | Candidate for the ordinary parent after verifying the tenant, request and item. |
| AI draft matches and exactly one legacy media link matches the same tenant, subject, draft and attachment | Candidate for the AI parent after independently validating provenance and historical ownership. A legacy metadata status is insufficient for media trust. |
| Both namespaces match, two subjects own the same draft ID in a tenant, or links disagree | Hold the attachment and preserve the contradictory associations. Require independent provenance to resolve the parent. |
| Only an AI draft ID matches and no link identifies its subject, no parent matches, or the tenant differs | Hold for review. A draft ID by itself cannot establish ownership. |
| The historical subject is inactive or membership is absent | Keep historical attribution for review. Current session and membership checks must govern any future access. |

Before a schema proposal, exercise content status reads, pending-file
receipt and discard, trusted byte inspection, scanner and rights decisions,
review readiness and AI draft link reads against these cases. Inspect how the
legacy integrity preflight reports attachments whose only parent is an AI
draft. Keep its existing blocker until classification and ownership rules
have independent evidence.

### Disposable attachment parent results

The SQLite fixture classified only an ordinary row with a required item and
no conflicting link, and an AI row with one scoped owner and one matching
link, as candidates. An unmatched item, unlinked AI draft, cross-tenant row,
foreign link, duplicate owner, conflicting link, or same-tenant namespace
collision stayed held. The existing integrity preflight still flags
AI-only rows as missing an ordinary parent. The review leaves all source
rows intact and grants no media trust.

The disposable PostgreSQL model enforced exactly one parent type with
separate composite foreign keys. Two namespaces can share an ID when
their typed associations are explicit. The model preserved historical
subject and storage references after membership was deactivated or removed,
while the fixture's subject-scoped read denied access. This is a candidate
shape for comparison, with no preview schema or runtime change.

Existing ordinary status, verified binding and review readiness accept a
synthetic legacy row when its AI draft ID collides with an ordinary request.
The pending-file status reader and signed evidence probe also treat that
collision as an ordinary request. For an AI-only ID, the existing receipt
and staged evidence probe refuse the row, and ordinary discard leaves its
file and metadata in place. These fixtures expose the limits of untyped
lookups. A future proposal needs to bind the explicit parent to file receipt,
discard, scanner and rights evidence, review readiness, and AI draft reads.
Keep colliding rows held and require independent provenance before approval.

### Typed attachment binding proposal

Use the attachment ID and the immutable parent tuple as the shared binding.
For a content request, the tuple contains the parent type, tenant and
request ID. For an AI draft, it contains the parent type, tenant, subject
and draft ID. The same attachment ID must resolve to exactly one binding.
Keep verified bytes and the storage key tied to that binding during receipt
and discard. Ordinary and AI callers each need an explicit lookup path.

| Boundary | Evidence to rehearse |
| --- | --- |
| Pending receipt and discard | Load the typed row under the current principal. Verify the same type and complete scope on each read and before file or metadata mutation. Exercise a same-tenant collision, stale membership and an interrupted discard with bytes and metadata in different states. |
| Byte inspection and signed claims | Include parent type and the complete applicable scope in a new claim version, with attachment ID, byte digest, item and media type. Exercise parent substitution, subject substitution, reused bytes and attempts to use legacy claims as typed evidence. |
| Revocation | Bind a revocation to the version and digest of the exact claim. Preserve existing legacy records and hold attachments with unresolved legacy claims. Verify that a newly typed claim cannot bypass a relevant unresolved revocation. |
| Review and AI draft reads | Resolve status and approval prerequisites through the same typed parent. Check current sessions and membership at the read or write boundary. Exercise collisions in both directions and prevent identifiers or storage metadata from leaking through error responses. |

Keep the legacy claims and unresolved parent rows available for review.
Require new, independently reviewed evidence before promoting any association
into a typed trust path. Evaluate the proposal only with disposable data.

### Disposable typed binding results

- A versioned signed envelope binds the complete parent tuple to an
  existing independently signed scan or rights claim. The test checks
  actual synthetic PNG bytes and denies namespace, subject and attachment
  substitutions, including an identical PNG under a second attachment.
- The authenticated revocation chain records a digest of the exact signed
  claim. The fixture supplies a complete synthetic claim index so the
  original attachment can be held after reissue, including a revoked
  legacy claim. An unknown digest holds the check. An older chain fails
  against the supplied current head. Production still needs an independently
  maintained head and authenticated durable claim retention and resolution.
- A private SQLite fixture keeps an immutable parent tuple and commits a
  discard intent before unlink. It retries after failed unlink or failed
  metadata finalization and denies new receipt while discard is pending.
  Reopening the fixture preserves the intent and a current membership is
  required to finish. A colliding request's attachment stays intact. This
  covers selected interruption cases with synthetic files. It does not
  measure power-loss durability or distributed storage recovery.
- A non-login PostgreSQL function owner gets a column grant for row locking
  and can insert the canary. It cannot change the generation or mode. The
  writer cannot create objects in the authority schema or replace the
  function. Temporary lookalike tables cannot redirect the fenced insert.
  The confirmation fixture requires a deadline and samples the database clock
  after the row lock. Missing or stale restored revocation state cannot
  confirm against the supplied independent pin.

Next, rehearse typed read and approval visibility, and review how an
authenticated claim index is retained, independently recovered and checked
for completeness. Keep the current runtime and production transforms gated.

### Claim index and review visibility follow-up

The revocation ledger contains a digest of the full signed claim. Recover the
matching canonical claim bytes from a private index before attributing a
revocation to an attachment. Recompute the digest, verify the claim version
and issuer evidence, and preserve the original scope. Keep a missing digest,
unrecognized version, or conflicting record held. An independently supplied
checkpoint must bind the index inventory and revocation head together.

Use disposable fixtures to rehearse a consistent restore of the index and
ledger, including an incomplete index, a stale but internally consistent
snapshot, cross-tenant claim substitution and key rotation. Verify a single
attachment ID cannot resolve to more than one typed parent. Exercise ordinary
and AI read and review queries with the same parent ID and different subjects.
Keep legacy and ambiguous rows unavailable to approval paths and preserve
historical evidence for review. Gate rollout on an independently verified
runtime writer and reader inventory and an authorized operational restore.

### Disposable claim-index restore and review results

The SQLite rehearsal commits each revocation and its canonical signed claim
together, then copies the database with the SQLite backup API. A separate
fixture witness retains a digest of the ledger head and ordered claim index.
The restored read verifies the complete chain, requires a one-to-one match
between revocation digests and index entries, checks the canonical bytes
and historical issuer signature, and verifies the attachment binding before
returning review candidates. Missing, extra, corrupt or unknown evidence
holds the read. A stale copy fails against the latest independently supplied
pin even when its own earlier ledger and index agree.

The synthetic issuer catalog supplies separate historical scan keys and a
rights key, with issuance windows. A legacy claim retains its original
tenant, attachment ID and parent ID. Typed claims additionally verify the
parent type and subject. The test claim formats are private fixture formats.
An attachment ID has one immutable typed parent, ordinary and AI readers
resolve different scopes for the same parent ID, and ordinary viewers can
see scoped metadata while review eligibility requires an active reviewer.
Pending and legacy-held records stay outside the review candidates.

A disposable PostgreSQL test runs confirmation and restore staging on two
connections. Restore takes the authority lock, advances the generation and
stages a frozen row. Confirmation under a stale pin is refused. When
confirmation obtains the lock first, restore waits for a retry and the
subsequent restore closes admission again. The fixture models staging a
restored head and reconciliation. Actual disaster recovery requires an
independent witness, issuer key custody, authenticated operators and
measured off-host backup restore. The fixture grants no editorial approval
and supplies no new runtime attachment reader or migration transform.

### Authenticated witness and encrypted replica rehearsal

A disposable SQLite test takes a consistent snapshot, serializes it in
memory, and uses the existing AES-GCM archive and signed manifest helpers.
It relocates ciphertext to a separate private directory on the same host
and restores it after simulated loss of the original ciphertext. A separate
Ed25519 fixture witness binds the checkpoint to the archive manifest head,
archive name, revocation and claim-index digest, and issuer-key fingerprints
and issuance windows. Restore receives the current witness key, epoch and
checkpoint pin independently from the replica. Historical issuer keys
remain available for verifying prior revocations.

The test rejects a previously valid witness and archive, a missing witness
key, an old key signing the current epoch, and removed, substituted or
re-windowed issuer keys. SQLite integrity and foreign keys are checked before
the existing review gate runs in memory. An interrupted restore produces no
review result and can retry against the same independently pinned checkpoint.

In disposable PostgreSQL, confirmation and a signed rotation share the
authority lock. Rotation advances the revocation head and key epoch and
closes the confirmed generation. After restoring an older row, the fixture
stages a generation above the independent floor and requires a current-key
confirmation. The test uses preauthorized fixture keys and an in-process
witness. Operational key custody, cross-instance admission and measured
off-host recovery remain open.

### Witnessed promotion and revocation ordering

A disposable SQLite authority file stages the verified replica digest under
the current generation and revocation checkpoint. The replica and the
completion witness use separate fixture keys. Promotion compares the staged
digest, checkpoint and generation in one transaction. Closing and reopening
the authority connection leaves the candidate staged and review closed. An
interruption before commit rolls back both pointer changes. Once promoted,
each review checks the generation and reopens the replica through the
existing ciphertext, issuer catalog and claim-index validators.

The fixture simulates publishing a newer revocation to authority after
staging. That transition advances the generation and clears the staged and
active pointers. An older completion cannot promote the previous backup.
The current replica must validate and receive a new completion before its
scoped review can run. Corrupted ciphertext or missing issuer history
blocks review. The staged and active entries are fixture pointers rather
than a replacement of a live database.

In disposable PostgreSQL, a signed revocation advance and an admission
canary acquire the same authority row lock on separate connections. The
first lock holder commits before the other can proceed. A revocation
advances the head and leaves the new generation pending. A new connection
observes the committed pending state after the revocation connection closes
before acknowledgement. Old signatures, replayed updates and an
acknowledgement superseded by another revocation cannot reopen admission.
An independently signed acknowledgement for the current generation does
open the fixture. The canary records only its test operation and generation.
External witness custody and transaction-bound checks in deployed paths
remain required.

### Receipt reconciliation and recovery grants

The disposable SQLite promotion transaction records a receipt over the
signed completion, generation and checkpoint. If the commit succeeds and
the caller loses the acknowledgement, repeating the exact completion
returns the same receipt. A separate reconciliation step matches it to the
independent generation, state pin and receipt. Both scoped review and the
write canary check that tuple and the reconciled state under the authority
lock. A receipt mismatch keeps both paths closed.

The test restores a real older SQLite authority snapshot taken before a
newer revocation. That snapshot contains a locally reconciled receipt. An
independently retained current generation blocks the older state even when
the local row looks open. A second recovery advances above that generation,
validates the new encrypted replica and reconciles a fresh receipt before
admitting either operation. The external witness is represented by fixture
inputs. The test measures no off-host recovery or external witness custody.

The PostgreSQL grant fixture uses separate non-login caller roles for staging,
acknowledging a pinned receipt and invoking write admission. Public function
execution is removed, tables are qualified, and each function has a fixed
search path. The writer cannot reset authority or insert the canary
directly. A stale or pending generation is refused, and the acknowledgement
function requires a matching independently seeded receipt digest. The
trusted fixture setup seeds that digest. Deployed receipt authentication,
function ownership, grant inheritance and direct client coverage still
require operational verification.

### Signed witness journal and function owner grants

A separate disposable SQLite file retains ordered, Ed25519-signed witness
records. Each record binds the previous record digest, generation,
revocation state pin and promotion receipt. An independent fixture observer
retains the latest digest. After a lost acknowledgement, a fresh connection
can repeat the exact append against that digest without duplicating a row.
A valid older backup still verifies under its historical digest and fails
under the latest digest. A completion signing key cannot verify journal
records.

The authority fixture closes admission before publishing a newer witness.
While it holds the write reservation, a second connection with the previous
signed tuple cannot reconcile. Retrying after commit also fails because
the generation and state have changed. Current witness evidence and
receipt reconciliation are required before review or a test write. Journal
and authority files are local fixtures. The ordering and latest-head
observer must be established independently for any operational design.

The PostgreSQL rehearsal assigns separate owners to stage, acknowledgement
and admission functions. The admission owner has the lock-column grant
and reads only witness generation metadata. A role inheriting the writer
grant can invoke admission but cannot stage, acknowledge, or reopen the
authority row. Public function execution and witness writes are refused.
A newer pin blocks an older pending acknowledgement and invalidates an
older open generation on a subsequent admission. These tests observe
already-committed witness rows. Concurrent witness updates, external
latest-head custody and deployed role membership remain operational gates.

### Signed witness-head publication

A disposable SQLite rehearsal signs publication with a key distinct from
the journal and promotion completion keys. A publication identifies its
key epoch, sequence, predecessor and latest journal digest. The publisher
validates the journal chain and checks the committed promotion while
holding the authority, journal and publication reservations. The signed
publication lives in a separate local file. Exact retry is idempotent.

The test closes and reopens the files after the journal commits and before
the head is published. The old publication cannot authenticate the newer
journal. An old key epoch, a journal key acting as publisher, or a signed
fork cannot publish the pending head. A second connection encounters the
publication lock and may retry after it is released. Review and writes
remain closed until the new publication is verified and reconciled.

The test caller retains the publication sequence and SHA-256 digest of its
signed bytes independently of the journal, publication and authority files.
An append requires the retained predecessor. After an interrupted response,
an exact retry can recover the committed pin from that same predecessor.
Review and write admission recheck the retained pin and the journal head
under the fixture's SQLite reservations. Restoring a valid older journal and
publication together fails the pin check, even when the older publisher key
is accepted and the authority file is restored to its reconciled state. The
new key also refuses the older publication and a stale pending head. The
test caller supplies the pin in memory. Durable external custody is still
an operational requirement.

Disposable PostgreSQL tests put publication, acknowledgement and write
admission on a common authority-row lock across two connections. When
acknowledgement or admission takes the lock first, publication must retry.
When publication takes it first, the competing acknowledgement and
admission cannot proceed and are refused on retry with the old generation.
The publisher's function owner can append a pin and lock the authority row.
Caller grants separately cover publication, staging, acknowledgement and
write admission. The PostgreSQL fixture uses synthetic digests and database
roles. Operational key custody, independent persistence and deployed
reader and writer coverage still require verification.

The fixture increments a revision on the authority row in the same
transaction as the new publication pin. Under PostgreSQL `REPEATABLE READ`
and `SERIALIZABLE`, overlapping transactions with older snapshots must retry
after the authority row changes. Tests discard the committed publisher
and acknowledger responses, then check that retries cannot append a
competing pin or admit the previous generation. Forced rollbacks leave
the previous pin or the pending acknowledgement in place.

The acknowledgement rehearsal also leaves the caller's independent
checkpoint on the previous publication after the database commits and the
response is discarded. The open database row alone cannot admit a write.
The writer supplies a generation and digest, both of which must match the
latest publication while the transaction holds the authority lock. A retry
on a fresh connection can confirm the exact acknowledged pin without
updating the row again. The previous pin and a current generation with
the wrong digest fail acknowledgement and admission. Only after the caller
advances its retained pin does the fixture admit a write.

The caller checkpoint is a SQLite file in a separate temporary directory
from the disposable PostgreSQL database. With the PostgreSQL acknowledgement
committed and its response discarded, the restarted caller reads the
previous pin from a fresh SQLite connection. Two fresh PostgreSQL sessions
confirm the same acknowledged generation and digest. Both callers then race
to update the SQLite row. The update matches the exact predecessor's
generation and digest and permits only the next generation. One update
commits. The other reports that it changed no row.

A wrong predecessor digest and a generation skip both leave the SQLite
checkpoint unchanged. After another acknowledged transition advances the
file, PostgreSQL refuses the superseded acknowledgement and write admission.
The local update also refuses the old transition that had already been
confirmed, so delayed work leaves the newer checkpoint intact. The write
canary accepts the pin read from the file after each successful advance.

The restart is simulated by closing and reopening connections. Both stores
run locally under the test runner. Authenticated checkpoint reads and
updates, crash and storage guarantees on the chosen infrastructure, and
independent operational custody still require evidence.
