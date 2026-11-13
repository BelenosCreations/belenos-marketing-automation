# BAM private beta infrastructure — proposed, not authorized

**Latest independently verified BAM functional checkpoint — November 12, 2026:** PRs [#86](https://github.com/BelenosCreations/belenos-marketing-automation/pull/86), [#87](https://github.com/BelenosCreations/belenos-marketing-automation/pull/87) and [#88](https://github.com/BelenosCreations/belenos-marketing-automation/pull/88) all merged, with separately successful exact-head and merged-main GitHub Actions. #86: [43363216197](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363216197) / [43363520290](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363520290), merged main `af5154b94573a01bd4c4e2fc08184149a2b1ec09`; #87: [43363803609](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363803609) / [43363985496](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43363985496), merged main `177ecd90728e96a7d6c604bb4ba4f1731039e023`; #88: [43364238789](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43364238789) / [43364411439](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43364411439), merged main `d0b3255597349fd864842625e7dc0a5f6def55df`. Both main and development were independently compared identical, zero commits ahead/behind, after a non-force fast-forward.

**Verified offline scope, NOT production release:** #86 checks exact source/target synthetic values, integer ranges, finite floating-point/text/binary assumptions and independently pinned schema/mapping fingerprints without querying source rows or migrating data. #87 prepares a dormant ClamAV subprocess interface with external executable/CVD hashes, safe private file reinspection and negative mocked-CLI tests; no genuine engine/signatures were invoked in CI, no trusted worker isolation or rights adjudication is proven, and no scan claim/status approval is issued. #88 validates two-connection **in-memory synthetic SQLite** lock and rollback behavior only, not a BAM-wide production write fence. Real customer data transformation, transactional PostgreSQL runner, application rollback, authoritative offsite AES-GCM backup/head/key custody, independently authenticated scanner/rights reviewers, hosted session/tenant/CSRF/ingress hardening and publishing authorization remain blocked. No Render, Neon, paid APIs, social publishing or EdgePilot activation. Incremental spending: **$0**.

## Verified recovery checkpoint after PRs #86–#88

Latest independently verified functional main: `d0b3255597349fd864842625e7dc0a5f6def55df`; last verified merged-main Actions **43364411439** succeeded. PR #86 exact/main Actions **43363216197 / 43363520290**, PR #87 **43363803609 / 43363985496**, PR #88 **43364238789 / 43364411439** all succeeded. Main and development were synchronized without force and independently verified zero ahead/behind. No pending functional PR at this point; PR #89 is a documentation-only recovery checkpoint candidate. **Production is still inactive offline Alpha, not approved private Beta.** Distinguish: a synthetic conversion canary does not approve customer values; a mocked ClamAV CLI response does not prove real malware scanning or legitimate usage rights; a shared-memory SQLite lock does not fence BAM web workers or production PostgreSQL; same-host encrypted ciphertext is not offsite customer backup. Remaining gates: independently reviewed column/default/tenant transforms, versioned atomic migration/rollback and operator wide-area write fencing, externally controlled offsite backup/keys/heads, independently attested real ClamAV signatures and isolated worker, human rights-review and tenant-scoped revocation authority, hardened real sessions/CSRF/proxy/abuse tests, explicit operator authorization. Keep $0 added costs and all Render/Neon/paid providers/social/EdgePilot services disabled.


## Verified CI-only PR #87 — trusted-scanner worker prerequisites

An offline-only, CI-gated `clamscan` subprocess adapter validates supplied engine and single signature DB SHA pins plus staged-media SHA before and after invocation and bounds time/output with a fixed sanitized environment. CI subprocesses are mocked; no real ClamAV installation or signature database verification is exercised. Actual Beta requires an independently installed/signed scanner, vetted signature update workflow and freshness SLAs, isolated least-privilege worker with file-descriptor-safe input, tenant-scoped authenticated queue/audit, human rights assessment, evidence and revocation authority, plus negative production deployment tests. No hosted execution, media approval, or publication is active.


## Verified post-merge recovery checkpoint after PRs #83–#84

Main SHA `10e18ce0e5554fd9dab80048b9ef002bf5e58654`; both branches identical, no forced update. PR #83 exact/main Actions 43357261226/43357506877 succeeded, PR #84 43357908998/43358111378 succeeded. All features remain offline Alpha proofs. Next major branch: independently audited per-column value transforms and a disabled transactional operator protocol; offsite encrypted replicas and external key/head authority; verifiable isolated ClamAV/signature provenance and human rights review; tenant-scoped evidence/media authorization and hostile private Beta session/CSRF/ingress tests. Obtain explicit authorization before connecting or spending. No genuine malware scan, offsite production backup, live cutover or publisher exists.


## Verified CI-only PR #84 — same-host encrypted relocation is not disaster recovery

The offline CI rehearsal copies a pinned HMAC-manifest-bound encrypted synthetic archive to a *different* private local directory with no plaintext/key in the transfer API, fsync and atomic no-replace publication. It then independently restores through AES-GCM after deleting the source copy. This cannot satisfy offsite-copy independence, customer key custody, key escrow, external authoritative head pins, immutable retention, disaster-region isolation, recovery time objectives or Beta readiness. No upload/network/hosting or scheduled retention deletion is added. $0 additional cost.


**Latest independently verified BAM engineering checkpoint — November 12, 2026:** PR [#83](https://github.com/BelenosCreations/belenos-marketing-automation/pull/83) and PR [#84](https://github.com/BelenosCreations/belenos-marketing-automation/pull/84) both merged after exact-head and independent merged-main CI. #83: [Actions 43357261226](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357261226) and [43357506877](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357506877); #84: [Actions 43357908998](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43357908998) and [43358111378](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43358111378). Latest independently verified merged `main` commit `10e18ce0e5554fd9dab80048b9ef002bf5e58654`. Development fast-forwarded without force and independently compared identical, zero ahead/behind.

**Verified engineering scope only:** #83 adds deterministically pinnable SQLite-to-PostgreSQL source/target column/type review proposals for 46 preview tables, with explicit value/default/tenant/identity review still outstanding and customer migration blocked. #84 adds independently signed synthetic ciphertext relocation between separate private *same-host* directories and an AES-256-GCM restore after original local loss. Neither proves real offsite backup, external key/head custody, retention, production migration, customer restore, actual ClamAV scanning or human rights review. Hosted sessions, private Beta security and trusted media workers remain incomplete. No Render, Neon, paid API, social publishing or EdgePilot integration was activated. **Additional spending: $0.** Passing CI is not production readiness.

**Operator boundary after verified PRs #79–#81:** Offline migration planning, synthetic signed backup inventory/rotation and locally durable signed revocation records have passed GitHub CI. There is no operator-managed offsite backup, external head custody, tenant-scoped key service, real antivirus/rights-review worker, authenticated hosted service or production private Beta acceptance. Test outputs cannot lift any release gate. $0 additional spend; no hosting or publishing activated.


**Verified CI-only PR #81 — read-only audit-durability rehearsal:** The offline event writer persists synthetic HMAC-linked revocations with fsync and inode/permission checks, but no trusted production signing service, immutable cross-host store, independent head custody, actual malware scan or licensed rights review exists. $0 and providers inactive.


**Verified CI-only PR #80 — recovery policy simulation:** Hash-linked, independently signed local encrypted-backup manifests can model rotation and expiration while refusing corrupt archives, but do not create an offsite recovery system, persistent authoritative head/pin custody, key storage, deletion scheduler, production backup, hosted environment or service authorization. Incremental spending remains $0.


**Verified security-checkpoint November 12, 2026:** PR #73 merged as `7f4248940a84ad40d097c4541d11eba49b3f5b4a` and full [merged-main Actions 43347901980](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43347901980) passed. Standalone local authentication and media byte-receipt WSGI transports now share loopback-only restrictions and reject untrusted proxy/original URI/method-override or ambiguous framing metadata. This applies only to deliberately local/disposable previews; production proxy trust/TLS/session/rate limits, secrets management and operational logging require separate review. No public deployment or provider provisioning has occurred. The active incremental spending limit remains **$0**.

**Candidate PR #73:** Local WSGI authentication and media-receipt transports explicitly refuse remote/forwarded/ambiguous HTTP ingress. This is defense-in-depth for disabled-by-default offline previews; deploying the same adapters behind Render, an Internet reverse proxy or public TLS is not authorized or supported without a separately reviewed production ingress architecture.

**November 12, 2026 | Planning only.** This document does not create hosting, authorize charges, enable publishing or mark BAM Beta-ready.


## Active $0 incremental-cost development policy — November 12, 2026

The owner has superseded the immediate paid-hosting direction with **$0 additional BAM costs** until either (a) a functioning application is ready to justify paid infrastructure or (b) further development demonstrably cannot proceed through practical free alternatives. These are conditions to **request a new explicit authorization**, not automatic purchase or deployment triggers.

Use free standard public-repository GitHub Actions runners with minimal duplication, artifacts and storage; local offline runtimes; and disposable PostgreSQL containers in CI. Do not provision Render Starter, Render Free, Neon Free, other providers, or use EdgePilot's existing hosting for BAM without a separate authorization. Render/Neon free tiers may still have quotas and possible overage billing. Provider account settings/budgets, quotas, billed usage and trial expiry must be checked before any later connection or trial.

The previously designed dedicated Render Starter ($7/month base) plus separate Neon Free project stays as a **deferred architectural target**; it is not the current expenditure budget. No service is active, no charges are authorized, and no eventual commercial feature is cancelled. Full tenant separation and all existing application security rules still apply. The `BAM_HOSTING_PLAN.json` development policy is reviewed in CI, but does not impose actual billing-provider limits.

## Deferred paid hosting design — selected earlier, not approved for purchase

The owner selected **one new, separate Render Starter web service ($7/month base compute)** paired with **one new Neon Free PostgreSQL project ($0/month under its usage limits)**. This is the engineering target for BAM's eventual private beta, **not authorization to create either service, incur a charge, expose BAM publicly, or deploy code**. The existing EdgePilot web service, database, tokens and credentials must remain segregated and unchanged. Use Render's Hobby workspace pricing assumption where eligible; independently confirm the actual billing workspace before provisioning.

**Planning estimate:** $7/month in base web+database compute only. The Render Starter instance has **512 MB RAM** and a small CPU allocation. Neon Free currently provides **1 GB storage and 100 compute-unit hours per project per month**; usage and plan limits can change. Render's Hobby workspace includes finite bandwidth/build allowances and charges can arise from overages; Neon Free is quota constrained. The $7 figure is **not a provider-enforced hard spending cap**.

**Unapproved, excluded extras ($0 authorized):** additional servers/background workers, scheduled/cron execution, extra databases or instance upgrades, disk/object storage, paid backups, email/OTP delivery, paid Google/Meta integrations, OpenAI API traffic, paid monitoring, bandwidth/build overages, custom domains and any other non-base charge. Each needs explicit approval or a tested free-tier alternative. Provider OAuth may not itself be billable, but connecting real accounts is still gated.

**Database strategy:** current BAM source is SQLite-oriented and cannot just be pointed at Neon's PostgreSQL URL. Create a separate, reviewed PostgreSQL persistence adapter/migration workstream; migrate identity, tenant memberships, sessions, content, invites, audits and calendar without losing atomic isolation. No real connection string is stored in GitHub. Future TLS/verified server-only credentials must use Render secrets; Neon and Render are separate projects/services.

**Reliability tradeoffs:** Render service filesystem is ephemeral; never persist production uploads, credentials or SQLite files there. Neon Free sleeps compute when idle, has quota/restore constraints and cannot replace a verified encrypted off-site backup/restore design. A single Starter web service is for a small supervised beta, not a demonstrated scalable publisher or guaranteed uninterrupted scheduler; final job execution needs a separate reliability and cost decision.

**Deployment safety:** no `render.yaml` blueprint, deployment trigger, configured service ID, Neon project ID, hosted API entrypoint or automatic deploy was introduced. `BAM_HOSTING_PLAN.json` is a read-only planning record with all activation flags disabled; `hosting_plan_contract.py` and its tests flag unauthorized drift in CI, but **do not** control Render billing or deployment actions. Explicit owner approval plus a reviewed staging rollout is still required.

**Official planning sources (checked November 12, 2026):**
- Render pricing: https://render.com/pricing
- Render ephemeral filesystem: https://render.com/docs/deploys
- Render environment variables: https://render.com/docs/configure-environment-variables
- Neon free plan limits: https://neon.com/docs/introduction/plans
- Neon Oct 2026 free-plan update: https://neon.com/blog/neon-free-plan-1-gb-per-project

## Architecture target

One trusted HTTPS API/backend serves multiple BAM users, businesses and team members. Isolate all records and permissions by **verified identity and server-selected business**. Use a durable transactional relational database for membership, sessions, drafts, reviews, audit and calendar; private object storage with scanning/quarantine for user media; a separately controlled durable work queue and worker; and a server-side encrypted credential vault, monitoring and encrypted backups. Shared resources avoid one paid server per employee, but do not grant cross-business access.

BAM should publish directly via supported official Meta/Facebook Page APIs once provider review and **separate owner activation** are complete. Metricool is not a required scheduling dependency. OpenAI API spending also needs a separately approved model, budget and key-management policy.

## Explicit trust separation

The current `BAMOfflineGateway` and `dev_http_gateway.py` are local development fixtures. BAMOfflineGateway now rejects detectable remote addresses, public Host and reverse-proxy headers before any route. **This is defense in depth, not a security guarantee**: a proxy can strip metadata, and a direct WSGI server could be misconfigured. Never deploy the offline app publicly. Create a distinct, reviewed production application factory after hosting decisions; enforce real TLS/origin/CSRF, provider verification, durable IP/global throttles, credential secrecy, restart safety and tenant isolation.

## Still-unapproved decisions before deployment

Render Starter and Neon Free are selected for *design only*. Before actual service creation, obtain an explicit authorization for the $7 recurring Render charge, confirm eligible billing workspace, identify region and domain/subdomain, decide private-beta user count, and obtain a safe plan for any necessary media storage, email delivery, encrypted backups, monitoring, scheduler and overages. None of those other services has an approved cost or activation. EdgePilot's live deployment, database, tokens and secrets are out of scope.

## Beta verification gates

- Two separately authenticated people and at least two businesses work on separate real devices; cross-business reads/writes and stale sessions are denied.
- Verified Google and email enrollment, recovery, invites, anti-abuse and revocation all work with real provider configuration.
- Durable migrations, encrypted backup/off-site retention, restore and rollback are demonstrated.
- Media is private, scanned and explicitly approved; posting remains off regardless of a stored draft or calendar proposal.
- Read-only official provider connection and analytics permission checks precede a later **separately authorized** publishing launch.
- Actual resource use, costs and data protection are measured rather than inferred from offline green CI.

**Next work before authorization:** independent production-runtime design and offline threat/regression tests. **No new paid service is added by this milestone.**

## Account-throttle shared-state hardening (offline)

The alpha login-failure counter uses one SQLite write per failed attempt and tests independent concurrent clients; this prevents an avoidable lost-update issue. The next hosted admission layer must still enforce atomic request attempt reservation, trusted client IP/device and global quotas, distributed or database-backed consistent enforcement, safe account enumeration responses and rollback/monitoring. Neither these offline tests nor a passing CI run constitute production identity security or owner authorization to deploy.


### Recovery architecture gate — disposable ciphertext is not a backup service

The offline CI archive experiment demonstrates authenticated ciphertext disk persistence under strict local permissions, no replacement and explicit hash pinning. It is deliberately guarded by the disposable test flag and inherits a 4 MiB synthetic envelope cap and seven-day freshness. Production architecture must specify: independently controlled root-key generation/custody, least-privilege restore access, rotation/re-encryption, disaster loss of application+primary site, separate offsite key and ciphertext domains, immutable version retention and legal deletion, encrypted metadata/catalog, periodic restore parity and drill evidence, recovery objective, secure disposal and incident revocation. No offsite provider, vault, retention process or recovery point exists yet.
