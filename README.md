# BAM — Belenos Automatic Marketing

**BAM is an AI-assisted marketing planning, creation, collaboration, scheduling and analytics platform for businesses.** It is designed to support multiple independent businesses and teams, with direct social-media platform integrations instead of requiring Metricool. Each business has its own voice, products, media, permissions, calendar and performance reporting. The Belenos name identifies the product's origin, not a restriction to one store or industry.

**Current release status (November 12, 2026): Offline Alpha.** The GitHub repository is public, but there is **no publicly deployed BAM application**. A local-only responsive web workspace, signed-in collaboration, held drafts, independent AI copy/image-prompt components and safety checks can be tested offline. Live Meta OAuth, social publishing, executable scheduling, native analytics ingestion, paid OpenAI API generation, hosted multi-user production and Android APK distribution are **not active**. None of the tested previews authorize publication.

**Current development spending authorization: $0 in additional charges.** Continue with local tools, standard public GitHub CI runners and disposable PostgreSQL tests. Do not activate even a nominally free hosted Render/Neon service, paid AI provider, public publishing or new infrastructure without separate approval. A dedicated $7/month Render Starter plus separate Neon Free database remains a **deferred design**, not an expense, and EdgePilot's paid hosting is strictly separate.

**Verified GitHub checkpoint:** [PR #53](https://github.com/BelenosCreations/belenos-marketing-automation/pull/53) merged at `25a99947829121b792f9d74d5542a9638d847fb9`, and full [merged-main Actions 43326407161](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43326407161) passed. `main` and `development/phase-3-5-account-directory` are identical. Synthetic, CI-only PostgreSQL supports held draft creation/revision, protected draft reads, owner roster and invitation metadata, and private review note creation/versioned editing with atomic event recording.

**Current development candidate:** Complete private feedback parity with the offline Alpha by adding a **versioned, owner/marketing-manager-only note removal** plus **read-only owner/manager history** to the CI-only PostgreSQL adapter. The removal must be authorized in its DELETE, must create a `removed` audit event in the same database transaction, and must roll back if auditing fails. Deleted note bodies must not appear in history. Cross-business users, viewers, revoked sessions and stale tokens must not modify notes or view private history. This candidate is not a deployed feature and requires exact-head PR and merged-main tests.


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
