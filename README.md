# BAM — Belenos Automatic Marketing

**BAM is an AI-assisted marketing planning, creation, collaboration, scheduling, and analytics platform for businesses.** It is intended to replace the need for a separate marketing scheduler such as Metricool for its core supported workflows. Each business has its own workspace, brand voice, content, social connections, team permissions, and reporting. BAM is the product name; it is **not limited to Belenos Creations or any particular industry**.

> **Current status — November 11, 2026:** **Private offline alpha, not a deployed commercial service.** A responsive, authenticated local web interface and extensive Python/JavaScript backend foundations exist on the active development branch. Real social-account OAuth, live analytics, executable post scheduling/publishing, paid OpenAI calls, production hosting, and an Android APK are **not yet active**. Publishing remains **disabled** and requires separate, explicit authorization. See [alpha readiness](ALPHA_BETA_READINESS.md) and [development continuity](DEVELOPMENT_CONTINUITY.md).

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

The existing offline alpha already has tenant-scoped sessions, role checks, business switching, shared draft data, version-safe editing, private reviewer notes, activity metadata and team counts and owner-only existing-member details. Role changes or removals require a second confirmation, current membership revision and a current owner session, revoke only the affected business's sessions, and record an audit event. **Owner-only management of existing members is now implemented in the offline Alpha Settings view, including role changes and access removal. Invitation delivery, ownership transfers, reactivation, production hosting and real multi-device collaboration remain unimplemented.** Business switching must immediately invalidate stale private UI and prevent cross-business data leakage.

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

## GitHub branches, recovery and release discipline

On **November 11, 2026**, the backlog of Alpha development was reconciled into `main` through [pull request #2](https://github.com/BelenosCreations/belenos-marketing-automation/pull/2), merge commit `f774564d7348e47f34ae0ee9da6279cf14a93677`. The merge preserves both the advanced development history and the independent branding commits originally on `main`. The exact integration SHA `748c3a1a` passed push and PR CI, and [GitHub Actions run 43100795231](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43100795231) **passed on the merged `main` commit**. The active development branch was then fast-forwarded to the same verified commit, without force-pushing.

Independent recovery branches were saved at `checkpoint/alpha-last-green-2026-11-11` (`74e55d53`), `checkpoint/alpha-ci-green-2026-11-11` (`cff912f9`) and `checkpoint/alpha-pre-merge-2026-11-11` (`f66522a4`). These are Git references, not enforced branch protection or off-site backups.

**Ongoing policy:** New features stay on the development branch; after a meaningful tested milestone (or before divergence exceeds roughly 50 commits), use a reviewed pull request to merge into `main`, then fast-forward development to the resulting verified merge. Never rewrite history or delete checkpoints as part of routine synchronization. Verify the exact merge candidate with full offline CI, and verify `main` again after merging. A green test run is not approval to deploy, connect paid APIs, or publish posts.
