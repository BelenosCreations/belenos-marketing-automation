## Disposable AI store mapping rehearsal (2026-11-13)

- Checked exact memory text and compare-and-swap, receiptless request scope,
  nullable draft fields and legacy quota backfill against the PostgreSQL preview.
- Reproduced rejection of a SQLite attachment whose parent exists only as an AI
  draft. Recorded same-tenant draft-owner ambiguity for the ownership review.

## Disposable PostgreSQL recovery rehearsal (2026-11-13)

- Reviewed AI store migration fields and documented independent evidence
  required for the deployment writer inventory.
- Exercised receipt-based request finalization and atomic audit recording,
  with stale authority, mismatched scope, missing receipts and replay cases.
- Exercised rollback of a draft prompt revision and its media-link removal,
  and write denial during pending resume and after a stale authority restore.

## AI draft request recovery design (2026-11-13)

- Recorded a proposed operator transition and independent-head confirmation
  sequence for crash and restore, and verified the GitHub deployment inventory
  available from repository metadata.
- Mapped generation and targeted revision to request, quota, draft and
  usage stores, with separate recovery decisions for missing receipts and
  uncertain provider results.
- Added regression coverage for interrupted requests in the existing SQLite
  stores and atomic receipts and generation locks in disposable PostgreSQL CI.

## Alternate writer inventory and split-commit rehearsal (2026-11-13)

- Documented alternate CLI, startup, operator, provider, analytics, scanner
  and recovery write paths alongside the gateway reviews.
- Added a disposable SQLite rehearsal for a freeze between draft persistence
  and request completion. Recovery requires a matching committed receipt.
- Tested stale and replayed operations, missing or mismatched receipts,
  lost acknowledgements, rollback on close and lock ordering.

## Offline editorial and AI write review (2026-11-13)

- Mapped posting preferences, calendar proposals, review feedback, AI facts,
  memory and manual draft edits to their SQLite boundaries.
- Added pinned read classifications for calendar and AI previews, with
  regression coverage for source drift and conditional media-link removal.
- Documented separate commits in the disabled AI generation workflow and
  the recovery evidence a future migration freeze needs.

## Offline identity and local draft write review (2026-11-13)

- Traced local draft aliases, sign-in, logout, business switching, membership
  changes and invitations to their SQLite writes and commits.
- Documented preview and demo startup writers and kept injected verifier
  and delivery behavior unresolved in the CI report.
- Added regression coverage for alias drift and separate commit boundaries.

## Offline held-draft and media write boundary review (2026-11-13)

- Added CI-only, source-pinned maps for draft creation, hold, revision, priority,
  pending attachment registration, media receipt and media discard.
- Documented the SQLite and filesystem boundaries, including discard's split
  file/metadata effects, startup writes and unresolved indirect local draft calls.
- Added regression tests for source drift, linked files, ambiguous attribution,
  deterministic evidence and the CI gate. No application write path was enabled.

## Verified #109 handoff simplification (2026-11-13)

- Made `DEVELOPMENT_CONTINUITY.md` the canonical handoff for future checkpoints.
- Exact-head Actions #43443398238 and merged-main Actions #43443740177 passed.
  Main and development matched at `f855a265a2973324637db23621de1e5cfcfbf62e`.

## Verified #107; candidate #108 WSGI downstream source call review (2026-11-13)

- #107 exact-head GitHub Actions #43438915110 PASSED; independently verified merged-main 7c557ed43f7696982e5e2bcf8130e807707636c9 Actions #43439178092 PASSED, main/development non-force synchronized identical 0/0 and no open PRs.
- #108 candidate adds CI-only AST inspection of direct WSGI handler dependency method names and constructor-parameter hints, deterministic digest binding and adversarial tests; migration/Beta documentation refreshed.
- Runtime/deployed service graph, transactional fencing, operator approval, actual backups, media safety and hostile hosted Beta security remain blockers. Exact-head and merged-main #108 checks pending. $0 additional spend, all external services off.

## Candidate #107 (2026-11-13) — static offline gateway binding candidates

- Added CI-only neon_ci_wsgi_binding_review.py and its adversarial tests, deterministic inventory-bound AST handler binding and literal guard hints.
- Added MIGRATION_WSGI_BINDING_REVIEW.md with explicit runtime and dynamic-call gaps.
- No production integrations, customer data movement, real cross-instance fencing, paid APIs or publishing. $0 cost; exact-head/merged-main CI pending.

## Verified #105; candidate #106 recovery review (2026-11-13)

- PR #105: CI-only conservative Python/WSGI/worker/callback possible source-call paths, unknown dynamic calls, unmapped writer sites and stable digest bound to the prior writer inventory; synthetic regression tests. First test run #43435037937 failed on an over-broad synthetic job fixture; repaired before final verification.
- Verified exact-head 5614680051aa569d39c6b844c644df70959d3d5b Actions #43435447478 PASSED; merged-main e8f5dd509463c83235724920e1beb23fb73fede0 Actions #43435718147 PASSED; main/development fast-forward identical 0/0, no open PRs.
- #106 candidate documentation-only: concrete source-level dispatch review notes, remaining dynamic handler bindings, risks and recovery checkpoint. No runtime read/write behavior or deployments changed. Exact-head/merged-main CI pending; no real migration, Beta, paid APIs or publishing. $0 incremental spend.

## Candidate #105 — offline ingress-to-writer static trace (2026-11-13)

- Started from independently verified #104 SHA 0cd22728bf63966252d7893dde526f44c986105f, main Actions #43430594571 PASSED, branches identical 0/0, zero open PRs.
- Added CI-gated AST-only possible direct-call paths connecting Python entrypoints, simple import aliases and candidate writer signals. Preserved unresolved calls, untraced mutation sites and stable source fingerprint binding.
- Added synthetic regression tests for cross-module alias, class method dispatch, dynamic-call gaps, source drift, gate and unsafe source refusal.
- No runtime coverage, real fencing, external authority, customer migration, Postgres connection, hosting or publishing. Beta blocked; $0 additional spend. Exact-head/merged-main CI pending.

## Verified #102–#103; candidate #104 documentation checkpoint (2026-11-13)

- #102 merged `5ccff62cd27ffb2230026a8b008478a788e8c83f`: exact-head Actions #43428652129 and merged-main #43428902180 PASSED. CI-gated AST Python/WSGI writer candidate inventory; deterministic digest; adversarial tests; fencing architecture review.
- #103 merged `099b79e5a92035af812d08ed6f612405fffac5cb`: exact-head Actions #43429490616 and merged-main #43429752709 PASSED. Disposable, transaction-bound SQLite generation test; stale/duplicate/abandoned-writer and crash/reopen controls, with no BAM writer enforcement.
- Both main and development fast-forward synchronized without force and independently confirmed identical, 0/0 divergence after #103.
- #104 documentation only: final verification and limitations recorded in README, CHANGELOG, DEVELOPMENT_CONTINUITY, milestones, migration roadmap and Beta/infrastructure documentation. Exact-head and merged-main #104 Actions pending.
- Customer migration, full writer fencing, independently recoverable offsite backups, operator authentication, genuine ClamAV provenance/worker, media rights, public/paid integrations and publishing remain disabled or unproven. $0 incremental spending.

## Candidate #103 — CI-only disposable generation admission test (2026-11-13)

- Independently verified #102: exact-head Actions #43428652129 and merged-main Actions #43428902180 passed, merged at `5ccff62cd27ffb2230026a8b008478a788e8c83f`, development fast-forward synced 0/0.
- Added `neon_disposable_generation_authority.py` with private auto-cleaned SQLite fixture, transactional generation/mode CAS, synthetic canary admission inside the same transaction, freeze and resume with epoch increments and duplicate request rejection.
- Added adversarial tests for stale generations, crash/connection reopening, transaction rollback, concurrent writer locks, invalid requests, and CI-only gate.
- Added `MIGRATION_EPOCH_FENCE_REHEARSAL.md` with explicit omitted distributed/operator/backup/production boundaries.
- No live BAM writer or PostgreSQL integration, customer data migration, publishing or infrastructure activation; #103 requires exact-head and merged-main CI before verification.

## Candidate #102 — CI-only migration writer-surface source inventory (2026-11-13)

- Added `neon_static_writer_surface_inventory.py` static, non-executing AST discovery of top-level BAM Python source SQL/transaction/file and WSGI/HTTP ingress candidates, including unknown SQL and deterministic source/inventory hashes.
- Added `test_neon_static_writer_surface_inventory.py`: real repository presence, static classification, digest drift, malformed source, symlink/hardlink, CI gate and unknown SQL regression tests.
- Added `MIGRATION_WRITER_SURFACE_REVIEW.md`: persistent epoch authority, transaction-bound fencing, stale callback/worker and crash safety, independent custody and rollback architecture requirements.
- Documentation updated; no production source writer, migration runner, PostgreSQL connection, customer data, hosting, scanner, paid API or publishing activated. Exact-head/merged-main checks pending; production Beta remains blocked.

## 2026-11-13 — Verified PRs #99–#100; candidate #101 recovery checkpoint

**Independently verified November 13, 2026:** PR [#99](https://github.com/BelenosCreations/belenos-marketing-automation/pull/99) exact-head Actions [#43378330269](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43378330269) PASSED, merged as `5398dbcb3772bb8a291fb1c5201413a57668d771`, independent merged-main Actions [#43378572835](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43378572835) PASSED; development fast-forward synchronized without force, 0/0 divergence. PR [#100](https://github.com/BelenosCreations/belenos-marketing-automation/pull/100) initially failed Actions #43379118389 on an HH:MM CVD parser delimiter regression, corrected on the same PR and verified exact-head Actions [#43379526308](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43379526308) PASSED; merged as `75824ebc75dda5a8a06969773b899a614c99d1b5`, independent merged-main Actions [#43379830054](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43379830054) PASSED. Development then non-force fast-forward synchronized and independently compared to main identical, 0 ahead/behind.

#99 adds private 0600 disposable SQLite HMAC operation-ledger test, reconnect persistence, verified caller-pin replay/epoch protection, terminal abort and tamper negative tests. All files vanish after CI; signing key and independent-head custody are unproven, and no BAM-wide API/worker fence or PG migrations are implemented. #100 adds read-only pinned 512-byte daily.cvd header metadata age and digest checks and adversarial parser/inode tests. An operator-supplied hash and reported freshness do **not** authenticate ClamAV's database signature, provenance, engine execution, isolation or media rights. No genuine scan, media approvals, production services or customer data migration. Remaining blockers: independently reviewed null/default/JSON/tenant/identity transformations, authenticated operator custody/approval, real globally respected writer fencing and replay/rollback, actual independently custodied encrypted offsite backup and measured recovery, authentic ClamAV signature/worker and human rights/revocation evidence, hostile hosted IAM/session/CSRF/media/proxy/tenant/abuse testing and explicit Beta authorization. $0 added spend; Render/Neon/paid AI/social publishing/EdgePilot remain disabled. **This PR #101 is documentation-only and must independently pass its own PR and merged-main Actions before becoming the newest verified checkpoint.**

**Test status:** #99 and #100 all final exact-head and merged-main CI passed. Initial #100 delimiter regression failed once and was fixed and retested. Documentation-only #101 CI pending; no production release claims.

## 2026-11-13 — Candidate #100 read-only ClamAV signature-metadata freshness

**Added:** separate CI-only synthetically tested 512-byte CVD header parser, SHA-256 pin, file inode safety, UTC timestamp consistency and configurable bounded age check, stale/tamper/forged-header tests. **Not achieved:** trusted publisher signature verification, authentic ClamAV execution/worker isolation, human rights review or any media approval. This is not production-ready; CI pending. $0 spend, services disabled.

## 2026-11-13 — Candidate PR #99 offline durable replay canary

**Added:** CI-only private local synthetic SQLite HMAC event ledger, reconnect persistence and replay/fence-epoch rejection, authenticated receipts against a caller-held head, terminal abort, tamper/permission/negative tests. **Test status:** candidate; exact-head/main CI not yet independently verified. **Limits:** no customer data, real PostgreSQL, app writer fence, true external authority or production DR; no paid services; $0 extra cost.

## 2026-11-13 — Verified functional PRs #96–#97; documentation-only checkpoint candidate

**Verified:** #96 CI-only SQLite v1 protocol (ordered stages, CAS receipts, ephemeral replay/stale-token guard, rollback/abandoned connection, blocked stage 08): PR Actions #43370721912 PASS, merged-main #43370961873 PASS, non-force reconciliation `d967dccfd6059a0b60a39e8e393cc550fff670c9` and final main #43371191220 PASS. #97 pinned real unexecuted journal and semantic/preview metadata prerequisites with tamper, replay, drift, privacy negative tests: exact-head #43371588657 PASS, merged-main #43371792518 PASS, main `b21f132009402f00f54a59df9843224ecea82c0a`, dev fast-forward synced without force, 0/0. **Unchanged limitations:** only disposable CI fixture; no authenticated operator, independently held keys/heads, approved customer mappings, durable replay authority or global worker fencing, PostgreSQL customer migration/rollback, offsite recovery, genuine malware or human rights approval, hosted private Beta, external publishing or paid AI activation. **This docs-only checkpoint** requires its own exact-head and merged-main Actions to be marked verified. Extra costs $0.

## 2026-11-13 — Verified #96, candidate #97 metadata-bound disposable protocol

**#96 verified:** PR exact-head Actions #43370721912 passed, merged-main Actions #43370961873 passed, followed by no-content two-parent non-force synchronization at `d967dccfd6059a0b60a39e8e393cc550fff670c9` and final main Actions #43371191220 passed; main/dev identical 0/0. **#97 candidate:** Add `neon_disposable_protocol_binding.py` and hostile tests to inspect a real proposed seven-step migration intent hash chain and pinned schema/plan/mapping/PG-preview/semantic metadata before the isolated v1 SQLite rehearsal; reject stale/tampered/partial pins and private-row disclosure. **Limitations:** No independently authenticated operator approval/key/head custody, accepted column/tenant/JSON transformations, persistent replay authority, BAM-wide fence, PG transaction/restore, offsite recovery, real malware or rights review, hosted Beta or publishing. **Test status:** candidate requires exact-head and merged-main CI. Additional spending $0; all production integrations disabled.

## 2026-11-13 — Candidate PR #96: inactive versioned migration protocol rehearsal

**Added:** `neon_disposable_versioned_protocol.py` and adversarial test coverage for version=1 ordered synthetic migration stages 01–07, atomic in-memory SQLite receipts, same-fixture operation replay and stale-fence rejection, staged synthetic payload rollback, abandoned-connection recovery and stage 08 refusal. **Security boundary:** CI gate `BAM_EPHEMERAL_PG_TEST=1`, unique in-memory SQLite URI, no external path, no customer rows or hosted PostgreSQL. **Known limitations:** Provided intent-head SHA is not authenticated and does not validate an actual operator journal, replay protection lasts only during the synthetic fixture, mock SQLite locks are not an application-wide fence, and no real PostgreSQL migration/rollback, offsite disaster recovery, malware/rights validation, Beta activation or publishing exists. **Test status:** locally unverified candidate, requires exact-head and merged-main GitHub Actions before verified release notes; added spending $0.

## 2026-11-12/13 — Verified PRs #93–#94, documentation recovery checkpoint

**Verified November 12–13, 2026:** PR #93 merged as `2b3afbf69519feccfd62d3479967d5addcf392a3` after exact-head Actions **#43368157960 PASSED** and independently successful merged-main Actions **#43368340201**. PR #94 merged as `bc9a0ba046a0ec5ae43d6ec95c14f853eae58e27` after exact-head Actions **#43368737129 PASSED** and independently successful merged-main Actions **#43368931927**. At both checkpoints development was fast-forward synchronized without force and independently compared to main as identical, 0 commits ahead/behind.

Both features remain CI-only synthetic/inactive research: #93 parses schema *metadata* to flag column nullability, default-presence, JSON-text, tenant/FK/constraint and identity review; independent hashes do not approve transforms, eliminate SQLite PK ambiguity or validate customer data. #94 checks signed *manifest metadata* for candidate incident planning; cannot prove an archive survives host loss, independent key/head custody, offsite redundancy, measured RPO/RTO, actual restored plaintext or production disaster recovery. Remaining blockers: independently reviewed real mappings/defaults/JSON/tenant ownership, disabled transactional PostgreSQL migration runner and full-application write fence with replay prevention/rollback, independently controlled offsite encrypted backups/keys/heads and measured restore tests, genuine isolated ClamAV binary/signature provenance plus human rights/revocation authority, hostile hosted authentication/session/CSRF/media/proxy/tenant tests and explicit Beta release authorization. No real customer migration, Render, Neon, external publishing, paid AI or EdgePilot activation. All production integrations remain disabled; **$0 additional costs**.

The earlier "candidate" descriptions for these PRs were written before their required CI gates. The checks above are the post-merge verification record; they do not confer production authorization.

## 2026-11-12 — Candidate PR #94: signed synthetic recovery incident planning

- Added CI-only recovery incident scenario planning around independently pinned, HMAC-signed synthetic recovery chain metadata, expiration policy, externally claimed key IDs and incident age limits.
- Added failure tests for wrong head/signer, changed/reordered manifests, expiration, host loss, unavailable keys and invalid/disabled inputs.
- A candidate manifest is **not** a validated local/offsite ciphertext, customer backup, actual restore, measured RPO/RTO, custody proof or DR acceptance. No filesystem access in planner, remote backup, deletion, migration, hosting, AI charge or publishing. $0 extra cost. Verification pending.

## 2026-11-12 — Candidate PR #93: CI-only migration column semantics review

- Added deterministic, independently pinnable, metadata-only source/target semantics report for 46 preview tables: nullable/PK ambiguity, default *presence* parity, JSON-text/tenant/FK/constraints, and sequence-reseed TODOs.
- Added negative CI fixtures for schema drift, incorrect external fingerprints, malformed DDL parsing, inactive-mode rejection and private-row non-disclosure.
- No SQL default expression export; all row transformations, operator signoff, PostgreSQL transactions, production fences, rollback, migration, hosted services, media proof and posting remain disabled. $0 additional costs; CI verification pending.

# Changelog

**Independently verified offline recovery checkpoint — November 12, 2026 (PRs #90–#91):** PR [#90](https://github.com/BelenosCreations/belenos-marketing-automation/pull/90) passed exact-head Actions [#43365704852](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43365704852), merged as `c68f33c1b1256aaacf3e2e6b77ec98845291c49c`, and passed independent merged-main Actions [#43365912019](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43365912019). PR [#91](https://github.com/BelenosCreations/belenos-marketing-automation/pull/91) passed exact-head Actions [#43366276568](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43366276568), merged as `e547e68aecd6a39cfcc16db71b7af4611e2b81a6`, and passed independent merged-main Actions [#43366443537](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43366443537). Both `main` and `development/phase-3-5-account-directory` were independently compared identical, zero ahead/behind, following non-force fast-forward. PR #90 adds **only CI-only, unexecuted hash-chained operator intent stages** 01–07 with pinned schema/plan/mapping and head drift detection; hashes do not authenticate approval, stage 08 is disallowed and no PostgreSQL, customer-data or rollback action occurs. PR #91 performs **only read-only same-host synthetic ciphertext inventory** against HMAC-signed manifests and independent head pins, classifying expiration without deletion; it does not establish offsite redundancy, escrow, external head custody, authorized retention action or actual customer recovery. Real column/default/JSON/constraint/tenant transformations, application-wide write fencing, versioned migration execution, independent backups/keys, authentic ClamAV signatures/isolation, human usage-rights adjudication and secure hosted private Beta ingress/session/CSRF controls remain blocked. All Render/Neon/paid AI/social publishing/EdgePilot integrations remain disabled. Additional spend **$0**.

**Candidate PR #91 — read-only CI ciphertext retention inventory:** Inspect existing private, same-host synthetic AES-GCM archive files against independently pinned HMAC-signed recovery manifests. Reject missing/extra names, symlink/hardlink/public inodes, digest mismatch and altered signer/head; report expired names for manual review only. No data is decrypted, copied, deleted or promoted; no offsite recovery, independent head custody, externally trusted retention enforcement or production backup is claimed. $0 extra cost and all production integrations disabled.

**Candidate PR #90 — CI-only pinned migration intent journal (not execution):** Adds a hash-chained, schema/plan/mapping-bound sequence for proposed migration stages 01–07, with independent head comparison, strict ordering, replay/tamper/promotion rejection and adversarial fixture tests. SHA-256 chaining is not a signature or independently authenticated approval. No PostgreSQL connection, SQL runner, BAM-wide write fence, actual rollback, customer rows, live services or promotion occurs. Stage 08 remains impossible. All production transformations, signed operator authority, offsite recovery and Beta gates remain blocked; incremental spending $0.

**Latest independently verified BAM functional checkpoint — November 12, 2026:** PRs [#86](https://github.com/BelenosCreations/belenos-marketing-automation/pull/86), [#87](https://github.com/BelenosCreations/belenos-marketing-automation/pull/87) and [#88](https://github.com/BelenosCreations/belenos-marketing-automation/pull/88) all merged, with separately successful exact-head and merged-main GitHub Actions. #86: [43363216197](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363216197) / [43363520290](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363520290), merged main `af5154b94573a01bd4c4e2fc08184149a2b1ec09`; #87: [43363803609](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363803609) / [43363985496](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363985496), merged main `177ecd90728e96a7d6c604bb4ba4f1731039e023`; #88: [43364238789](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43364238789) / [43364411439](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43364411439), merged main `d0b3255597349fd864842625e7dc0a5f6def55df`. Both main and development were independently compared identical, zero commits ahead/behind, after a non-force fast-forward.

**Verified offline scope, NOT production release:** #86 checks exact source/target synthetic values, integer ranges, finite floating-point/text/binary assumptions and independently pinned schema/mapping fingerprints without querying source rows or migrating data. #87 prepares a dormant ClamAV subprocess interface with external executable/CVD hashes, safe private file reinspection and negative mocked-CLI tests; no genuine engine/signatures were invoked in CI, no trusted worker isolation or rights adjudication is proven, and no scan claim/status approval is issued. #88 validates two-connection **in-memory synthetic SQLite** lock and rollback behavior only, not a BAM-wide production write fence. Real customer data transformation, transactional PostgreSQL runner, application rollback, authoritative offsite AES-GCM backup/head/key custody, independently authenticated scanner/rights reviewers, hosted session/tenant/CSRF/ingress hardening and publishing authorization remain blocked. No Render, Neon, paid APIs, social publishing or EdgePilot activation. Incremental spending: **$0**.

## Verified recovery checkpoint after PRs #86–#88

Latest independently verified functional main: `d0b3255597349fd864842625e7dc0a5f6def55df`; last verified merged-main Actions **43364411439** succeeded. PR #86 exact/main Actions **43363216197 / 43363520290**, PR #87 **43363803609 / 43363985496**, PR #88 **43364238789 / 43364411439** all succeeded. Main and development were synchronized without force and independently verified zero ahead/behind. No pending functional PR at this point; PR #89 is a documentation-only recovery checkpoint candidate. **Production is still inactive offline Alpha, not approved private Beta.** Distinguish: a synthetic conversion canary does not approve customer values; a mocked ClamAV CLI response does not prove real malware scanning or legitimate usage rights; a shared-memory SQLite lock does not fence BAM web workers or production PostgreSQL; same-host encrypted ciphertext is not offsite customer backup. Remaining gates: independently reviewed column/default/tenant transforms, versioned atomic migration/rollback and operator wide-area write fencing, externally controlled offsite backup/keys/heads, independently attested real ClamAV signatures and isolated worker, human rights-review and tenant-scoped revocation authority, hardened real sessions/CSRF/proxy/abuse tests, explicit operator authorization. Keep $0 added costs and all Render/Neon/paid providers/social/EdgePilot services disabled.


## 2026-11-12 — Verified CI-only PR #88: synthetic write-fence and rollback canaries

- Rehearse SQLite `BEGIN IMMEDIATE` writer rejection from a second independent disposable connection in shared memory, rollback on explicit release and on abandoned connection, and successful post-release writer.
- No user-controlled paths, customer connections, hosted PG execution, real BAM writer freeze or application rollback. Explicit inactive gate, bad-mode negatives, and CI fingerprint. Not production migration acceptance.


## 2026-11-12 — Verified CI-only PR #87: disabled ClamAV CLI worker boundary

- Prepared non-HTTP standalone scanner execution with externally pinned `clamscan` binary + CVD file, private pending inode SHA checks, bounded subprocess and mutation verification.
- Mocked-only CI tests cover clean/infected/error/timeout, external pin mismatch, hash changes, hard links, unsafe permissions, unsupported filenames and inactive gate.
- CI does **not** run genuine ClamAV; no independent vendor provenance, signature freshness, OS sandbox, tenant-scoped signed attestation, actual rights reviewer or attachment approval. All production integrations disabled.


## 2026-11-12 — Verified CI-only PR #86: strict synthetic migration type acceptance (pending verification)

- Add offline, CI-gated and dual-fingerprint-pinned candidate conversion checks for TEXT, integer target widths, finite IEEE-754 floats and byte arrays, with no returned plaintext or row reads.
- Negative tests cover NULL, NUL text/surrogates, oversized values, boolean coercion, target overflow, nonfinite float, wrong pins, source drift and inactive gate. **No approved value transformation or production migration.**


## Verified post-merge recovery checkpoint after PRs #83–#84

Main SHA `10e18ce0e5554fd9dab80048b9ef002bf5e58654`; both branches identical, no forced update. PR #83 exact/main Actions 43357261226/43357506877 succeeded, PR #84 43357908998/43358111378 succeeded. All features remain offline Alpha proofs. Next major branch: independently audited per-column value transforms and a disabled transactional operator protocol; offsite encrypted replicas and external key/head authority; verifiable isolated ClamAV/signature provenance and human rights review; tenant-scoped evidence/media authorization and hostile private Beta session/CSRF/ingress tests. Obtain explicit authorization before connecting or spending. No genuine malware scan, offsite production backup, live cutover or publisher exists.


## 2026-11-12 — Verified PRs #83–#84 (exact-head and merged-main CI passed)

- #83 merged at `8fe6eedf41f6576fd1d44e2960727e2c6dcb1775`; exact-head Actions 43357261226 and separate merged-main Actions 43357506877 passed. Development/main synchronized. Offline 46-table column/type proposals, drift pins and negative tests; no approved value migration.
- Verified #84 adds an immutable, private local ciphertext-only relocation rehearsal tied to independently signed recovery manifests. Tests simulated original loss and externally keyed AES-GCM restoration, wrong head/signature, ciphertext corruption, expiry, unsafe permissions and overwrite. Same-host synthetic test **is not offsite backup**.


## 2026-11-12 — Candidate PR #83: Offline target-column transformation review (CI verified)

- Add deterministic and independently pinnable metadata-only 46-table target-column/type review, with explicit binary/integer/identity and missing-column proposals.
- Add drift, malformed-pin, no-private-data and non-execution negative tests. Human review is still outstanding for **every** value, default, constraint and tenant relationship; no executable customer migration or activation.


**Latest independently verified BAM engineering checkpoint — November 12, 2026:** PR [#83](https://github.com/BelenosCreations/belenos-marketing-automation/pull/83) and PR [#84](https://github.com/BelenosCreations/belenos-marketing-automation/pull/84) both merged after exact-head and independent merged-main CI. #83: [Actions 43357261226](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357261226) and [43357506877](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357506877); #84: [Actions 43357908998](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357908998) and [43358111378](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43358111378). Latest independently verified merged `main` commit `10e18ce0e5554fd9dab80048b9ef002bf5e58654`. Development fast-forwarded without force and independently compared identical, zero ahead/behind.

**Verified engineering scope only:** #83 adds deterministically pinnable SQLite-to-PostgreSQL source/target column/type review proposals for 46 preview tables, with explicit value/default/tenant/identity review still outstanding and customer migration blocked. #84 adds independently signed synthetic ciphertext relocation between separate private *same-host* directories and an AES-256-GCM restore after original local loss. Neither proves real offsite backup, external key/head custody, retention, production migration, customer restore, actual ClamAV scanning or human rights review. Hosted sessions, private Beta security and trusted media workers remain incomplete. No Render, Neon, paid API, social publishing or EdgePilot integration was activated. **Additional spending: $0.** Passing CI is not production readiness.

## 2026-11-12 — Verified PRs #79–#81 and recovery checkpoint (PR #82 documentation-only candidate)

- #79: source metadata migration planning, dual schema/plan drift pins; exact-head Actions 43352486026 and merged-main 43352747474 green.
- #80: signed local ciphertext manifests, external keys, rotation/retention and authenticated restore; Actions 43353272446 and merged-main 43353494577 green.
- #81: durable append-only offline HMAC media revocations, independent head and tamper/rollback regressions; Actions 43354006070 and merged-main 43354211421 green.
- Latest verified engineering main SHA 2b01175e424c91121f78830ed169d705e426e8c1; synchronized development. All capabilities remain offline synthetic and not production. No new costs or services.


## 2026-11-12 — Durable local synthetic media-revocation audit (verified PR #81)

- Added bounded offline append-only HMAC event log with exclusive lock, atomic no-replace file publication, fsync and full independently pinned chain verification.
- Added negative tests for head rollback, tampering, removed events, stale append, symlink/hardlink, unsafe permissions and inactive gate.
- No persistent authoritative head, cross-host audit, actual scanner/reviewer, media approval or production authorization.


## 2026-11-12 — CI-only signed recovery manifests and key-rotation rehearsal (verified PR #80)

- Added externally keyed, separately pinned HMAC manifest chain for local synthetic encrypted recovery points with signer/encryption key ID rotation and bounded retention metadata.
- Added ciphertext reinspection/AEAD restore, missing-key, altered-byte, wrong-pin, truncation, tamper, replay and expiry regressions.
- No persistent audit/head custody, offsite replication, retention deletion, customer restore or production backup activation.


## 2026-11-12 — Inactive migration planning (verified PR #79)

- Added deterministic, metadata-only, eight-step source-column/target-table inventory and independent source/plan drift pins.
- Explicitly blocks all row mapping, PostgreSQL execution, writer fencing, cutover, application rollback and publication.
- Added private-content, drift and malformed-pin regressions. No new costs or services.


## November 12, 2026 — Fully verified PR #70–#73 engineering checkpoint

- PR #70: [merged main `9b1ad4fc`](https://github.com/BelenosCreations/belenos-marketing-automation/pull/70); exact-head Actions 43346035365 and merged-main Actions 43346263328 passed. CI-gated in-memory AES-256-GCM/HKDF recovery envelope; no retained backup.
- PR #71: [merged main `f7259ff3`](https://github.com/BelenosCreations/belenos-marketing-automation/pull/71); exact-head Actions 43346697060 and merged-main Actions 43346980909 passed. Private pending file-byte and independently signed scan/rights claim read-only cross-check; no real scanner/reviewer, state approval or publishing.
- PR #72: [merged main `016ebce4`](https://github.com/BelenosCreations/belenos-marketing-automation/pull/72); exact-head Actions 43347258606 and merged-main Actions 43347460345 passed. All 47 disposable PostgreSQL table restore payloads now cross authenticated in-memory encryption and tamper rollback tests, not durable disaster recovery.
- PR #73: [merged main `7f424894`](https://github.com/BelenosCreations/belenos-marketing-automation/pull/73); exact-head Actions 43347696317 and [merged-main Actions 43347901980](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43347901980) passed. Disabled-by-default local authentication and media byte-receipt transports reject remote/proxy-tainted/ambiguous framing.
- `main` and `development/phase-3-5-account-directory` synchronized without force at `7f4248940a84ad40d097c4541d11eba49b3f5b4a`. Candidate headings below are historical pre-verification notes. Production PostgreSQL adapter/migration, off-host encrypted retained backups/key custody/recovery targets, actual scanning/rights review with auditable revocation, and production Beta ingress all remain open. No hosting, paid services, customer data transfer, social posting or EdgePilot integrations activated; $0 added cost.

## November 12, 2026 — Candidate PR #73: fail-closed local identity/upload network ingress

- Standalone local HTTPS login and pending-media byte adapters now share the loopback-only network restriction already applied by the offline gateway. The guard also rejects unknown `X-Forwarded-*`/`X-Original-*`, proxy-address headers, `Transfer-Encoding`/duplicate-framing indicators and method override inputs. Negative tests verify requests are rejected before credentials or media reach handlers. This is private Beta ingress preparation, not a hosted/public reverse-proxy configuration or publishing enablement.


## November 12, 2026 — Candidate PR #72: encrypted synthetic PostgreSQL COPY roundtrips

- Integrate the existing CI-only authenticated AES-256-GCM envelope into every one of the 47 disposable PostgreSQL table-copy paths; each table has a distinct migration-plan/table fingerprint. Corrupted ciphertext must abort and rollback without a residual restore schema. Both the per-run key and ciphertext stay in memory; no durable encrypted file, recovery point, customer export, hosted database or social publishing is enabled.


## November 12, 2026 — Candidate PR #71: staged file and dual-signed proof probe

- Add a CI-only, read-only bridge between private pending image bytes, current tenant/draft attachment metadata, and two independently signed media evidence contracts. Reject swapped/corrupt or unsafe inodes, stale/foreign/closed records, tampered claims and wrong-channel rights. Keep pending status, evidence audit, review, scheduling and publishing untouched. Real scanner, rights reviewer and audit/revocation remain Beta blockers.


## November 12, 2026 — Candidate PR #70: synthetic encrypted backup envelope

- Add offline-only AES-256-GCM authenticated encryption for bounded synthetic restore rehearsal payloads, with random per-envelope salt/nonce, HKDF key separation, schema/freshness binding and tamper/wrong-key/expiry rejection. CI uses pinned `cryptography==46.0.2`. No durable backup, storage provider, key escrow, hosted database, customer migration, live publishing or spending is enabled.


## November 12, 2026 — Snapshot-consistent synthetic restore (verified PR #68)

- PR #68 merged as `3052f1e2a7ab65c4a19cf7b8a31e854fc94b6b88`; [exact-head CI 43344020606](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43344020606) and [merged-main CI 43344264999](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43344264999) passed. Development synchronized without force.
- Repeatable-read snapshot consistency is proven under a separate simultaneous PostgreSQL writer; source row changes committed by another connection survive while the synthetic target is discarded. Not durable backup, offsite recovery, hosted Neon, or release authorization.
- Status: all three milestones in this session, PRs #66–#68, fully verified. Prior "unverified candidate" changelog entries below are historical proposals.


## November 12, 2026 — Consistent-snapshot restore under concurrent edits (unverified candidate)

- In CI-only PostgreSQL logical restore, set the transaction to REPEATABLE READ before any schema/data access. Exercise a second connection changing a source draft immediately after its table COPY; both exported rows and parity checks must use the original MVCC snapshot while the committed external edit survives. No live backup or point-in-time recovery is claimed.

## November 12, 2026 — Independent signed media evidence contract (verified PR #67)

- PR #67 merged as `fdc179b5ba8260458019cb1f8092f71d34604734`, exact-head Actions 43343292465 and [merged-main Actions 43343554641](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43343554641) passed; development synchronized without force.
- Independent scanner-clean and rights-grant HMAC claims now undergo strict offline binding/signature/freshness checks. No actual scan, licensing review, worker integration, audit store, attachment-state change or publishing capability exists.

## November 12, 2026 — Signed media evidence contract (unverified candidate)

- Add a pure server-side offline verifier for separate HMAC-authenticated malware-scan and channel-specific owned/licensed-rights attestations, bound to exact pending attachment ID, tenant, request, item, MIME and SHA-256. Reject altered, foreign, expired, future-dated and wrong-signer claims. Never change attachment state or authorize publishing; a signed statement alone does not prove a scan or license exists.
- Synthetic tests only; actual trusted scanner, rights-verification workflow, private storage, tamper-resistant audit and production integration remain private-Beta blockers. $0 spend.

## November 12, 2026 — PostgreSQL restore constraint/index parity (verified PR #66)

- PR #66 merged as `51944ce3b222979b6d5a69a1ee4dff9894224b3f`; exact-head Actions 43342519053 and [merged-main Actions 43342715656](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43342715656) succeeded. Development fast-forward synchronized safely.
- All 47 CI objects are now checked for constraint, index and same-schema foreign-key metadata parity as well as column shape and row parity; deliberate check/index drift rolls back cleanly. Not production recovery readiness.

## November 12, 2026 — CI PostgreSQL constraint/index parity (unverified candidate)

- Compare schema-independent foreign-key, check/unique/primary-key and index catalog attributes for all 46 reviewed tables plus migration journal in the disposable second-schema restore rehearsal. Foreign keys must preserve same-schema target scope.
- Regress unreviewed source CHECK constraints and indexes; both must fail transactionally, leave no target schema and allow clean retry. Receipts remain aggregate-only. No production migration, durable backup, paid service or social publishing.
- Verified starting point: PR #65 merged at `7ea77bed`; merged-main Actions 43340767900 succeeded. Candidate requires exact-head and post-merge CI before being called verified.

## November 12, 2026 — Disposable PostgreSQL restore column-shape drift detection (candidate)

- Check ordered column names, physical types, nullability and identity/generated metadata for all 46 reviewed PostgreSQL preview tables and the migration journal before any synthetic data COPY. Detect source schema changes that row parity alone might not reveal, and roll back the temporary schema without touching source data.
- Add real ephemeral PG negative regression for unreviewed column injection and a clean retry; no hosted Neon, durable encrypted backup, real customer data or publishing.

## November 12, 2026 — Restored PostgreSQL tenant-session authorization (verified PR #64)

- PR #64 merged as `3f89c948a5e453b2516a9faa40c35eae294a3397`; [exact-head PR CI 43339979250](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43339979250) and [merged-main CI 43340205353](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43340205353) passed; development synchronized non-force.
- Run actual authenticated SELECTs inside the restored disposable PG schema: active own-business sessions can read held drafts; wrong-business, revoked, expired and tampered sessions cannot. Only counts, never tokens or private drafts, appear in receipt. Failure rolls back; production networking and posting remain unapproved.

## November 12, 2026 — Restored PostgreSQL session isolation drill (candidate)

- Add a bounded, synthetic CI-only restore probe that runs the real token-hash-bound draft SELECT within the restored temporary schema after 46-table parity validation. It must allow active same-business sessions and deny foreign-business, revoked, expired or tampered sessions.
- The probe returns only the count of checks, never a bearer or private draft; a falsely expected grant fails and rolls back the entire restore. Continue keeping customer backup, hosted Neon/Render and provider publishing disabled.

## November 12, 2026 — Restore rollback/parity fault testing (verified PR #63)

- PR #63 merged as `fe1fe32ab49ca38add64ec7a25b1915cb4d6a7b5`; [exact-head PR CI 43339310351](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43339310351) and [merged-main CI 43339557139](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43339557139) both passed; development synchronized non-force.
- A partial COPY and deliberately altered restored draft both fail the CI-only recovery exercise, leave no partial second schema, preserve original synthetic records, and allow clean retry. Not a production recovery guarantee.

## November 12, 2026 — CI restore transaction rollback and parity fault injection (candidate)

- Add constrained synthetic fault modes for a mid-copy interruption and a changed restored draft. Both must fail the disposable PostgreSQL exercise, roll back temporary schema creation, retain original business data and permit a later clean rehearsal.
- Strictly local/CI-only; not a production backup, encrypted archive, or migration. No customer content, new service, paid AI or publishing.

## November 12, 2026 — Full PostgreSQL preview copy/restore rehearsal (verified PR #62)

- PR #62 merged as `7beccbbd8c448de277744aedd5d798e8662ed9e3`; [exact-head CI 43338521752](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43338521752) and [merged-main CI 43338797005](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43338797005) both passed. Development safely synchronized non-force.
- Verified in-memory CSV round-trip parity for all 46 reviewed PostgreSQL preview tables and migration journal in a disposable second schema. No durable encrypted backup, customer recovery or production authorization.

## November 12, 2026 — Disposable PostgreSQL logical copy/restore rehearsal (candidate)

- Add a CI-only, loopback-restricted second-schema rehearsal that copies all 46 reviewed PostgreSQL preview tables plus the eight-stage migration journal through bounded in-memory CSV, checks exact two-way row parity and drops the temporary schema transactionally.
- Exercise synthetic cross-business drafts, revoked session digest, password test bytes and pending attachment metadata. Neither a durable/encrypted backup nor a production restore is created; private beta remains blocked until independent backup/restore and gateway work.
- Require exact PR-head and merged-main CI before treating this as verified. No new hosting, paid APIs, EdgePilot infrastructure reuse or provider publishing.

## November 12, 2026 — Media preflight container integrity (verified PR #61)

- PR #61 merged as `82b1a0bd27cd5bf8c34ca373b890774b12dd43c7`; exact-head [PR CI 43337875235](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43337875235) passed and [merged-main CI 43338078991](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43338078991) passed. The development branch was safely fast-forwarded without force.
- Strengthened preliminary hash-matched PNG/WebP/MP4/JPEG/PDF structure checks; repaired synthetic fixture images. These are **not** malware scanning, usage-rights verification, customer media storage or approval to publish.

## November 12, 2026 — Offline media container boundary hardening (candidate PR)

- Tighten hash-matched, local-only file preflight to reject truncated/CRC-invalid PNG chunks, corrupt WebP RIFF boundaries, malformed MP4 top-level boxes and incomplete PDF/JPEG wrappers. This does **not** decode content, scan for malware, determine rights, store uploads, approve drafts or publish anything.
- Add deterministic one-pixel PNG fixture and malformed-container regressions; review via exact-head CI and full merged-main CI.
- Remain offline Alpha and at $0 additional cost; do not connect storage, Neon/Render, paid AI or social providers.

## November 12, 2026 — Read-only PostgreSQL editorial readiness with media status checks (verified PR #59)

- Introduce a session-hash-bound, tenant/private single-draft SELECT returning bounded held-draft state and only synthetic **verified attachment IDs + item names**, excluding media bytes, hashes and private storage keys.
- Compute missing, unverified, unexpected and held-material blockers in Python from the one-statement snapshot. Even fully complete material always retains TruthGuard review, owner approval not implemented, and social publishing disabled blockers.
- Add strict JSON/row-shape fail-closed validation and synthetic SQLite-free contract tests, plus real temporary PostgreSQL tests for pending/rejected media, foreign business/viewer access, revoked sessions, changed media status and malformed extraneous items.
- PR #59 passed exact-head CI and merged at `e0fa3c1fc051bb8ccda2357cd9b1193b4bf22183`; [full merged-main Actions 43334593446](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43334593446) passed and development safely synchronized. PRs #56–#59 now form one verified media/privacy checkpoint. No paid API, provider, uploader, scheduler or hosted app.

## November 12, 2026 — Metadata-only attachment integrity checks before future migration (verified PR #58)

- Add local-only SQLite aggregate checks for `content_attachments` references that point to missing drafts or drafts in a different tenant. Detect attachment metadata incompatible with stage-8 PostgreSQL checks (ID/item shape, MIME type, SHA-256 format, nonempty storage key, allowed status and nonnegative timestamps).
- Keep reporting counts and fixed check names only; never export media paths, hashes, IDs, tenant names or customer copy. `require_clean_offline_fixture` refuses unsafe records, but passing it does **not** enable a production migration.
- Add regression fixtures for a valid attachment, orphaned and wrong-business references, and malformed local data. No external access, downloads, scanner, approvals, scheduling or social provider calls.
- Last verified baseline: PR #57 merged `7a97c6c`, [full merged-main Actions 43333173764](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43333173764) success. Current candidate pending PR/main CI. $0 new costs; no hosted database, paid AI or publishing.

## November 12, 2026 — Session-verified attachment reference binding for held drafts (verified PR #57)

- Add a single revision-CAS PostgreSQL UPDATE that links an existing synthetic **verified** attachment to precisely its own tenant, held draft, required item and authenticated owner/manager/creator session. Pending/rejected, mismatched, stale, held or foreign-business media cannot be attached.
- Match existing offline Content Requests behavior by incrementing draft revision and marking the request `ready_for_review` only when required item keys are complete, with no unexpected provided keys. This status remains an editorial state, not owner approval or social publishing authority.
- Extend the disposable CI-only psycopg session adapter, pure SQL argument/receipt checks, and actual PostgreSQL tests for two required items, concurrent editors, live role/revocation changes and no scheduled jobs. No uploads or trust scanner are implemented.
- Verified baseline: PR #56 merged at `1cfcca10`; [full merged-main Actions 43332328800](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43332328800) succeeded. Current candidate requires new PR and merged-main verification. $0 new costs, no hosted services, paid AI, or provider writing.

## November 12, 2026 — Eighth PostgreSQL constraint stage: private attachment metadata (verified PR #56)

- Harden the existing stage-3 `content_attachments` table with additive PostgreSQL media-type/ID/hash/timestamp/item constraints, private state index and a composite (tenant,request) foreign key. The existing status check remains unchanged. No table is created twice: **46 reviewed tables in seven creation groups**, plus an **eighth constraint-only migration stage**.
- Add session-bound read-only attachment metadata lookup for active business members. Never expose SHA-256, storage path, file bytes, URLs or credential material. A row marked `verified` reflects only an existing synthetic test value; no trust scanner or publication permission is created.
- Extend the disposable CI-only psycopg adapter, local SQLite parity, unchanged 46-table metadata inventory and real PostgreSQL schema/privacy tests. No customer data is copied. PR and merged-main CI still pending.
- Last verified checkpoint: PR #55 merged `508f5c2b`, [main Actions 43329651094](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43329651094) passed; development safely synchronized. **$0 new costs**; no Render/Neon provision, EdgePilot reuse, paid AI or live publishing.

## November 12, 2026 — Session-scoped versioned scheduling preferences in ephemeral PostgreSQL (verified PR #55)

- Add pure parameterized PostgreSQL read plus first-create/revision-CAS updates for existing per-tenant `scheduling_settings` schema. Each statement derives identity from the hashed live session and current membership/role/verified identity, not a caller-asserted user.
- Only owner/marketing-manager/content-creator roles can edit. Any active business member may read. Validate IANA timezones, unique bounded weekday HH:MM slots, distinct preferred hours, and manual-mode time requirements before writing.
- Extend the CI-only psycopg facade with session-scoped read/save methods and add SQLite SQL-parity and actual disposable PostgreSQL tests for cross-tenant/viewer denial, conflict between two editors, role drift, revocation, saved-data validation and zero executable schedule jobs.
- Last fully verified baseline: PR #54 at `165a5398` and [merged-main Actions 43328713423](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43328713423) success. New candidate still needs PR/main CI. $0 additional costs; no hosting, paid OpenAI, social publishing or EdgePilot resource sharing.

## November 12, 2026 — Owner-reviewed feedback removal and metadata-only history (verified PR #54)

- Add token-hash-bound, same-statement verified role/membership/tenant checks to versioned feedback DELETE. Its successful receipt returns only a non-approval, non-publishing removal status.
- Add a separate live-authorized, metadata-only `removed` event in **the same disposable PostgreSQL transaction**, failing and rolling back the DELETE if the audit insert fails. Add a bounded 50-event owner/marketing-manager history view, retaining audit records after the note itself has been removed without exposing historical note bodies.
- Add SQLite SQL parity and ephemeral PostgreSQL tests for denial of cross-business/viewer/revoked-session actions, wrong versions, concurrent deletion, event rollback and history order/limits. Existing draft review, priority and publication states remain untouched.
- Last fully verified checkpoint: PR #53 merged as `25a99947`, [merged-main Actions 43326407161](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43326407161) succeeded, branches safely synchronized. This candidate still requires PR and main CI. **$0 new costs**, no paid API, public hosting, Neon provisioning or social publication.

## November 12, 2026 — PostgreSQL private feedback and atomic audit trail (verified PR #53)

- Add session-bound business-specific feedback list, new-note creation and compare-and-swap note revision SQL with current identity, membership, role and expiry/revocation checked against the same PostgreSQL statement. Owners and marketing managers can write; other current members can only read.
- Integrate feedback note creation/update with a matching event-history insertion inside a single disposable-CI PostgreSQL transaction; failed event recording rolls back the note. Compare-and-swap version tokens and draft revision checks reject stale concurrent review edits.
- Add SQLite SQL-parity and ephemeral PostgreSQL tests for audit atomicity, cross-business isolation, viewer denial, token revocation, stale note visibility and racing writers. No note can approve or schedule a post.
- Verified baseline: PR #52 merged `ada3ee5b`, [merged-main Actions 43325036530](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43325036530) passed; development safely synchronized. This candidate still needs its own PR and main CI. **$0** new costs, no Render/Neon creation, EdgePilot reuse or paid OpenAI/provider activity.

## November 12, 2026 — Authenticated held-draft creation and conflict-safe revision on disposable PostgreSQL (verified PR #52)

- Prepare session-token-hash-bound INSERT for new held drafts and single-column UPDATE for draft copy/guidance. Both recheck active, verified same-tenant editor permissions in the SQL statement; request ID and version token are server-generated. Status remains `needs_content` at creation and all mutations remain non-publishing.
- Extend the strictly CI-only psycopg adapter with transaction-scoped create and revise methods. Match existing offline ContentRequests semantics without granting approval, schedule or provider calls.
- Add SQLite parity regressions plus real disposable PostgreSQL tests for cross-business isolation, viewer denial, current role/identity/revocation, stale editor conflicts, concurrent clients and unchanged media/review states.
- Last fully verified baseline PR #51 merged at `386efe5f`; [post-merge main CI 43317840660](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43317840660) passed and the development branch safely synchronized. This candidate requires new PR/main CI. $0 additional costs; no hosted Render/Neon, EdgePilot reuse, paid AI or publishing.

## November 12, 2026 — Owner-private team roster PostgreSQL read (verified PR #51)

- Add signed-in, PostgreSQL session-hash-bound owner-only member roster SELECT with live session/identity/membership authorization and strict business scoping. Match existing offline roster fields for active and inactive members, current owner identity, revision, role and optional verified email.
- Redact target email when target identity is disabled/unverified; refuse missing self-owner, malformed rows or teams larger than the current 200-member preview cap rather than silently truncating.
- Test via synthetic SQLite and actual disposable PostgreSQL, including cross-business, viewer, stale-role, expiry and revocation denial; no mutation API or external provider operation.
- Previous PR #50 passed exact-head and [merged-main Actions 43316746266](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43316746266) on `dd0b3210`. PR #51 has now passed both PR checks and merged-main Actions 43317840660 at 386efe5f. New costs remain $0; no hosted Neon/Render, paid AI or publishing.


## November 12, 2026 — Tenant-private held-draft PostgreSQL inbox pagination (verified PR #50)

- Introduce SQL-only signed-in held-draft inbox SELECT with per-statement current identity/member/session checks, strict business scope, optional validated status and bounded stable (created_at, request_id) keyset pagination.
- Extend the disposable CI-only psycopg session facade to execute inbox reads without opening external connections, scheduling, approving, publishing or changing content.
- Add SQLite parity tests and real ephemeral PostgreSQL tests for multiple pages with equal timestamps, session hash secrecy, viewer role drift, token revocation, disabled identity and cross-tenant denial.
- Verified starting baseline: PR #49 merged `e8b696cb` and full merged-main Actions 43312549398 passed; development safely synchronized. This candidate remains unverified until its exact PR/head and post-merge main CI pass. $0 incremental spend; no Render/Neon activation or EdgePilot service sharing.

## November 12, 2026 — Disposable PostgreSQL authenticated read/CAS execution facade (candidate)

- Add a strictly CI-loopback PostgreSQL psycopg facade to execute existing token-hash-bound held draft, non-executable calendar, owner invitation and draft-priority CAS SQL against synthetic data. It opens no connections and refuses unknown host, database, user or schema.
- Add actual temporary PostgreSQL end-to-end tests for expired/revoked sessions, cross-tenant reads, stale priority writes, unchanged draft copy/revision, separate-client revocation and owner-private invitations; fail closed when PostgreSQL context is not the known CI fixture.
- Last verified baseline: PR #48 merged at 7baf3be0, full main Actions 43271490619 green. This candidate is not a production adapter, public gateway, customer data migration, Neon integration, live publishing or an authorized expense.

## November 12, 2026 — Live-session-bound owner invitation reads (candidate)

- Add SQL-only PostgreSQL pending-invitation metadata read, accepting a server-presented session bearer, not a caller-supplied member ID. Recheck current business membership and owner role, verification, session expiration and revocation in one statement.
- Add SQLite source and real disposable PostgreSQL privacy tests for cross-business denial, viewer exclusion, expired/revoked invitation status, stale roles and disabled identities; no bearer tokens are selected or exposed.
- Move README's product experience to the top before extensive historical engineering checkpoints for easier onboarding while preserving details. Previous PR #47 at 5176238e passed merged-main Actions 43270187751. No hosted provider, delivery, publishing, paid OpenAI or incremental charges.

## November 12, 2026 — Full seven-stage PostgreSQL preview coverage inventory (candidate)

- Extend metadata-only local schema inventory beyond its original nine-table subset, explicitly counting all 46 reviewed table DDL previews in seven groups and showing remaining unreviewed table names/counts without exposing data.
- Preserve original nine-table fields for compatibility; add per-table reviewed flag and separately report optional preview tables not initialized in the current local database.
- Add regression tests for stage counts, private data exclusion and non-production flags. PR #46 successfully merged to main at bc037ded and passed merged-main Actions 43268647305. This candidate needs exact-SHA PR/main CI. No customer migration, hosted resources or additional expense.

## November 12, 2026 — Token-bound PostgreSQL draft priority edit (candidate)

- Add a pure PostgreSQL SQL builder for a priority-only draft CAS update. Derive the actor from the presented session token hash, rechecking same-tenant role, active/verified identity, expiry, revocation and the expected priority token in the update statement.
- Add offline SQLite parity and real ephemeral PostgreSQL integration/concurrent writer tests. No draft copy, approval state, schedule or publishing action is changed.
- Previous baseline: PR #45 merged at 1bfedc0e, merged-main Actions 43262031729 successful. Candidate PR/main CI still required. No Render/Neon creation or additional costs.

## November 12, 2026 — Session-hash-bound draft/calendar PostgreSQL reads (candidate)

- Add prepared read-only PostgreSQL SQL contracts deriving identity from a stored **hashed bearer session**, not from a caller-supplied subject ID. Each query checks active verified identity, current same-business membership, matching live role, expiry and revocation in one statement.
- Add offline local-fixture and actual temporary PostgreSQL security tests against cross-business, expired, revoked, disabled-identity and stale-role requests, without revealing bearer tokens in SQL parameter sets.
- Update README verified baseline to PR #44 merged at `3f41a028` and Actions `43260833020` passed; maintain full development continuity/roadmap. No new paid or free service, provider login, real social posting or hosting. Exact PR/main CI pending.

## November 12, 2026 — Editorial and sensitive-security PostgreSQL stage seven (candidate)

- Review six more source schema tables (46 PostgreSQL CI previews total): editorial identity/competitor attestations, private editorial inbox with candidate fingerprint, owner approval intents with content digest, TruthGuard business facts, creator account risk status and hashed credential recovery actions.
- Retain offline status constraints and TruthGuard tenant/revocation index; prepared current-member private fact queries exclude expired/revoked values and cross-business access.
- Test local source parity/no secret export plus real temporary PostgreSQL status checks. No real email delivery, user credentials, provider approval, live publishing or extra costs. Exact PR/main CI pending.

## November 12, 2026 — Nonpublishing tenant post/review/scheduling PostgreSQL stage six (candidate)

- Add four Postgres DDL previews for tenant posts, review decisions, events and manual scheduling preferences (40 reviewed tables total).
- Source SQLite parity and actual disposable PostgreSQL tests verify same-business post/decision foreign keys, separate business post identities, active owner access, private scheduling settings, and disallow `published` as a legacy local status.
- Add prepared owner-scoped read contracts without any execution or external provider integration. CI and reviewed PR required. No new charges, hosted database or live social posting.

## November 12, 2026 — Business-scoped research/analytics schema stage five (candidate)

- Add seven explicit PostgreSQL DDL previews (36 reviewed tables total): business profiles, topics, research sources, blocked competitors, imported-analytics checkpoints, audience observations and transitional tenant resource ownership.
- Add local SQLite schema-parity/no-data-export tests and PostgreSQL fixture tests for tenant isolation, active ownership, review-only research reads and cross-table foreign keys.
- Add stage 5 to disposable public GitHub runner migration; no Neon or Render provisioning, live provider insights, paid services, publishing or extra hosting costs. PR and merged-main CI required.

## November 12, 2026 — $0 incremental-cost development policy (pending CI)

- Owner directs **$0 additional spend for BAM** until the app functions well enough to justify hosting or an essential development task is blocked with no practical free option. Either condition requires a fresh explicit approval; no cost or service activation is automatic.
- Preserve planned separate $7/month Render Starter plus Neon Free as the *deferred architecture* rather than an approved monthly charge. Do not share EdgePilot's live Render service, secrets, accounts or data.
- Use free standard public GitHub runners, temporary PostgreSQL CI and offline tools. Minimize duplicate workflows, build time, artifacts, overages and storage. Free Render or Neon is an option only for separately approved testing.
- Add a strict source-controlled `BAM_HOSTING_PLAN.json` zero-cost policy, CI validation/tamper regressions and refreshed README/product/infrastructure/readiness/continuity documentation. This guard is not a provider billing cap.
- Starting verified baseline is PR #40 merged at `babbba517`, [main CI 43246016783](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43246016783) **success**. Current planning-only change must pass exact PR/main CI before acceptance.

## November 12, 2026 — AI budget, drafts and cost ledger PostgreSQL schema stage (candidate)

- Extend disposable PostgreSQL CI migration to stage 4, with eight more AI business fact, copy/prompt, media reference, usage receipt, generation idempotency, tenant/operator quota and paused operator-control tables (29 reviewed total).
- Add migration of user AI usage `reserved_micro_usd` and `unpriced_requests` columns, explicit unique trusted-usage receipt reference per tenant/user, and **default paused** staging operator AI control.
- Add source SQLite schema parity and real PostgreSQL checks for receipt duplicate denial, separate-business cost records and never-unpause control. No paid provider activation, billing or live database created. PR/main CI pending.

## November 12, 2026 — Seven additional provider/AI/auth tables (candidate)

- Expand the reviewed PostgreSQL preview to 21 tables by adding AI preferences, AI private memories/usage, read-only provider connection metadata, Google challenges, OAuth attempts and private attachment metadata.
- Add strict local SQLite column parity, parameterized current-member/tenant-scoped provider metadata reads (never exposing vault references), personal AI usage reads, and disposable real PostgreSQL security tests.
- Add migration stage 3 to the *CI-only* checksum journal, with all live AI, real provider connections, social publishing, subscriptions and hosting disabled.
- README/roadmap/continuity updated. PR and merged-main CI required.

## November 12, 2026 — Transactional PostgreSQL CI schema versioning (candidate)

- Introduce a fixed, two-version disposable CI migration loader using one PostgreSQL transaction, advisory lock, script checksum journal and strict schema-table parity check.
- Add actual PostgreSQL regressions for idempotent re-run, tampered checksums, unknown future versions, missing table detection and permanent no-Neon/no-data-migration/no-publishing flags.
- Safe test-only guard requires explicit CI opt-in, Psycopg connection, local 127.0.0.1 PostgreSQL test database, schema, user and autocommit. No production schema tool, no hosted migration or paid service. CI pending.

## November 12, 2026 — Team and invitation PostgreSQL schema parity (candidate)

- Add five additional explicit PostgreSQL DDL preview tables: business invitations, invitation activity, team role-change audit, private review feedback and review history. Convert SQLite autoincrement to PostgreSQL identity columns while retaining explicit legacy unique/index behavior.
- Add metadata-only SQLite parity checks, pure owner-scoped pending-invite read SQL, and new live **ephemeral container** PostgreSQL tests for unique invitation IDs, invalid review-event actions, owner/read-role separation, invitation consumption and role revocation.
- Expansion grows the reviewed schema preview from 9 to **14 tables**; still no Neon account, production migration or paid provisioning. Exact PR/main CI needed.

## November 12, 2026 — Public runner real PostgreSQL CI (candidate)

- After owner-confirmed public repository PR #35, fast-forwarded development safely from the verified public main commit `5c283175`.
- Updated the existing Python/JS CI workflow to run once for pull requests and merged main rather than duplicated development pushes; retained read-only repo permissions, added checkout credential persistence disable and no artifact uploads.
- Added an **ephemeral local PostgreSQL 16 service container** on standard GitHub-hosted runners with an in-memory/temporary test-only user/password. Tests execute nine-table DDL, prepared tenant-scoped read queries, guarded draft-priority CAS, concurrent stale-token writes, viewer and revocation denials on real PostgreSQL.
- These tests require no Neon project, Render service, real credentials or billable database. This candidate needs PR and merged-main CI; public repo history scan remains a separate security gate, not a guarantee.

## November 12, 2026 — Verified offline Neon migration preparation checkpoint

- PRs [#30](https://github.com/BelenosCreations/belenos-marketing-automation/pull/30), [#31](https://github.com/BelenosCreations/belenos-marketing-automation/pull/31), [#32](https://github.com/BelenosCreations/belenos-marketing-automation/pull/32), [#33](https://github.com/BelenosCreations/belenos-marketing-automation/pull/33) were merged after exact-head CI; merged `main` at each checkpoint passed Actions `43215433909`, `43216601082`, `43217385358`, `43218122644` respectively.
- Foundations now include nine-table DDL preview, all-table SQLite portability backlog, prepared tenant/member checked read statements, private aggregate integrity preflight, and versioned held-draft priority update SQL preview; each remains offline-only.
- README, roadmap, alpha readiness and development continuity synchronized with the verified state. Documentation-only reconciliation itself still needs its exact-commit CI.
- **Remaining blockers:** port all tables/queries, prove actual PostgreSQL transactions and session/role isolation, production security, encrypted backups, media storage and reliable scheduling. Hosting is only designed ($7 Render Starter + Neon Free); nothing has been bought, created, deployed or published.

## November 12, 2026 — PostgreSQL-style tenant-safe draft priority CAS (offline)

- Add non-executing `UPDATE ... RETURNING` builder to compare-and-swap private held-draft priority token while checking current verified identity, active membership, editorial role and tenant in the same SQL statement.
- Add test-only SQLite query-shape/behavior checks for successful edits, unchanged draft content revision, stale-editor conflicts, cross-tenant isolation, viewer denial and identity/member revocation.
- Receipt mapping permanently disallows publishing or scheduling. No actual PostgreSQL execution, database credentials, deployment, paid service or live social calls. CI pending.

## November 12, 2026 — Read-only data integrity preflight for future Neon migration

- Add aggregate-only SQLite integrity and foreign key checks plus orphan-identity/membership/session, stale session role, inactive identity, malformed session digest, casefold email collision and orphan calendar proposal diagnostics.
- Add synthetic-fixture tests for no-record/no-secret output, corrupted relational links, stale permissions, duplicate email and strict clean-fixture gating.
- This is a local **preflight only**: no data migration, Neon access or production readiness claim. Full CI pending; no deployment or billable operation authorized.

## November 12, 2026 — Prepared tenant-scoped Postgres read contracts (offline)

- Define pure parameterized draft/calendar SELECT templates that recheck active/verified identity and tenant membership in the same read statement; no SQL identifier interpolation from clients.
- Offline SQLite compatibility tests exercise cross-business denial, current member deactivation, identity deactivation/unverified status, invalid identifiers, and the permanent no-publishing state.
- No PostgreSQL driver, Neon query execution, real social API, migration or host activation. The tests do not establish real Postgres transaction semantics; CI pending.

## November 12, 2026 — Complete local SQLite table inventory (offline)

- Add `neon_schema_inventory.py` for deterministic, privacy-safe metadata inventory across all initialized alpha tables, with explicit nine-table blueprint mapping and unmapped backlog.
- Report SQLite DDL review flags without exposing CREATE TABLE SQL, account/draft/session contents, provider tokens or customer rows; add regression tests for schema drift and malformed identifiers.
- Keep real Neon PostgreSQL, data migration, billable hosting and publication disabled. Full CI required.

## November 12, 2026 — Neon partial schema portability groundwork (offline)

- Add nine-table review-only PostgreSQL DDL blueprint for BAM identity, sessions, membership, account throttle, held drafts, posting preferences and nonpublishing calendar proposals.
- Add privacy-safe SQLite schema inventory with strict local-column compatibility checks, deterministic digest, row counts and permanent incomplete-migration blockers. It exports no data and cannot connect to Neon or execute DDL.
- Add regression tests for privacy, schema drift, core table matching and no-deployment guard; add migration roadmap and README/continuity/readiness updates.
- No database migration or external activation. Exact-source CI and reviewed PR required.

## November 12, 2026 — Hosting design selected ($7 Render Starter + Neon Free), unprovisioned

- Record the owner-selected BAM infrastructure design: **one independent Render Starter web service ($7/month base)** and **one Neon Free PostgreSQL project ($0 within quotas)**, with strict separation from existing EdgePilot service and data.
- Add `BAM_HOSTING_PLAN.json`, a read-only fail-closed planning contract and CI tests for all-disabled activation, uncreated resource identifiers, no service blueprint and $0 other approved charges. These tests protect plan history, not Render operational billing.
- Update README, product plan, beta architecture, alpha readiness, development milestones and continuity; identify SQLite/PostgreSQL migration, ephemeral local file storage, verified backups, external auth and reliable job execution as real remaining gates.
- **Planning only:** no Render or Neon creation, no charge authorization, no actual hard spending cap, no live users, paid AI or social posting. Requires reviewed PR and exact-head CI.

## November 12, 2026 — Atomic shared-account login throttling groundwork

- Replace the offline throttle's read-then-write count updates with a single SQLite UPSERT, preventing lost increments when independent app/database clients log failures simultaneously.
- Validate trusted timestamps and prevent an older failure event from rewinding the current lockout window.
- Add independent two-connection concurrent tests, window-reset and malformed-clock regressions.
- **Source code CI pending** on the exact new branch head; this checkpoint is not production-ready authentication. Rate-limit check and credential verification remain separate operations, and per-IP/device/global protections are still missing. No hosting, paid AI or social publishing is activated.

## November 12, 2026 — Offline gateway network isolation and beta architecture plan

- Add a fail-closed test-gateway guard for public remote IPs, non-loopback Host/ServerName and forwarded-proxy metadata. Enforce it before sign-in, team invitations or UI assets.
- Add negative regression tests and a host-neutral proposed production architecture covering multi-business persistence, media, worker, vault, backup, hosting and cost-approval boundaries.
- **Verification pending:** exact source CI plus reviewed PR and merged-main CI required. No production hosting, new payment, live OAuth, paid AI or publishing enabled.


## November 12, 2026 — Verified multi-milestone checkpoint

Five reviewed PRs passed full Python and JavaScript CI at the PR source and after merge to `main`, with fast-forward-only synchronization of development:

| PR | Verified main commit | Successful main Actions |
| --- | --- | --- |
| #21 — AI request/response safeguards | `c8a48f359789f0ee63b601c9ba51a3beb74267df` | 43171790537 |
| #22 — Password invitation redemption | `e24a2b3e46ec924c19a0e8b5e4ea6affd3419dff` | 43172997850 |
| #23 — Google invitation redemption | `39b3c04f31b8c2fc91b0348bf36d658cf4bcbff7` | 43174049448 |
| #24 — Disabled-by-default offline WSGI invitation acceptance | `b81430bcd3496d2504a2651534e6fa726eb781a7` | 43174989252 |
| #25 — Private calendar readiness diagnostics | `427566c610bbbcc03b78b4a436746f9832410638` | 43175777320 |

Older changelog entries that say "CI pending" describe their **at-writing-time** status, superseded by this verified checkpoint. No live publishing, production hosting, email delivery, provider OAuth or paid API was activated.

## November 12, 2026 — Non-executable calendar readiness digest

- Added tenant-scoped, authenticated `GET /api/v1/calendar-readiness` to display stale-draft and outdated posting-time blockers for held calendar proposals, with bounded counts and no draft edit tokens.
- The digest always reports missing final publication review and unavailable social publishing, even when the draft and configured time are current. It never schedules a job, approves a post or calls any social API.
- Added offline service, WSGI, negative schema/permission and full gateway tests for role/business isolation, stale revision, changed manual schedules, unsafe responses and disallowed writes.
- **Full exact-source GitHub Actions pending.** No production hosting, publishing, OAuth, paid OpenAI or scheduler worker was activated.


## November 12, 2026 — Offline HTTPS-style invitation acceptance integration

- Added `BAMInvitationAcceptWSGI`, an offline-only, disabled-by-default acceptance adapter with separate password and Google paths, HTTPS and exact-field parsing, strict output redaction and no session grant.
- Added an independent gateway `enable_invitation_acceptance` switch requiring trusted invitation-delivery composition. Neither issuing invitations nor acceptance becomes active just because the other has been enabled.
- Integrated the existing current identity proof, throttle, one-use invite claim, business role checks and audit through a single offline application route.
- Added WSGI end-to-end regressions for disabled paths, invalid/duplicate fields, client tenant spoofing, wrong credentials, Google nonce and subject verification, single-use and no session leaks.
- **CI pending at new exact branch HEAD**; no public endpoint was deployed, no external invitation email was sent, and no paid OpenAI, OAuth browser flow or social publishing was enabled.


## November 12, 2026 — Internal Google-only invitation redemption

- Added an internal verified Google identity lookup that can validate a known, registered Google-only BAM subject without implicitly granting membership or a login session. Ordinary Google login still requires current business membership.
- Extended the disabled-by-default invitation admission gate to consume a one-use Google challenge, verify the ID token including nonce, match the registered identity, apply hashed-email throttling and redeem the invitation transactionally.
- Added tests for registration mapping persistence and duplicate-subject atomic rollback, Google-subject impersonation, mismatched emails, missing membership, nonce reuse and successful post-acceptance Google login.
- **Exact-source GitHub Actions pending.** No live Google OAuth browser flow, public invite acceptance, hosted registration, paid AI or social publication was activated.


## November 12, 2026 — Internal invitation redemption admission gate

- Added explicit, disabled-by-default AuthLoginAPI admission for invitation password redemption. Turning it on requires both a trusted invitation service and a shared LoginThrottle.
- Failed email/password or token verification increments the existing hashed-email throttle. A successful one-time redemption clears failures but **never issues a login session**.
- Added tests for off-by-default behavior, missing throttle, lockout timing, accepted membership, token non-disclosure, cross-business isolation and subsequent ordinary login.
- **Verification:** new code awaiting exact-head full CI. There is no HTTP invitation-acceptance endpoint; production enrollment, email transport, IP/global abuse limits, hosted access and posting remain disabled.


## November 12, 2026 — Trusted offline invitation redemption for new team members

- Extracted the existing password-KDF verification into an internal verified-identity check that does not require existing business membership, issue a login session or change permissions. Normal member logins still require current business membership.
- Added a trusted invitation password-redemption entry point for previously email-verified BAM identities. It verifies password first, then reuses the existing atomic, one-time tenant-scoped acceptance checks and audit.
- Added negative tests for wrong password, wrong identity, unverified identity, malformed token, token replay and business isolation. Successful redemption permits the new member's normal session afterward.
- **CI status:** exact-head Actions must pass before merging. No public acceptance endpoint, unauthenticated signup, invitation email provider or production rate-limiting service is present.
- **Activation:** offline-only, no paid AI, hosted beta or live publishing.


## November 12, 2026 — Strict offline OpenAI draft and request boundaries

- Refuse missing/malformed tenant or user scopes before invoking any sponsored Responses transport. Reject duplicate JSON keys at the provider-envelope or generated-copy level, blank/non-string posts, and oversized copy or image prompts before any draft can be staged.
- Allowlist outbound HTTPS request fields. Reject background jobs, conversation linkage, unreviewed request parameters, parallel tool calls, non-user messages, non-text parts and non-strict schema descriptors.
- Add regression tests for rejected scopes, duplicate or malformed model output, post-size limits, unapproved API parameters, and safe provider-usage observation even when generated text is rejected.
- **Code candidate:** 93caf1ab18a6adf299ccffc42da1012699b91e3c. CI is not yet claimed; GitHub Actions must verify the exact full checkpoint before a merge.
- **No activation:** The transport remains disabled by default. No paid API requests, real credentials, hosting, billed usage, media creation or publication was enabled.


## November 11, 2026 — Provider response identity wired into estimated AI cost deduplication

- The offline OpenAI Responses executor now requires a strictly validated `resp_...` identifier **when a trusted usage observer is configured**. It derives a deterministic, private 128-bit SHA-256-based `usage_ref` and forwards it with tenant/user/model/token counters to `AICostLedger.record_trusted`.
- The earlier optional ledger deduplication is now exercised end to end with synthetic Responses API envelopes: repeated identical provider IDs produce one estimated-cost event, conflicting counts for a reused ID fail closed, different businesses remain isolated, and malformed/missing IDs never reach the observer.
- The raw Responses identifier is not persisted in the usage ledger or surfaced to clients; the underlying optional SQLite receipt reference is hashed again in storage. Legacy ledger rows remain intact.
- **Code verified:** `f95f0820080ac77600257e0ea072a0d0c0af3fa3` passed [GitHub Actions 43145005354](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43145005354); this documentation-only checkpoint requires its own exact-SHA run.
- **Limitations:** These are fake-transport local tests, not verified live provider usage, billing reconciliation, or a money-back guarantee. An actual provider request may have incurred costs even if its returned ID or usage is unusable. Live OpenAI, customer billing, publishing and hosting stay disabled.

## November 11, 2026 — Mandatory pre-dispatch OpenAI pause checks

- The *injected* `OpenAITransport` now requires a **trusted server-side dispatch guard whenever explicitly enabled**; an absent, noncallable, false, nonboolean or exception-raising guard fails closed before resolving an API key or using the network opener.
- The offline sponsorship quota exposes `authorize_new_dispatch_trusted`, which reads the persisted operator pause and denies dispatch when paused or when the control row is missing. The transport checks the guard before secret lookup **and again immediately before HTTPS opener execution**, so a pause during slow vault resolution also stops dispatch.
- Added disabled/default, strict-guard, pause/resume, callback-error sanitization, before-key and during-key-resolution tests. No actual OpenAI network call was made.
- **Verified code:** `d14bbd3f1857d73777a6ec8b958ac0b474a2a1d6` passed [GitHub Actions 43144166053](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43144166053), including full offline Python/JS/compilation suites. This documentation-only follow-up requires its own CI.
- **Boundary:** These checks are point-in-time. They do **not** atomically fence the network send or cancel already-running requests. Production needs trusted worker fencing, vault handling, approved pricing and explicit operator consent before enabled transports may be deployed.

## November 11, 2026 — Deduplicated trusted AI usage ledger

- Added an **optional, trusted server-owned 32-hex usage reference** to `AICostLedger.record_trusted`. When supplied, its SHA-256 digest is stored in a new nullable column and uniquely scoped to the business and subject. Replaying the same reference with identical model, token counts and operator-estimated cost returns the original event rather than double-counting it; reusing the reference with different data fails closed.
- The migration preserves all pre-existing cost events with NULL reference hashes and **does not invent** historical provider IDs. Legacy reference-free calls remain supported but **cannot promise deduplication**.
- Regression coverage verifies independent tenants, mismatch rejection, existing-data migration and two simultaneous SQLite clients competing to record the same usage reference.
- **Verified code:** `9765961fc8a63433863c91c9700f80891a9544fb` passed [GitHub Actions 43143316508](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43143316508) (Python compile, JavaScript syntax/tests and complete offline Python suite). This documentation-only follow-up requires exact-SHA CI.
- **Limitations:** Usage references are not yet wired to a real OpenAI response identifier, actual invoice, paid model call, or quota/receipt reconciliation workflow. Cost values remain operator-priced estimates. No real provider traffic or new fees.

## November 11, 2026 — BAM-sponsored AI operator pause and safe budget holds

- Added persistent **operator-only** offline pause controls to `SponsoredAIQuota`: `set_operator_paused_trusted` and `operator_pause_status_trusted`. Pause blocks **new** sponsored reservations for all businesses, users and UTC months after revalidation under the SQLite write lock; no counters or estimated charges are added for refused requests.
- Added an independent two-SQLite-client race test in which an operator pause wins after a writer's initial policy check but before reservation commit. A missing control row fails closed, and invalid non-boolean or untrusted-time settings are rejected.
- Whitelisted explicit, non-sensitive quota refusal reasons across both HTTPS generation and targeted-revision routes and strict JavaScript clients, including `operator_paused`, historical-unpriced blockers and per-user/business/operator projected-cost ceilings. Unknown hold reasons cannot leak to the browser.
- Added offline HTTPS end-to-end coverage proving the pause prevents draft-generation and targeted-revision executors, consumes no additional quota while paused and does **not automatically retry** a failed request key when subsequently resumed.
- **Verified code:** `cb23ebbd212986e72e6351b34c834fc3fd43a12c` passed [GitHub Actions 43142566744](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43142566744), covering Python compilation, the complete offline Python suite, JavaScript syntax checks and UI tests. This documentation-only follow-up requires its own exact-SHA verification.
- **Limitations:** This is a **trusted operator configuration primitive**, not an authenticated customer-accessible pause UI, not a provider-level emergency stop, and **cannot cancel already-reserved or in-flight provider requests**. It does not enable or authorize paid OpenAI traffic. Real pricing, input token enforcement, provider usage reconciliation, billing safeguards and a production dispatch circuit breaker remain separate gates.

## November 11, 2026 — Final preflight recheck and trusted sponsored AI projection input

- Sponsored quota admission now revalidates the current role and funding mode under `BEGIN IMMEDIATE` before writing any user/business/operator count or projected-cost counters. A membership demotion or own-key switch after the initial preflight can no longer pass the transaction boundary.
- Added separate SQLite-client regression tests that pause precisely **after** the initial role/funding preflight, change the membership on a second connection, and verify that no reservation is committed. Added corresponding same-connection mode-switch coverage.
- Added `conservative_request_cost_micro_usd` with **explicit operator-provided** `AITokenPricing`, bounded input/output token assumptions and upward micro-USD rounding; no current model pricing is hard-coded and token ceilings are not yet enforced against a real provider request.
- Added `reserve_current_utc_month` for future trusted composition, deriving the billing month from the server clock instead of trusting a user-supplied month. Existing legacy `reserve(month=...)` is a fixture/internal path that **must not** be exposed as a production client argument.
- **Verification:** [Actions 43139361336](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43139361336) **passed** exact source `5d80f58c7896fa73965ff6e8c3081af07410188f`, with full offline regression suite, Python compile and JavaScript UI tests. This documentation follow-up still requires exact-head CI.
- No hosted billing, paid OpenAI request, actual usage receipt, guaranteed final cost, password/token exposure, external hosting or publication activation.

## November 11, 2026 — Atomic projected micro-USD AI reservation ceilings

- Expanded the existing disabled-by-default sponsored OpenAI quota primitive with optional **per-user, per-business and overall-operator estimated micro-USD ceilings**, alongside existing monthly request-count limits.
- All three estimated-cost reservations are transacted with count increments in **one SQLite write transaction**. Concurrent independent SQLite connections cannot exceed a capped aggregate; denial at any layer rolls back all counters.
- Added safe backward-compatible schema migration from historical count-only usage to `unpriced_requests`; introducing an estimated-dollar cap mid-month fails closed if prior reservations have no projected cost rather than inventing historical costs.
- Bounded per-request estimated amounts to avoid SQLite integer overflow, validated trusted plan input, and added a server-side `actual_billing_verified=False` marker to reservation results.
- Added new unit, migration, mid-month and independent-client race tests. **GitHub Actions 43138168968** [passed](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43138168968) on source `5dee209bb2df1c9b6bb3afe1470cdd2f69798aea`; this documentation follow-up requires its own exact-SHA test.
- These are **projected accounting ceilings only**. No OpenAI calls, invoices, verified current model pricing, actual USD enforcement, secret vault, subscription billing, hosting, or social publishing was activated.

## November 11, 2026 — Read-only social permission lifecycle and atomic analytics import

- Tightened the offline provider metadata registry to accept only the internal `read_insights` capability, not arbitrary strings that happen to lack “publish” or “write.” This is not an authorization claim about real Meta scopes.
- Enforced monotonic trusted metadata timestamps, terminal offline revocation, and fail-closed status for legacy write-capable scope records and future-dated metadata. Stale workers cannot resurrect a revoked connection.
- Rechecked the current analytics-connection authorization inside SQLite's write transaction immediately before persisting observations and sync checkpoints; reject mismatched transactional stores.
- Added in-memory and **two independent SQLite-client** regression tests, including revocation during simulated provider fetch and confirmation that no analytics data or checkpoint is committed afterward.
- **Verification:** [GitHub Actions 43136954406](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43136954406) **passed** at code commit `2bf15248172ed56d78b98ad8d84250b45c6749a3`, with Python compilation, JS syntax/UI tests and offline Python suite. This documentation follow-up must pass its own exact-SHA CI before merging.
- **Safety:** No real OAuth grant, vault-managed credential, Meta request, hosted connection, AI spend, live scheduler or publishing action was activated. Reconnecting a revoked account requires an explicitly verified future integration.

## 2026-11-11 — Offline sponsored AI cost-containment layers

- Extended server-issued `SponsorshipPlan` with optional per-business and BAM-operator **monthly request-count ceilings**, in addition to existing individual request and output-token allowances; all caps are validated with strict integer bounds.
- Sponsored quota reservations now use a single SQLite transaction across individual, tenant aggregate and operator aggregate counters. A depleted cap rolls back every partial increment, and denials explicitly identify `limit_reached`, `tenant_limit_reached` or `operator_limit_reached` without granting a draft or paid call.
- Aggregate usage is metered on **all accepted sponsored reservations**, including while a cap is not configured, so adding a limit mid-month cannot overlook earlier activity. Viewer-only members cannot reserve generation quota.
- Added in-memory regression tests for business isolation, unchanged per-user counters on denial, mid-month cap configuration, invalid plan values, and independent-file-backed SQLite races between two users in one business and competing businesses under one operator ceiling.
- **Verification:** [Actions 43127670375](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43127670375) passed the initial optional-ceilings and independent-client tests at `7d18e5ed789d353416236beb934de08ce334957f`. Mid-month metering improvement through `ef3e3509f273e621d0ad26663d02dd36cba650fa` and this documentation require exact-head CI.
- No USD spend cap, billing integration, provider key, live AI call or social publishing has been activated. Operator still needs to approve an actual spend budget before any production traffic.

## 2026-11-11 — Atomic held-draft calendar proposal updates

- Replaced read-then-upsert updates with a database-guarded conditional insert/compare-and-swap update. The current `content_requests` revision and held status are checked within the same SQLite write as the saved proposal, preventing a stale service snapshot or race from assigning a changed draft.
- New draft assignments cannot overwrite another editor's existing proposal; updates require its exact current random `proposal_token`. The existing unique business/UTC-slot constraint still prevents double-booking.
- Added a targeted stale-service-cache regression and independent-file-backed SQLite-client race tests for simultaneous first assignment, conflicting editors updating a common version, and separate drafts competing for one slot.
- **Verification:** Core SQL CAS implementation `d8fc324d3ece50ed835ef48030ebad403cb78fa5` passed [Actions 43126412492](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43126412492). Expanded race tests through `5a0a4b6984f9815bc1af00531ab88fbf2aa8491e` and these documentation updates still require exact-SHA CI.
- **Nothing executes**: proposals have no scheduling worker, platform connection or posting authority; `posts_scheduled=0`, `publishing_enabled=false`. No hosting or paid provider activation.

## 2026-11-11 — Opt-in owner invitation issuing controls (offline only)

- Added server-side `invite_current` to derive the invitation business exclusively from a current owner session. The optional HTTPS `POST /api/v1/team/invitations/create` accepts **only** normalized recipient email and a non-owner role, never a client business ID or bearer token; response is strictly validated and excludes the secret.
- Added a **second explicit server switch** `enable_invitation_issuing`, disabled by default even when trusted pending-invitation previews are available. The gateway rejects enabling it without a trusted callback; no real outbound email transport is configured.
- Added a separate, default-off owner-only browser mode with a review → confirm invitation flow, safe error/reload behavior, no owner-grant choice, and logout/race regressions. No controls are exposed to viewers or employees.
- Added WSGI, real offline gateway, browser client and DOM tests for disabled paths, spoofed tenant fields, duplicate active recipients, token redaction, role checks, and confirmation. A JavaScript regex fix correctly accepts valid emails containing the letter "s".
- **Verification status:** Full code/UI checkpoint `7f9b34ea3449af64d217e9540a6d66c044e4ad85` is undergoing GitHub Actions review; do not declare the new issuance UI validated until the exact-SHA tests pass. The prior `main` checkpoint `07d4a66b472fa01a68afb4b47067ed2d64d43503` passed [Actions 43124178398](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43124178398).
- No hosted beta, live email, social publishing, paid AI or deployment activation.

## 2026-11-11 — Transactional invitation redemption and concurrent-client safety

- Changed `BusinessInvitations.accept_trusted` to claim the one-use token and revalidate the verified recipient, inviting owner's current role, and pre-existing membership **under one SQLite writer transaction**. If any check or audit write fails, the entire attempted redemption rolls back without granting access.
- Added offline file-backed, separate-connection race tests for simultaneous duplicate active invitation creation, two clients redeeming one link, and cancellation racing redemption. Added a forced audit-write failure regression to confirm neither member creation nor token consumption persists.
- **Verification:** The first transactional redemption code `350272042a3b84f49d7dc82cc109aff1317ef086` passed [GitHub Actions 43123314052](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43123314052). The expanded concurrency/rollback tests through `bd08b9b19878b34bfbca62e1b7dda52e054f0045` and this documentation still require exact-SHA CI.
- Private offline Alpha only; trusted delivery callbacks remain optional and disabled without configuration, and no production invitation acceptance route, email, hosting, paid API or publishing is enabled.

## 2026-11-11 — Tenant-private invitation activity trail (offline Alpha)

- Implemented append-only server metadata for delivered, failed-delivery, cancelled and accepted business invitations. The audit is written transactionally with state changes, is scoped to the current business and never stores/returns a bearer invitation token or recipient email in the audit record.
- Added owner-only `GET /api/v1/team/invitations/activity`, disabled unless the separately trusted delivery callback is configured. The HTTPS adapter validates exact, bounded, descending activity records and refuses additional sensitive fields.
- Added strict browser response validation, an optional deeper Team Settings activity view and lifecycle guards against showing old-business activity after logout.
- Added Python service, HTTP boundary, end-to-end gateway, and JavaScript client/UI regressions. Historical invitation actions before installation are **not backfilled**.
- **Test status:** [GitHub Actions 43122286878](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43122286878) **passed** on full code/documentation checkpoint `538bb79d874821e406b2521384d3feaad0297c33`: Python compilation, JavaScript syntax and UI tests, plus all offline Python regressions. This follow-up status-only commit must be independently verified.
- No external email delivery, hosted rollout, paid AI, OAuth or social posting was activated.

## 2026-11-11 — Owner-private invitation safety and CI syntax gate

- The optional, owner-only **pending invitation list and two-step cancellation** UI is backed by an authenticated tenant-scoped HTTPS adapter. It only becomes available with a separately configured trusted invitation-delivery callback; BAM does **not** send invitations from this UI, expose invite bearer tokens, or activate social posting.
- Added a single-statement atomic duplicate check so one business cannot accidentally issue multiple simultaneous unexpired active invitations to the same email. Existing memberships, including deactivated members, must be managed through the authorized team-administration path rather than a fresh invitation. Other businesses remain independent.
- Cover duplicate, cancelled, expired, failed-delivery, existing-member and cross-business scenarios in Python; browser tests cover owner cancellation and the safe state after logout during an outstanding cancellation.
- GitHub Actions now runs `node --check` on **every** `ui/*.js` file before JavaScript regressions, not only scripts executed by an individual test.
- **Verification:** [Actions 43120107192](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43120107192) passed for repaired invitation UI checkpoint `2f030b7e`; [Actions 43120560150](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43120560150) passed for duplicate/membership safeguards and syntax gate at `92d17255`. The additional logout-race regression and this documentation commit still require their own exact-SHA CI result.
- All capabilities remain **offline Alpha**, without real email delivery, hosted multi-user release, external publishing, or paid service activation.

## 2026-11-11 — Ephemeral offline SQLite snapshot and restore drill

- Added temporary-file, consistent SQLite backup and restore regression tests for business-isolated drafts, pre-snapshot revisions, hashed sessions, scoped revocations, and team audit persistence.
- Verified SQLite integrity after snapshot and restoration; tests clean up temporary databases.
- [GitHub Actions run 43108646726](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43108646726) passed on `1444094af143eaa40c43402d995319f7921f2407` with **928 Python tests**, browser regressions and compilation.
- No operational, encrypted, scheduled or off-site backup was configured. No social publishing, hosting or paid service activation.

## 2026-11-11 — Separate-client persistence and collaboration verification

- Added file-backed SQLite end-to-end tests with two independently initialized BAM gateways, separate owner/editor sessions and distinct business memberships.
- Verified shared draft persistence, stale editor HTTP 409 conflict, successful refreshed edits, business isolation, role-change session revocation and state after simulated app restart.
- [GitHub Actions 43107825592](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43107825592) passed `17c5b470ba4891714953e993c499e1892a712d66`: **926 Python tests**, JS UI regressions and Python compilation.
- Remains offline Alpha. No hosted user collaboration, production database, publishing or paid service activation.

## 2026-11-11 — Private owner-only access-change history

- Added a tenant-scoped read-only recent member-change audit, owner-only `GET /api/v1/team/activity`, strict response validation and a deeper Settings history view.
- Displays only recorded access events; no invented activity, credentials, invitation tokens or cross-business history.
- Verified `d6a79329d2ed2ed5f7d37114aad557be60d464ab` with [GitHub Actions 43107012958](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43107012958): **924 Python tests**, browser regression scripts and compilation passed.
- No live hosting, invitation email, publishing or paid AI changes.

## 2026-11-11 — Owner-controlled existing-member access (offline Alpha)

- Added strict owner-only current-business team roster with verified member emails, non-owner role changes, deactivation and two-stage Settings confirmation.
- Added migration-safe revision tokens, stale-write HTTP 409 responses, same-business session revocation and local audit records.
- Added Python/JavaScript/WSGI end-to-end tests; **922 Python tests and browser suite passed** at [run 43105750364](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43105750364) on commit `38e799dba7df86378c0f89ecb216626df07cfff2`.
- Invitation delivery, production enrollment, reactivation, live hosting, paid AI and publishing remain disabled.

## 2026-11-11 — Alpha code synchronized into main (verified)

- Reconciled the former 993-commit development lead and three independent `main` branding commits through [PR #2](https://github.com/BelenosCreations/belenos-marketing-automation/pull/2) and merge commit `f774564d7348e47f34ae0ee9da6279cf14a93677`. Maintained full source history; no force push, reset, or deletion of development work.
- Kept original BAM branding source, Android resource templates, regression tests, and the updated product-accurate README.
- Created three independent GitHub checkpoint branches at previously known good code and frozen development snapshots.
- Exact integration candidate `748c3a1a`: GitHub Actions [push run 43100505574](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100505574) and [PR run 43100515217](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100515217) **passed**. Final merged `main` commit: [run 43100795231](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100795231) **passed**.
- Fast-forwarded the active development branch to the merged `main` commit after verifying its head was unchanged.
- Added a routine milestone PR / maximum-divergence checkpoint discipline. This is **source-control stabilization, not a deployed beta, a publishing launch or paid-service activation**.

## Main-branch reconciliation candidate — 2026-11-11

The protected-by-convention development snapshot `f66522a40e2696ca49adb183435d218bf3353beb` is the source for this integration candidate. The `main` baseline `fcb28f7a3f8be8d2edf70bd3dfcabbee90e36214` has three separate historical branding commits. Every introduced branding/Android template/test/tool blob is **byte-for-byte identical** in the development snapshot; the only content differences are the historical `README.md` and `CHANGELOG.md`. This merge candidate retains the latest product-accurate README, preserves the distinct `main` history via a two-parent merge commit, and explicitly records the original branding milestone below.

**Safety:** No real social publishing, OAuth, paid model calls, production hosting or APK build was activated. This branch is a merge candidate only. Merge into `main` only after Actions tests complete successfully at the exact candidate SHA and review confirms no conflicting concurrent changes.

### Preserved `main` branding milestone (November 10, 2026)

The original `main` branch approved BAM's branding: light/dark SVG wordmarks, app icon sources, Android adaptive/monochrome icon sources, brand color palette, Android resource templates and an optional deterministic image generator with four offline branding regression tests. Main branding milestone commit `0a5d1be57d420b3a810651754af1f3fc4be31510` previously passed its offline workflow. No Android APK or connected publishing service resulted from these assets. See `docs/BRANDING_MILESTONE.md` and `branding/README.md`.

## 2026-11-11 — Product direction clarified: direct social APIs and collaboration (documentation)

### Changed
- Rewrote the README as a current BAM product overview rather than an accumulating phase log; separated implemented local-alpha capabilities from future hosted/paid/publishing features.
- Made **direct official social-platform APIs** the core publishing and analytics architecture, starting with eligible Facebook business Pages. **Metricool is not required** for onboarding, publishing, scheduling or Smart analytics; older Metricool-first documentation is superseded.
- Documented same-business team collaboration, business-specific permissions, shared tenant infrastructure, AI/media cost controls, and the operator-funded sponsored OpenAI model without promising unlimited free services.
- Added `PRODUCT_PLAN.md` with implementation gates, owner-approval checkpoints, verification criteria and a cost-conscious multi-tenant hosting strategy.

### Test and deployment status
- Documentation changes only; **no runtime tests were executed for this documentation update**.
- Previously committed security changes may remain unverified; consult `DEVELOPMENT_CONTINUITY.md` and the exact-SHA GitHub Actions run before merging or deploying.
- **No live social connection, publication, scheduling, hosting or paid AI was activated.**

## 2026-11-11 — Stale-role safety for team invitations and trusted facts

- Require current tenant-specific sessions for issuing/revoking offline team invitations, changing business scheduling settings, and owner-only TruthGuard fact approval/revocation/lookup.
- Prevent a role promotion from granting privileges to a session created before the promotion; regression tests require a fresh trusted session.
- No outbound invites, paid AI, executable scheduling, live approvals or publishing.
- **Verification pending:** GitHub Actions queued after commit `4fc1a648`.

## 2026-11-11 — Alpha / private beta acceptance gate

- Added `ALPHA_BETA_READINESS.md` with an explicit offline-alpha capability matrix, evidence required to call each task done, pending private-beta integration conditions, and publish/paid-service prohibition.
- Documented that GitHub Actions for recent security and stale-edit changes are queued; no release or success implied.

## Alpha safety — current sessions and edit conflicts (2026-11-11)

### Changed
- Editorial source intake and both offline approval facades revalidate the business-bound session and unchanged membership role before accessing protected actions.
- Held-draft hold APIs and Content Studio now submit the current draft revision; an outdated hold cannot overwrite a newer revision and maps to HTTP 409 Conflict.
- Concurrent verified-media references are written only if the previously read draft revision is still current.

- Content Studio refreshes the current authenticated draft list on rejected mutations, including stale editor conflicts, without pretending the rejected write succeeded. Added a browser regression for a simulated HTTP 409.

### Tests
- Additional tenant, role-change, stale hold, concurrent media and authenticated WSGI regression coverage committed.
- **Pending CI:** workflow runs for code checkpoint `800e3277` and its predecessors are queued; no new successful test claim is made.

## 2026-11-11 — Editorial recheck session isolation hardening

- Recheck now validates current membership and exact active business rather than only a still-live token and membership in the target business.
- Regression tests cover cross-business membership with a token scoped to another business and stale roles after membership downgrade.
- No approvals, scheduling, publishing, network calls or paid AI activation.
- **CI pending:** run 43095601077, code commit `e957aeadd75f07457bf0d987c71d9c5f94275973`.

## Zero-cost, authenticated advance marketing topic planning — 2026-11-11

### Added
- A user/business-scoped `AIBatchPreview` validates 1–14 distinct topics and existing owner-confirmed business facts before assembling a future OpenAI-compatible plan. It returns only the safe topic list, platform, fact revision and explanatory counts; no prompts, personal memories or business fact values are disclosed in the response.
- `POST /api/v1/ai/batch-preview` runs solely through the opted-in *offline* HTTPS gateway with live session/role checks, strict JSON and nonpublishing output validation. It never calls OpenAI, reserves quota, stages drafts, grants approval, estimates a bill or creates a publishing schedule.
- The authenticated AI Drafts view now includes **Plan future marketing topics**, with one topic per line, a platform and an optional image-prompt flag. The result is clearly labeled as an informational advance plan, not generated posts. Stale account, role or business requests are ignored and a viewer cannot access planning controls.
- The existing trusted internal AI memory-write path now shares the secret-resistant validation used by the new checked Settings editor, closing a bypass for likely credential strings.
- Added Python business isolation, HTTP boundary and zero-spend tests, plus JavaScript client/DOM tests for malformed topics, forged billing or publishing claims, duplicate lists, failed server calls and stale sessions.

### Verification
- **Passed:** [GitHub Actions run 43058003130](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43058003130), commit `97f8f2de`: **845 Python tests and 55 JavaScript UI test scripts**, plus Python compilation.

### Known limitations
- This is **not** generated content, provider Batch API processing, a discounted price, a future job, a confirmed cost, quota entitlement or a publishing queue. An operator must separately authorize and deploy paid AI generation with spend, security, and provider controls. The preview does not guarantee that future model output will be factual or accepted.
- The signed-in preview is still a restricted local/offline development application, not a hosted production service.

## Isolated per-user AI writing preference editor — 2026-11-11

### Added
- `AIPolicyStore.replace_memory_checked` allows a creator to update their own business-scoped AI writing guidance with an optimistic compare-and-update. Changes on another device cannot be silently overwritten. The values are bounded and key/value validation rejects likely credentials.
- A strict, authenticated `PUT /api/v1/ai-memory` route edits only memory associated with the current BAM identity and business. Client-supplied tenant, role, API key, publication, billing or entitlement claims fail closed. Conflict returns 409 and requires a fresh read.
- AI Settings now offers an editor for individually labeled preferences (tone, audience, style, post length) with add, edit and remove-by-empty-row controls. The editor saves explicitly, refreshes the trusted account state and disappears for viewers or after business switching/logout.
- Browser and Python tests cover privacy, current-user isolation, conflicts, secret-like fields, forged scope, unauthorized roles, stale controls, strict responses, and zero automatic AI requests.

### Verified
- [GitHub Actions run 43056197885](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43056197885), commit `c1f31d52`: **836 Python tests, 53 JavaScript UI test scripts**, and compilation passed.

### Known limitations
- Writing preferences are editable in the local preview, not independently verified marketing facts. They cannot override owner-confirmed business facts or approval controls. This is not credential vaulting, production user-profile hosting, paid AI generation, or publication.

## Opt-in, confirmation-gated targeted AI regeneration controls — 2026-11-11

### Added
- `ui/ai_targeted_revision_client.js` strictly validates a one-component revision request and private, unpublished response. A cryptographic randomness dependency generates a 128-bit idempotency key with no insecure fallback.
- AI Drafts has separate, explicitly prepared/confirmed actions for regenerating post copy or an existing image prompt. It displays a warning that a provider request may consume BAM-sponsored allowance or charge a personal API key. Two user actions are required; there is no silent regeneration or automatic retry.
- The authenticated workspace ignores late responses after a business or session switch, reloads the current draft only after a verified success and does not claim a held provider attempt completed.
- The feature is **opt-in and disabled by default**. The ordinary signed-in application does not configure it, the offline gateway does not mount a live paid revision route, and no OpenAI call is enabled.
- Added browser-client, two-step DOM and full workspace regression tests for strict data contracts, confirmation, request idempotency header, secure entropy, permissions, stale buttons and no publishing.

### Verification
- **Passed:** [GitHub Actions run 43054882416](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43054882416), commit `6ebe7d86`: **830 Python tests, 50 JavaScript UI scripts**, plus Python compilation.

### Known limitations
- Actual OpenAI provider execution, encrypted key vault, distributed usage accounting, operator activation and public hosting remain separate release gates. A renderable UI test does not mean AI regeneration is available to users.
- A targeted edit is still unpublished and unapproved; changing the prompt requires fresh media verification.

## Disabled-by-default targeted AI revision HTTPS boundary — 2026-11-11

### Added
- `POST /api/v1/ai/targeted-revision` is a separately disabled, strict HTTPS route for changing one existing AI draft component at a time using a trusted executor. Request fields are limited to draft ID, expected revision, selected component, instruction and topic; a unique idempotency key is mandatory.
- The server—not the client—selects business/user scope, UTC billing month, sponsorship plan and output token limits. Successful responses reveal only scoped draft ID, revision and held status, never provider payload or secrets.
- The disabled AI composition factory includes the revision path with the existing facts, quota, idempotency and draft services and credential-disabled transport.
- Full in-memory WSGI-to-draft integration tests verify copy-only/prompt-only changes, stale requests, cross-business isolation, plan-claim rejection, media hold invalidation and ambiguous model output. A strict transport-result metadata mismatch was discovered and fixed.

### Verification
- **Passed:** [GitHub Actions run 43053763455](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43053763455), commit `1187b467`: **830 Python tests, 47 JavaScript scripts**, and Python compilation.

### Known limitations
- This is zero-network offline integration, not live OpenAI generation. Production requires encrypted key vaulting, billing reconciliation, atomic distributed quota/spend controls, rate limiting, real hosting and safety reviews. AI regeneration, provider connection and live publication remain disabled in the user-facing app.

## Offline targeted AI draft revisions and strict response validation — 2026-11-11

### Added
- `ai_targeted_revision_workflow.py` implements an offline, trusted-executor pathway for regenerating **one component at a time**: `post_text` or an existing `image_prompt`, preserving the other component.
- The workflow validates live tenant/user ownership, draft revision, current owner-confirmed business facts, operator-configured sponsored quota, input bounds, and idempotency **before** an injected provider call. Only server-trusted usage limits can be passed to the executor.
- The generated result is checked again for fact-revision and draft-revision changes before staging. A targeted image-prompt revision clears any prior verified-media match and retains the media-needed hold.
- Provider JSON parsing now rejects duplicate fields at any nesting depth rather than silently accepting ambiguous structured output. Duplicate/conflicting model responses cannot be published or used to overwrite a draft.
- Added isolated, zero-network tests for idempotency, quota, stale/cross-tenant/cross-user edits, changed facts, forged publishing claims, ambiguous provider JSON and image-prompt media invalidation.

### Verification
- **Passed:** [GitHub Actions run 43052414192](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43052414192), commit `2f540470`: **824 Python tests, 47 JavaScript UI regression scripts**, plus Python compilation.

### Known limitations
- This is **not** a live OpenAI service: the executor is a trusted injected test dependency and no production API, paid provider traffic, encrypted personal-key vault, public subscription, or model-based social publishing is connected.
- Quota and idempotency remain local SQLite foundations. Production needs shared atomic storage, provider reconciliation, entitlements, observability and independent approval before real paid requests.
- No frontend AI regeneration control is enabled. Manual component editing and the optional ChatGPT image handoff remain separate working paths.

## Explicit, bounded CSV import of held marketing drafts — 2026-11-11

### Added
- A browser-only CSV parser validates a strict `channel,draft_text,suggestion,required_items` header, quoted/escaped fields, bounded size (128 KiB), 1–20 rows, supported platforms and required item names. Missing required items default to `image`; repetitive copy within the file is rejected before any network requests.
- Content Studio's Advanced section can preview every unpublished row and then requires a separate **Confirm import** action. It checks for exact duplicates against currently loaded drafts and creates each request through the existing authenticated held-draft endpoint. The importer never makes AI calls, attaches images, approves a claim, schedules, or publishes.
- A server failure stops the import immediately. BAM reports only confirmed successes and explicitly warns that partial imports cannot be automatically rolled back or blindly retried. Business rotation or sign-out cancels further actions and discards the import preview.
- Added CSV parser regression tests plus an end-to-end browser import test for success, duplicates, partial failure and session lifecycle.

### Verification
- **Passed:** [GitHub Actions run 43038527274](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43038527274), commit `0b98f105`: **813 Python tests, 47 JavaScript UI scripts**, and Python compilation.

### Known limitations
- The importer does not guarantee cross-device duplicate prevention under concurrent writes. It does not create verified media or automated posts, and it is available only in the currently offline authenticated preview.

## Private read-only marketing claim-risk preview — 2026-11-11

### Added
- A disabled-by-default authenticated `GET /api/v1/content/risk-preview?request_id=...` endpoint scans only an accessible, existing draft in the current business for bounded, deterministic risk signals: price/discount, guarantee, urgency/availability, business hours, and testimonial language.
- Content Studio offers an explicit **Check marketing claim risks** button. Results display flagged excerpts using safe text rendering, remain tied to the reviewed draft revision and are invalidated when the copy changes or the user switches businesses.
- The server never accepts tenant/approval override parameters, and the client rejects forged verification or publishing claims. Zero flags is explicitly **not** proof that a statement is accurate or eligible to publish.
- Added Python WSGI/business isolation tests and browser response-validation/lifecycle tests for bounded risk signals and safe failure.

### Verification
- **Passed:** [GitHub Actions run 43037661505](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43037661505), commit `4b92f5c3`: **813 Python tests, 45 JavaScript UI test scripts**, and Python compilation.

### Known limitations
- Heuristic scanning is not comprehensive fact extraction or truth verification. Manual owner review, trusted business evidence, media inspection, final approval and live publishing remain separately gated and inactive.

## Explicit sign-out from all BAM devices — 2026-11-11

### Added
- The authenticated Settings page offers a two-step, explicit **Sign out on all devices** action, plus a warning and Cancel control.
- On confirmation the shell clears private DOM and the in-memory BAM session before calling the existing authenticated `POST /api/v1/auth/logout-everywhere`. A successful response reports the revoked-session count; an unconfirmed network response warns that other device sessions may remain valid.
- Signed-in HTML shell regression tests cover cancellation, confirmation, session clearing, correct bearer session and the dedicated route. Existing tests separately exercise server-side session revocation and stale concurrent sign-ins.

### Verification
- **Passed:** [GitHub Actions run 43036158603](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43036158603) on `c13fb91e`: 809 Python tests, 44 JavaScript UI scripts and compilation.

### Known limitations
- This is a local-only security workflow, not a production device-management screen. Neither social-media account connections nor external social tokens are revoked; no live publishing or cloud hosting is activated.

## Owner-only aggregate team access — 2026-11-11

### Added
- An authenticated, read-only `GET /api/v1/team-overview` route returns aggregate active membership counts by role and inactive count, only after the server checks current-business `MANAGE_TEAM` permission. Client-supplied role, tenant overrides and mutations are rejected.
- Settings now includes a Team Access panel. Owners see anonymized role totals; managers, creators, employees and viewers receive an access-restricted explanation without a private team request.
- No member names, subject IDs, email addresses, invitation secrets or publication authority are returned. Team invitations are explicitly shown as unavailable rather than implied to work.
- Pending reads are cleared after business rotation, logout or a role downgrade. A failed optional team-count read does not revoke an otherwise valid BAM session.
- Added Python transport/role checks and JavaScript schema/workspace/HTML shell regressions.

### Verification
- **Passed:** [GitHub Actions run 43035508617](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43035508617), commit `65f7663c`: **809 Python tests, 44 JavaScript UI test scripts**, plus Python compilation.

### Known limitations
- Read-only aggregate counts cannot invite, enroll, grant roles or revoke permissions. Google browser login, live provider OAuth, production hosting and social publishing remain disabled.

## Version-guarded independent Content Studio editing — 2026-11-11

### Added
- Existing held Content Requests now carry a server-managed monotonic revision. Old local SQLite databases gain the revision column through a non-destructive migration and retain their existing drafts.
- A disabled-by-default, HTTPS-only `PUT /api/v1/content/drafts` adapter lets an authenticated business editor change exactly one field: `draft_text` or `suggestion`. The client supplies an expected revision; stale changes receive an explicit conflict rather than overwriting newer work.
- The authenticated Content Studio now offers separate manual text editors and Save buttons for copy and guidance. It reloads the verified business-scoped record after each save, refuses forged role/tenant/publishing claims and drops late results after a business/session switch.
- Hold and verified-content changes also increment the same draft revision. A prior owner review intent becomes stale when the draft copy is edited, even if previously verified attachments remain associated with the request.
- Added WSGI request/privacy, legacy-database migration, service-role, review invalidation, browser client, and signed-in interface regression tests.

### Verification
- **Passed:** [GitHub Actions run 43034533473](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43034533473), commit `19ac808b`: **807 Python tests and 42 JavaScript UI test scripts**, plus Python compilation.

### Known limitations
- These are explicit manual text revisions, not an OpenAI generation call or a social platform update. They never verify media, approve a post, set a schedule, or publish.
- BAM is still a loopback-only offline development service; production authentication, cloud-safe concurrency, real provider connections, human review and live publication remain separate release gates.

## Actionable scheduling and human-review dashboard details — 2026-11-11

### Added
- The large Scheduled card now opens a read-only seven-day Manual-mode posting-time preview derived from the current signed-in business, with a link to owner-only Posting Time settings. It explicitly distinguishes suggested clock slots from real scheduled posts and never claims audience-optimal Smart times without verified data.
- The Approvals card now lists only that business's requests currently marked `ready_for_review`, with an explicit link to Content Studio. Reviewable content remains unapproved, unpublished and unscheduled.
- Both drilldowns clear tenant-sensitive state after business switching or sign-out, invalidate stale async replies and show unavailable/error states instead of synthetic schedule data.
- Added independent browser regression coverage for manual time previews, explicit navigation, human-review labels, failed preview reads, and cancellation of stale requests.

### Verification
- **Passed:** [GitHub Actions run 43032704184](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43032704184), commit `03d1495a`: **797 Python tests, 41 JavaScript test scripts**, and Python compilation.

### Known limitations
- No real provider scheduling, audience analysis, human approval recording, social publication or external marketing account OAuth was activated. The current HTTPS preview remains offline and loopback-only.

## Authenticated read-only Connections drilldown — 2026-11-11

### Added
- A new `GET /api/v1/connections` endpoint returns only the current business's authorized read-only provider connection status and safe account metadata. The account directory independently rechecks current membership and analytics-read permissions; request parameters cannot select a different business.
- The authenticated large-card dashboard now opens a detailed Connections view, with statuses for connected, pending, reconnect required, expired, or revoked provider accounts. Connection details cannot expose OAuth tokens, vault keys, provider secrets, post publication rights or scheduling authorization.
- Restricted roles receive a read-only access message rather than requesting sensitive connection details. Pending or failed reads fail closed; logout and business switches invalidate late responses and old card controls.
- Strict browser data contracts and regression tests cover tenant isolation, stale sessions, malformed and duplicate account metadata, restricted business roles, and read-only labels.

### Verification
- **Passed:** [GitHub Actions run 43031957718](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43031957718), commit `badf0ac6`: **797 Python tests, 40 JavaScript UI test scripts**, and Python compilation.

### Known limitations
- This reports offline test-registry connections only. No social OAuth account linking, refresh-token exchange, real analytics import, provider publishing, or external credentials are enabled.
- The browser state is informational and is not an authority to schedule or publish.

## Read-only posting-time preview — 2026-11-11

### Added
- `posting_time_preview.py` generates bounded future manual posting-time previews from saved, authenticated tenant preferences without creating a queue, approval, or publishing instruction. Nonexistent or ambiguous daylight-saving wall times are omitted rather than silently shifted or guessed.
- A strictly read-only `GET /api/v1/posting-time-preview` route derives the business from the live BAM session. No tenant query override or POST action is accepted.
- The authenticated Settings panel shows possible next-seven-day local posting times, with explicit language that these are not scheduled posts. Smart mode reports missing verified audience evidence rather than inventing recommendations.
- Browser response validation rejects malformed preview claims, duplicate/unsorted slots and any implied publication. Business-switch tests verify the previous tenant's saved preferences do not appear in the new tenant's preview.

### Verification
- **Passed:** [GitHub Actions run 43023029480](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43023029480) on commit `9a2eee75`: **795 Python tests, 38 JavaScript test scripts**, Python compilation.

### Known limitations
- Posting-time previews do not create jobs, schedule content, estimate engagement, or enable publishing. Smart recommendations still require trusted platform analytics and explicit business configuration. The local-only HTTPS app remains an offline prototype.

## Verified local HTTPS image lifecycle smoke test — 2026-11-11

### Added
- Extended the real localhost TLS network smoke test to exercise the complete opted-in private media path: authenticated preflight with SHA-256, binary PNG receipt, status transition from `awaiting_file` to `pending_scan`, unchanged draft hold, explicit pending discard, private-file removal and tenant-scoped status isolation after switching businesses.
- The test also confirms that neither the receipt nor the status response confers media verification or publishing. It is a loopback-only fixture using disposable accounts and generated files.

### Verification
- **Passed:** [GitHub Actions run 43021239317](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43021239317) on commit `c5501af8`: **789 Python tests, 37 JavaScript test scripts**, Python compilation, and local TLS socket integration.

### Known limitations
- This is a network-level test using Python's TLS client, not real browser automation or a production security review. Public hosting, actual image scanning, rights/consent verification, third-party OAuth and social publishing remain disabled.

## Explicit discard and replacement of unverified images — 2026-11-11

### Added
- An authenticated, disabled-by-default `DELETE /api/v1/content/media-pending` route removes pending-only media records and private quarantine bytes for **one server-authorized business/request/checklist item**, without accepting arbitrary file paths, attachment IDs, tenant or role claims.
- Content Studio now provides a two-step, explicit “Discard pending image” action when an image is in private quarantine. After server-confirmed deletion, the signed-in panel refreshes and allows a replacement image; no verified attachment or published content is affected.
- Session/tenant checks guard the removal endpoint; stale browser controls cannot trigger an old business's removal after logout or business switching. The browser rejects unexpected response fields or any implied verification/publishing permission.
- Added Python and JavaScript tests covering cross-tenant denial, symlink-safe unlink, duplicate/unreceived metadata, explicit confirmation, replacement picker restoration and fail-closed transport.

### Verification
- **Passed:** [GitHub Actions run 43020735001](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43020735001), commit `4baf5528`: **789 Python tests and 37 JavaScript test scripts** plus Python compilation.

### Known limitations
- This is a local-only pending receipt privacy workflow. It does not delete any verified media, run a scanner, establish content rights, or activate approval/publishing. Storage concurrency and retention policies need production-grade implementation before external deployment.

## Persistent, isolated pending-media receipt status — 2026-11-11

### Added
- `BAMPendingMediaStore.statuses` derives tenant and READ_DRAFTS permission from the live BAM session and exposes only `awaiting_file` or `pending_scan` for active, missing image checklist items. It never returns attachment IDs, file paths, digests, raw bytes, media verification, approval or publishing permission.
- `BAMPendingMediaStatusWSGI` provides a default-disabled HTTPS-only, read-only `GET /api/v1/content/media-status` endpoint with strict response validation and no tenant-selection query parameter.
- Content Studio retrieves authenticated pending status after refresh and displays either a pending private review message or an image upload control, avoiding repeat submission when an image was already received. Failed status checks fail closed by disabling image transfer, without signing out the user.
- The browser stops a stale media transfer between hashing, metadata preflight and byte receipt when the business changes or the session is cleared.
- Added backend, browser client and DOM regression tests covering tenant isolation, status persistence, malformed data, forged approval and session-change cancellation.

### Verification
- **Passed:** [GitHub Actions run 43019581144](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43019581144) on commit `2618f139`: **784 Python tests, 37 JavaScript test scripts**, and Python compilation.
- The earlier image-status mock had an unreachable response branch; this was corrected before verifying the complete suite.

### Known limitations
- Pending image status reflects only a private quarantine receipt, not a media scan, consent/rights check, an approved attachment, a public gallery, or a ready-to-publish draft.
- Quarantined files still need lifecycle/retention controls and a separate trusted verification pipeline. The local preview is limited to loopback HTTPS and never enables live scheduling or publishing.

## Content Studio pending-media capability redraw regression — 2026-11-11

### Fixed
- Content Studio now redraws immediately when private pending-image receipt capability is enabled or disabled. This prevents a stale file picker from remaining visible after media receipt is disabled and restores the expected capability-gated browser behavior.
- Existing browser DOM regression test covers capability revocation; CI verification is required before this fix is considered green.

## Private, pending-only local image receipt (without verification) — 2026-11-11

### Added
- Implemented `BAMPendingMediaStore`, a local opt-in private receiving area for PNG/JPEG/WebP image bytes matching an existing tenant-scoped, server-registered pending content attachment. Files are held under server-generated IDs with private permissions outside the Git checkout, per-image limits and a bounded global pending quota.
- Added a separate, disabled-by-default `PUT /api/v1/content/media-bytes` route with HTTPS bearer authentication, strict attachment-ID/type/size validation, server-side tenant membership/edit checks, SHA-256 digest matching, signature inspection and duplicate-upload refusal.
- Content media remains in registry status `pending`, and the service responds only with `pending_scan`, `media_verified:false` and `publishing_enabled:false`. It cannot mark required content supplied, bypass ownership/consent inspection, schedule or publish.
- The local HTTPS preview now accepts an optional explicit `--pending-media-dir` directory path to enable this **local-only** receipt. With no directory, byte transfer remains unavailable. Added multi-tenant isolation, private-file, malformed-byte, failed digest, duplicate, absent config and response-forgery tests.

### Verification
- **Passed:** [GitHub Actions run 43016103634](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43016103634), commit `9ff5d4d6`: Python compilation, **779 Python tests and 35 JavaScript tests**.

### Known limitations
- This is **quarantined pending media only**: no malware scan, decoded-image safety validation, copyright/owner consent proof, attached media gallery, platform permissions, production object storage/encryption or live post approval. Files are never served publicly.
- A browser file-picker workflow is not wired yet; image byte transfer is currently exercised through WSGI tests and optional local-only API composition.
- The default preview remains without media-byte transfer unless a separate private directory is configured. No public deployment is authorized.

## Two independently isolated businesses in one local BAM account — 2026-11-11

### Added
- Extended the nonpublic `bam_local_preview.py` CLI with an explicit `add-business` operation. It requires the existing preview owner's verified password and active **owner** membership before creating an additional test tenant under that same identity. The password is prompted locally, never passed in a URL, browser form or command-line argument.
- The trusted setup refuses duplicate businesses and nonprivate SQLite files. It cannot create/verify new users, bypass existing membership, or be called from the public HTTP surface.
- Extended the actual localhost TLS test to provision two business tenants, sign in once, create content in the first business, rotate the session into the second business through the real WSGI switch endpoint, verify revocation of the original token, reject cross-business draft visibility, and sign out of the replacement session.
- Updated [Local HTTPS preview guide](LOCAL_PREVIEW.md) with a second-business command and clear local-only limitations.

### Verification
- **Passed:** [GitHub Actions run 43015125493](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43015125493), commit `9fff773a`: Python compilation, **770 Python tests and 35 JavaScript tests**.

### Known limitations
- Only the local test-owner CLI is supported; there is no public/invited-user signup or independent verified email provider flow. Real production multi-business authorization still requires a secure database, migrations, audit controls and hosted OAuth.

## Verified end-to-end local HTTPS browser-shell/API socket flow — 2026-11-11

### Added
- A loopback-only TLS integration regression opens the actual signed-in BAM page, browser JavaScript and canonical brand icon over an ephemeral HTTPS socket with a temporary test certificate.
- The same test signs in with a local password, reads the authenticated owner dashboard, creates an unpublished content request, lists drafts, rejects unknown/private source routes, signs out and verifies the old session is rejected.
- All traffic remains on `127.0.0.1`; the test performs no real social API, OpenAI call, production enrollment, upload, or external HTTPS request.

### Verification
- **Passed:** [GitHub Actions run 43014624796](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43014624796), commit `4a6a3d50`: Python compilation, **769 Python tests and 35 JavaScript tests**.

### Known limitations
- This verifies Python HTTPS transport, not an automated browser session or Android UI. Browser certificate trust, accessibility, production database/concurrency and public service security remain separate release gates.

## Explicit loopback HTTPS preview and private local test-owner setup — 2026-11-11

### Added
- Implemented `bam_local_preview.py` for optional manual local testing of the signed-in BAM shell and authenticated WSGI gateway over HTTPS. The server binds **only** `127.0.0.1`, rejects nonlocal request origins and DNS-rebinding Host headers, and derives HTTPS status solely from its local TLS termination, never from a forwarded request header.
- Requires an explicit `--i-understand-local-only` acknowledgement, an externally supplied local TLS certificate/private key and a populated preview SQLite file outside the source repository. A private-key permission check is enforced on POSIX systems.
- Added `bootstrap` for one local test owner, using an interactively entered password that is never passed on a shell command line. A fresh outside-repository database is created with mode 0600 before credentials are written. The bootstrap's email verification shortcut is **strictly local/test only** and is never attached to an HTTP route.
- Added a [Local HTTPS preview runbook](LOCAL_PREVIEW.md) with nonproduction warnings and self-signed local certificate examples.
- Added tests for host/loopback guarding, missing consent, insecure port validation, local test-owner authentication, private database permissions and refusal to overwrite an existing owner.

### Verification
- **Passed:** [GitHub Actions run 43014114797](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43014114797), commit `e74448c4`: Python compilation, **768 Python tests and 35 JavaScript scripts**.

### Known limitations
- The local preview must not be exposed through port forwarding, a tunnel, public network, reverse proxy or production deployment. It uses a development-only bootstrap, single-process WSGI server and local SQLite; enterprise/production session security, Google authentication and live account verification are not implemented.
- The runner has been validated through a Python HTTPS loopback client using a temporary self-signed certificate, **not** a real web browser or production security assessment. No live social publishing, media transfer or paid AI calls are enabled.

## Opt-in same-origin browser delivery for the authenticated BAM shell — 2026-11-11

### Added
- Built `bam_signed_in_assets_wsgi.py` to serve exactly the existing signed-in HTML, referenced browser JS/CSS and canonical BAM icon via a trusted HTTPS WSGI composition. Routes reject arbitrary file names, traversal paths, demo-only pages, request query parameters, non-GET/HEAD methods and insecure scheme claims.
- Browser asset delivery has an **independent default-off** `serve_browser_assets` switch on the existing default-off offline gateway; neither flag starts a public HTTP/HTTPS listener.
- The page receives same-origin-only connections, a restrictive script/content security policy, and a SHA-256-restricted inline stylesheet. Removed an inline style attribute that would otherwise require unsafe-inline styling permissions.
- Added a Node regression that loads the page's actual script sequence in browser-global mode without CommonJS, alongside Python tests of asset allowlisting, canonical branding paths, HTTP security headers, and the offline gateway opt-in.

### Verification
- **Passed:** [GitHub Actions run 43013333985](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43013333985), commit `5ac2bd1e`: Python compilation, **764 Python tests and 35 JavaScript UI tests**.

### Known limitations
- The WSGI module has **no listener**, TLS certificate management, external account registration, hosting or deployment authorization. It must not be mounted on a publicly exposed service until production security, session transport, abuse protection, recovery and privacy review are complete.
- Test-only HTTPS WSGI environment flags are supplied by a trusted wrapper; no external proxy-supplied protocol headers are trusted. Social publishing and paid AI calls remain disabled.

## Zero-OpenAI-request service-business spotlight support — 2026-11-10

### Added
- Extended local, literal social-media spotlight templates to non-retail service providers. Owner-confirmed `business_name` and `service` fields can produce a short, factual service marketing draft with optional generic conceptual image prompt, without OpenAI API requests.
- Added a separate disabled-by-default HTTPS `POST /api/v1/ai/local-service-draft` route. The same server-derived tenant, confirmed fact, authenticated role, content hold, zero-request cost and no-publication safeguards apply as for product drafts.
- Updated the signed-in AI Drafts editor to choose only currently available product/service template types backed by owner-confirmed facts. Service businesses do not need a fabricated product field to use the local draft option.
- Added service-template server/client, non-retail business isolation, generic image-prompt and service UI regression tests.

### Verified tests
- **Passed:** [GitHub Actions run 42962115509](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42962115509), commit `4ceed04c`: Python compilation, **760 Python tests and 35 JavaScript UI test scripts**.

### Known limitations
- Templates create only generic, literal product/service highlights; they are not full OpenAI campaign generation, image creation or real photographs of actual work.
- Confirmed owner facts still require review before any future public posting. No live media upload, schedule/publish execution, hosted web app or Android build is enabled.

## Independent manual AI draft component editing — 2026-11-10

### Added
- Introduced a disabled-by-default, HTTPS-only `PUT /api/v1/ai-drafts` endpoint for an authenticated creator to manually revise **exactly one** component of their own unpublished AI draft: either `post_text` or an existing `image_prompt`.
- Integrated post copy and image prompt editors in the signed-in AI Drafts view. Each Save uses an expected revision to prevent stale overwrites and then reloads the server-verified draft. No OpenAI call is made.
- The server derives both business and subject from the current session; clients cannot claim a tenant, role, approval, billing mode or publication state. Revisions are owner/creator-scoped and reject different-user drafts.
- Changing an image prompt invalidates its old verified-media association and reestablishes the media-needed hold. Editing post copy retains an existing valid media association but still requires content review.
- Added strict request/response contract, browser, revision-conflict, cross-tenant, no-API-cost and end-to-end UI regression tests.

### Verified tests
- **Passed:** [GitHub Actions run 42961746379](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42961746379), commit `c96d5611`: Python compilation, **757 Python tests and 34 JavaScript UI test scripts**.

### Known limitations
- Edits are manual text changes, not targeted paid AI regeneration. The latter remains in the approved roadmap and requires quota and provider readiness.
- New image prompts cannot be added to drafts that did not have one; a separate confirmed-fact draft workflow can create them. No image file transfer, review approval, scheduling or publishing is enabled.
- Offline integration only: no production OAuth, hosted service, Google browser flow or Android installable artifact.

## Role-aware authenticated business controls — 2026-11-10

### Added
- The signed-in dashboard now normalizes an active-business role supplied by the authenticated backend, rejects unrecognized role values, and fails closed to read-only presentation when a legacy response omits the role.
- Owner-only fact confirmation and Smart/Manual posting preference editors are visible only for authenticated business owners. Content Studio write controls and local no-API-cost draft creation are shown only to owners, marketing managers and content creators; employees and viewers retain read-only access.
- Business switching and logout clear capability flags and private panels. Every server-side create/edit operation independently checks the session's current business membership and role; browser UI capability flags are **not** security authorization.
- Extended business-switch smoke tests and capability validation tests to verify that a user moving from owner to viewer permissions loses business-editing controls immediately.

### Verified tests
- **Passed:** [GitHub Actions run 42961295058](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42961295058), commit `69836808`: Python compilation, **750 Python tests and 32 JavaScript UI test scripts**.

### Known limitations
- Frontend role affordances are convenience only; production access control always depends on the server. There is no role-administration UI or production Google sign-in yet.
- No social publishing, live scheduling, trusted media upload, public hosting or native Android binary is enabled.

## Zero-OpenAI-request local product drafts — 2026-11-10

### Added
- Added an explicitly invoked local product spotlight path using business-owner-confirmed `business_name` and `product` facts. The post text is assembled locally without guessing prices, hours, availability, promotions or other customer-facing claims.
- Extended `ai_local_templates.py` to optionally assemble a generic conceptual image-generation prompt for the user's **own ChatGPT session**. It must not be presented as an actual photograph or approved product representation. BAM makes **zero OpenAI API requests** for this path.
- Introduced `POST /api/v1/ai/local-product-draft`, a disabled-by-default, authenticated HTTPS adapter, and business-scoped `AccountReadAPI.create_local_product_draft` that saves the resulting post/prompt as a pending AI draft.
- Connected an explicit “Create cost-free product draft” action in the authenticated AI Drafts section. The option appears only when the current business has owner-confirmed required facts. Business switch and sign-out invalidate stale UI results.
- Added browser/transport and end-to-end tests for unsupported client claims, zero OpenAI requests, pending-media holds, cross-business isolation, safe image-prompt content and fact prerequisites.

### Verified tests
- **Passed:** [GitHub Actions run 42960676199](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42960676199), commit `7aa04a03`: Python compilation, **750 Python tests and 31 JavaScript UI test scripts**.

### Known limitations
- The template covers a literal product spotlight, not generative AI creativity or automatic factual verification. It is available only after explicit owner fact confirmation.
- The optional image brief does not create, upload or validate an actual image; ChatGPT user-account usage limits are separate from BAM API costs.
- No paid AI, social connection, scheduling, approval, publication, real image upload, production HTTPS server or Android app is enabled.

## Signed-in owner-confirmed AI business facts — 2026-11-10

### Added
- Mounted the existing disabled-by-default owner-only `PUT /api/v1/ai-business-facts` HTTPS route in the offline authenticated gateway.
- Activated the already-developed owner-confirmed fact editor in the signed-in Settings panel. The explicit Save action uses the active in-memory business session, sends only bounded fact strings and an expected revision, and re-reads the trusted business snapshot after success.
- Server-side permission verification prevents content creators from confirming business facts, rejects stale revisions and isolates each business.
- Extended WSGI and browser smoke tests for owner confirmation, denied creator access, stale revisions, and a two-fact editor submission.

### Verified tests
- **Passed:** [GitHub Actions run 42960261912](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42960261912), commit `db99e5f9`: Python compilation, **743 Python tests and 30 JavaScript UI test scripts**.

### Known limitations
- A nonowner may see the editor in this integration-stage shell; the backend is authoritative and denies unauthorized Save actions. A future trusted capability flag should hide it for nonowners.
- Fact confirmation records the owner's provenance, not independent public verification. It does not authorize publishing or AI billing.
- The gateway is still offline and disabled by default; no live hosted signup, Google browser sign-in, social posting or media transfer is enabled.

## Pending-only media metadata preflight — 2026-11-10

### Added
- Introduced `bam_upload_preflight_wsgi.py`, a separate disabled-by-default HTTPS-only attachment preflight route. It validates business-session identity, current edit access, associated content request/checklist item, allowed media type, exact SHA-256 digest and bounded file size.
- `AccountReadAPI.begin_content_upload_preflight` derives tenant identity from the session, delegates to `ContentUploadPreflight`, and registers only a private **pending** attachment metadata record. It never returns a storage key or signed upload URL and cannot mark a file verified, attach bytes, approve or publish.
- Wired the preflight to `bam_offline_gateway.py` and added transport, malformed-request, forged-role/tenant, cross-business and end-to-end tests.
- Kept the existing manual ChatGPT image handoff concept unchanged. Users cannot yet transfer their images into BAM.

### Verified tests
- **Passed:** [GitHub Actions run 42959953634](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42959953634), commit `07456b3a`: Python compilation, **742 Python tests and 30 JavaScript UI scripts**.

### Known limitations
- A preflight metadata record is not an uploaded or verified file. No object-store integration, server-side file transfer, malware scan, consent review, image validation/preview, or publishing eligibility is provided.
- Production quotas, secure storage lifecycle, cleanup and anti-abuse controls are still needed before media upload can safely be turned on.

## Owner-controlled Smart/Manual posting times — 2026-11-10

### Added
- Implemented a separate disabled-by-default `PUT /api/v1/posting-preferences` HTTPS WSGI write adapter. Session-derived tenant and current owner role are enforced server-side. Only `mode`, IANA `timezone` and validated `manual_times` are accepted.
- Connected a nested Posting Times editor to the signed-in Settings view. Owners can explicitly select Smart timing or enter validated 24-hour manual local times; the UI reloads confirmed server state after saving, clears on logout or tenant change and rejects forged tenant/publishing responses.
- Added Python boundary tests, owner-only end-to-end WSGI tests and JavaScript contract/workspace tests; the signed-in HTML shell smoke test exercises saving manual times.
- Maintained the approved overview-first dashboard and Content Studio drilldown; successful integration and browser tests are documented below.

### Verified tests
- **Passed:** [GitHub Actions run 42959720838](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42959720838), commit `9967b893`: Python compilation, **735 Python tests and 30 JavaScript UI test scripts**.
- The Content Studio navigation and browser form test additions were separately verified by [run 42959453544](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42959453544) on commit `0730b8fd`.

### Known limitations
- Preferences are not scheduled posts, live optimum-time recommendations, or execution authorization. Smart timing still requires measured audience evidence and an approved scheduler.
- The unified gateway and signed-in HTML remain an offline/direct-call integration fixture. Production account enrollment, Google browser sign-in, media upload, social OAuth, hosted security and live publishing remain unavailable.

## Authenticated Content Studio and secure held-draft editing — 2026-11-10

### Added
- Connected a separate Content Studio tab to the signed-in BAM large-card interface. Members can explicitly create unpublished content requests, mark them postponed/unavailable and reopen incomplete drafts.
- Added `ui/held_draft_write_client.js` and `ui/held_draft_workspace.js`, strict business-scoped browser POST calls and tenant-verified refresh after content writes. In-flight UI results are discarded on sign-out or business switch.
- Added direct navigation from the Content overview card into the detailed Content Studio panel.
- Extended browser integration and lifecycle regression coverage, including real form submission and tenant-scoped held states.
- The already-present `bam_content_write_wsgi.py` is a disabled-by-default offline WSGI HTTP boundary for creating and holding drafts. No approval, media upload or publication route was added.

### Verification
- **Passed milestone:** [GitHub Actions run 42959259493](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42959259493), commit `374dc694`: Python compilation, **727 Python tests and 28 JavaScript UI test scripts**.
- Final direct-card navigation and end-to-end form smoke test updates remain subject to the next CI run.

### Known limitations
- Content Studio writes are only usable with a separately configured and enabled trusted HTTPS service; the HTML file itself is not a deployed service.
- Uploading and scanning photos, Google browser authentication, live social connections, AI execution, approval/publishing and Android packaging remain unimplemented or inactive.
- Browser tokens stay in memory; real production session and infrastructure security review is still required.

# Changelog

## Phase 3.5 — 2026-11-11 (priority-aware unpublished content queue)

### Added
- Explicit draft queue-priority choice at creation, with Normal as the default and server-side existing priority bounds enforced.
- Content Studio summary of current-business incomplete/review-ready/paused drafts, high-priority content needs and outstanding required checklist items.
- Priority selection filter and high-priority/review-ready/full-queue quick filters; all views are derived locally from previously authenticated data.

### Changed
- Draft cards display review queue priority without implying publishing order.
- Signed-in shell regression tests locate draft form inputs by stable field labels, protecting against new optional controls.

### Safety and verification
- No post is approved, scheduled, published or promoted merely by its priority; no new permission or provider call was added.
- **Passed:** [GitHub Actions run 43091924513](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43091924513), commit `5c53c736`: 882 Python tests, 72 JavaScript regression scripts and Python compilation.

### Known limitations
- Queue priority is currently chosen on draft creation. Reprioritizing an existing draft needs separate versioned business-authorized editing design; this release does not silently modify existing drafts.


## Phase 3.5 — 2026-11-11 (auditable reviewer note changes)

### Added
- Transactional immutable metadata events for review-note creation, edits and explicit removal, preserving event records when a note is removed.
- Feedback write rollback when its corresponding event cannot be saved; no historical note-text duplication in the audit table.
- Strict, business-scoped, owner/marketing-manager-only `GET /api/v1/review-feedback-history` (50-event cap; no query-supplied tenant) and an Approvals detail panel displaying the latest 10 redacted events.
- Event type, unique ID, timestamp, draft revision and nonapproval validation at both HTTPS transport and browser client boundaries.

### Safeguards and limitations
- Event records do not grant TruthGuard approval, final owner authorization, social scheduling or publishing. Actors are tracked internally but are not displayed in the current history API.
- Audit coverage begins when this change is installed; earlier note revisions cannot be reconstructed retrospectively.
- No production database, legal retention policy or anti-tamper external storage is configured; this is an offline SQLite audit foundation, not a tamper-proof distributed system.

### Verification
- **Passed:** [GitHub Actions run 43090679750](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43090679750), `f553f4b0`: 882 Python tests, 70 JavaScript UI scripts and Python compilation.


## Phase 3.5 — 2026-11-11 (confirmed unpublished calendar suggestions)

### Added
- Two-step confirmation from the Scheduled dashboard suggestion panel to save a **draft-only** proposed date, without first navigating into Content Studio.
- Server-validated revision and currently unused Manual-mode clock slot, explicit writer role checks, duplicate slot rejection, tenant/session invalidation, and fail-closed refresh on conflicts.

### Safety
- No date is saved on preview or the first click. Viewers and employees cannot write; even an explicitly confirmed proposed date does not schedule, approve or publish a social post.

### Tests
- **Passed:** [GitHub Actions run 43089512284](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43089512284), `88a9cca1`: 877 Python tests and 68 JavaScript UI scripts plus compilation.


## Phase 3.5 — 2026-11-11 (private editorial feedback and held-draft filters)

### Added
- Business-private editorial comments bound to the current held draft revision, visible to draft readers and writable only by currently authorized owners and marketing managers.
- Compare-and-set feedback tokens with conflict rejection, delete/recreate protection and stale-draft warnings, without altering draft contents or review/publication status.
- Strict HTTPS `GET/PUT/DELETE /api/v1/review-feedback` with explicit nonapproval flags; no social/AI provider call, automatic action, or tenant selected by the browser.
- Approvals drilldown feedback editor with explicit save, double-confirmed removal and stale-session protection; read-only linked feedback beside drafts in Content Studio.
- Content Studio in-browser channel/status/text filters, with no server-side search or mutation and automatic state clearing on account switches.

### Safeguards and fixes
- Creators/viewers/other tenants cannot write feedback. Missing or stale drafts and stale note versions require refresh before changing anything.
- Review notes are comments, **not** TruthGuard approval, final owner authorization, scheduled posts or an editable publishing flag.

### Verification
- **Passed:** [GitHub Actions run 43088917850](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43088917850) on commit `b52643de`: 877 Python tests, 65 JavaScript UI scripts, Python compilation.

### Known limitations
- This offline local development environment does not provide production audit retention, team notifications, real identity enrollment, media scanning, external social scheduling or automatic publishing.
- Notes are private business data; do not enter passwords, API keys or confidential customer material.


## Phase 3.5 — 2026-11-11 (private editorial preparation workflow)

### Added
- Read-only `ReviewReadiness` service which checks the active business's unpublished draft states, required content, and registered verified attachments without returning media paths or permissions.
- Strict authenticated, tenant-derived, GET-only `/api/v1/review-readiness` HTTP adapter; no tenant in query or body, no write methods, no provider network access.
- Deeper Approvals dashboard checklist with readiness counts and actionable missing/unverified material labels. Explicitly distinguishes complete material from human editorial/owner approval and publishing permission.
- Fail-closed browser parsing, cross-business tests, interface lifecycle tests, and gateway integration coverage.

### Safeguards
- Every checklist item remains held and lists TruthGuard review, final owner approval and social publication as unavailable, including for fully verified material.
- No content approval, scheduling, live social provider interaction, account credential exposure, public hosting or paid AI usage was introduced.

### Test status
- **Passed:** [GitHub Actions run 43081725025](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43081725025), commit `91d0e0cb`: 867 Python tests, 62 JavaScript scripts and Python compilation.

### Known limitations
- Attachment verification is based on the existing trusted local registry; actual production scanning/consent workflow, independent TruthGuard publication gate, owner approval interface, production data store and scheduler still need separate development and authorization.


## Phase 3.5 — 2026-11-11 (version-safe draft calendar collaboration)

### Added
- One-time proposal-version tokens for every saved draft-calendar assignment, and migration that backfills already saved SQLite records without loss.
- Compare-and-set semantics on proposed-time update/delete, including protection against stale tabs, concurrent edits and delete/recreate ABA conflicts.
- Version-aware strict HTTPS validation and Content Studio browser requests, with 409 refresh-required responses on stale writes.

### Fixed
- Prevent older editors from silently changing or removing another editor's newer saved draft time. No write can create an approved post or scheduling job.

### Test status
- **Passed:** [GitHub Actions run 43080077237](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43080077237) for commit `d03753f2`: 859 Python tests, 60 JavaScript test scripts, and Python compilation.

### Known limitations
- Version checks run in the offline local SQLite gateway; production database concurrency controls, authorization review, host deployment and external social scheduling are still pending. Proposal tokens are not secrets or login credentials.


## Phase 3.5 — 2026-11-11 (safe unassigned draft time suggestions)

### Added
- Prioritized, business-scoped, read-only suggestions pairing up to 20 unassigned held drafts with available, configured Manual posting times over the preview window.
- Strict HTTPS-only, disabled-by-default `GET /api/v1/calendar-suggestions` with validated tenant-bound browser response contracts.
- Separate Scheduled dashboard suggestions panel, linked to Content Studio for a subsequent explicit date selection.

### Changed and safeguards
- Persisted proposals, including stale ones, remain untouched and continue reserving their slots until removed by an authorized user.
- Postponed/unavailable drafts, non-current Smart scheduling recommendations, cross-business reads, extra response fields, and any purported scheduled-post count fail closed or remain unavailable.
- **No automated date assignment, live scheduling, publication, social provider calls, or paid AI requests.**

### Test status
- [GitHub Actions run 43078999350](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43078999350), commit `263c1c91`: 857 Python and 60 JavaScript test scripts passed; compilation passed.

### Known limitations
- These are non-binding suggestions, not saved dates. No production scheduler, worker, publishing or public hosting is enabled.


## Phase 3.5 — 2026-11-11 (private proposed draft calendar)

### Added
- Tenant-isolated persistence for draft-only possible posting times, restricted to unambiguous upcoming owner-configured Manual-mode slots and versioned held content.
- Strict authenticated HTTPS GET/POST/DELETE proposal-only routes, plus validated browser clients and Content Studio save/remove controls.
- Read-only proposed-calendar detail beneath the Scheduled dashboard drilldown, clearly separated from genuine scheduled posts (none are enabled).

### Safety and verification
- Reject stale draft revisions, conflicting business slots, unauthorized roles, cross-business access, unsafe time inputs and ambiguous/nonexistent DST times.
- Saved proposals remain `proposal_only`, return `posts_scheduled: 0`, and never grant approval or publication.
- GitHub Actions [run 43060585710](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43060585710) passed for commit `912c1ebc` (Python compilation, all Python and JavaScript tests).

### Known limitations
- Calendar proposals are not executable jobs and do not schedule social posts. Outdated proposals require manual attention.
- The local HTTPS preview is not a deployed public service; real provider connections and publishing remain disabled.


## Multi-business session rotation, offline WSGI integration and branded shell — 2026-11-10

### Added
- Connected the previously approved BAM icon, wordmarks and Android adaptive launcher templates from the main branch to the active development branch, preserving source files and verification tests.
- Built `bam_offline_gateway.py`: disabled-by-default composition of real SQLite identities, login and logout, business membership, dashboard, owner-confirmed AI facts, draft views, estimated cost and posting preferences through strict HTTPS WSGI adapters.
- Added `bam_business_switch_wsgi.py` and `ui/business_switch_client.js`: authenticated, tenant-checked business switching issues a new session and revokes the old one; invalid target businesses or client-supplied role claims are rejected.
- Added a business selector in the mobile-first signed-in HTML shell. Selecting a different permitted business clears the old dashboard before receiving the new tenant's data. Stale responses are discarded.
- Added extensive end-to-end Python and JavaScript tests for tenant isolation, unauthorized changes, HTTPS requirements, in-flight sign-out and abandoned token cleanup.

### Test status
- **Passed:** [GitHub Actions run 42954241030](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42954241030), commit `30da362dd56ac25aed076e656f96c0b691757db2`: Python compilation, **717 Python tests and 26 JavaScript UI test scripts**.

### Known limitations
- The unified WSGI gateway remains a local direct-call integration fixture, not a production HTTP listener, deployed website or Android APK.
- Brand assets and native launcher templates are not an installed app.
- Production TLS and OAuth/Google client configuration, verified email/password enrollment and recovery, server-level rate limits, real social/API connections, media scanning and publishing review remain mandatory.
- Publishing, live OpenAI generation and paid billing were not enabled.

## Authenticated large-card HTML shell and session lifecycle — 2026-11-10

### Added
- Responsive signed-in HTML shell with BAM branding, email/password form, four large read-only dashboard cards and drilldowns, AI draft section and nested AI Settings with Light/Dark/Auto.
- Frontend coordinator joining authenticated password/Google session logic to the dashboard and AI data adapters. Explicit sign-out and sign-out-everywhere clear private views and revoke trusted server sessions.
- Backend authenticated logout/logout-everywhere WSGI routes; pending login responses are discarded and revoked if sign-out wins.
- HTML DOM smoke tests for sign-in, dashboard rendering, tab navigation, appearance change, refresh, sign-out and secure-transport refusal.

### Test status
- **Passed:** [GitHub Actions run 42952514922](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42952514922), commit `569a9473818bf8bb5579410290938b315b331926`: Python compilation, **693 Python tests and 25 JavaScript test scripts**.

### Known limitations
- The HTML shell requires a separately deployed trusted HTTPS API. It is an integration-stage UI, not a working public service or Android APK.
- Google browser sign-in still needs configured provider credentials, verified OAuth/ID-token handling, enrollment and production session security.
- Posting, payment, live OpenAI calls, social account connections and actual scheduling remain disabled.

## Disabled-by-default HTTPS sign-in transport — 2026-11-10

### Added
- Added `bam_auth_wsgi.py` with strict HTTPS-only, bounded JSON routes for email/password login, one-time Google sign-in challenges, and server-verified Google login; refuses activation unless the trusted login API includes a throttle.
- Added `ui/auth_login_client.js`, a same-origin, no-cookie, no-storage browser client that supplies tenant context for verified membership checks and rejects unexpected sign-in responses.
- Added 13 Python gateway regression tests, including live offline IdentityAuth/membership verification, and one JavaScript client regression script.

### Test status
- **Passed:** [GitHub Actions run 42951600141](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42951600141), commit `9ef6e73eaa48f74e25ef4c235841b76fc4ddc739`: **689 Python tests, 23 JavaScript scripts and Python compilation**.

### Known limitations
- Authentication adapter is not mounted, deployed or permitted for production exposure. Separate TLS, IP/global throttles, external Google verifier configuration, secure hosting and a completed sign-in screen remain required.
- No business enrollment, social provider token exchange, OpenAI paid calls or publishing were enabled.


## CI recovery, scheduling reliability and private UI cleanup — 2026-11-10

### Fixed
- Repaired a Python syntax error in the disabled-by-default AI draft endpoint that prevented all development-branch checks from executing.
- Recognized the plural audience term "families" in smart posting-time suggestions; preview results remain proposals, not scheduled jobs.
- Cleared the privileged owner-confirmed business facts editor after failed workspace refreshes, preventing stale private form data.
- Corrected regression assertions to match explicit viewer analytics permission, known-competitor subdomain blocking, and invitation expiry at the exact TTL boundary; added the one-second-before-expiration test.

### Changed
- CI now automatically discovers and runs every `ui/*_test.js` JavaScript regression script and cancels superseded runs on the same branch.

### Test status
- **Verified passed:** [GitHub Actions run 42951059295](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42951059295) at commit `fa3647b5eb9d6688e23e448845814fc329a2728e`.
- Python compilation passed; **676 Python tests passed**; **22 JavaScript regression scripts passed**.
- The original isolated Phase 3.2 ZIP baseline also passed 26/26 locally during recovery.

### Known limitations
- CI is offline regression coverage, not real-browser, security-penetration, OAuth, provider or production-deployment verification.
- The current mobile-first HTML sample is not an installed Android app. Social publishing and live AI/network integrations remain disabled.


## Explicit owner-confirmed business facts editor — 2026-11-10

### Added
- Nested AI Settings fact editor with owner-only display, explicit Save action, unique key validation and optimistic revision payload.
- Optional integration with the authenticated AI workspace and business-switch cleanup.
- JavaScript regression tests for manual save, duplicate facts and permission display; selected tests passed in isolated harness.

### Limitations
- Production login and write endpoint mounting remain disabled; backend must independently enforce owner permission.


## Disabled-by-default AI service composition — 2026-11-10

### Added
- Complete offline AI service bundle wiring confirmed facts, quotas, idempotency, drafts, cost ledger and both write adapters.
- Default-deny OpenAI transport and WSGI endpoints with no credentials or network access.
- Regression test verifying the bundle cannot generate, edit facts or record charges.

### Limitations
- Production credential provisioning and endpoint activation are deliberately excluded.


## Optional manual ChatGPT image handoff — 2026-11-10

### Added
- Explicit copy-prompt and open-ChatGPT controls for media-held AI drafts, without automated login, image generation or publishing.
- Optional authenticated workspace callbacks and regression tests for manual actions and already-attached media.

### Verification
- Selected JavaScript view/handoff tests passed in an isolated harness; full CI not verified.


## Product README and historical milestone separation — 2026-11-10

### Changed
- Reorganized README into a detailed product and current architecture description rather than an append-only phase changelog.
- Preserved the complete prior phase-by-phase notes in `DEVELOPMENT_MILESTONES.md`.
- Linked AI architecture, UI integration and CI verification documentation.


## AI request reconciliation and JSON ambiguity hardening — 2026-11-10

### Added
- Authenticated, business/user-scoped read-only generation request status lookup.
- Duplicate JSON-key rejection for AI generation and owner-confirmed fact writes.
- Regression tests for failed/completed status isolation and ambiguous request bodies.

### Limitations
- No automatic retry or live provider billing reconciliation.


## Business-bound AI generation hold responses — 2026-11-10

### Fixed
- Include authenticated tenant scope on all non-created AI generation results.
- Reject held browser responses from another business and cover with regression tests.


## Coordinated authenticated workspace lifecycle — 2026-11-10

### Added
- Single session/business lifecycle coordinator for live dashboard cards and read-only AI workspace.
- Fail-closed clearing of private panels on refresh errors and stale-response invalidation on logout/switch.
- Isolated JavaScript lifecycle regression test, included in CI.

### Limitations
- Production login shell, deployment and real provider credentials are still unconnected.


## Authenticated large-card live dashboard foundation — 2026-11-10

### Added
- Mobile-first four-card dashboard controller and stylesheet for real authenticated read-only data.
- Safe held-content drilldown, explicit disconnected scheduling state, and business-switch/logout stale-response isolation.
- JavaScript regression test included in CI; isolated harness run passed.

### Limitations
- Component is not yet mounted into a production authenticated shell; existing HTML preview remains sample-only.


## Offline AI HTTP replay integration regression — 2026-11-10

### Added
- End-to-end Python regression test for authenticated HTTPS generation, fake OpenAI response, quota/idempotency and held draft persistence.
- Duplicate request must not cause a second provider invocation or draft.


## Explicit-action authenticated AI write client — 2026-11-10

### Added
- Browser client for idempotent held-draft generation and owner-confirmed fact updates over HTTPS.
- Input validation, no cookies/automatic retries, restricted origin/token characters and safe unpublished response contracts.
- Node regression tests for request integrity and exclusion of client-controlled tenant/publishing/model claims.

### Verification
- Selected JavaScript tests passed in isolated harness; full CI still pending.


## Owner-confirmed AI facts write boundary — 2026-11-10

### Added
- Disabled-by-default HTTPS `PUT /api/v1/ai-business-facts` endpoint for authorized owner confirmation.
- Strict bounded JSON input, active-business session scoping, optimistic revision checks and tests.

### Limitations
- Not mounted in a production service; owner confirmation is provenance, not independent verification.


## Disabled-by-default authenticated AI generation endpoint — 2026-11-10

### Added
- Separate HTTPS-only `POST /api/v1/ai-generate` WSGI adapter, disabled by default.
- Bearer-session, idempotency-key, bounded-body and server-owned quota/month constraints; minimal unpublished draft response.
- Offline tests for disabled mode, unauthorized calls, invalid client scope and unsafe publishing claims.

### Not enabled
- Public endpoint mounting, provider API calls, billing or social publishing.


## Required generation request keys when deduplication is configured — 2026-11-10

### Fixed
- Reject missing idempotency keys in deduplicated AI generation workflows.
- Added same-business, different-user isolation tests.


## Private AI usage summary and Settings panel — 2026-11-10

### Added
- Authenticated read-only `/api/v1/ai-cost-summary` scoped to the current user and business.
- Strict browser contract and optional AI Settings usage panel distinguishing estimated costs from actual charges.
- API, WSGI and UI tests for tenant isolation, safe estimates and failed-load cleanup.

### Verification
- Selected Node UI tests passed in an isolated harness; complete CI/Python run not yet verified.


## AI generation idempotency and duplicate protection — 2026-11-10

### Added
- Durable per-business/per-user generation request claims with fingerprint checks and completed/failed states.
- Optional generation-workflow integration preventing duplicate sponsored quota reservations, provider calls and drafts.
- Tests for replay, changed inputs, failed attempts and cross-business isolation.

### Limitations
- Production endpoints must require request keys; crash recovery and provider billing reconciliation remain pending.


## AI token usage and estimated-cost accounting — 2026-11-10

### Added
- Operator-priced, tenant-scoped token and estimated-cost ledger without invented default rates.
- Optional required provider-usage observer in the OpenAI Responses adapter.
- Offline integration test recording usage and estimated cost before staging a held draft.

### Limitations
- Estimated costs are not invoices, real billing reconciliation or a live pricing feed.


## Disabled-by-default HTTPS transport and offline AI integration — 2026-11-10

### Added
- Server-injected OpenAI HTTPS transport that refuses requests until explicitly enabled, with model/token limits, bounded payloads and sanitized errors.
- Offline end-to-end test from owner-confirmed facts through quota and structured provider response to a held, unpublished draft.
- Transport tests for disabled mode, secret isolation and unsafe request rejection.

### Not enabled
- Live OpenAI requests, actual charges, customer API key provisioning, social publishing or production deployment.


## Keyless OpenAI Responses adapter — 2026-11-10

### Added
- Strict, injected-transport Responses payload adapter with structured post/image-prompt schema, explicit token cap, disabled storage/tools and model allowlist.
- Tests for malformed provider responses, unexpected tool calls, unpublished-only requests and no API-key exposure.

### Limitations
- Production HTTPS transport, secret management, real API calls and billing remain unimplemented.


## Generation-time fact revision guard — 2026-11-10

### Fixed
- Reject AI output when owner-confirmed business facts change during generation, rather than staging content grounded in an obsolete snapshot.
- Added regression test for a mid-generation fact update.


## Quota-gated AI generation orchestration — 2026-11-10

### Added
- `ai_generation_workflow.py`: owner-confirmed facts → sponsored quota reservation → trusted executor → strict structured validation → held draft staging.
- Tests for missing facts, quota exhaustion, personal-key mode isolation, malformed executor output and no publishing.

### Limitations
- No OpenAI network executor, encrypted key vault, production cost accounting, real image generation or social publishing.


## Image-prompt revision reopens media hold — 2026-11-10

### Fixed
- Revising an AI image prompt invalidates its prior verified-image association and reopens the media-needed hold.
- Revising only post text preserves the existing verified-image association; regression tests cover both cases.


## AI fact provenance workspace integration — 2026-11-10

### Added
- Read-only business-fact provenance panel with safe text rendering and unconfigured-fact warnings.
- Optional AI workspace integration for authenticated fact snapshots, plus Node CI tests.

### Fixed
- Stale refresh errors cannot clear newer same-session data; active-session errors clear the fact panel as well.


## Authenticated AI fact provenance read — 2026-11-10

### Added
- `GET /api/v1/ai-business-facts` authenticated, read-only owner-confirmed fact snapshot.
- Strict browser contract and HTTPS client support for fact provenance and revision.
- Cross-business API and WSGI/Node regression tests.


## Owner-confirmed AI fact registry — 2026-11-10

### Added
- `ai_business_facts.py`: owner-confirmed business facts with tenant isolation, revision checks and provenance metadata.
- `AIContentPlan.create_from_confirmed_facts`: draft request construction from an authenticated, current-business fact snapshot.
- Tests for owner-only confirmation, creator use, business isolation and stale fact revision denial.

### Limitation
- Owner confirmation is not independent external verification; final TruthGuard and approval remain required.


## AI workspace refresh ordering — 2026-11-10

### Fixed
- Older AI workspace refreshes cannot overwrite newer same-business results; regression coverage added for out-of-order responses.


## AI authorization and response hardening — 2026-11-10

### Fixed
- Deny Viewer-role attempts to change AI funding mode, user memory or personal-key reference.
- Reject targeted AI revision outputs with extra fields, including model-generated publishing claims.
- Added regression tests for both safeguards.


## Trusted image association for held AI drafts — 2026-11-10

### Added
- AI draft method to link an image only after the existing attachment registry confirms trusted verification for the exact business, draft and item.
- Browser contract and read-only UI state distinguishing missing media from verified attached media.
- Tests for unverified images, mismatched draft references and continued factual-review holds.

### Not enabled
- Direct uploads, scanner service, automatic approvals or social publishing.


## Authenticated AI workspace coordinator — 2026-11-10

### Added
- `ui/ai_workspace.js`: read-only session-scoped AI Content Studio and Settings loading, with stale-response cancellation on business switch/logout.
- `ui/ai_workspace_test.js`: tests for business-switch race conditions, logout and failed-load cleanup.

### Fixed
- Clear previously rendered private AI content when a current-session read fails.
- Corrected an existing HTTP-client test assertion to count all three requests.


## AI business-switch integration regression — 2026-11-10

### Added
- Account API integration test covering per-business AI memory, stored AI drafts and cross-business switch isolation.


## Targeted AI revision schema correction — 2026-11-10

### Fixed
- Removed conflicting combined-generation JSON instructions from targeted component revisions; the revision request now asks for only `revised_text` and preserves the untouched component.


## Nested AI Settings presentation — 2026-11-10

### Added
- Read-only Settings → AI component showing OpenAI mode, configured-but-hidden key status and isolated content preferences.
- DOM regression test for safe rendering and cross-business response rejection; added to CI.


## Secret-free OpenAI Settings read — 2026-11-10

### Added
- Authenticated read-only `/api/v1/ai-settings` endpoint for OpenAI mode and per-user business-scoped memory.
- Strict browser validation rejecting raw credential fields and cross-business settings responses.
- Python WSGI and Node client regression tests in CI.

### Not enabled
- Personal API-key upload, encrypted vault, mode-changing HTTP endpoint, billing or AI generation.


## AI Content Studio read-only integration — 2026-11-10

### Added
- Authenticated read-only `/api/v1/ai-drafts` endpoint for current-user, current-business AI drafts.
- Strict AI draft browser contract, HTTPS client integration and safe draft/image-prompt DOM renderer.
- Python WSGI route tests and Node contract/view tests in CI.

### Safeguards
- Missing media remains on hold; no publishing, approval, file upload or actual AI call is enabled.


## Persistent AI draft staging — 2026-11-10

### Added
- `ai_content_drafts.py`: business/user-isolated SQLite storage for structured post and optional image prompt, explicit media-needed holds, and optimistic revision counters.
- `test_ai_content_drafts.py`: tests for draft persistence, no-publish state, user/business isolation, media requirements and stale-edit rejection.

### Limitations
- No actual OpenAI calls, image uploads, verified-media linking or publishing.


## Reversible personal OpenAI key mode — 2026-11-10

### Fixed
- Switching back to BAM-sponsored AI retains a trusted personal-key vault reference for convenient future switching.
- Added explicit key-reference removal operation and tests; secret deletion from a future encrypted vault remains separate.


## Approved structured AI content plan — 2026-11-10

### Added
- `ai_content_plan.py`: one structured post plus optional image-prompt request, targeted copy/image-prompt revisions, and bounded advance draft batches.
- `ai_local_templates.py`: verified-fact-only, zero-API-cost product spotlight draft.
- Offline tests for structured output, component preservation, batch validation and local template safeguards.
- Documented optional ChatGPT Free/paid image creation as a user-operated workflow, not a BAM API integration.

### Safeguards
- All generated or templated content remains pending verification and approval; no image generation or publication is claimed.


## Approved OpenAI-only AI architecture — 2026-11-10

### Added
- `AI_ARCHITECTURE.md` documents three supported scenarios: owner-only two posts/day with BAM-sponsored AI, 5–10 invited users with sponsored AI preferred, and a future monetized Google Play release.
- `ai_account_policy.py`: per-user and per-business OpenAI mode, reversible BAM-sponsored/personal-key settings using trusted vault references, and independent AI memories.
- `ai_sponsorship.py`: server-configured scenario plans, bounded output tokens and atomic SQLite monthly quota reservations.
- `ai_draft_request.py`: safe OpenAI-only prompt request builder requiring verified business facts, user-specific memory and unpublished draft output.
- `test_ai_account_policy.py`, `test_ai_sponsorship.py`, and `test_ai_draft_request.py`: offline regression coverage for isolation, credential-reference validation, quota exhaustion and content constraints.

### Preserved
- Existing authentication, tenant boundaries, GUI, manual/smart scheduling, Content Studio, and disabled social publishing.

### Not yet implemented
- Real OpenAI generation, encrypted API-key vault, billing, direct Facebook Page connection, live deployment and end-to-end UI integration. Public prices and exact allowances remain undecided.


## Posting preference browser validation — 2026-11-10

### Added
- Strict browser validator for per-business posting preference responses.
- HTTPS client validation and CI tests for unconfigured timezone, manual time validation and disabled publishing.


## Read-only Content Studio browser components — 2026-11-10

### Added
- Strict client-side held-draft list contract covering all four hold statuses.
- Safe read-only Content Studio DOM renderer grouping drafts by status.
- HTTPS read client validates Content Studio responses.
- Node regression tests added to CI for invalid states, cross-business responses and safe text insertion.


## Business-switch UI isolation hardening — 2026-11-10

### Changed
- HTTPS read client and DOM renderer can reject responses with an unexpected tenant ID.
- Renderer exposes explicit clear operation to remove prior-business content before switching.
- Updated integration runbook and regression tests for stale-response protection.


## Authenticated UI integration checkpoint — 2026-11-10

### Added
- End-to-end offline WSGI integration regression covering real account sessions and cross-business restricted dashboard views.
- `AUTHENTICATED_UI_INTEGRATION.md` with architecture boundaries, production prerequisites and test commands.

### Status
- Components committed; automated CI outcomes and live deployment remain unverified.


## Read-only HTTPS transport foundation — 2026-11-10

### Added
- HTTPS-gated, GET-only WSGI endpoints for authenticated dashboard, held drafts and posting preferences.
- No-cache and restrictive response headers, generic authentication/service errors and no CORS exposure.
- Browser HTTPS read client using memory-supplied bearer tokens, no cookie credentials, no storage and no redirects.
- Offline WSGI and JavaScript transport tests; frontend tests added to CI.

### Limitations
- No deployed server, production TLS proxy, login screen or browser-to-server integration yet; no posting or scheduling.


## Authenticated dashboard DOM renderer — 2026-11-10

### Added
- Read-only browser DOM renderer for validated tenant-scoped dashboard data.
- Explicit Not connected/Restricted card states and attention-list display.
- Tests for safe text rendering and rejection of malformed payloads before DOM replacement; included in CI.

### Limitations
- Backend HTTP transport, browser authentication, and live integration remain future milestones.


## Persistent posting preferences — 2026-11-10

### Added
- SQLite-backed, business-scoped Smart/Manual posting preferences with explicit IANA timezone.
- Authenticated read/update API methods deriving the tenant from the active session.
- Tests for persistence, owner-only mutation, cross-business isolation, invalid timezones/times and session revocation.

### Security and accuracy
- Strict Smart/Manual input pairing; Smart mode has no fabricated recommendations.
- Preference storage never triggers scheduling or publishing.


## Persistent posting preferences — 2026-11-10

### Added
- Tenant-scoped offline Smart/Manual posting preference persistence with validated IANA timezone and sorted unique manual times.
- Authenticated read and owner-only update methods in `AccountReadAPI`.
- Unit and API tests for authorization, tenant isolation, malformed times, timezone and disabled publishing.

### Limitations
- Standalone GUI preferences remain local-only. No live scheduling, daylight-saving-time execution or publishing.


## Smart/manual calendar controls — 2026-11-10

### Added
- Per-business Smart versus Manual posting-time selector in the Calendar prototype.
- Explicit 24-hour manual time entry, removal and sorting in the offline UI.
- UI regression coverage for mode selection, manual times and business isolation.

### Fixed
- Corrected escaped regular expression preventing valid manual times from being accepted.

### Limitations
- Preferences are temporary preview state; no actual scheduling, smart-time recommendations or publishing.


## Verified content and frontend contract — 2026-11-10

### Added
- Authenticated `supply_verified_content` API for existing scanner-approved attachments; completed drafts move to review without publishing.
- Regression test for rejecting unverified attachments and safe transition to review.
- Strict JavaScript adapter for authenticated dashboard payloads, including tenant/card/draft and unavailable-metric validation.
- Frontend data-contract tests added to GitHub Actions.

### Limitations
- Real media uploads, trusted scanner workers, hosted HTTPS transport and frontend-to-backend fetching are not implemented.


## Complete held-draft list API — 2026-11-10

### Added
- Authenticated, tenant-scoped `list_held_drafts` API with optional status filtering and sanitized draft metadata.
- Regression coverage for postponed draft visibility, cross-business isolation and invalid status rejection.

### Security
- Raw attachment references and publication permissions remain unavailable in UI list payloads.


## Authenticated dashboard view contract — 2026-11-10

### Added
- `AccountReadAPI.get_dashboard_view` and `dashboard_view.py` for a safe, read-only tenant-scoped GUI payload.
- Regression tests for draft isolation, connection visibility, unknown analytics/schedule metrics and invalid sessions.

### Fixed
- Wired dashboard cards into actual `AccountReadAPI.get_overview` and business-switch responses; previous documentation had described this before the integration existed.

### Limitations
- No public HTTPS endpoint or frontend data fetching yet. The HTML preview remains sample-only; CI run not yet independently confirmed.


## Settings appearance navigation — 2026-11-10

### Changed
- Removed the prominent theme-toggle button from the dashboard.
- Added Settings → Appearance with explicit Light, Dark and Auto (device) selections; Auto is the prototype default.
- Added reserved Settings section for account, notification, business and connection preferences.
- Updated UI smoke tests to verify settings navigation and appearance selections.

### Verification
- JavaScript Settings and theme-selection smoke checks passed in V8. GitHub Actions run remains unverified.


## Automated GUI smoke-test gate — 2026-11-10

### Added
- Dependency-free Node.js dashboard smoke test for sample-business isolation, navigation, content drilldowns and theme switching.
- GitHub Actions Node.js 22 setup and dashboard smoke-test step ahead of Python unit tests.

### Verification
- Matching dashboard interactions passed a local V8 stub-DOM smoke check. The committed Node test and full CI result remain unverified.


## Authenticated dashboard card contract — 2026-11-10

### Added
- Server-side card view model exposing authorized content and review counts, plus permission-aware connection counts.
- Explicit unavailable scheduling metric rather than invented zero or fabricated scheduled-post data.
- Card view model added to account overview and business-switch API responses, with regression tests.
- Verified GUI JavaScript syntax and initial render, theme switch, and business-switch behavior using a minimal V8 DOM stub.

### Limitations
- HTML UI still uses sample data and is not connected to authenticated API; full browser tests and CI remain pending.


## Mobile-first GUI prototype — 2026-11-10

### Added
- Standalone responsive BAM dashboard prototype with large home cards and drilldown pages for content, individual drafts, calendar, analytics and social connections.
- Business switcher with isolated Belenos Creations and Busy B Cleaning Service sample data, sample engagement chart, held-draft creation and local hold-state controls.
- Desktop sidebar and mobile bottom navigation, semantic landmarks, keyboard focus and reduced-motion support.
- Static structural and offline-safety regression checks for the HTML prototype.

### Limitations
- Browser-local demonstration only. No live backend, production authentication, real analytics, media upload, scheduling or publishing; browser end-to-end tests and current CI status remain unverified.


## Authentication integration checklist — 2026-11-10

- Added `AUTH_DEPLOYMENT.md` with Google OAuth, email verification, session security, mobile integration and release requirements.
- Clarified that current identity services are offline backend foundations, not live public login routes.


## Business invitation foundation — 2026-11-10

### Added
- One-use seven-day business invitation tokens bound to verified BAM identity email and an owner-authorized non-owner role.
- Tenant-scoped membership creation only after trusted identity proof and valid inviter authorization.
- Invitation tests for tenant isolation, forbidden owner grants, identity mismatch, expiry and replay.

### Limitations
- No live email delivery, public invitation acceptance flow or production-grade concurrency/abuse protection.


## Password login throttling — 2026-11-10

### Added
- Persistent hashed-email failed-login counter and lockout window for password authentication.
- Optional trusted AuthLoginAPI throttle integration and lockout/expiry/privacy regression tests.

### Limitations
- Not a substitute for mandatory production per-IP/device/global rate limits or concurrency-safe storage; no public authentication endpoints enabled.


## Account enrollment and recovery primitives — 2026-11-10

### Added
- One-time hashed email verification and password-reset tokens with 15-minute expiry and trusted out-of-band delivery callback.
- Password reset that revokes existing BAM sessions, with non-enumerating request responses.
- Google-only signup from verified nonce-bound Google ID tokens, creating an identity without implicit business membership.
- Regression tests for token expiry/replay, session revocation and refusal to auto-merge existing email identities.

### Limitations
- No real email sender, public account signup, user invitations, production rate limiting or mobile login interface; current tests not independently verified.


## Authentication foundation — 2026-11-10 (development branch)

### Added
- Verified-email password identity storage using salted PBKDF2-HMAC-SHA256 hashes; no automatic business access on registration.
- Google ID-token verifier with issuer, audience, expiry, issued-at, email verification and nonce checks; optional trusted google-auth integration.
- Single-use, five-minute Google nonce challenge ledger and sign-in API boundary.
- Explicit Google-to-BAM identity linking requiring authenticated BAM session and fresh password proof; no email-only auto-linking.
- Authenticated password rotation with global session invalidation and authentication security regression tests.

### Limitations
- Backend foundation only: no actual Google OAuth client, verified email delivery, password reset, public login routes, mobile UI or deployed production identity service. Current-branch tests not independently confirmed passing.


## Verification workflow update — 2026-11-10

- Added Python compile-all validation before GitHub Actions unit-test discovery.
- CI pass status for the current development branch remains unconfirmed.


## Held-draft lifecycle controls — 2026-11-10 (development branch)

### Added
- Authenticated hold-state API and local terminal controls for postponing, marking unavailable, and reopening incomplete drafts.
- Regression tests for hold/reopen lifecycle, cross-tenant access denial, viewer permissions and strict request validation.

### Fixed
- Return a not-found HTTP response instead of an unhandled exception when a draft ID does not exist in the active business.

### Limitations
- Local prototype only; no upload, AI generation, scheduling or publishing.


## Local held-draft workflow integration — 2026-11-10 (development branch)

### Added
- Tenant-scoped held Content Requests and missing-content suggestions in the account dashboard and terminal demo.
- Authenticated HTTP creation of manually entered held drafts, with strict request validation and server-derived tenant.
- Demo drafts for each example business and interactive terminal draft creation.
- HTTP integration regression cases for draft creation, tenant isolation and rejection of client-supplied business IDs.

### Limitations
- No AI draft generation, actual media upload, public server, production authentication, social OAuth or publishing. Current branch test run not independently verified.


## Cross-workflow authorization hardening — 2026-11-10 (development branch)

### Fixed
- Require current session role in Content Request and owner approval-intent operations.
- Reject stale sessions following role upgrades, not only downgrades.
- Update Content Request test fixture to use verified attachment IDs instead of unsupported content references.

### Added
- Regression tests for stale role promotion into content creation and owner approval.


## Local account workflow prototype — 2026-11-10 (development branch)

### Added
- Loopback-only development HTTP gateway with BAM account overview, business activation, logout, and identity-wide logout routes.
- Runnable disposable demo server and interactive terminal client for switching between sample businesses.
- End-to-end HTTP integration tests using real BAM session, membership, connection registry and dashboard services.
- Authenticated self-service logout everywhere, revoking sessions across businesses without affecting other users.
- Transport regression cases covering malformed input, cross-origin requests and DNS rebinding attempts.

### Fixed
- Revoke newly issued session when dashboard activation fails after business switching.

### Limitations
- Offline local-only development demo, not a production HTTP service or Android UI. Tests committed but passing CI not independently confirmed. No social OAuth or publishing.


## Account read API boundary — 2026-11-10 (development branch)

### Added
- Transport-neutral read-only BAM account adapter for overview, authorized business activation and current-session logout.
- Six additional regression cases for tenant isolation, role-scoped switching, logout and invalid requests.

### Limitations
- No HTTP server, deployed authentication, live OAuth or publishing. CI results not independently verified in this session.


## Account dashboard integration — 2026-11-10 (development branch)

### Added
- Read-only, role-aware account dashboard composed from BAM sessions, business switching and social account directory.
- Five focused regression cases for tenant visibility, permission filtering, switching, session revocation and stale roles.

### Fixed
- Business selection now requires a current-role session; a role change invalidates stale source sessions before switching.

### Limitations
- No deployed API or mobile UI; tests committed but not independently executed. Live provider connections and publishing remain disabled.


## Phase 8.9 — 2026-11-10 (development branch)

### Added
- Fresh membership and role validation for privileged BAM session resolution.
- Identity-wide session revocation across businesses for trusted administrative flows.
- Stronger session checks in business switching and social connection directory.
- Three additional regression cases for role freshness, inactive memberships and global sign-out.

### Limitations
- Offline security primitives only; no live identity provider, mobile token vault or publishing.


## Phase 8.8 — 2026-11-10 (development branch)

### Added
- Target-business session issuance in existing business selector, using current tenant membership and role.
- Revalidation of source-business membership before business listing and switching.
- Three additional regression cases for activation, unauthorized targets and revoked source access.

### Limitations
- Production identity verification, mobile account switch UI and provider integrations remain outstanding. Publishing disabled.


## Phase 8.7 — 2026-11-10 (development branch)

### Added
- Read-only multi-platform social connection directory behind BAM session and tenant-scoped analytics permissions.
- Seven regression cases for independent business/platform listings, role checks, session expiry and metadata privacy.

### Architecture
- BAM authentication remains independent from optional social platform account connections.

### Limitations
- No live provider OAuth, global BAM account-switching interface, production identity verification or publishing.


## Phase 8.6 — 2026-11-10 (development branch)

### Added
- Backend-only OAuth attempt state ledger with PKCE S256 challenge and bounded expiry.
- Single-use, tenant/provider/account-bound callback state validation with transactional replay prevention.
- Ten regression cases for replay, scope, expiry, verifier and stored-hash behavior.

### Limitations
- No OAuth redirect handling, token exchange, vault, session binding, live provider connection or publishing.


## Phase 8.5 — 2026-11-10 (development branch)

### Added
- Fail-closed provider connection gate before analytics preview and import.
- Rejection of unconnected, expired, refresh-required and revoked connections before fetching.
- Eight regression cases for connected access, invalid connection states and tenant/caller isolation.

### Limitations
- The underlying adapter is internal and can be called directly unless a production server enforces the gated interface. No OAuth or live provider integration.


## Phase 8.4 — 2026-11-10 (development branch)

### Added
- Offline per-tenant/provider/account connection metadata registry with secret-vault references, scope and lifecycle states.
- Expiry-aware status responses that do not expose vault references.
- Nine regression cases for lifecycle, isolation, read-only scopes and validation.

### Limitations
- No OAuth, real secret vault, token refresh, provider verification or live connection.


## Phase 8.3 — 2026-11-10 (development branch)

### Added
- Authorized read-only synchronization health assessment with missing/current/stale/invalid checkpoint states.
- Configurable freshness threshold and nonexecuting recovery guidance.
- Eight regression cases for health states, isolation and validation.

### Limitations
- No real provider authentication, automatic retries, network requests or publishing.


## Phase 8.2 — 2026-11-10 (development branch)

### Added
- Provider-neutral, offline analytics page adapter with pre-fetch account authorization and checkpoint-aware import.
- Business-local weekday/hour bucketing of historical publication times.
- Seven regression cases for authorization, validation, preview and import.

### Limitations
- The injected fetcher is not a live provider connector; no OAuth, live data access, scheduling or publishing.


## Phase 8.1 — 2026-11-10 (development branch)

### Added
- Offline tenant/platform/account synchronization checkpoints with exact expected-cursor validation.
- Bounded atomic batch imports, preserving checkpoint and observation rollback together.
- Seven regression cases for credentials, stale cursors, duplicate imports and partial rollback.

### Changed
- Import boundary exposes reusable credential authorization; observation insertion preserves caller-owned transactions.

### Limitations
- No live provider synchronization, OAuth, background jobs or publishing.


## Phase 8.0 — 2026-11-10 (development branch)

### Added
- Tenant/platform/account-bound offline analytics import interface using server-injected credentials.
- Validation and normalization of integer engagement and impression counts, with duplicate post protection through the observation store.
- Nine regression cases for authentication, isolation, malformed metrics and duplicate ingestion.

### Limitations
- Caller authentication is not provider-origin verification; no OAuth, external API synchronization or publishing.


## Phase 7.9 — 2026-11-10 (development branch)

### Added
- Offline SQLite engagement observation store keyed by tenant, platform and source post ID.
- Bounded time-window and candidate queries with tenant/platform filtering.
- Seven regression cases for deduplication, scope isolation, validation and ranker integration.

### Limitations
- Ingestion is not authenticated against a social provider and is not a live analytics connection. No scheduling or publishing.


## Phase 7.8 — 2026-11-10 (development branch)

### Added
- Offline tenant-scoped candidate ranking using supplied observed engagement rates and minimum sample thresholds.
- Optional smart-preview integration with explicit insufficient-data fallback; manual selection remains independent.
- Seven regression cases for ranking, malformed/cross-tenant data and nonpublishing previews.

### Limitations
- No connected analytics ingestion, statistical confidence adjustment, prediction or publishing.


## Phase 7.7 — 2026-11-10 (development branch)

### Added
- Timezone-aware, read-only manual/smart scheduling preview tied to the held readiness assessment.
- Validation of daylight-saving gaps/overlaps, duplicate candidates, mode mismatch and tenant isolation.
- Eight regression cases for preview boundaries.

### Limitations
- Smart mode uses earliest-candidate demonstration only; no engagement optimization, job creation or publishing.


## Phase 7.6 — 2026-11-10 (development branch)

### Added
- Read-only schedule-readiness assessment with explicit safety blockers and owner/tenant authorization inherited from the intent ledger.
- Seven regression tests for held scheduling, revoked intent, stale content, unverified media, invalid time and tenant isolation.

### Limitations
- All proposed schedules remain held; final approval and publishing integrations are not implemented.


## Phase 7.5 — 2026-11-10 (development branch)

### Security
- Validate all required supporting attachments against the tenant/request/item-scoped verified registry before recording intent.
- Revalidate attachments when inspecting previously recorded intent; expose `attachments_verified`.
- Replace fake attachment fixtures with registered verified attachments; add three negative regression cases.

### Limitations
- The offline attachment registry does not inspect file bytes or grant publishing permissions.


## Phase 7.4 — 2026-11-10 (development branch)

### Added
- Approval-intent snapshot digest of channel, required items and supplied content references.
- Inspection flag `content_unchanged`; changed supporting content requires new review.
- Schema migration for existing intent tables, with missing historical digests treated as stale.
- Three regression cases for replacement, unchanged content and legacy records.

### Limitations
- Metadata fingerprinting does not independently verify underlying media or grant publishing rights.


## Phase 7.3 — 2026-11-10 (development branch)

### Changed
- Approval-intent inspection now rechecks current Content Request readiness, not just draft text.
- Adds `content_complete` and `requires_new_review` status indicators.
- Regression case for a previously completed request later placed on hold.

### Safety
- Approval intent remains nonpublishing and does not grant scheduling access.


## Phase 7.2 — 2026-11-10 (development branch)

### Added
- Owner-authenticated, tenant-scoped approval-intent recording bound to a complete Content Request and exact review receipt.
- Revocation and read-only current-draft integrity inspection.
- Five regression tests for authorization, completeness and revocation.

### Limitations
- Intent is not final approval and cannot schedule or publish content.


## Phase 7.1 — 2026-11-10 (development branch)

### Added
- Draft-bound, deterministic TruthGuard review receipt and stale/tampered report validation.
- Eight regression cases covering integrity, cross-tenant/request mismatch and held-only receipts.

### Limitations
- SHA-256 receipts are not signed authorization; production audit storage and separate approvals are future work.
- No publishing or scheduling capability is enabled by receipts.


## Phase 7.0 — 2026-11-10 (development branch)

### Added
- Correlation of heuristic risk signals with exact stored-draft annotation spans.
- Read-only `uncovered_risk_signals` and `risk_signals_annotated` review indicators.
- Two regression cases; annotation never authorizes publication.


## Phase 6.9 — 2026-11-10 (development branch)

### Security
- Reject facts whose approval timestamp is later than the requested review time.
- Add five regression cases for temporal and tenant boundaries.
- Preserve held review status and disabled publishing.


## Phase 6.8 — 2026-11-10 (development branch)

### Security hardening
- Validate bounded, correctly typed TruthGuard claim lists before hash-based draft span matching.
- Add malformed and oversized claim regression coverage.
- Retain fail-closed held status and disabled publishing.


## Phase 6.7 — 2026-11-10 (development branch)

### Added
- Heuristic source-span signals for pricing/discounts, guarantees, urgency/availability, business hours and testimonials.
- Risk signals integrated into authenticated, read-only TruthGuard Content Request review.
- Ten regression tests committed.

### Limitations
- Pattern matching is incomplete and cannot establish factual correctness or publication eligibility.
- Current-branch tests have not yet been independently executed; publishing disabled.


## Phase 6.6 — 2026-11-10 (development branch)

### Changed
- TruthGuard review now cross-checks supplied verified claims against exact source-span annotations in the stored draft.
- Exposes detached claims separately from knowledge-base verification, avoiding false draft-grounding impressions.
- Three regression tests committed.

### Limitations
- Does not independently extract every factual claim; all drafts remain held and publishing disabled.
- Full current-branch test execution still unverified.


## Phase 6.5 — 2026-11-10 (development branch)

### Added
- Exact source-span audit for TruthGuard claim annotations, with overlap/mismatch detection, unannotated-text visibility and draft fingerprint.
- Audit included in authenticated read-only Content Request review results.
- Ten audit tests and two integration tests committed.

### Limitations
- Source-span integrity does not prove factual completeness or truth. No publish eligibility is granted.
- Current-branch test execution not yet confirmed; publishing disabled.


## Phase 6.4 — 2026-11-10 (development branch)

### Added
- Authenticated read-only TruthGuard review for stored business content requests.
- Claim evidence and content-completeness reporting without approval or publishing side effects.
- Seven regression tests.

### Limitations
- Claim lists are supplied by the caller and are not guaranteed complete; all drafts remain held.
- Tests committed but not independently executed.


## Phase 6.3 — 2026-11-10 (development branch)

### Added
- Authenticated owner-only TruthGuard fact approval, lookup and revocation service.
- Fresh membership, tenant and session checks; eight regression tests.

### Limitations
- Owner confirmation is not independent external verification; no production API, Android UI or publish gate.
- Tests committed but execution unverified.


## Phase 6.2 — 2026-11-10 (development branch)

### Added
- TruthGuard approved fact registry with tenant isolation, provenance, expiration and revocation.
- Exact normalized claim verification against current approved facts and evidence references.
- Fail-closed full-draft review; twelve regression tests.

### Limitations
- No authenticated fact administration, independent source verification, complete claim extraction or production publishing gate.
- Tests committed but not independently executed; publishing remains disabled.


## Verification checkpoint — 2026-11-10

### Verified
- Executed the archived Phase 3.2 offline Python unit tests: 26 passed, 0 failed, 0 errors.
- Recorded test command, verification scope and release gates in VERIFICATION.md.

### Still unverified
- Newer GitHub development modules through Phase 6.1; no passing current-branch CI run confirmed.
- Live integration, Android UI and publishing remain disabled/not implemented.


## Phase 6.1 — 2026-11-10 (development branch)

### Added
- Read-only multi-post schedule preview from authenticated per-business Manual/Smart settings.
- Distinct proposed slots, held-draft visibility and settings revision metadata.
- Six regression tests.

### Limitations
- Preview readiness flags are caller-provided; they are not trusted for actual publishing.
- No scheduling jobs, Android UI, HTTP API or publishing. Tests not independently executed.


## Phase 6.0 — 2026-11-10 (development branch)

### Added
- Strict Manual/Smart scheduling settings screen data contract.
- Validated mode switching, exact weekly time editing and revision metadata.
- Seven tests for data roundtrip, access restrictions and stale updates.

### Limitations
- No rendered Android screen or HTTP API; publishing disabled.
- Test execution unverified.


## Phase 5.9 — 2026-11-10 (development branch)

### Added
- Authenticated business-specific saved scheduling settings wired to the posting-time proposal engine.
- Explicit not-configured response, revision metadata and nonpublishing result flags.
- Seven integration regression tests.

### Limitations
- No actual scheduling jobs, publishing or Android UI.
- Test execution unverified.


## Phase 5.8 — 2026-11-10 (development branch)

### Added
- Session-authenticated Manual/Smart scheduling settings service.
- Fresh tenant membership validation and revision-aware edits.
- Seven security and persistence regression tests.

### Limitations
- No network endpoint, Android screen, scheduler or publishing.
- Test execution unverified.


## Phase 5.7 — 2026-11-10 (development branch)

### Added
- Persistent tenant-scoped Manual/Smart scheduling settings, timezone, weekly times and smart-hour preferences.
- Fresh business membership checks and revision-based edit conflict protection.
- Nine regression tests for persistence, permissions and isolation.

### Limitations
- Internal offline repository only; no HTTP or Android settings screen, no publishing.
- Tests committed; execution unverified.


## Phase 5.6 — 2026-11-10 (development branch)

### Added
- Manual weekly posting times per business timezone, preserving exact user-selected minutes.
- Smart posting-time suggestions based on post subject, audience, preferred hours and supplied engagement observations.
- Explicit per-post time overrides in either mode.
- Mandatory hold for missing content or approval; suggestions never auto-publish.
- Twelve scheduling-policy regression tests.

### Limitations
- Offline policy engine only; no saved user settings, platform analytics, Android scheduling UI or publishing integration.
- Tests committed, execution unverified.


## Phase 5.5 — 2026-11-10 (development branch)

### Added
- Offline SHA-256 byte comparison, size enforcement and basic file signature checks for attachments.
- Tenant-scoped pending-record inspection that never grants verification or publishing permission.
- Ten regression tests for byte validation, signatures, hash mismatch and access boundaries.

### Limitations
- No storage integration, malware scanner, full media decoding or consent validation.
- Tests committed but execution remains unverified; publishing disabled.


## Phase 5.4 — 2026-11-10 (development branch)

### Added
- Authenticated upload preflight for active business-specific content requests.
- File-type allowlist and size limits; server-generated private storage identifiers.
- Pending-only attachment registration with no upload URL or publish capability.
- Ten regression tests for authorization, limits and session handling.

### Test status and limitations
- Tests committed; execution unverified.
- No actual byte transfer, object storage, scanning, hash verification or Android UI.
- Publishing remains disabled.


## Phase 5.3 — 2026-11-10 (development branch)

### Added
- Authenticated, read-only Content Requests dashboard projection with business-specific counts and cards.
- Per-draft missing/supplied content checklist, prepared text, capture suggestions and priority.
- Explicit non-publishable and non-schedulable flags.
- Five tests covering partial completion, tenant isolation, revoked sessions and hold states.

### Test status and limitations
- Tests committed; not independently executed.
- No rendered Android screen, live upload, trusted scanner or publishing integration.


## Phase 5.2 — 2026-11-10 (development branch)

### Added
- Tenant-scoped attachment metadata and pending/verified/rejected lifecycle.
- Authenticated Content Request completion now requires a matching verified attachment ID, rather than an arbitrary user-supplied reference.
- Ten attachment tests and two additional authenticated service tests.

### Limitations and test status
- No actual file uploader, scanning worker, consent verification or private object storage integration.
- Tests committed; execution and CI status remain unverified.
- Publishing disabled.


## Phase 5.1 — 2026-11-10 (development branch)

### Added
- Authenticated Content Request application service with fresh per-operation membership and role checks.
- Session revocation, expiry, cross-business access, role downgrade and viewer-read-only test cases (14 tests).
- Content completion continues to mean ready for review, never scheduled or published.

### Test status and limitations
- Tests committed; execution and CI results not independently verified.
- Internal offline service only; trusted asset validation, external login and HTTP endpoints remain future work.


## Phase 5.0 — 2026-11-10 (development branch)

### Added
- Tenant-isolated Content Requests storage for prepared drafts that need user photos, videos, details or permissions.
- Per-draft suggestions, required-item checklists, priority, content references and hold states.
- Transition to ready-for-review only after all requested references are supplied; never auto-publish.
- Nine regression tests for partial completion, cross-tenant isolation, postponement and validation.

### Test status and limitations
- Tests committed, execution not independently verified.
- Content reference presence is not yet proof of actual upload or permission; trusted backend validation remains required.
- No mobile UI, authenticated API, scheduling or publishing in this phase.


## Phase 4.9 — 2026-11-10 (development branch)

### Security and integrity
- Persisted editorial candidate SHA-256 digests and added migration for existing review queues.
- Rechecks reject modified source, summary, verification, and safety metadata; legacy undigested rows fail closed until re-intake.
- Capped server attestations at 24 hours and added expiry-limit test coverage.
- Corrected an intake test expectation for unverified creators held in review.

### Test status and limits
- Regression tests committed; execution not independently verified.
- No external verification worker, Android release, or publishing integration.


## Phase 4.8 — 2026-11-10 (development branch)

### Added
- Authenticated editorial intake facade that reads server-side creator attestations instead of client clearance flags.
- Business-role authorization, expired-attestation hold, and competitor re-screening safeguards.
- Ten intake regression tests.

### Test status
- Committed, not yet independently executed or confirmed by CI.

### Limitations
- No real external identity verification worker, public API, Android client or publishing integration.
- Legacy direct inbox entry points remain internal-only; production must not expose them.
- Publishing disabled.


## Product naming decision — 2026-11-10

- Adopted **BAM — Belenos Automatic Marketing** as the official product and future Android app name.
- Clarified that Belenos is the software brand, not an industry or customer limitation.
- Updated the development README while retaining the existing GitHub repository path and history.
- Working tagline: *Your marketing. On autopilot.* Trademark and app-store name availability have not been checked.
- No code, app package identifier, GitHub repository name, or production publishing settings changed.


## Product scope clarification — 2026-11-10

- Clarified that the platform is industry-agnostic and multi-tenant, intended for businesses beyond the initial pilots.
- Identified Belenos Creations and Busy B Cleaning Service as examples, not hard-coded tenants or target-market limits.
- Updated README product goals to use business-neutral language.
- Documentation-only change; publishing remains disabled.


## Phase 4.7 — 2026-11-10 (development branch)

### Added
- Expiring, business-scoped server attestation registry for creator identity and competitor screening.
- Editorial review facade now rejects client-supplied identity/competitor clearance and reads fresh server attestations.
- Eight new attestation tests and two new review-facade regression tests.

### Test status
- Test definitions committed; execution remains unverified.

### Known limitations
- Attestation creation is a trusted internal operation; external verification worker and authorization-gated API are not yet implemented.
- Recheck grants human-review eligibility only, never scheduling or publishing.
- No Android application or live publishing integration.


## Phase 4.6 — 2026-11-10 (development branch)

### Added
- Authenticated editorial review facade requiring an active owner or marketing-manager membership.
- Fresh creator/source/competitor recheck before human review, with no scheduling or publishing action.
- Ten role, revocation, cross-tenant and policy-change tests.

### Test status
- Code and tests committed; full test execution not verified. GitHub Actions push and pull-request triggers exist but successful runs have not been confirmed.

### Known limitations
- The facade accepts identity verification and competitor clearance from its caller: production must derive these solely from a trusted resolver, never mobile/client parameters.
- No authenticated HTTP endpoint, Android UI, scheduling authorization, or publishing integration yet.
- Publishing disabled.


## Phase 4.5 — 2026-11-10 (development branch)

### Added
- Fresh policy re-evaluation before a queued link can be considered for editorial review; blocked creators are removed.
- Business-neutral curation categories, including facility care and case studies.
- Guard against accidental whole-platform competitor blocks on common social domains.
- Eleven additional regression tests covering rechecks, commercial cleaning and shared social platforms.

### Test status
- Code and test definitions committed; full suite execution and GitHub CI status not yet verified.

### Known limitations
- Review check is not yet bound to an authenticated API, approval, scheduler or publication transaction.
- Trusted identity verification and competitor clearance remain external dependencies.
- Existing queue records are not automatically swept when policies change; review check must be called on use.
- No live discovery or publishing enabled.


## Phase 4.4 — 2026-11-10 (development branch)

### Added
- Tenant-specific editorial inbox for discovered third-party links.
- Combined recommendation gate applied before queuing; review required even for eligible sources.
- Duplicate-link handling and blocked-source re-screen removal.
- Nine new offline tests for review, isolation, duplicate and blocked content.

### Test status
- Code and tests committed; execution and CI status not verified.

### Known limitations
- Inbox reads do not automatically re-screen after policy changes; trusted production review must re-evaluate on every approval or scheduling action.
- Discovery ingestion is offline only; no external source crawler or platform API integration.
- No Android UI, authenticated production API, or publishing activation.


## Phase 4.3 — 2026-11-10 (development branch)

### Added
- Combined recommendation gate requiring both approved business-specific source and verified creator identity.
- Unknown/possible local competitors remain held, known competitors blocked.
- Ten integration tests for topic, tenant, source, creator and competitor controls.

### Test status
- New test definitions committed; execution not yet independently verified.

### Known limitations
- Trusted identity verification and competitor clearance are not implemented.
- The recommendation gate is not connected to ingestion, scheduled jobs, or publishing.
- No Android APK, authenticated public API, or live posting.
- Publishing remains disabled.


## Phase 4.2 — 2026-11-10 (development branch)

### Added
- Business-scoped verified creator identity policy keyed by platform and account ID.
- Explicit blocked, review and approved states, with unknown identities held.
- 12 additional identity policy regression tests.

### Test status
- Tests committed but not independently executed; remote GitHub Actions results still unverified.

### Known limitations
- Creator identity verification is not implemented; trusted external verification must supply it.
- Legacy URL/host-based curation is still separate; production must combine both checks before recommending content.
- Approved creator identity does not authorize publishing, reposting, or use of copyrighted media.
- Publishing remains disabled.


## Phase 4.1 — 2026-11-10 (development branch)

### Added
- Authenticated, read-only business switcher with per-business role resolution.
- Eight account-switching tests covering separate business access and deactivation.

### Test status
- Test definitions committed; GitHub workflow run not returned for latest commit, so execution remains unverified.

### Known limitations
- Login identity verification and Android business-switching UI are not implemented.
- Trusted server must derive creator screening outcomes; callers must not be allowed to mark competitors cleared.
- Competitor host blocklist is conservative and needs profile-level social account identifiers to avoid broad shared-domain blocks.
- Publishing disabled.


## Phase 4.0 — 2026-11-10 (development branch)

### Added
- General-purpose per-business industry/topic/source curation, independent across business tenants.
- Local competitor blocklist by business and conservative review for unknown or possible local competitors.
- Business-specific curation and competitor regression tests.

### Test status
- Tests committed; full suite and CI results not yet verified.

### Known limitations
- Competitor detection is not automated: trusted configuration and human screening are required. Domain blocking alone cannot identify all competitors, social profiles, syndicated content, or mirrors.
- Business profiles and source settings lack authenticated owner-facing API; no automatic sharing enabled.
- Publishing remains disabled.


## Phase 3.9 — 2026-11-10 (draft PR #1)

### Added
- Owner-authorized, one-use, expiring, revocable employee invitation tokens (hashes stored at rest).
- 12 invitation lifecycle tests; 98 tests defined across repository.
- Draft pull request #1 for code review and CI without merging to main.

### Test status
- GitHub Actions run not yet visible for the draft PR; new tests unverified.

### Known limitations
- Invitation redemption requires externally authenticated verified subject identity; no authentication provider implemented.
- Invitation delivery, rate limits, audit and transactional concurrency hardening remain.
- Production exposure of legacy workflow prohibited; publishing disabled.


## Phase 3.8 — 2026-11-10 (development branch)

### Added
- Native tenant-keyed post, approval and event tables in `tenant_content.py`.
- Session and current-role authorized `TenantApprovalService` for native tenant records.
- 12 new isolation and permission tests; 86 tests defined across repository.

### Test status
- Commits completed; GitHub combined status returned no checks. Tests not independently verified.

### Known limitations
- Legacy workflow remains separately available and must not be exposed as production API.
- Native storage is an independent development path, not yet a migration of legacy records.
- Trusted ingestion, classification and user authentication are not production-ready.
- No API, Android client, or live publishing; publishing disabled.


## Phase 3.7 — 2026-11-10 (development branch)

### Added
- Immutable tenant ownership registry for offline posts and discovered events.
- Fail-closed ownership checks before approval and event confirmation.
- Four ownership regression tests; prior approval tests updated to register ownership.

### Test status
- Changes committed; test execution and CI results not yet verified.

### Known limitations
- Ownership is a transitional side table rather than native tenant columns and tenant-filtered queries.
- Registration is trusted-server-only and must never accept unverified client ownership claims.
- Existing workflow functions can bypass the gateway; no production API exposure is safe yet.
- Publishing remains disabled.


## Phase 3.6 — 2026-11-10 (development branch)

### Added
- Offline approval gateway combining session validity and current membership authorization.
- Owner-only promotional/event approvals and revocations; manager routine approvals.
- 12 security-focused unit tests committed.

### Test status
- New tests committed; full suite execution and GitHub Actions status not yet verified.

### Known limitations
- Legacy posts and events are not tenant-scoped in the database: **do not expose gateway through an API** until tenant isolation is added to these records and queries.
- Session issuance still depends on an external authenticated identity provider that is not implemented.
- Legacy workflow functions remain callable internally without the gateway; production must restrict access through trusted services.
- Publishing remains disabled.


## Phase 3.5 — 2026-11-10 (development branch)

### Added
- Offline tenant-scoped account directory and one-time owner bootstrap.
- Owner-managed employee role assignment and deactivation.
- Authorization against current directory membership rather than stale role claims in sessions.
- 10 account-directory unit tests.

### Test status
- Changes committed to development branch; CI and local test results not yet verified.

### Known limitations
- No authenticated login, secure invitation workflow, API middleware, or Android client.
- Bootstrap must be restricted to trusted server setup in production.
- Production implementation must use transactional database operations and enforce last-owner safeguards.
- Publishing remains disabled.


## Phase 3.4 — 2026-11-10 (session prototype)

### Added
- SQLite-backed opaque session tokens with SHA-256 token hashes at rest.
- Server-side expiry, single-session revocation, and tenant-scoped user-wide revocation.
- 10 unit tests for issuance, expiry, revocation, and invalid inputs.

### Test status
- Tests committed; local execution and GitHub Actions results not yet verified.

### Known limitations
- No real login, identity provider, password handling, biometric implementation, API authorization middleware, or employee directory.
- Sessions currently capture a role at issuance; a production API must recheck current user/tenant membership and permissions on each request, or revoke sessions on role changes.
- SQLite prototype is not configured for production cloud hosting. Publishing remains disabled.


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


### 2026-11-12 — Inactive PostgreSQL operator preflight (PR candidate)
- Added metadata-only source integrity, unknown-table and pinned-schema drift checks for a future reviewed cutover, plus deterministic SHA-256 fingerprints for eight existing CI DDL preview stages.
- Added negative regression tests for schema drift, unsafe inputs, confidential data leakage and the non-authorizing nature of a passing source pin.
- No production migration executor, connection, customer export, rollback, publishing activation or new cost.


### 2026-11-12 — Disposable ciphertext durability rehearsal (PR candidate)
- Added atomic, no-overwrite and fsync-backed local ciphertext archive prototype reusing authenticated AES-256-GCM synthetic envelopes and a separately pinned ciphertext SHA-256.
- Added tests for durable roundtrip, wrong-key/modified bytes, duplicate names, untrusted directories, pathname injection and symlink/hardlink exposure.
- Preserved no-activation CI gate, no key persistence, no production PG dump, no offsite replication or retention execution.


### 2026-11-12 — Signed media revocation proof (PR candidate)
- Added independently keyed authenticated revocation chain for exact signed malware-scan and usage-rights claims; revision and removal require a matching independently pinned head.
- Added wrong-key, reordering, log truncation, replay, cross-tenant and rights-withdrawal regressions.
- No actual scan, legal proof review, hosted ledger, media state transition or publication is performed.


### 2026-11-12 — Staged media and revocation composition (PR candidate)
- Connected the read-only byte-bound private staged-media proof to independently signed revocation-chain validation, with final pending-record consistency check.
- Added tampered-media, wrong-tenant, changed-head, revoked-scan and withdrawn-rights regressions. No upload state mutation or live scanning was introduced.
