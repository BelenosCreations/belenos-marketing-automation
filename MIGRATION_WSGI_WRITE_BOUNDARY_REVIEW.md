# Offline held-draft and pending-media write boundaries

For auth, membership, invitations and the local product/service draft alias,
see the [offline identity write review](MIGRATION_WSGI_IDENTITY_WRITE_REVIEW.md).

This source review follows selected calls through the local-only
`BAMOfflineGateway` to their SQL and filesystem sites. The CI report in
`neon_ci_wsgi_write_boundary_review.py` binds the hand-reviewed paths to the
gateway, handler, service and store source hashes. If a pinned file changes
or disappears, the report withholds its reviewed write mappings. The report
retains unreviewed delegates and handlers whose indirect calls the upstream
AST review could not extract. Source hashes identify the reviewed revision.
Deployment reachability and production enforcement require separate evidence.

## Request paths

| Method and route | Service chain from the handler | Mutation and boundary |
| --- | --- | --- |
| `POST /api/v1/content/drafts` | `AccountReadAPI.create_held_draft` → `ContentRequestService.create` → `ContentRequests.create` | [SQLite context and INSERT](content_requests.py#L64-L71) |
| `POST /api/v1/content/hold` | `AccountReadAPI.update_draft_hold` → `ContentRequestService.set_hold` → `ContentRequests.set_hold` | [SQLite context and revision-conditional UPDATE](content_requests.py#L177-L183) |
| `PUT /api/v1/content/drafts` | `AccountReadAPI.revise_held_draft` → `ContentRequestService.revise` → `ContentRequests.revise` | [SQLite context and revision-conditional UPDATE](content_requests.py#L198-L208). The reviewed source limits the dynamic SQL column to two allowed names. |
| `PUT /api/v1/content/priority` | `AccountReadAPI.update_held_priority` → `ContentRequestService.set_priority` → `ContentRequests.set_priority` | [SQLite context and priority-version-conditional UPDATE](content_requests.py#L114-L125) |
| `POST /api/v1/content/upload-preflight` | `AccountReadAPI.begin_content_upload_preflight` → `ContentUploadPreflight.begin` → `AttachmentRegistry.register_pending` | [SQLite context and pending metadata INSERT](content_attachments.py#L38-L43) |
| `PUT /api/v1/content/media-bytes` | `BAMPendingMediaStore.authorize_slot`, then `BAMPendingMediaStore.receive` | [Exclusive file creation, write, file fsync and error cleanup](bam_pending_media_store.py#L195-L208). Receipt leaves the metadata pending. |
| `DELETE /api/v1/content/media-pending` | `BAMPendingMediaStore.discard` | [File unlink, then SQLite context and pending metadata DELETE](bam_pending_media_store.py#L160-L171). These are separate effects. |
| `GET /api/v1/content/media-status` | `BAMPendingMediaStore.statuses` | [Direct SQL reads and filesystem stat](bam_pending_media_store.py#L68-L111). The reviewed body contains no direct mutation. |

The gateway wires the draft handlers to `AccountReadAPI` and the pending
handlers to a local store when pending media is enabled and a directory is
configured. It supplies the same SQLite connection to the two content
repositories. A `with db:` location shows where SQLite exits the connection
context, committing or rolling back when a transaction is active. Session and
membership checks occur upstream, and draft and priority versions protect
against conflicting edits. The reviewed paths lack a shared migration epoch
check inside those transactions.

## Other entry points and open paths

- The [loopback HTTP demo](dev_http_gateway.py#L81-L121) also calls the draft
  create and hold methods. Its [demo entry point](dev_server.py#L22-L25) uses
  in-memory SQLite. The [HTTPS preview](bam_local_preview.py#L166-L202) opens a
  local SQLite file. Its provisioning commands and gateway construction can
  mutate storage outside request handling.
- [ContentRequests initialization](content_requests.py#L13-L46) can run DDL and
  a priority-version backfill. [Pending-store initialization](bam_pending_media_store.py#L22-L36)
  can create a directory. Both need explicit treatment in any freeze plan.
- [Local product/service draft handlers](bam_local_draft_wsgi.py#L124-L126)
  select a callable through a local variable. The upstream scan emits no
  direct delegate for them. The identity review adds a separate pinned alias
  mapping and traces auth, invitations and membership. Preferences, calendar,
  review feedback and other AI state remain open.
- The tracked [hosting plan](BAM_HOSTING_PLAN.json) lists deployment and job
  activation as disabled. It provides no independent inventory of actual
  workers, callbacks, provider retries, scheduled jobs, operator tools,
  object-storage writers, subprocesses or non-Python clients.

## Inactive design requirements for the mapped paths

For database writers, the proposed generation row and each mutation must use
the same authoritative database transaction. Each writer must present its
original admitted generation and use a lock that conflicts with the freeze
transition, held through commit. An independently authenticated operator
transition advances the generation while holding that same lock. If the
writer commits first, the freeze waits and its snapshot includes that commit.
If the freeze wins, a stale or paused writer must fail before its mutation.
Retries after an uncertain commit must resolve the original operation ID
against a transactionally written receipt before retrying. A restarted worker
must never re-stamp old work with a new generation. Startup schema/backfill and
manual tools need the same admission or a separate, explicitly drained phase.

The media file store cannot join the SQL transaction. Receipt writes a file
after its metadata check, and discard can unlink a file before the later SQL
delete succeeds. A future design needs durable, idempotent media operation
records and a recoverable state machine, with storage-enforced denial of stale
publish/delete operations or independently verified drain and credential
revocation before freeze. A database epoch alone cannot stop a writer that
already holds an open file descriptor. Recovery tests need to cover crashes
after file creation, after unlink and before the associated metadata decision.
Review storage durability, directory metadata sync, orphan reconciliation and
which media operations may resume after a generation change.

Independently authenticated operator transitions, externally custodied latest
heads and signing keys, deployed writer inventory, independently recoverable
backups and security review are still required before an authorized cutover.

Run the source-evidence tests with:

```sh
python -m unittest test_neon_ci_wsgi_write_boundary_review -v
```
