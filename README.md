## BAM for Android

BAM 0.5.0 uses the approved Belenos Automatic Marketing wordmark and adaptive
launcher icon. The screens follow Android's light or dark setting with the
navy, silver, gold and teal BAM palette.

BAM Personal runs directly on an ARM64 Android phone. The app downloads
a 1.6 GB Qwen model once over Wi-Fi and then writes drafts on the phone using
LiteRT-LM. No account, computer, or paid AI API is required for drafting.

1. Install the BAM APK and open the app.
2. Tap **Download offline AI**. Reopen BAM after the download to verify the model.
3. Tap **Generate test draft**, then turn on **Generate scheduled drafts**.
4. Review the captions in the inbox. Use **Edit caption** to make changes,
   then tap **Copy caption** to post manually.

Use **Campaign notes and skips** to choose a date, supply an upcoming topic
and confirmed details, or skip a slot already handled elsewhere. These
settings apply to drafts that are still pending. **Generate due drafts now**
checks today's missing slots even while automatic drafting is paused.
Existing captions and skipped slots are left out of that run.

BAM 0.6.0 asks the model for one short caption focused on a single subject.
Before saving a new generated draft, BAM removes common AI labels and wrapping
quotes and checks for generated operating times or immediate visit wording.
Opening reminders can invite a visit and get their hours from the app's
confirmed schedule. Review captions before posting to Facebook.

The 0.2.0 test APK installs separately as **BAM Personal** because the 0.1.0
GitHub build used an ephemeral debug signing key. The earlier app keeps its
drafts. The new app has its own inbox and requires its own model download.
Pause scheduling in the older app if you enable it in BAM Personal.

The app targets 10 AM Eastern for morning drafts and for preparing the
11:30 AM opening reminders on Thursday through Saturday. It targets 6:30 PM
Eastern on Monday, Wednesday, Friday and Saturday for evening drafts.
Android can defer background work while the phone is idle. Opening BAM
checks for drafts due that day, and opening reminders expire at noon.
The app uses the known holiday closures and requires reconfirmation of
regular hours after December 10, 2026.

### Check draft timing on your phone

In BAM Personal 0.3.0, **Today's draft timing** shows the Eastern target,
whether the slot is still due, and the save time and delay for each new draft.
Each draft also identifies the work that saved it: periodic background check,
app catch-up, manual catch-up, or test. Captions already in the inbox keep their
original text and display no inferred timing.

1. Download the model and generate a test draft. Read, edit and copy the caption.
2. Add a dated campaign topic and confirmed facts, then verify they appear in
   the next relevant caption. Test skipping one slot and use **Generate due
   drafts now** to check that existing captions and skipped slots are preserved.
3. Enable scheduling before an upcoming slot. Leave BAM using Home, let the
   phone idle, and reopen BAM after the target. Record the slot, save time and
   work source. A draft labeled **Periodic background check** whose save time
   precedes reopening is evidence of background delivery for that run.
4. Repeat for a morning and an evening slot before replacing the existing
   ChatGPT tasks. Facebook posting is manual.

The Android CI suite uses simulated Android 15 and synthetic captions to
exercise opening the inbox, editing and copying a caption, database upgrades,
and how retries handle a caption you already edited. The phone check above
measures real model inference and background timing on your device.

### Install the preview or sign a personal build

Starting with 0.4.0, the **BAM Preview** APK installs alongside 0.1.0 through
0.3.0. It has its own inbox, settings and one-time model download. Pause
automatic drafting in any older installation while testing the preview.
CI preview builds use temporary signing keys. Android may require a fresh
preview install for a subsequent preview signed with a different key.

The **BAM Personal** release build also has a new package ID. Sign it with a
key you keep and use that same key for later updates. The first install has
its own inbox and model download. Drafts from earlier apps remain accessible
in those apps. This build path requires a computer for signing once per APK.
The signed app generates drafts on the phone by itself.

Use JDK 21, Android SDK and Build Tools 35, and Gradle 8.13. Build both variants
with `gradle -p android :app:testDebugUnitTest :app:assembleDebug :app:assembleRelease`.
The output paths are `android/app/build/outputs/apk/debug/app-debug.apk` and
`android/app/build/outputs/apk/release/app-release-unsigned.apk`. For the
personal build, run these commands from the repository root. Create the key
once, outside the repository, and keep a private backup. The tools prompt
for passwords locally.

```sh
keytool -genkeypair -keystore "$HOME/bam-personal.p12" -storetype PKCS12 \
  -alias bam-personal -keyalg RSA -keysize 3072 -validity 10000

bam_build_tools="$ANDROID_HOME/build-tools/35.0.0"
bam_unsigned="android/app/build/outputs/apk/release/app-release-unsigned.apk"
"$bam_build_tools/apksigner" sign --ks "$HOME/bam-personal.p12" \
  --ks-key-alias bam-personal --out BAM-Personal.apk "$bam_unsigned"
"$bam_build_tools/apksigner" verify --verbose --print-certs BAM-Personal.apk
```

For each later version, reuse the existing key and run only the signing and
verification commands. Check that the signer certificate SHA-256 digest
matches the previous APK before installing the update.

The model is downloaded into app-specific storage and verified by SHA-256.
See the [model card](https://huggingface.co/litert-community/Qwen2.5-1.5B-Instruct)
and [LiteRT-LM documentation](https://developers.google.com/edge/litert-lm/android).
See [Android app signing](https://developer.android.com/studio/publish/app-signing)
for signing and key custody.

## BAM Scheduled Posts on a computer

BAM writes and saves Belenos Creations Facebook drafts on the personal
marketing schedule. The 10 AM run prepares the daily main post and, on
Thursday through Saturday, a separate 11:30 AM store-opening reminder when
hours are confirmed. Evening drafts run at 6:30 PM Monday, Wednesday,
Friday and Saturday. All times are Eastern. The inbox has a separate copy
button for each caption. Publishing stays manual.

### Run on your computer

1. [Download the BAM source](https://github.com/BelenosCreations/belenos-marketing-automation/archive/refs/heads/main.zip) and extract it.
2. Install [Python 3.11 or newer](https://www.python.org/downloads/) and [Ollama](https://ollama.com/download). Start Ollama and run `ollama pull gpt-oss:20b`. See the [local model setup and hardware guide](https://developers.openai.com/cookbook/articles/gpt-oss/run-locally-ollama).
3. In the extracted folder, run `python bam_scheduled_posts.py` and open [the draft inbox](http://127.0.0.1:8787/). If needed, use `python3` on macOS/Linux or `py` on Windows. If Python reports missing time-zone data, run `python -m pip install tzdata` using the same Python command.

Keep the app and Ollama running on the same awake computer. The browser tab
can be closed. Restarting catches up on today's due drafts, with opening
reminders expiring at noon. The app uses the local model with no OpenAI API
key or API charges. It binds only to the computer running it.

Drafts live under `~/.bam-scheduled-posts`. An optional `marketing.json`
file in that directory can supply confirmed hours and exceptions. For example:

```json
{
  "hours_confirmed_through": "2026-12-10",
  "closed_dates": ["2026-11-26"],
  "hours_overrides": {"2026-12-05": "1–5 PM"},
  "skip_slots": {"2026-11-16": ["morning"]},
  "extra_facts": {"2026-12-05": "Add confirmed campaign details here."}
}
```

The built-in holiday hold suppresses opening reminders December 11–18,
2026. After December 10, regular-hours reminders require an extended
confirmation date or a date-specific override. Closed dates take
precedence over hours. A supplied `skip_slots` map replaces the built-in
skip map. Review the generated caption before copying it to Facebook.

Personal use comes first. Shared access and multiuser collaboration remain
the long-term product goal. See the [product plan](PRODUCT_PLAN.md).

## Offline AI request recovery design

The [AI request recovery design](MIGRATION_AI_REQUEST_RECOVERY.md) traces
claims, reservations, draft writes and completion in the existing stores.
Disposable tests exercise draft and receipt rollback and PostgreSQL freeze
lock ordering. Requests with uncertain provider outcomes remain held. The
design also specifies independent confirmation of the operator's latest
transition before reopening writes after a restore.
The disposable PostgreSQL suite exercises receipt-based finalization,
targeted revision rollback, and closed admission after a stale restore.
The recovery design includes a source-level review of AI store migration
fields and the evidence needed to verify ownership and legacy values.
Synthetic SQLite-to-PostgreSQL tests preserve memory text, historical request
state and unpriced quota counts. They also expose a preview constraint that
rejects attachments linked only to an AI draft. The attachment parent and
subject ownership model needs review before migration.
Additional disposable tests order request recovery against freeze and require
separately signed transition and confirmation evidence before resuming.
The disposable attachment model tests scoped parents and holds ambiguous
legacy links. The authority rehearsal adds expiry, revocation, rollback
and separate writer and operator grants.
The offline attachment rehearsal checks signed parent and subject binding,
revocation across claim versions, and retry after an interrupted discard.
A restored SQLite fixture ties the revocation head to its claim index and
tests typed review visibility after colliding IDs or issuer key rotation.
Disposable PostgreSQL tests exercise both lock orders for confirmation
racing a restore. A signed checkpoint now binds the claim index, issuer-key
catalog and encrypted synthetic replica. The authority rehearsal tests
witness rotation and recovery above an independently supplied generation.
Disposable recovery now stages the replica before a separately signed
completion and binds review admission to the promoted generation. The
recovery receipt rehearsal keeps review and writes closed until the
promoted generation matches an independently retained receipt. A signed
fixture journal also checks restart, rollback and superseded receipts.
A separate signed publication records the latest fixture head. Disposable
PostgreSQL tests order publication against acknowledgement and write admission.

## Alternate writer inventory and offline recovery rehearsal

The [alternate writer inventory](MIGRATION_ALTERNATE_WRITER_INVENTORY.md)
covers checked-in preview and CLI paths, provider and operator interfaces,
and recovery tools. A disposable SQLite rehearsal checks whether a saved
synthetic draft can be reconciled after freeze without writing it twice.

## Offline editorial and AI write review

The offline review maps preference, calendar, feedback, AI fact, memory and
draft edits to their SQLite writes. It also traces the separate, disabled AI
generation flow across quota reservation, draft storage and request completion.
[Editorial and AI write review](MIGRATION_WSGI_EDITORIAL_WRITE_REVIEW.md)

## Offline identity and local draft write review

The offline review now traces local product and service drafts, authentication,
session switching, membership changes and invitation writes to SQLite. It
identifies commits that can succeed before a later step fails and records
unresolved Google verifier and invitation delivery implementations.
[Identity write review](MIGRATION_WSGI_IDENTITY_WRITE_REVIEW.md)

## Offline held-draft and media write review

The CI-only review locates the SQLite transaction contexts for draft creation,
hold, revision, priority and attachment preflight. It also records where local
media receipt writes files and where discard unlinks files before deleting
metadata. The report withholds mappings on source drift and keeps indirect or
unreviewed routes visible. Deployed writer coverage and an enforced generation
fence remain prerequisites for cutover. [Write boundary review](MIGRATION_WSGI_WRITE_BOUNDARY_REVIEW.md)

PR #109 made [DEVELOPMENT_CONTINUITY.md](DEVELOPMENT_CONTINUITY.md) the canonical
handoff. Use its top section for the next offline work and verify the current
GitHub checkpoint before resuming.

## Candidate #108 — CI-only WSGI service-delegation review (2026-11-13)

PR #107 independently verified: exact-head Actions #43438915110 PASSED; merged-main SHA 7c557ed43f7696982e5e2bcf8130e807707636c9 Actions #43439178092 PASSED. Main/development non-force synchronized, identical 0/0, no open PRs. Candidate #108 adds a second source-only inspection hop from offline WSGI handlers into direct service-method call names and constructor dependency hints, bound to source digests. See MIGRATION_WSGI_SERVICE_REVIEW.md. No actual SQL commit, worker fencing, tenant authorization, hosted readiness, customer migration or paid/publishing activation. Full CI for #108 pending; additional cost $0.

## Candidate #107 — CI-only WSGI handler-source binding review (2026-11-13)

Independently verified starting checkpoint #106: ee7c385303efa150a0c38fea02b71951521ad85c, merged-main Actions #43436668950 PASSED, development/main identical 0/0, no open PRs. Candidate #107 adds AST-only WSGI gateway constructor-to-handler binding hints, route/method literal clues and adversarial regressions. See MIGRATION_WSGI_BINDING_REVIEW.md. No deployed writer coverage, authenticated shared generation authority, production database changes or Beta readiness. Exact-head and merged-main CI pending. Additional cost $0, all production integrations disabled.

## Verified #105; candidate #106 dispatch review checkpoint (2026-11-13)

PR #105 independently verified: final exact-head Actions #43435447478 PASSED at 5614680051aa569d39c6b844c644df70959d3d5b, merged-main e8f5dd509463c83235724920e1beb23fb73fede0 Actions #43435718147 PASSED. Development non-force fast-forward synchronized and independently compared identical, zero ahead/behind; no open PRs. A first source inspection of BAMOfflineGateway.__call__ found bound WSGI handler dispatch for authentication, team/invitations, content edits, AI facts, posting preferences, media staging and calendar/review routes. Basic static direct-call traces cannot resolve all of those instance attributes; real deployment coverage is NOT proven. Candidate #106 documents this gap and the next independent review tasks. PostgreSQL cutover, producer-wide fencing, offsite recovery, genuine ClamAV/rights and hosted Beta security remain blocked; $0 additional cost and integrations disabled. Candidate #106 must pass exact-head and merged-main CI before verification.

## Candidate PR #105 — CI-only ingress-to-writer path review (2026-11-13)

After independently verified #104 main 0cd22728bf63966252d7893dde526f44c986105f (Actions #43430594571 PASSED; main/development identical 0/0; no open PRs), proposed #105 adds read-only, CI-gated direct-call hypotheses from Python/WSGI and candidate job/callback functions to potential write sites. Unresolved calls and unmapped writes remain explicit; no runtime writer coverage or production fence is proven. See MIGRATION_DISPATCH_REVIEW.md. Exact-head/merged-main CI pending. $0 additional cost, no deployment, migration, publication or paid services.

## Verified #102–#103 engineering milestones; candidate #104 recovery documentation (November 13, 2026)

**Independently verified:** [PR #102](https://github.com/BelenosCreations/belenos-marketing-automation/pull/102) exact-head Actions [#43428652129](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43428652129) PASSED and merged-main Actions [#43428902180](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43428902180) PASSED; merged-main SHA `5ccff62cd27ffb2230026a8b008478a788e8c83f`. [PR #103](https://github.com/BelenosCreations/belenos-marketing-automation/pull/103) exact-head Actions [#43429490616](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43429490616) PASSED and merged-main Actions [#43429752709](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43429752709) PASSED; merged-main SHA `099b79e5a92035af812d08ed6f612405fffac5cb`. Main/development independently compared identical, 0 ahead/behind, after non-force fast-forward; no open PRs before documentation candidate #104.

#102 adds CI-only read-only AST candidate writer/WSGI source inventory and deterministic review digest. #103 adds an automatically destroyed, private SQLite generation/epoch guard rehearsal testing synthetic transaction-bound writer admission, freeze/resume, stale worker rejection, replay, uncommitted rollback and lock order. **Neither fences real BAM services or proves independent persistent authority.** No PostgreSQL/customer data migration, hosted cutover, externally approved rollback or publishing. Remaining blockers: full real writer mapping, independently controlled operator and key/head custody, approved null/default/JSON/constraint/identity/tenant mappings, actual off-host encrypted backup and measured restore, genuine ClamAV publisher signatures and isolated authenticated scan jobs, human rights/revocation, hosted auth/session/CSRF/proxy/multitenant/abuse validation, explicit Beta authorization. Added cost $0; Render/Neon/paid AI/social/EdgePilot remain inactive. **PR #104 is documentation-only and is not verified until its own exact-head and merged-main Actions pass.**

## Candidate PR #103 — disposable transaction-bound generation guard, not a BAM-wide fence

PR #102 was independently verified: exact-head Actions #43428652129 PASSED; merged-main SHA `5ccff62cd27ffb2230026a8b008478a788e8c83f` and Actions #43428902180 PASSED. Main/development were non-force synchronized at 0 ahead/behind. Proposed #103 adds an isolated CI-only 0600 SQLite generation authority and canary write gate, where stale generations are rejected inside the write transaction; tests cover freeze, resume, crashes, duplicates and competing locks. See [MIGRATION_EPOCH_FENCE_REHEARSAL.md](MIGRATION_EPOCH_FENCE_REHEARSAL.md). This is **not connected to a BAM service, hosted PostgreSQL or any real worker**. Independent key/head custody, operator approval, real distributed fencing, restore/rollback, migration and Beta authorization are still missing. Exact-head/merged-main CI for #103 pending. $0 incremental spend and all external integrations remain disabled.

## Candidate PR #102 — static Python/WSGI migration writer-surface inventory (CI only)

After the independently verified #101 merged-main checkpoint `9a19829997ef09c5a8f163c5c872fb042501b3e9` (Actions #43380395873 PASSED), this proposed milestone adds a **read-only AST source inventory** of BAM Python write/ingress candidates, deterministic digest, negative tests, and an independent review plan. It reads Python files only; it never imports a module, opens PostgreSQL/customer storage, fences any real writer, authenticates an operator, backs up data or enables publishing. Discoveries are incomplete: indirect calls, distributed workers, provider retries, runtime SQL, non-Python code and actual hosted entrypoints require operator review. See [MIGRATION_WRITER_SURFACE_REVIEW.md](MIGRATION_WRITER_SURFACE_REVIEW.md). **No production readiness claim; no code path is activated.** $0 incremental cost; all Render, Neon, paid AI, external publishing and EdgePilot restrictions remain. Await exact-head and merged-main CI; do not mark candidate #102 verified yet.

## Verified #99–#100 offline replay and ClamAV-header milestones; candidate #101 documentation checkpoint

**Independently verified November 13, 2026:** PR [#99](https://github.com/BelenosCreations/belenos-marketing-automation/pull/99) exact-head Actions [#43378330269](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43378330269) PASSED, merged as `5398dbcb3772bb8a291fb1c5201413a57668d771`, independent merged-main Actions [#43378572835](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43378572835) PASSED; development fast-forward synchronized without force, 0/0 divergence. PR [#100](https://github.com/BelenosCreations/belenos-marketing-automation/pull/100) initially failed Actions #43379118389 on an HH:MM CVD parser delimiter regression, corrected on the same PR and verified exact-head Actions [#43379526308](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43379526308) PASSED; merged as `75824ebc75dda5a8a06969773b899a614c99d1b5`, independent merged-main Actions [#43379830054](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43379830054) PASSED. Development then non-force fast-forward synchronized and independently compared to main identical, 0 ahead/behind.

#99 adds private 0600 disposable SQLite HMAC operation-ledger test, reconnect persistence, verified caller-pin replay/epoch protection, terminal abort and tamper negative tests. All files vanish after CI; signing key and independent-head custody are unproven, and no BAM-wide API/worker fence or PG migrations are implemented. #100 adds read-only pinned 512-byte daily.cvd header metadata age and digest checks and adversarial parser/inode tests. An operator-supplied hash and reported freshness do **not** authenticate ClamAV's database signature, provenance, engine execution, isolation or media rights. No genuine scan, media approvals, production services or customer data migration. Remaining blockers: independently reviewed null/default/JSON/tenant/identity transformations, authenticated operator custody/approval, real globally respected writer fencing and replay/rollback, actual independently custodied encrypted offsite backup and measured recovery, authentic ClamAV signature/worker and human rights/revocation evidence, hostile hosted IAM/session/CSRF/media/proxy/tenant/abuse testing and explicit Beta authorization. $0 added spend; Render/Neon/paid AI/social publishing/EdgePilot remain disabled. **This PR #101 is documentation-only and must independently pass its own PR and merged-main Actions before becoming the newest verified checkpoint.**

## Candidate PR #100 — ClamAV CVD header freshness is not signature authenticity

PR #100 adds an **inactive CI-only** read-only `daily.cvd` header/digest freshness validator, with private inode/whole-file hash checks, bounded claimed build age, disagreement/future/stale detection and adversarial fake-header tests. It uses the ClamAV-documented 512-byte CVD header format (https://docs.clamav.net/manual/Signatures.html) but **does not validate the CVD publisher's digital signature**: a forged header with a newly chosen caller pin can appear fresh. The binary was not executed, no genuine signature corpus was loaded, no sandbox/tenant job or usage-rights reviewer was authenticated, and no scan/approval was issued. Do not trust CI fabricated headers as malware protection; production remains blocked and all Render/Neon/paid AI/social/EdgePilot integrations are disabled; incremental cost $0. Require exact-head and merged-main CI before marking verified.

## Candidate PR #99 — locally durable synthetic migration replay rehearsal

CI-only disposable HMAC-authenticated local SQLite operation ledger (candidate PR #99): uses a generated 0700 temporary directory and 0600 SQLite fixture, caller-supplied synthetic HMAC key and *separately supplied* latest-head pin, strictly ordered signed event receipts, persisted duplicate-operation and epoch checks after connection reopen, stage 08 refusal, terminal-abort/no-promotion semantics, and tamper/private-file negative tests. It records no customer data and never connects to PostgreSQL. The trusted latest-head/key are only caller claims (not independent custody); the fixture is deleted afterward and does NOT supply a production durable replay service, application-wide writer fence, external keys, authenticated operator, PG cutover/rollback, offsite backup, real ClamAV/rights review or hosted Beta. All integrations disabled; $0 new costs. Candidate requires exact-head and merged-main GitHub Actions before verified.

## Independently verified inactive migration milestones — PRs #96–#97 (November 13, 2026)

PR [#96](https://github.com/BelenosCreations/belenos-marketing-automation/pull/96) passed exact-head Actions [#43370721912](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43370721912) and merged-main Actions [#43370961873](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43370961873). The no-content, two-parent, **non-force** main/development reconciliation at `d967dccfd6059a0b60a39e8e393cc550fff670c9` passed final merged-main Actions [#43371191220](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43371191220). PR [#97](https://github.com/BelenosCreations/belenos-marketing-automation/pull/97) passed exact-head Actions [#43371588657](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43371588657), merged as `b21f132009402f00f54a59df9843224ecea82c0a`, and passed separately on merged-main [#43371792518](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43371792518). Development was then non-force fast-forwarded, and main/dev independently compared **identical, 0 ahead/behind**.

#96 adds a CI-gated unique SQLite shared-memory v1 transaction-protocol rehearsal: ordered 01–07 receipts, synthetic same-fixture operation replay/epoch/fence rejection, forbidden stage 08, and rollback/abandoned-owner canaries. #97 validates actual proposed migration intent chain and pinned source/plan/mapping/PG-preview/semantic fingerprint signals *before* that rehearsal, with hostile/tamper/privacy tests. **No migration runner, customer row access/copy, accepted JSON/default/nullability/identity/tenant transformations, independent operator authority/head custody, durable replay protection, global application writer fence, PostgreSQL cutover/restore or production DR was implemented.** Genuine ClamAV provenance/isolation, human rights/revocation review, hostile hosted auth/session/CSRF/proxy/media/tenant evidence and explicit Beta approval remain blockers. All Render/Neon/AI/provider/social/EdgePilot production integrations disabled; $0 additional spend. This documentation checkpoint is candidate-only until its own PR exact-head and merged-main CI complete.

## Candidate PR #97 — bind disposable protocol to independently pinned intent and semantic review

After verified PR #96 (exact-head Actions **#43370721912 PASSED**, merged-main Actions **#43370961873 PASSED**, non-force two-parent branch-history synchronization `d967dccfd6059a0b60a39e8e393cc550fff670c9`, final main Actions **#43371191220 PASSED**, branches identical 0/0), the CI-only `neon_disposable_protocol_binding.py` now validates an actual *unexecuted* stage 01–07 journal and its caller-held head, pinned source/plan/mapping fingerprints, and a pinned PostgreSQL preview/column semantics review *before* running PR #96's synthetic-only SQLite transaction rehearsal. Hostile tests reject tamper, replay/missing stages, drift and potential private-row disclosure. These hashes do **not** prove real independent custody, human approvals, accepted JSON/default/tenant transforms, customer copy, durable cross-process operation replay defense, global writer fencing, PostgreSQL cutover/rollback, offsite recovery, genuine ClamAV/rights review, hosted Beta or publishing. CI gate required; no live providers or added spend. Candidate is not verified until exact-head and post-merge main Actions pass.

## Candidate PR #96 — CI-only versioned migration transaction protocol (NOT executable PostgreSQL migration)

A disabled-by-default `neon_disposable_versioned_protocol.py` now rehearses v1 stages 01–07 using *only* two connections to a unique synthetic SQLite shared-memory database. It atomically records step receipts, rejects duplicate operation IDs within that single disposable fixture, stale epochs/fence tokens/intent-head claims, step skipping/replay and stage 08; it verifies an uncommitted synthetic payload is discarded on rollback or abandoned connection. `test_neon_disposable_versioned_protocol.py` adds negative/replay/tamper coverage. The caller-supplied journal-head digest is **only syntax-checked**, not independently authenticated or cross-validated with PR #90 journal. There is no persistent operation authority, genuine operator signoff, BAM-wide writer fencing, PostgreSQL transaction, approved column transform, offsite backup/restore, real rights/scanner evidence, hosted private Beta, production cutover or publishing. All services/providers inactive, $0 extra cost. Verify exact-head PR Actions, separately verify merged-main Actions, then non-force synchronize branches before marking this milestone complete.

## Latest independently verified engineering milestones: PR #93–#94

**Verified November 12–13, 2026:** PR #93 merged as `2b3afbf69519feccfd62d3479967d5addcf392a3` after exact-head Actions **#43368157960 PASSED** and independently successful merged-main Actions **#43368340201**. PR #94 merged as `bc9a0ba046a0ec5ae43d6ec95c14f853eae58e27` after exact-head Actions **#43368737129 PASSED** and independently successful merged-main Actions **#43368931927**. At both checkpoints development was fast-forward synchronized without force and independently compared to main as identical, 0 commits ahead/behind.

Both features remain CI-only synthetic/inactive research: #93 parses schema *metadata* to flag column nullability, default-presence, JSON-text, tenant/FK/constraint and identity review; independent hashes do not approve transforms, eliminate SQLite PK ambiguity or validate customer data. #94 checks signed *manifest metadata* for candidate incident planning; cannot prove an archive survives host loss, independent key/head custody, offsite redundancy, measured RPO/RTO, actual restored plaintext or production disaster recovery. Remaining blockers: independently reviewed real mappings/defaults/JSON/tenant ownership, disabled transactional PostgreSQL migration runner and full-application write fence with replay prevention/rollback, independently controlled offsite encrypted backups/keys/heads and measured restore tests, genuine isolated ClamAV binary/signature provenance plus human rights/revocation authority, hostile hosted authentication/session/CSRF/media/proxy/tenant tests and explicit Beta release authorization. No real customer migration, Render, Neon, external publishing, paid AI or EdgePilot activation. All production integrations remain disabled; **$0 additional costs**.

## Candidate PR #94: offline signed-manifest disaster scenario planning

A new **CI-only, non-restoring** `bam_offline_disaster_scenarios.py` combines HMAC-verified recovery manifests with an independently supplied latest-head pin, bounded incident time, retention age and caller-claimed encryption key IDs to select **unverified metadata candidates** for archive loss, local directory loss, whole-host loss and key-loss scenarios. It never opens archives or transfers/decrypts files; it cannot prove ciphertext is actually present, offsite failure-domain isolation, independent key or head custody, measured RPO/RTO, successful restore, or customer backups. Synthetic manifest issue time is **not** an authoritative snapshot time. Negative tests include tamper/replay, stale age, expired points, key rotation, host loss and inactive use. This is a proposed milestone pending exact-head and merged-main CI. Hosted services and production integrations inactive, incremental cost $0.

## Candidate offline migration semantic review (PR #93)

The CI-only `neon_disposable_column_semantics.py` now enumerates independently fingerprintable, conservatively parsed target/source nullability, default-presence, JSON-text, tenant/reference, constraint and identity-reseed review signals for 46 PostgreSQL preview tables. It reads schema metadata only; no raw default SQL expressions, customer rows, PostgreSQL connections, writes, backups, permissions, approvals, or migration execution. Matching independent source/mapping/preview/semantics SHA-256 pins still **never** approve a mapping. Private Beta and production cutover remain blocked; all integrations inactive, $0 additional costs. This is a proposed milestone pending exact-head and merged-main CI.

# BAM — Belenos Automatic Marketing

**Independently verified offline recovery checkpoint — November 12, 2026 (PRs #90–#91):** PR [#90](https://github.com/BelenosCreations/belenos-marketing-automation/pull/90) passed exact-head Actions [#43365704852](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43365704852), merged as `c68f33c1b1256aaacf3e2e6b77ec98845291c49c`, and passed independent merged-main Actions [#43365912019](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43365912019). PR [#91](https://github.com/BelenosCreations/belenos-marketing-automation/pull/91) passed exact-head Actions [#43366276568](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43366276568), merged as `e547e68aecd6a39cfcc16db71b7af4611e2b81a6`, and passed independent merged-main Actions [#43366443537](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43366443537). Both `main` and `development/phase-3-5-account-directory` were independently compared identical, zero ahead/behind, following non-force fast-forward. PR #90 adds **only CI-only, unexecuted hash-chained operator intent stages** 01–07 with pinned schema/plan/mapping and head drift detection; hashes do not authenticate approval, stage 08 is disallowed and no PostgreSQL, customer-data or rollback action occurs. PR #91 performs **only read-only same-host synthetic ciphertext inventory** against HMAC-signed manifests and independent head pins, classifying expiration without deletion; it does not establish offsite redundancy, escrow, external head custody, authorized retention action or actual customer recovery. Real column/default/JSON/constraint/tenant transformations, application-wide write fencing, versioned migration execution, independent backups/keys, authentic ClamAV signatures/isolation, human usage-rights adjudication and secure hosted private Beta ingress/session/CSRF controls remain blocked. All Render/Neon/paid AI/social publishing/EdgePilot integrations remain disabled. Additional spend **$0**.

**Candidate PR #91 — read-only CI ciphertext retention inventory:** Inspect existing private, same-host synthetic AES-GCM archive files against independently pinned HMAC-signed recovery manifests. Reject missing/extra names, symlink/hardlink/public inodes, digest mismatch and altered signer/head; report expired names for manual review only. No data is decrypted, copied, deleted or promoted; no offsite recovery, independent head custody, externally trusted retention enforcement or production backup is claimed. $0 extra cost and all production integrations disabled.

**Candidate PR #90 — CI-only pinned migration intent journal (not execution):** Adds a hash-chained, schema/plan/mapping-bound sequence for proposed migration stages 01–07, with independent head comparison, strict ordering, replay/tamper/promotion rejection and adversarial fixture tests. SHA-256 chaining is not a signature or independently authenticated approval. No PostgreSQL connection, SQL runner, BAM-wide write fence, actual rollback, customer rows, live services or promotion occurs. Stage 08 remains impossible. All production transformations, signed operator authority, offsite recovery and Beta gates remain blocked; incremental spending $0.

**Latest independently verified BAM functional checkpoint — November 12, 2026:** PRs [#86](https://github.com/BelenosCreations/belenos-marketing-automation/pull/86), [#87](https://github.com/BelenosCreations/belenos-marketing-automation/pull/87) and [#88](https://github.com/BelenosCreations/belenos-marketing-automation/pull/88) all merged, with separately successful exact-head and merged-main GitHub Actions. #86: [43363216197](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363216197) / [43363520290](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363520290), merged main `af5154b94573a01bd4c4e2fc08184149a2b1ec09`; #87: [43363803609](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363803609) / [43363985496](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363985496), merged main `177ecd90728e96a7d6c604bb4ba4f1731039e023`; #88: [43364238789](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43364238789) / [43364411439](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43364411439), merged main `d0b3255597349fd864842625e7dc0a5f6def55df`. Both main and development were independently compared identical, zero commits ahead/behind, after a non-force fast-forward.

**Verified offline scope, NOT production release:** #86 checks exact source/target synthetic values, integer ranges, finite floating-point/text/binary assumptions and independently pinned schema/mapping fingerprints without querying source rows or migrating data. #87 prepares a dormant ClamAV subprocess interface with external executable/CVD hashes, safe private file reinspection and negative mocked-CLI tests; no genuine engine/signatures were invoked in CI, no trusted worker isolation or rights adjudication is proven, and no scan claim/status approval is issued. #88 validates two-connection **in-memory synthetic SQLite** lock and rollback behavior only, not a BAM-wide production write fence. Real customer data transformation, transactional PostgreSQL runner, application rollback, authoritative offsite AES-GCM backup/head/key custody, independently authenticated scanner/rights reviewers, hosted session/tenant/CSRF/ingress hardening and publishing authorization remain blocked. No Render, Neon, paid APIs, social publishing or EdgePilot activation. Incremental spending: **$0**.

## Verified recovery checkpoint after PRs #86–#88

Latest independently verified functional main: `d0b3255597349fd864842625e7dc0a5f6def55df`; last verified merged-main Actions **43364411439** succeeded. PR #86 exact/main Actions **43363216197 / 43363520290**, PR #87 **43363803609 / 43363985496**, PR #88 **43364238789 / 43364411439** all succeeded. Main and development were synchronized without force and independently verified zero ahead/behind. No pending functional PR at this point; PR #89 is a documentation-only recovery checkpoint candidate. **Production is still inactive offline Alpha, not approved private Beta.** Distinguish: a synthetic conversion canary does not approve customer values; a mocked ClamAV CLI response does not prove real malware scanning or legitimate usage rights; a shared-memory SQLite lock does not fence BAM web workers or production PostgreSQL; same-host encrypted ciphertext is not offsite customer backup. Remaining gates: independently reviewed column/default/tenant transforms, versioned atomic migration/rollback and operator wide-area write fencing, externally controlled offsite backup/keys/heads, independently attested real ClamAV signatures and isolated worker, human rights-review and tenant-scoped revocation authority, hardened real sessions/CSRF/proxy/abuse tests, explicit operator authorization. Keep $0 added costs and all Render/Neon/paid providers/social/EdgePilot services disabled.


**Verified CI-only PR #88 — CI-only SQLite writer-fence/rollback rehearsal:** Two independently opened connections to a unique memory-only synthetic SQLite database demonstrate that a competing writer cannot begin while `BEGIN IMMEDIATE` is held and that rollback or abandoned connection release removes uncommitted canaries before a new writer commits. No customer database URI/path is accepted or opened, no actual BAM workers are fenced, no hosted PostgreSQL transaction, and no executable production cutover/rollback. This is an engine-semantics canary only; $0 additional costs.


**Verified CI-only PR #87 — inactive local ClamAV command boundary:** Adds standalone CLI execution plumbing for a separately installed `clamscan` with externally supplied exact binary/signature-file SHA-256 pins, private staged-byte hash/inode/permission checks, bounded subprocess with no shell/proxy and post-scan reinspection. The signed-claim system is deliberately NOT connected: no database status mutation, rights approval, or publication. CI uses mocked ClamAV responses, not a real scanner or known-good signed signatures. Execution is only permitted with the disposable CI environment gate. Independently establishing actual engine/sig origin, update freshness, worker sandbox, tenant binding, reviewer authority and durable audit remains required before real scanning approval or Beta. Costs $0.


**Verified CI-only PR #86 — CI-only typed-value acceptance:** A strict, operator-pin-bound synthetic cell validator for the already proposed SQLite-to-PostgreSQL types checks exact TEXT/UTF-8 without NUL, integer widths/booleans, finite DOUBLE PRECISION, exact bounded BLOB/BYTEA and NULL rejection. Only keyed schema identifiers and a synthetic digest are returned; no source rows are read, no SQL generated, and no data is migrated or approved. Every target constraint/default, tenant identity and customer-value mapping still requires independent review. No production cutover, costs or integrations.


## Verified post-merge recovery checkpoint after PRs #83–#84

Main SHA `10e18ce0e5554fd9dab80048b9ef002bf5e58654`; both branches identical, no forced update. PR #83 exact/main Actions 43357261226/43357506877 succeeded, PR #84 43357908998/43358111378 succeeded. All features remain offline Alpha proofs. Next major branch: independently audited per-column value transforms and a disabled transactional operator protocol; offsite encrypted replicas and external key/head authority; verifiable isolated ClamAV/signature provenance and human rights review; tenant-scoped evidence/media authorization and hostile private Beta session/CSRF/ingress tests. Obtain explicit authorization before connecting or spending. No genuine malware scan, offsite production backup, live cutover or publisher exists.


**Verified offline PRs #83–#84:** Source-to-target column/type review merged as `8fe6eedf41f6576fd1d44e2960727e2c6dcb1775` after exact-head Actions [43357261226](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357261226) and merged-main [43357506877](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357506877) passed, with both branches independently confirmed identical. All type/value transforms still unapproved. **Verified PR #84:** ciphertext-only no-overwrite relocation from one owner-only local directory to a different owner-only local directory, followed by a separate authenticated recovery after simulated source loss. No offsite storage, key escrow, retention deletion, actual customer backup, hosting or publication. Cost $0.


**Candidate next milestone (#83; verification pending):** Adds a read-only SQLite-to-PostgreSQL target-column/type comparison proposal for all 46 reviewed target tables. Exact names, types, INTEGER/SMALLINT/BIGINT range concerns, BLOB/BYTEA adaptations and generated identity-sequence reseeding are inventoried with independently pinnable mapping SHA. All value/constraint/tenant reviews remain explicitly unapproved; no customer rows are read, no transactional migration, backup, writer fence or cutover is enabled. All services inactive; additional cost $0.


**Latest independently verified BAM engineering checkpoint — November 12, 2026:** PR [#83](https://github.com/BelenosCreations/belenos-marketing-automation/pull/83) and PR [#84](https://github.com/BelenosCreations/belenos-marketing-automation/pull/84) both merged after exact-head and independent merged-main CI. #83: [Actions 43357261226](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357261226) and [43357506877](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357506877); #84: [Actions 43357908998](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357908998) and [43358111378](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43358111378). Latest independently verified merged `main` commit `10e18ce0e5554fd9dab80048b9ef002bf5e58654`. Development fast-forwarded without force and independently compared identical, zero ahead/behind.

**Verified engineering scope only:** #83 adds deterministically pinnable SQLite-to-PostgreSQL source/target column/type review proposals for 46 preview tables, with explicit value/default/tenant/identity review still outstanding and customer migration blocked. #84 adds independently signed synthetic ciphertext relocation between separate private *same-host* directories and an AES-256-GCM restore after original local loss. Neither proves real offsite backup, external key/head custody, retention, production migration, customer restore, actual ClamAV scanning or human rights review. Hosted sessions, private Beta security and trusted media workers remain incomplete. No Render, Neon, paid API, social publishing or EdgePilot integration was activated. **Additional spending: $0.** Passing CI is not production readiness.

**Next engineering gates:** Complete independently reviewed source-to-target column/value transforms and a disabled-by-default production-safe transaction/cutover runner; obtain external backup key/head custody and provable retained offsite recovery; implement authentic independently evidenced ClamAV-class scan worker plus human rights adjudication with tenant-scoped immutable audit; perform hostile production-auth/session/proxy tests before any private Beta. No deployment activation is authorized.


**Verified CI-only PR #81 (durable offline media-revocation audit):** An append-only private 0700 directory of canonical 0600 HMAC-linked revocation events uses no-replace atomics, fsync and full independent-head revalidation. Missing, altered, replayed, linked or public-permission events fail closed. The authoritative latest-head pin, per-tenant key custody, verified scanner output, rights decision, production logs and media state transitions remain absent. No new services, costs or publishing.


**Verified CI-only PR #80 (CI-only signed recovery manifest):** A bounded HMAC-authenticated, hash-chained manifest binds existing local ciphertext receipts to operator-provided key IDs, retention windows and a separately pinned latest head. Independently supplied signer/encryption keys can be rotated across synthetic archives; actual disk bytes and AES-GCM authentication are rechecked on restore. There is no persisted manifest/head authority, off-host copy, deletion, escrow, production data, recovery SLA or production approval. No new service or cost.


**Verified CI-only PR #79 (inactive migration planning):** New read-only source-column / reviewed target-table inventory, 8-step operator execution checklist and two separately supplied drift pins. It neither maps customer rows nor executes PostgreSQL DDL, maintenance/write-fencing, recovery or publishing. The existing 46-table preview is not a production migration.


**Earlier verified engineering checkpoint — November 12, 2026:** PRs [#70](https://github.com/BelenosCreations/belenos-marketing-automation/pull/70)–[#73](https://github.com/BelenosCreations/belenos-marketing-automation/pull/73) were merged and tested on exact PR heads and separately on merged `main`. Current synchronized `main` and `development/phase-3-5-account-directory` SHA: `7f4248940a84ad40d097c4541d11eba49b3f5b4a`; [latest merged-main Actions #43347901980](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43347901980) succeeded. PR #70 introduced CI-only AES-256-GCM/HKDF recovery envelopes; #71 required actual privately staged image bytes to match offline dual-signed claims; #72 exercised encrypted in-memory roundtrips for all 47 disposable PostgreSQL restore objects; #73 added loopback/proxy/ambiguous-framing protections for standalone local authentication and media receipt. Earlier headings marked "candidate" record now-completed proposals, not unmerged functional work. None of these changes creates durable/offsite backup, production SQLite→PostgreSQL migration, real malware scanner, independent rights adjudication, evidence audit/revocation, an Internet-ready Beta gateway, or executable publishing. All hosted Neon/Render, EdgePilot resources, paid AI and external publishing remain inactive. Additional spending authorization is **$0**.

**Candidate PR #73 — private Beta ingress safeguards for offline adapters:** Explicitly apply the existing loopback-only network/host gate to standalone local authentication and private image-receipt WSGI transports. Reject untrusted proxy/forwarded/original-URI metadata, ambiguous transfer framing and method overrides before reading secrets or media. Dedicated production reverse-proxy trust, rate limiting, TLS operations and Beta review remain unimplemented; this change is not authorization to expose these local adapters publicly.

**Candidate PR #72 — encrypted 47-object PostgreSQL restore rehearsal:** Each synthetic table COPY payload is sealed and reopened through the CI-only AES-256-GCM envelope before being copied to the disposable target schema. A per-table fingerprint binds reviewed migration plans and table identity; randomized in-memory key/nonce and tampering regressions fail closed and rollback. This is not a retained encrypted archive, customer migration, offsite recovery, storage/key escrow, hosted Neon connection or production release approval. No additional cost.

**Candidate PR #71 — read-only staged-byte trust check:** On the private offline media staging path, require an exact current pending SQLite attachment and active held draft, private regular-file inode (no symlink/hardlink or group/other access), bounded actual bytes matching declared SHA-256/container, and two independently authenticated fresh scanner/rights claims for that draft's actual channel. This does not run malware or rights review, does not persist/revoke evidence, never marks an attachment verified, and cannot publish. Disabled outside disposable CI.

**Candidate PR #70 — encrypted recovery envelope (offline only):** Adds a bounded, in-memory AES-256-GCM backup envelope with HKDF-derived per-envelope keys, authenticated schema fingerprint/freshness, random salt/nonce, and fail-closed recovery tests. The only enabled context is the disposable CI PostgreSQL flag. It writes no backup files and supplies neither off-host retention, key custody nor production migration or restore. Customer data and real services remain inactive.

**BAM is an AI-assisted marketing planning, creation, collaboration, scheduling and analytics platform for businesses.** It is designed to support multiple independent businesses and teams, with direct social-media platform integrations instead of requiring Metricool. Each business has its own voice, products, media, permissions, calendar and performance reporting. The Belenos name identifies the product's origin, not a restriction to one store or industry.

**Current release status (November 12, 2026): Offline Alpha.** The GitHub repository is public, but there is **no publicly deployed BAM application**. A local-only responsive web workspace, signed-in collaboration, held drafts, independent AI copy/image-prompt components and safety checks can be tested offline. Live Meta OAuth, social publishing, executable scheduling, native analytics ingestion, paid OpenAI API generation, hosted multi-user production and Android APK distribution are **not active**. None of the tested previews authorize publication.

**Current development spending authorization: $0 in additional charges.** Continue with local tools, standard public GitHub CI runners and disposable PostgreSQL tests. Do not activate even a nominally free hosted Render/Neon service, paid AI provider, public publishing or new infrastructure without separate approval. A dedicated $7/month Render Starter plus separate Neon Free database remains a **deferred design**, not an expense, and EdgePilot's paid hosting is strictly separate.

**Previously verified implementation checkpoint (November 12, 2026):** [PR #64](https://github.com/BelenosCreations/belenos-marketing-automation/pull/64) merged at `3f89c948a5e453b2516a9faa40c35eae294a3397`, and full [merged-main Actions 43340205353](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43340205353) passed. Development was safely synchronized. PRs #61–#64 strengthened local attachment file-container checks, introduced disposable CI-only PostgreSQL round-trip backup/restore rehearsal, demonstrated transactional rollback on interrupted/corrupt restores and checked live session/tenant authorization against restored synthetic records. The 46 reviewed schema tables/eight CI stages remain **not production-ready**, and no customer data or paid provider was involved.

**Last fully verified development checkpoint (November 12, 2026):** [PR #68](https://github.com/BelenosCreations/belenos-marketing-automation/pull/68) merged as `3052f1e2a7ab65c4a19cf7b8a31e854fc94b6b88`; [exact-head CI 43344020606](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43344020606) and [merged-main CI 43344264999](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43344264999) both succeeded. `main` and `development/phase-3-5-account-directory` synchronized without force. PR #66 added constraint/index/FK catalog parity to 47-object synthetic restore; PR #67 added offline dual-signed media scan/usage-rights evidence validation; PR #68 enforced REPEATABLE READ across the disposable restore and verified coherent snapshots during concurrent source writes.

**Remaining work before private Beta:** A reviewed production migration and live database adapter, durable encrypted retained/off-host backup and measured restore drills, signed media evidence stored with revocation/audit and actual trusted workers, private object storage, hardened multi-user ingress and authorization, and separately approved third-party provider integrations. The current verified work does not deploy or run these capabilities. $0 additional costs; no EdgePilot infrastructure, hosting, paid AI or publishing authorization.

**Next engineering priorities:** Complete safe production persistence and migration/restore tests, tenant-isolated authenticating gateway, private durable media storage with trusted scanning and usage-rights verification, and a tested approval-to-publishing architecture. Direct provider integrations, AI API spending, production scheduling, hosting and social publishing remain disabled and require separate review/authorization. No unmerged functional work is assumed complete. See [development continuity](DEVELOPMENT_CONTINUITY.md) and [private beta readiness](ALPHA_BETA_READINESS.md).


**Media boundary hardening in progress (November 12, 2026):** A new offline file preflight rejects several malformed or truncated container formats after SHA-256 matching; this is preliminary sanity checking only, never malware/rights verification. Before claiming verification, check the exact PR-head GitHub Actions result and post-merge `main` test run. All provider writes and real uploads stay disabled.

**Verified media safety checkpoint:** [PR #61](https://github.com/BelenosCreations/belenos-marketing-automation/pull/61) merged at `82b1a0bd27cd5bf8c34ca373b890774b12dd43c7`; [merged-main Actions 43338078991](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43338078991) passed. Offline media containers undergo stronger sanity checks, not malware or rights verification. A disposable PostgreSQL logical restore rehearsal is next; it will **not** create a production backup or hosted service.

**Verified PostgreSQL restore rehearsal:** [PR #62](https://github.com/BelenosCreations/belenos-marketing-automation/pull/62) merged at `7beccbbd8c448de277744aedd5d798e8662ed9e3` and passed [merged-main Actions 43338797005](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43338797005). It round-trips the 46 reviewed CI-only PostgreSQL tables and migration journal; this is **not** an encrypted or production backup. Fault-injection rollback rehearsal is in development; never treat a synthetic restored schema as private-Beta recovery readiness.

**Verified recovery-failure coverage:** [PR #63](https://github.com/BelenosCreations/belenos-marketing-automation/pull/63) merged at `fe1fe32ab49ca38add64ec7a25b1915cb4d6a7b5`; [merged-main Actions 43339557139](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43339557139) passed. CI-only rollback now rejects interrupted or altered restores without residue. Next milestone tests restored session revocation, expiry and tenant boundaries inside that disposable schema. No production restore, paid services or posting.

## Product experience

BAM is designed to let an owner or authorized team run marketing from one place:

1. **Sign in to BAM** using email/password or Google sign-in, select an existing business or create a workspace, and access only businesses to which the account belongs.
2. **Set up each business:** confirmed products, services, contact and operating facts, voice, audience, marketing goals, media, and permission policies.
3. **Connect social accounts directly to BAM.** Start with eligible Facebook business Pages through official Meta authorization and APIs; expand platform support only where each provider permits the required actions. No Metricool account, subscription, or API key is required for BAM's planned core functionality.
4. **Plan and create content:** generate AI-assisted post copy and, when useful, a separate image-creation prompt; use factual zero-API-cost templates where appropriate; bring in original media and permitted third-party references.
5. **Collaborate and review:** assign access by role, save draft revisions, request photos or approvals, comment on content, and protect one editor's work from being silently overwritten by another.
6. **Choose when to post:** use owner-configured manual times or, after trustworthy audience data is connected, data-informed Smart recommendations. Schedule only content that passes the applicable review and media checks.
7. **Publish and learn:** after a separately approved production rollout, BAM's own scheduler should publish directly through authorized social-provider APIs, reconcile platform results, and use available native insights to improve recommendations.

The workflow is intended to be **draft → factual/media checks → team review when needed → approval → schedule → direct publication → performance review**. Today, the offline alpha deliberately stops before real scheduling and publication.

## Core capabilities and direction

| Area | Intended product capability |
| --- | --- |
| Multi-business workspaces | Independent brand identities, facts, topics, campaigns, assets, schedules, social accounts, usage and access rules under a single login |
| Team collaboration | Individual employee logins, invitations, business-specific owner/manager/creator/employee/viewer roles, shared draft queue, feedback, activity history, and configurable approval policies |
| Content Studio | Post drafting and editing, revision/conflict detection, media-needed requests, campaign priorities, CSV draft imports, content queues and review checklists |
| OpenAI-assisted copy | One structured request for post copy plus an optional separately editable image prompt, targeted regeneration of only the changed component, optional advance batches and local templates |
| Artwork workflow | Upload owned or licensed media; optionally copy an image prompt into the user's own ChatGPT Free/paid account, refine the image there, and return it to BAM; ChatGPT is not a programmatic free image API |
| Publishing | BAM-managed job queue, retries, idempotency, cancellation, provider-status reconciliation and owner-controlled pause/emergency stop, all **planned and not live** |
| Analytics | Native platform insights where authorized and available, content performance, audience patterns, posting-time evaluation and transparent limits when providers expose insufficient data |
| Cost control | Shared hosting, business-level resource accounting, sponsored AI allowances, optional personal OpenAI API keys, usage limits and budget safeguards |

The first business examples are **Belenos Creations** and **Busy B Cleaning Service** in Marion, Ohio. They are examples for testing business separation, not hard-coded target customers.

## Direct social-platform integrations — no Metricool dependency

**The approved architecture is direct connection to social networks, not a required Metricool integration.** BAM will provide the scheduler, publishing records, review process and analytics views itself.

- **Facebook first:** authorize an eligible business Page via Meta's official login/permission flows; securely store and refresh/revoke authorized credentials; publish to Pages through supported APIs only after review and activation.
- **Other social platforms later:** implement separate provider adapters only after verifying current API eligibility, supported account types, app-review requirements, publishing capabilities and limits. Access to personal profiles, groups, particular content formats or private insights must never be assumed.
- **BAM analytics:** use the social platforms' own authorized data when available; never display sample activity scores as live metrics. Smart posting suggestions must declare when usable audience evidence is missing.
- **Resilience:** local scheduling and audits must not depend on Metricool. Failed/revoked permissions, provider outages, rate limits, duplicate submits and status mismatches require explicit reconciliation, safe retries and visible errors.

BAM does **not** promise unlimited posting or unrestricted analytics; each social network's rules, API approvals and quotas still apply. Metricool is not needed to create a BAM account or to use its planned supported publishing features.

## Accounts, teams and business isolation

Each person has one BAM identity and can have different permissions in different businesses. The current offline policy uses **owner, manager, content creator, employee and viewer** role boundaries. For the finished collaboration experience, owners should be able to invite and remove members, assign/restrict permissions, make approval mandatory for selected posts, and view an audit trail of editing, approval and publication events.

The existing offline alpha already has tenant-scoped sessions, role checks, business switching, shared draft data, version-safe editing, private reviewer notes, activity metadata and team counts and owner-only existing-member details. Role changes or removals require a second confirmation, current membership revision and a current owner session, revoke only the affected business's sessions, and record an audit event. Owners can also view the latest 30 member-access changes privately within Team settings; the history excludes credentials, invitation tokens and unrelated businesses. **Owner-only management of existing members is now implemented in the offline Alpha Settings view, including role changes and access removal. Invitation delivery, ownership transfers, reactivation, production hosting and real multi-device collaboration remain unimplemented.** Business switching must immediately invalidate stale private UI and prevent cross-business data leakage.

A team's additional members do not require individual application servers. Seats, AI allowances, media quotas and any future subscription policies are distinct configuration decisions; no unlimited free-seat or public-pricing promise is made here.

## AI and image generation

**OpenAI is the only approved generative-AI provider.** The intended default is BAM-sponsored OpenAI API access so that a user does not need to create a separate OpenAI API account or buy their own key. A user may optionally configure a **personal paid OpenAI API key** for their own API charges, held in an encrypted server-side secret vault after that capability is built. This must not expose the key to employees, the frontend or the repository.

The generation design uses business-approved facts and isolated per-user/per-business writing preferences. One model request can return structured `post_text` and an optional `image_prompt`. Users can change either field independently without regenerating both. Local factual templates can avoid API calls; future batch work may reduce generation overhead where supported and useful. Requested images are an optional **manual** workflow in ChatGPT or can be uploaded directly; BAM must not silently publish a post missing required artwork.

A sponsored experience **still costs the BAM operator money** for real API calls. Rate, token and spend caps; safe billing/usage records; abuse controls; and possible future plans remain subject to explicit configuration and validation. Public subscription pricing, user quotas, model choices and payment integrations are not finalized. See [AI architecture](AI_ARCHITECTURE.md).

## Scheduling and content safety

BAM should offer both **Manual** and **Smart** posting modes. Manual mode honors explicitly saved local times and time zones, handling daylight-saving transitions conservatively. Smart mode uses trustworthy first-party audience and performance measurements to recommend times, with no invented engagement forecasts. Posting intervals, campaigns, business hours, deadlines, duplicate protection and platform restrictions constrain both modes.

Content safeguards are fundamental:

- No invented discounts, prices, giveaways, promotions, inventory guarantees, events, opening hours, or order commitments.
- Owner-confirmed facts carry provenance; confirmation is not represented as independent verification. Uncertain claims remain held for review.
- New or changed promotional claims require applicable authorization. Previously approved claims may be reused only within their authorized scope and validity.
- Missing or unverified media, unclear content rights, sponsored/unfamiliar third-party references and sensitive content remain held. Credit creators and do not copy images without permission.
- A draft, reviewer note, image receipt, suggested time, or proposed calendar date is **never itself permission to publish**.
- All publication must require authenticated roles, current content and media state, trusted social permissions, an auditable approval policy, an explicitly authorized production switch, and an emergency stop.

## What works today (offline alpha)

The active development branch contains these **local development** components, not production integrations:

- A responsive **large-card, mobile-first HTML workspace** with deeper settings, Content Studio, Approvals, social connection status and posting-time previews. Native Android is a future delivery target.
- Local password sign-in/session foundations and Google sign-in verification scaffolding, multi-business membership isolation, logout on current/all sessions, role-aware access, switching and invitation policy foundations.
- Held draft creation, revisions and stale-edit conflict protection; priority/filtering, optional CSV import, missing-media holds, private reviewer feedback and audit metadata, factual-risk hints and review-readiness checklists.
- Owner-confirmed business-fact editing, independently editable user/business AI writing preferences, local zero-provider-cost templates, structured AI draft records, targeted-revision/test-executor flows, cost ledger/quota foundations and a **zero-OpenAI-call** future-topic preview.
- Owner-configured Manual/Smart preferences, daylight-saving-safe Manual time previews, proposed dates with conflict tokens, and suggested unpublished slots. **These are not executable scheduled posts.**
- Read-only social connection metadata and offline OAuth/PKCE foundations. **No real account connection, live platform insight or API publication is enabled.**
- Optional, explicitly opted-in **private quarantine** for pending image bytes. It does not perform production malware scanning, ownership verification or media approval.
- A local-only opt-in HTTPS preview/gateway and automated Python/JavaScript tests. The SQLite and WSGI development arrangement is **not** a production deployment.

Past successful CI runs are documented in [development milestones](DEVELOPMENT_MILESTONES.md). The exact latest security-batch commit may not yet have passed GitHub Actions; consult [development continuity](DEVELOPMENT_CONTINUITY.md) before merging or making any claim about a new release.

## Architecture and operating costs

The planned production system is a **shared hosted BAM backend** (Python service plus durable relational database, private media/object storage, background workers and monitoring), with strict tenant isolation and a responsive/web and eventual Kotlin/Jetpack Compose Android client. Each user signs in independently; phones do not need to remain open to run approved future jobs. SQLite remains an offline prototype store until production migrations, concurrency controls, backups and recovery are verified.

Content text, draft states, permissions, audit events and schedules belong in the database; privately stored media belongs in durable object storage. Published content also resides on the destination social network subject to its policies. Secure backups, retention controls, rights handling and deletion are required.

**Cost philosophy:** no mandatory Metricool fee, no server for each employee, and no separate OpenAI signup for BAM-sponsored AI. Ongoing operator costs will come from hosting/database, media and backups, OpenAI usage, observability and upkeep. AI usage and media storage may increase with more businesses; adding a colleague to one workspace should cause little incremental hosting overhead. Exact pricing and customer billing are **not yet set**; no zero-cost or unlimited-use guarantee is implied.

## Release path and developer documentation

The [current product and implementation plan](PRODUCT_PLAN.md) records direct social API delivery, team collaboration, shared hosting/cost design, phased integration gates and measurable acceptance criteria. [Alpha/private beta readiness](ALPHA_BETA_READINESS.md) covers security, hosting, media, provider and publishing evidence needed before release.

- [AI architecture and approved requirements](AI_ARCHITECTURE.md)
- [Development continuity / safe resume checkpoint](DEVELOPMENT_CONTINUITY.md)
- [Detailed development milestones](DEVELOPMENT_MILESTONES.md)
- [Changelog](CHANGELOG.md)
- [Local HTTPS preview](LOCAL_PREVIEW.md)
- [BAM brand assets](branding/README.md)
- [GitHub Actions tests](.github/workflows/tests.yml)

Development and documentation updates do not activate a paid API, launch a hosted service, connect Facebook, schedule a post or grant publication permission. **Publishing remains off until separately authorized, implemented and verified.**

## Offline engineering and migration checkpoints

### Private beta preparation (November 12)

The offline BAM WSGI composition now checks for loopback-only network context: requests advertising public origins or reverse proxies are denied before any route. This is an **offline defense-in-depth regression**, not production hosting or an endorsed public server. A separate hardened production runtime, explicit authorization to create the selected Render/Neon services, and approvals for any other costs remain prerequisites. See [private beta infrastructure proposal](PRIVATE_BETA_INFRASTRUCTURE.md).

### Atomic account login-failure accounting (offline Alpha)

The persistent account-level login throttle now records failures in one SQLite UPSERT instead of a separate read/write, preventing lost increments across independent application/database clients. Trusted timestamps are strictly validated and stale events cannot reset an active lockout window. Concurrent two-connection regression coverage is included. This is **not yet a production distributed rate limiter**: checking the throttle and performing authentication remain separate operations, and trusted per-IP/device/global limits are still required.

### Active development cost policy — $0 additional spending (November 12, 2026)

**Official current authorization: $0 in new monthly or one-time charges for BAM.** Continue development using free standard GitHub-hosted runners, disposable PostgreSQL CI containers and other free local/offline tools. Avoid extra workflows, CI artifacts, paid storage, background workers or any account service that might bill through overages. A free service may be considered for later hands-on testing, **but it is not authorized for provisioning by this decision**, and any potentially chargeable overage requires separate approval and provider-side usage safeguards. Do not host BAM inside EdgePilot's existing paid service, share its credentials or database, or modify its deployment.

**Budget reconsideration trigger:** only when a functioning BAM application is ready to justify hosting **or** a concrete development blocker genuinely cannot be addressed with free tools. At that point, present specific options, expected costs, risks and recommended limits for owner approval; reaching a trigger never automatically authorizes any charge or service. Preserve full multi-user functionality and commercial architecture, rather than scaling down the project to fit a temporary free tier. The previously selected **separate $7/month Render Starter + Neon Free** setup is a *deferred design*, not an active expense. See [hosting contract](BAM_HOSTING_PLAN.json) and [infrastructure gates](PRIVATE_BETA_INFRASTRUCTURE.md).

### Deferred $7 hosting design — not activated

BAM's intended first hosted setup is **its own Render Starter web service ($7/month base)** and **its own Neon Free PostgreSQL project ($0/month within free quotas)**. This replaces an open-ended hosting-provider choice, but **does not authorize creating either service, incurring charges or deploying the app**. BAM remains separate from EdgePilot. A standalone server does not imply a separate paid team instance for each user/business. Database migration away from SQLite, verified identity, durable media, encrypted backups and supported scheduling/worker operations are still required. The $7 is **not a guaranteed total or provider hard cap**. No other recurring charges, paid AI or publishing are approved. See [private beta hosting plan](PRIVATE_BETA_INFRASTRUCTURE.md) and [CI-checked planning record](BAM_HOSTING_PLAN.json).

### Neon migration foundation (offline preview)

The first database-portability milestone introduces a review-only PostgreSQL DDL blueprint for **nine** foundational BAM tables plus live SQLite schema parity checks, deterministic schema fingerprinting and privacy-safe row counts. No user records, credentials, or draft text are exported; no PostgreSQL driver, Neon service, Render deployment or paid integration is invoked. This is explicitly **incomplete** and cannot operate BAM on Neon yet. See [Neon migration roadmap](NEON_MIGRATION_ROADMAP.md).

### Complete local schema inventory before PostgreSQL port (offline)

Beyond the nine-table blueprint, `neon_schema_inventory.py` enumerates **all** initialized BAM SQLite tables, distinguishes previewed versus unported tables, and flags SQLite-specific DDL concepts that require manual PostgreSQL translation. It exposes only schema metadata and a fingerprint—not SQL source, customer rows or secrets—and has no PostgreSQL connectivity. `python -m neon_schema_inventory` prints an ephemeral in-memory inventory for development review. This is a prerequisite assessment, **not an actual migration or hosted-readiness claim**.

### Parameterized Postgres read-contract preview (offline)

The next portability slice defines **parameterized, read-only SQL** for private drafts and non-executable calendar proposals that rechecks a verified, active identity and current tenant membership **inside the same SELECT**. Tests adapt the query syntax to SQLite fixtures to verify current-business isolation and revocation behavior. This is *not* a Neon connection, full Postgres test, identity/session verifier, automatic publisher or production API. A trusted caller must establish the identity before using any future database adapter.

### Offline migration integrity preflight

A migration safety audit now checks synthetic/local SQLite data for **orphan identities or sessions, stale membership roles, malformed session hashes, duplicate normalized emails, and orphan draft-calendar links**. The report contains only aggregate counts and boolean readiness indicators—never email addresses, session tokens, password digests or draft text. It is read-only and permanently marks production readiness false; a passing local audit is **not** proof that Neon can host BAM. See [Neon migration roadmap](NEON_MIGRATION_ROADMAP.md).

### Guarded PostgreSQL-style priority write preview (offline)

BAM now has a **non-executing** SQL contract for editing a held draft's priority on PostgreSQL. It combines current active/verified identity, editable team role, tenant scope and `priority_token` compare-and-swap within one `UPDATE ... RETURNING` statement. Separate synthetic SQLite tests verify that stale editors, viewers, revoked members and other businesses cannot change priority. This does not approve, schedule or publish a post, and it is **not yet tested on Neon**. It is not wired into a production application or exposed as an API.

### Database transition checkpoint and next release gate

The current Alpha remains fully SQLite-backed. All Neon DDL, query and integrity additions are offline **planning/tests only**; no PostgreSQL connection is implemented or running. The first nine-table schema preview is incomplete, and the full inventory still lists unmapped tables. A useful hosted private beta will require complete schema and data migration, correctly authenticated PostgreSQL transactions, private durable media, encrypted backup/restore, and verified live cross-business isolation. The owner-selected **separate $7/month Render Starter + free Neon** design is recorded but **not authorized for provisioning or billing**. See [Neon roadmap](NEON_MIGRATION_ROADMAP.md), [hosting gates](PRIVATE_BETA_INFRASTRUCTURE.md), and [readiness evidence](ALPHA_BETA_READINESS.md).

### Public GitHub CI: actual ephemeral PostgreSQL validation (November 12, 2026)

After PR #35, the **source repository is public**, while the BAM product remains unhosted/offline Alpha. GitHub Actions now uses standard free public-repository runners to start a **temporary PostgreSQL 16 container** during the existing unit-test workflow. It runs the nine-table schema preview and tenant-scoped draft/calendar read and priority-write contracts against *real PostgreSQL*, including a two-client stale-write race test. This does **not** create a Neon database, copy customer data, or enable a production DB adapter. Development-branch pushes no longer duplicate the pull-request test run; tests execute on PRs and merged `main`. CI permissions remain read-only and Actions uploads no artifacts. The chosen one-service $7 Render Starter + separate Neon Free design remains **unprovisioned and charge-gated**.

### Team collaboration and invitation tables on PostgreSQL (CI)

The next offline migration slice adds **five more PostgreSQL table definitions** covering team invitation issuance/activity, role-change audit, private draft review notes and review event history. The preview preserves constrained event actions, one-use invitation identifiers and PostgreSQL identity columns for former SQLite autoincrement IDs. Real PostgreSQL CI tests check unique-token metadata, current-owner-only invitation visibility, role changes and no invitation bearer secrets in the returned rows. The source now has **14 PostgreSQL schema-preview tables**, but still lacks many other tables and a production migration service. Hosting, invitation delivery and social publishing remain disabled.

### Versioned migration safety in disposable PostgreSQL CI

The first two synthetic PostgreSQL schema stages (nine core tables, then five private collaboration tables) now run through a **transactional, versioned CI-only migration loader** with database advisory locking and SHA-256 script checksums. CI verifies repeat runs are no-ops and rejects tampered migration history, unknown future versions or missing tables. The loader *refuses non-loopback databases* and has no deployed entrypoint. A dedicated production migration framework, full table coverage, data conversion, encrypted backup/restore and explicit Neon/Render approval are still prerequisites.

### Provider/AI/authentication metadata PostgreSQL parity (offline)

Seven additional table definitions now have **actual disposable PostgreSQL CI coverage**, expanding the reviewed schema from 14 to **21 tables**. They cover each user's AI mode/memory/usage, *vault-reference-only* read-capable social connection metadata, Google nonce and OAuth PKCE attempt ledgers, and private content-attachment metadata. The new prepared read queries recheck current membership and business scope for connection metadata and each user's own AI usage. The query never returns vault references or provider tokens and does **not** establish live provider access. The CI-only migration journal now has a third version; many other tables and production work remain.

### PostgreSQL AI budget and held content schema safety (offline)

The fourth **ephemeral CI migration stage** now models AI business facts, independently editable post/image draft components and their verified-media references, projected AI cost receipts, generation idempotency, and tenant/operator spending counters. The reviewed subset expands to **29 tables**. It adds the reserved-cost/unpriced-request columns required by BAM's existing sponsorship logic, and starts staged PostgreSQL operator AI control **paused by default**. Real PostgreSQL CI verifies estimated-cost receipt deduplication and the pause invariant. This is a data-model safeguard, **not permission to call OpenAI or charge users**.

### Free PostgreSQL CI: business research and analytics metadata (offline)

A fifth versioned, disposable GitHub CI PostgreSQL stage now previews seven more source tables: per-business profiles, topics, approved research sources and competitor blocks, tenant-owned legacy resource labels, authorized analytics checkpoints, and audience observations. The reviewed schema grows from **29 to 36 tables**. New prepared read-contract tests confirm that an active owner can read only their business's synthetic analytics, and another business or deactivated identity cannot read that data; source classifications have real PostgreSQL foreign-key checks. This **does not fetch real analytics or scrape competitors**, and is not a hosted application or production migration. The $0 additional-cost policy remains active.

### Tenant post, review-decision and scheduling schema (offline)

Version six of the disposable PostgreSQL test schema now models four more legacy multi-business tables: **tenant posts, tenant review decisions, unconfirmed events, and per-business scheduling preferences**—bringing the reviewed test subset to **40 tables**. PostgreSQL tests enforce composite tenant/post foreign keys, deny cross-business reads and revoked roles, and explicitly reject a `published` status in the local-only approval schema. A stored review decision or preference does **not** schedule or publish any social post; there is no production queue, Meta connection or paid service.

### Editorial, verified-facts and credential-recovery schema (offline)

A seventh PostgreSQL CI schema stage covers six more private review/security tables: vetted editorial inbox, identity/competitor attestations, offline owner approval intents, TruthGuard verified business facts, creator identity status and hashed email recovery actions. The reviewed subset now contains **46 tables**, with protected PostgreSQL checks denying a `published` editorial state or marketing emails, and current owner/manager-scoped verified-fact reads excluding revoked and expired facts. This stage does **not** deliver email, publish posts, or run a production identity service. Development remains $0 additional spend.

### Session-backed PostgreSQL read contracts (offline security prototype)

Beyond earlier caller-subject SQL previews, `neon_authenticated_read_contract.py` builds read-only **session-token-hash-bound** PostgreSQL queries for held drafts and non-executable calendar proposals. It hashes the server-presented bearer token, verifies session expiration/revocation and current identity, tenant membership and matching role **within the same SELECT**, and refuses malformed scope or time values. Synthetic SQLite and real disposable PostgreSQL CI tests exercise cross-business denial, stale-role denial, session revocation, expiration and disabled identity. This is a more realistic authentication-to-data seam, but still **not a production HTTP gateway, token transport, PostgreSQL persistence adapter or live hosted app**.

## GitHub branches, recovery and release discipline

On **November 11, 2026**, the backlog of Alpha development was reconciled into `main` through [pull request #2](https://github.com/BelenosCreations/belenos-marketing-automation/pull/2), merge commit `f774564d7348e47f34ae0ee9da6279cf14a93677`. The merge preserves both the advanced development history and the independent branding commits originally on `main`. The exact integration SHA `748c3a1a` passed push and PR CI, and [GitHub Actions run 43100795231](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100795231) **passed on the merged `main` commit**. The active development branch was then fast-forwarded to the same verified commit, without force-pushing.

Independent recovery branches were saved at `checkpoint/alpha-last-green-2026-11-11` (`74e55d53`), `checkpoint/alpha-ci-green-2026-11-11` (`cff912f9`) and `checkpoint/alpha-pre-merge-2026-11-11` (`f66522a4`). These are Git references, not enforced branch protection or off-site backups.

**Ongoing policy:** New features stay on the development branch; after a meaningful tested milestone (or before divergence exceeds roughly 50 commits), use a reviewed pull request to merge into `main`, then fast-forward development to the resulting verified merge. Never rewrite history or delete checkpoints as part of routine synchronization. Verify the exact merge candidate with full offline CI, and verify `main` again after merging. A green test run is not approval to deploy, connect paid APIs, or publish posts.


### Collaboration durability evidence (offline only)

Two independent local gateway instances now pass a file-backed SQLite integration test covering shared drafts, conflicting simultaneous editor revisions, business-scoped role-change revocation and state persistence after reinitialization. This is stronger than a single mocked session, **but not evidence of an actually hosted or secure multi-device Beta**. See `test_offline_two_client_collaboration.py` and the [Alpha readiness gate](ALPHA_BETA_READINESS.md).


### Offline data recovery evidence

The local Alpha test suite now exercises a **consistent SQLite snapshot and restore in temporary directories**. It confirms that business-isolated drafts, session revocation and member audit records survive restoration, while edits made after the snapshot are not mistakenly included. This is test evidence only: **production backups, encryption, off-site storage and restore operations are not configured**. See `test_offline_sqlite_restore_drill.py` and [Alpha/Beta readiness](ALPHA_BETA_READINESS.md).

### Owner-private invitation controls (offline Alpha)

When an administrator separately supplies a trusted invitation delivery callback to the offline gateway, the owner-only team workspace can **view active pending invitations and cancel one through a two-step confirmation**. The invitation token itself never appears in the browser or cancellation response. The offline invitation service rejects duplicate active invitations to the same email for a business and refuses to invite an identity that is already a member (including an inactive member). A cancellation or expiration permits a new invitation, and separate businesses stay isolated. BAM does **not** currently provide outbound invitation email delivery, public registration from an invite link, hosted collaboration, or real posting permissions. Every JavaScript UI source now receives a syntax check in CI before execution tests.

### Private invitation activity (offline Alpha)

The optional owner-only Team Settings view can show redacted, tenant-scoped invitation activity: delivered, failed delivery, cancellation and acceptance. A new append-only SQLite metadata table records these transitions with trusted server timestamps and IDs, excluding recipient addresses and invitation secrets from audit responses. The private read-only endpoint and browser panel require the same opt-in, trusted delivery configuration as pending invitation cancellation. Prior invitation actions are not backfilled. This is an offline collaboration/audit milestone, **not** an operational invitation email service or a hosted Beta deployment.

### Transaction-safe invitation redemption (offline Alpha)

BAM now redeems a trusted invitation by claiming its one-use token **inside the same SQLite write transaction** that rechecks the verified identity, inviting owner's current permissions, existing business membership and audit recording. Any failed check, simultaneous attempt, or audit-storage failure rolls back the attempted claim rather than partially adding a member. File-backed tests with two independently initialized SQLite clients simulate simultaneous duplicate issuance, double redemption, and cancellation racing redemption. These protect **offline** consistency only; they do not constitute real hosted enrollment, live email delivery, social publishing, or an approved production database.

### Explicitly opt-in owner invitation issuance (offline Alpha)

The existing trusted server-side `BusinessInvitations` issuance logic now has an **optional** owner-only HTTPS adapter and two-step Team Settings form for entering an email and a non-owner access role. Its server route is **404/not available by default**, even if private invitation listing is enabled. A test-only gateway must separately supply a trusted delivery callback **and** turn on `enable_invitation_issuing`; the browser must also receive its own `enableTeamInvitationIssuing` option. The server derives the business from the owner's current session, rejects duplicate active invitations and existing memberships, and returns an opaque invitation ID/expiry only — **never the bearer invitation token**. The browser confirms intent before invoking a separately trusted delivery callback and clears stale results on logout. No real email delivery provider, self-service enrollment/acceptance route, hosting, or publishing was enabled.

### Concurrent-editor-safe calendar proposals (offline Alpha)

BAM's saved suggested posting times are **only private, non-executable proposals**. The database now checks a draft's *current* revision and status at the moment of the proposal write and uses the existing per-proposal random version token as a real SQL compare-and-swap condition. A stale editor cannot replace a newer proposal, revive an already replaced/deleted version, or overwrite a changed draft merely because an earlier browser read appeared valid. A business may have only one proposal per exact UTC slot. Separate-file-backed SQLite-client tests attempt simultaneous assignments, same-token edits, and competing drafts. Every result still reports **zero scheduled posts and publishing disabled**; this change does not create a worker, schedule a job, connect a social API, or authorize a publication.

### Sponsored AI request budget containment (offline Alpha)

BAM's sponsored-AI quota reservation now supports an optional **individual monthly request limit, shared per-business monthly limit, and overall BAM-operator monthly limit**. All three request counters are updated together inside one SQLite transaction, and denial at any layer rolls back the others. Aggregate usage is counted even when its optional ceiling is not enabled yet, so configuring a ceiling partway through a month still accounts for earlier sponsored reservations. Only members with current draft-creation permission may reserve. Two independent SQLite connections compete under the business and operator caps in offline race tests.

These are **request counts, not dollar limits, provider bills, or unlimited free AI**. The operator must configure consistent server-controlled budgets and pricing/cost limits before any real OpenAI API calls. The quota engine does not call OpenAI, hold keys, generate images, activate paid features, or publish.

### Read-only social metadata revocation safety (offline Alpha)

BAM now refuses unknown or posting-capable **internal analytics scope markers** in the test-only social connection registry; `read_insights` is a normalized internal capability label, **not proof that Meta or another provider has granted any actual OAuth permission**. A revoked social connection cannot silently become connected again through a delayed registry update. Older revisions and future-dated or historically unapproved scope records fail closed. Separately verifying reauthorization is a future production prerequisite.

The offline analytics import path checks the connection both before its simulated read-only fetch **and inside the SQLite transaction before writing imported metrics and the synchronization checkpoint**. Independent SQLite-client tests revoke permission during an in-flight fake fetch, confirming no observations or cursor are saved. The same connection-backed store is required for this particular transactional guarantee. No live provider requests, social account linking, publication, or scheduling were enabled.


### Atomic estimated AI spending reservations (offline Alpha)

The existing sponsored OpenAI request-count quotas now also support **operator-configured projected micro-USD reservations** for each individual BAM user, business, and the entire operator. All three count/estimated-cost increments occur atomically in one SQLite transaction; denial at any tier rolls back the whole reservation. Independent SQLite-client tests verify competing users and businesses cannot exceed a shared projected allowance.

To avoid misleading accounting, historical sponsored requests with **unknown estimated costs** are marked unpriced during schema migration; enabling an estimated-dollar ceiling partway through such a month fails closed rather than ignoring earlier requests. A server plan must explicitly supply a nonzero conservative per-request estimated amount before dollar-denominated projected caps can be used. The estimates are operator assumptions, **not provider token usage, an actual invoice, a guarantee about final spend, or permission for paid AI calls**. Before any live AI activation, the chosen model's current pricing, actual input token ceilings, receipts, reconciliation, circuit breakers, and operator-approved dollar spending policy must be verified and integrated.


### Trusted AI budget admission and conservative cost projection (offline Alpha)

The sponsored request budget now **rechecks the current business role and sponsored-versus-personal funding choice while holding SQLite's write lock**, after preliminary authentication. If an employee loses editing permission or switches funding modes during an in-progress request, no new BAM-sponsored count or projected-cost reservation is committed. Separate SQLite-client race tests simulate permission changes at that boundary.

A **pure pricing calculator** can estimate a conservative micro-USD request reservation from operator-supplied input/output token ceilings and explicit operator-configured token prices, rounding fractions upward. It is **not** verified pricing, actual tokenization, a bill, or evidence that the executor enforces the input limit. A separate internal `reserve_current_utc_month` entry point derives the accounting month from a trusted server timestamp; older explicit-month test fixtures remain and **must not be exposed to untrusted clients**. No live OpenAI traffic or payment capability was enabled.


### BAM-sponsored AI operator pause (offline Alpha)

A trusted, offline **operator-level pause** can now prevent **new** BAM-sponsored AI request reservations across all businesses and user accounts. The pause is stored in local SQLite, checked *after* current user-role/funding revalidation while holding the writer lock, and shared across local connections. Refused requests do not increase request-count or projected micro-USD counters. The generation and one-component revision interfaces now understand specific redacted pause/budget-hold reasons; they do not retry a previously failed request key automatically. This is an internal control, **not** a customer-facing setting, a real OpenAI dispatch stop, or an on/off switch for paid provider access. Already-reserved/in-flight requests are unaffected, and production integration still needs a separately authorized, enforceable provider-level kill switch and spending reconciliation. Code `cb23ebbd` passed [GitHub Actions 43142566744](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43142566744). No live AI calls were activated.

### Trusted AI usage report deduplication (offline Alpha)

An internal AI cost ledger now supports a server-owned, stable usage-event reference. Its hashed value is unique **per business and individual**, so duplicate callbacks from independently connected SQLite workers can return the same recorded event rather than overstating estimated AI costs. A conflicting reference is rejected, and legacy historical cost rows remain intact without invented IDs. This is an opt-in **internal accounting primitive**, not a completed connection to provider response IDs or an invoice-reconciliation service. Reference-free reports cannot be deduplicated automatically. No paid API call or customer billing was enabled. Verified source `9765961f` passed [GitHub Actions 43143316508](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43143316508).

### OpenAI HTTPS dispatch pause boundary (offline Alpha)

The disabled-by-default OpenAI transport now refuses to be configured as enabled unless its trusted server operator supplies an explicit dispatch authorization callback. The callback is checked **before retrieving any provider credential** and checked again immediately before the HTTPS opener, allowing the internally persisted BAM-sponsored AI pause to block requests that were reserved earlier but have not yet been sent. A false, missing, malformed or failing callback is rejected without disclosing internal details. These are point-in-time checks; a pause activated *after* the final check or after a request starts cannot guarantee cancellation, and production needs stronger worker fencing, a secure vault and a separately approved paid-usage policy. This is an offline dependency-injection safety milestone, **not** a live OpenAI connection or provider-level kill switch. Code `d14bbd3f` passed [GitHub Actions 43144166053](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43144166053).

### Trusted Responses usage identity (offline Alpha)

With a server-owned usage observer configured, the Responses execution adapter now validates a provider response identifier, derives a private stable deduplication reference, and passes it with estimated token counts to BAM's per-user/per-business cost ledger. Replayed synthetic Responses from the same scope no longer double-count estimated usage; conflicting counts or missing IDs fail closed. Raw provider response IDs are **not** stored in the estimated-cost ledger. This is verified **only with injected fake offline transports**, not a live billed receipt or reconciliation against OpenAI's invoice. Malformed provider responses can still represent attempted real usage, so a future production system requires independent error/usage reconciliation before enabling paid traffic. Verified source `f95f0820` passed [GitHub Actions 43145005354](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43145005354).

### OpenAI request and structured-response safeguards (offline Alpha)

The disabled-by-default sponsored Responses adapter now validates trusted business and user scope **before** an injected transport could send a request. Provider/generated JSON with duplicate keys, invalid component types, blank posts or oversized copy/image prompts is held out of the unpublished draft pipeline. If the optional trusted usage observer is configured, valid provider-reported tokens are accounted for **before** rejecting unusable generated text.

The HTTPS adapter allowlists the outgoing request fields, strict JSON-schema output and user-only text input. Unapproved background requests, previous-conversation linkage, implicit tools, parallel tool calls and extra API parameters are refused. This is offline fake-transport code and regression coverage; it is **not** live OpenAI access, verified billing, a deployed application, image creation or posting authorization.

### New verified member invitation acceptance primitive (offline Alpha)

An existing, email-verified BAM password identity can now be authenticated **without already belonging to a business**, solely for trusted invitation redemption. A correct password and valid, delivered, unexpired, one-use invitation matching that identity are required. Business membership is created transactionally; only **after** acceptance can the person obtain a normal role-scoped business session. Rejected attempts create no membership or session and do not spend the invitation. No cross-business permissions are granted.

This is an **internal offline backend method only**: there is still no public invite-acceptance page, self-service registration, email-verification delivery, or hosted employee collaboration. An external acceptance endpoint must have approved identity enrollment and rate limiting before exposure.

### Rate-limited internal invitation acceptance gate (offline Alpha)

The internal authentication service now requires an **explicit opt-in** and a shared persistent password throttle before it can invoke trusted invitation redemption. Failed credential/token claims consume the throttle allowance; successful acceptance clears the credential failures, creates the membership through the transactional invitation service and **returns no logged-in session**. A separate normal login is required afterward. No HTTP route is mounted for this action. Production still needs verified enrollment, IP/global anti-abuse controls, secure delivery, and hosted multi-user testing.

### Google-only invitation redemption groundwork (offline Alpha)

A Google-only BAM identity already stores its independently verified provider-subject mapping at registration, without business membership. The internal admission service can now resolve that verified identity **without issuing a session**, using a fresh one-time Google nonce, the trusted Google ID-token verifier, a shared hashed-email throttle, and a delivered, one-use business invitation. Only the membership is created. Subsequent Google login still separately requires that membership. Tests cover unknown subjects, mismatched emails, nonce replay, expired token reuse and successful team sign-in after acceptance. There is still no hosted Google browser flow, public invite endpoint, automatic email account linking or production hosting.

### Separately gated offline invitation acceptance API adapter (Alpha test only)

The local WSGI test composition now has two **default-404**, explicitly opted-in endpoints for previously verified BAM invitees: password-based and verified Google-nonce-based acceptance. An administrator supplying a trusted out-of-band invitation-delivery callback must also enable the **independent** acceptance feature switch; issuing invitations has its own separate switch. The routes require HTTPS, bounded JSON with exact fields and duplicate-field rejection, and refuse client business/subject/role selectors. They return a minimal non-secret membership receipt, **no bearer invitation, password, ID token or login session**. The original one-use, transaction-safe acceptance and hashed-email credential throttling remain enforced.

This is **not a production/public invitation flow**: the gateway is a direct-call offline fixture. Exposing these routes to a network requires separate production architecture and authorization, including verified-email onboarding, approved delivery, IP/global rate limits, anti-abuse controls, secure browser flow, hosted tenant isolation and recovery validation. Real email sending, hosting, social publishing and paid OpenAI remain disabled.

### Private calendar readiness digest (offline Alpha)

A new owner/teammate-scoped **read-only** `GET /api/v1/calendar-readiness` reports held draft-calendar proposals, counts of draft revisions requiring refresh and owner-configured posting times that have changed, plus an explicit publication-blocker list for each item. The response contains no proposal edit tokens, and neither a current draft nor an apparently valid posting time is presented as permission to publish. The final publication review and social writing integration are deliberately reported unavailable. HTTPS, session validation, tenant isolation and strict response shape checks are exercised in offline WSGI regression tests. It creates **zero scheduled jobs** and cannot publish.

## Public GitHub readiness (preparation only)

Hosting this source publicly is under consideration to reduce GitHub Actions compute costs. The repository remains private until a historical credential and Actions-artifact review is complete. See [Public repository readiness](PUBLIC_REPOSITORY_READINESS.md). Repository visibility does not grant permission for live integrations, production deployment, additional spending, trades, transfers or publishing.


### Inactive PostgreSQL operator preflight (November 12, 2026)

`neon_migration_operator_preflight.py` emits deterministic reviewed-DDL fingerprints and a metadata-only SQLite integrity/drift checklist. It flags unreviewed and optional uninitialized source tables; even a matching pinned digest cannot authorize a live cutover. No PostgreSQL connection, customer export, production migration, backup, rollback or publishing occurs. Run `python -m unittest -q test_neon_migration_operator_preflight` locally with the existing offline environment. All live infrastructure and additional spending remain unapproved ($0).


### Disposable durable encrypted archive experiment

`bam_offline_durable_archive.py` writes only AES-GCM ciphertext envelopes to a trusted owner-only local directory with atomic no-replace publication, fsync and external ciphertext-hash pin verification. It rejects altered, hard-linked, symlinked and incorrectly permissioned objects. **CI-only, synthetic, maximum 4 MiB plaintext per existing envelope:** no PostgreSQL streaming backup, real key vault, retained offsite replica, disaster-recovery guarantee or unattended retention. A separate reviewed production backup stack remains mandatory, and production and publishing remain disabled at $0 added cost.


### Offline signed media revocation audit

`trusted_media_revocation.py` extends the existing independent HMAC scan/rights evidence verifier with a separately keyed, hash-chained revocation proof. Removing or changing events, presenting an obsolete independently pinned chain head, using shared issuer/audit keys, and replaying revoked claims fail closed. The chain is **not** persisted or connected to an authoritative source; scanner and copyright-review workers still do not exist, and the module never approves media or publishing. A durable authenticated revocation register and trusted real scanner/reviewer service are prerequisites for Beta.


### Private staged-media revocation probe (offline only)

`probe_staged_signed_media_with_revocations` now composes actual local staged-inode/digest reinspection with independent signed scan/rights claims and a separately pinned revocation audit proof. It refuses revoked evidence while leaving the attachment pending. This is an optional **CI-only** read-only path, not an active AV engine, rights reviewer, persistent revocation authority, verified media status, publishing API or authorization to expose the gateway.
