# Alternate write entry points

Reviewed against main `afe883ede843dffff60a3c06c93dcb9c344973e1`. This is a
read-only inventory of checked-in entry points and candidate effects. The
[gateway](MIGRATION_WSGI_WRITE_BOUNDARY_REVIEW.md),
[identity](MIGRATION_WSGI_IDENTITY_WRITE_REVIEW.md), and
[editorial](MIGRATION_WSGI_EDITORIAL_WRITE_REVIEW.md) reviews identify
comparable request paths. Deployment and runtime bindings require independent
evidence. This review did not start services or access operational data.

## Repository inventory

| Entry point or callable | Checked-in effects | Relation to the gateway review |
| --- | --- | --- |
| HTTPS preview and provisioning CLI | [Preview startup](bam_local_preview.py#L166-L202) opens a local SQLite file and constructs stores, which may run schema setup and backfills. [Owner provisioning and add-business](bam_local_preview.py#L47-L130) create a private file as applicable and commit credentials, verification, memberships, profiles and temporary session changes separately. | Request handling delegates to the reviewed offline WSGI gateway. Provisioning and startup writes bypass its request routes. |
| Legacy loopback demo and client | The [demo server](dev_server.py#L22-L59) seeds an in-memory database. The [client](dev_client.py#L55-L98) sends draft, hold, logout and business-switch requests to the [legacy transport](dev_http_gateway.py#L81-L121). | Uses some of the same account API methods. Legacy business switching does not invoke the newer WSGI source-session cleanup. |
| Legacy engine and approval tools | The [engine demo](engine.py#L53-L79) stages a post in SQLite. [Workflow helpers](workflow.py#L26-L100) commit pause, approval, discovery and dry-run outbox records. [Tenant content helpers](tenant_content.py#L42-L80) commit tenant-specific posts, approvals and events. | Separate Python callers. A dry-run outbox record is a database write. The repository does not show an approved deployed dispatcher. |
| Editorial intake and scheduling settings | [Editorial inbox](editorial_inbox.py#L40-L98) can insert or delete a candidate, including during a review recheck. [Scheduling settings](scheduling_settings.py#L41-L63) and [approval intent](approval_intent_service.py#L62-L93) have separate SQL stores. | Distinct from posting preferences, feedback and calendar proposals in the WSGI map. External callers and publication decisions need review. |
| Disabled AI composition and operator controls | The [factory](bam_ai_offline_factory.py#L38-L64) constructs SQLite stores and disabled generation/revision adapters. Future invocation could commit idempotency, quota, output and completion separately. [Operator pause](ai_sponsorship.py#L117-L148) writes its own control row. [Cost accounting](ai_cost_ledger.py#L73-L132) writes independently. | Separate composition from the gateway's local drafts and previews. Plan resolution, provider calls, retries and usage attribution are unverified. |
| Trusted email recovery | [Recovery](email_credential_recovery.py#L36-L94) commits a token before calling injected delivery. Confirmation and password reset consume the token before later verification or credential changes. Session revocation is another commit. | Separate from sign-in and invitation routes. The actual delivery and any external caller remain unknown. |
| OAuth attempt and connection metadata | [OAuthAttemptLedger](oauth_attempt_ledger.py#L27-L74) writes a one-use attempt and consumes it under a write reservation. [Connection registry](provider_connection_registry.py#L27-L58) commits metadata with stale and revoked-state checks. | Gateway connection views read metadata. This source does not establish a mounted provider callback, vault writer or token exchange. |
| Analytics imports | An [injected fetcher](analytics_page_adapter.py#L31-L35) supplies the page before the write. The [connection gate](connection_gated_analytics.py#L31-L46) requires a shared connection and passes a recheck into the [transaction](analytics_sync_coordinator.py#L42-L67) that writes observations and the cursor. [Direct ingestion](audience_observation_store.py#L23-L43) can commit independently. | No verified deployed fetcher or schedule. Direct ingestion and scheduled/retry entry points need independent attribution. |
| Scanner worker boundary | The [CI-gated scanner](bam_clamav_worker_boundary.py#L95-L154) reads pinned local files and invokes a subprocess. The result is a candidate scan verdict. | Separate from WSGI receipt and file discard. Actual worker isolation, external process effects, genuine signatures and rights enforcement remain unverified. |
| Synthetic recovery tools | [Archive](bam_offline_durable_archive.py#L48-L90), [relocation](bam_offline_recovery_relocation.py#L58-L90) and [revocation ledger](bam_offline_revocation_ledger.py#L111-L156) rehearse private filesystem writes and durability. The [migration preflight](neon_migration_operator_preflight.py#L57-L119) reads supplied SQLite metadata. [Schema inventory CLI](neon_schema_inventory.py#L110-L123) builds a separate memory-only database. | Test and operator research. The [PostgreSQL migration helper](neon_ephemeral_ci_migrations.py#L42-L98) writes only under the disposable CI connection checks. |
| Repository tooling and browser clients | [Branding generation](tools/build_branding.py#L26-L56) writes PNGs. The [history audit](tools/public_git_history_scan.py) invokes Git to read repository data. Browser scripts call gateway HTTP routes. The checked-in [test workflow](.github/workflows/tests.yml) and [history audit workflow](.github/workflows/public-release-audit.yml) run CI. | Repository and client activity does not independently establish database access, a deployed worker, or a live release entry point. |

## Deployment evidence still needed

The tracked [hosting plan](BAM_HOSTING_PLAN.json) records hosting and job
activation as planning-only. There is no checked-in production release or
scheduler definition in the reviewed commit. Confirm the actual service and
entry-point inventory with the owner before freeze. For every process,
scheduled job, retry consumer, webhook, migration/admin command, non-Python
client, provider/vault integration and storage writer, record its release
version, account and write permissions, storage target, transaction boundary,
and how it drains or rejects stale work. Independent deployment evidence is
required to establish completeness.

## Isolated freeze and retry rehearsal

The selected split is [AI draft persistence before request finalization](ai_generation_workflow.py#L64-L110).
In the actual disabled workflow, the draft and completion marker have
separate commits. A crash can leave a draft while the request still reports
in progress.

The CI model `neon_disposable_split_commit_rehearsal.py` reuses the private
disposable SQLite generation fixture. The synthetic output carries the
original operation ID, tenant and generation as its durable receipt. Each
normal write checks the same admitted generation while holding a write
reservation. Following freeze, connection reopen and resume, an explicit
recovery action may finalize only a matching receipt from an earlier
generation. That action writes request status only, so repeating it cannot
create another draft or call a provider. An absent or mismatched receipt
leaves the operation unresolved. Ordinary workers cannot re-stamp an old
operation with the new generation.

Tests cover stale and frozen workers, operation replay, cross-tenant recovery,
missing or altered receipts, a lost acknowledgement, rollback on abandoned
connection and lock ordering. The fixture uses caller-supplied synthetic
identifiers and models recovery authority without authenticating an operator.
It cannot reconcile provider charges, quota reservations or real draft rows,
and it adds no fencing to BAM's runtime.

```sh
python -m unittest -v test_neon_disposable_split_commit_rehearsal
```

The [AI request recovery design](MIGRATION_AI_REQUEST_RECOVERY.md) maps
those receipts to the actual stores, separates uncertain provider outcomes
from committed output, and rehearses database locking and rollback in CI.
Independent recovery authorization and storage rollback remain open.
