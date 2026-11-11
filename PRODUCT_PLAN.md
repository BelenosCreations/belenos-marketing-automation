# BAM — Product Plan and Delivery Gates

**Decision baseline:** November 11, 2026  
**Project:** Belenos Automatic Marketing (BAM)  
**Planning status:** Approved direction and implementation roadmap; **not** a statement of shipped features or permission to activate services.

The authoritative product direction is **BAM-managed social publishing and analytics via direct, official platform integrations**. **Metricool is not a core dependency, not required during onboarding, and not part of the expected recurring customer stack.** This supersedes older README references to Metricool as the scheduler, source of posting-time scores, or required integration.

BAM is an industry-independent, multi-business platform. Initial test workspaces may include Belenos Creations and Busy B Cleaning Service; businesses share infrastructure, **not** their private data, content, social credentials or permissions.

## 1. Outcomes the product must deliver

1. A business owner can sign in to **one BAM account** using email/password or Google and manage multiple independently configured businesses.
2. Multiple people can collaborate **within one business** using individually authenticated, revocable memberships, role-based access, shared work queues, review feedback and configurable approval requirements.
3. Creators can produce factual marketing copy, optional image prompts and user-provided media without requiring a separate scheduler or their own OpenAI API signup.
4. BAM can, **after approval and verification**, schedule/publish directly to authorized supported accounts and capture the resulting platform status, without Metricool.
5. Audience and performance measurements, where providers permit access, drive transparent scheduling suggestions without inventing analytics.
6. One shared backend can serve many businesses and employees economically, with explicit AI/media usage policies, backups, isolation and operational controls.

These describe **target functionality**. The current stage remains **private offline alpha**.

## 2. Integration policy: direct platforms, not Metricool

### Primary social target

**Facebook business Pages via official Meta APIs** are the first planned end-to-end publishing integration. The initial launch must use supported permission and login flows; eligibility, required scopes, review, API version, rate limits, Page/business prerequisites, content formats, Page roles and token lifecycle are verified during development rather than assumed.

A BAM user connects an eligible social account through provider authorization. BAM login and social authorization are distinct. Only trusted server-side components store encrypted provider tokens; user agents receive limited connection summaries. Revoking a connection prevents further scheduled posts and permits safe cleanup/audit.

### Second and later providers

Other platforms, including Instagram professional accounts where eligible, require **separate adapter and capability reviews**. Unsupported destinations should offer a clearly labeled manual fallback rather than a claim of automatic publishing. Do **not** fall back to account-password sharing, unauthorized scraping or unstable UI automation to bypass provider API limits.

### Scheduler and analytics ownership

BAM owns calendar state, job persistence, permission/fact/media checks, idempotency, retry policy, provider request IDs, cancellation, delivery receipts and status reconciliation. It must survive the user closing the app. BAM retrieves **first-party provider insights where authorized** for analytics and posting-time optimization; when an API lacks audience data, Smart mode explicitly reports that limitation or offers grounded manual scheduling.

**Acceptance rule:** A supported platform's standard BAM workflow must not require a Metricool account, token, subscription or paid integration tier. No Metricool dependency may be introduced into the critical path without an explicit later product decision.

## 3. Team collaboration in one business

Keep the existing authorization model aligned with **owner, manager, content creator, employee and viewer**, plus action-specific permissions rather than inventing separate billing accounts or granting blanket team access.

**Planned collaboration capabilities:**

- Owner-managed invitations (issue, accept, expire, resend, revoke) tied to one business and an individual identity.
- A person may hold different roles in multiple businesses, with explicit active-workspace switching.
- Business-owned shared drafts, calendar proposals and media, with clear author/editor/reviewer attribution.
- Role-checked write, comment, approval, schedule and publish permissions; separate authority for managing social connections, AI spend, staff and billing.
- Draft-revision conflict detection, visible review feedback, stale-review warnings and auditable changes.
- Optional review gates per business/content category: for example, new promotional claims must be approved while narrowly authorized routine posts may later qualify for unattended publishing under a policy approved by the owner.
- Member removal and role changes invalidate sessions and prevent access to future updates; confidential data and provider credentials remain inaccessible to removed staff.

**Built now:** offline role/session boundaries, business switching, private reviewer feedback, metadata activity history, team counts, owner-only existing-member role/deactivation controls, revision-safe membership mutations, per-business session revocation and invitation foundations. **Not built yet:** production invitation delivery/acceptance, real shared online team hosting, finished approval/publish execution or subscription/seat administration.

**Acceptance tests:** two authorized editors see the same business drafts; a stale editor cannot overwrite newer work; members of Business A cannot access Business B; a revoked or demoted member cannot use an old session to retain elevated privileges; approvals cannot be spoofed through the client.

## 4. Content, AI and imagery

**Approved AI provider: OpenAI only.** Default BAM-sponsored API requests mean the person using BAM does not need a separate AI API account. Optionally, the person may use a **personal paid OpenAI API key**, never exposed to the browser or other employees. Do not activate this option until an encrypted secrets vault, verification, revocation and clear billing/limits exist.

**Generation contract:** one structured model request produces marketing post copy plus an **optional** image-creation prompt. Each component is stored and edited independently; regenerate only a requested component. Owner-confirmed factual inputs, explicit user choices and per-user/per-business writing memory govern the draft. Never invent discounts, claims, events, pricing or guarantees.

Use checked local templates for straightforward factual posts with no model API cost. Consider advance/batch generation when it offers measurable savings without stale facts, duplicated content or hidden publishing changes. Log accurate usage by business and user, track approved spend ceilings, and use operator-enforced quota/rate/circuit-breaker rules, not client-supplied billing claims.

**Image workflow:** users can create their own artwork in ChatGPT (Free or paid, subject to that product's limitations), revise it there and manually upload/share the image to BAM. This is optional, not a mandated sign-up, no BAM-to-ChatGPT-Free API integration, and no guarantee of free/unlimited image generation. BAM should offer a copyable prompt and clear `media_needed` state. File transfer remains **pending**, not verified, until appropriate scanning, rights and approval checks have passed.

**Built now:** owner facts, stored AI draft components, local templates, user preferences, planning previews, targeted revision offline execution boundaries and cost-control primitives. **Not live:** real paid OpenAI calls, a production secret vault, external image generation or hosted entitlement enforcement.

## 5. User experience

The main BAM screen uses **large, mobile-first summary cards** and a clear active-business identity. Details, charts, queue filters, approval actions, posting-time controls, analytics, connections and AI preferences live inside deeper views. Do not expose business-sensitive data in notifications or stale UI after switching accounts. Support Light/Dark/Auto appearance.

Deliver a usable responsive web interface first while continuing toward an Android app built with Kotlin/Jetpack Compose. Authentication, business logic, durable schedules, tokens and media live on the trusted backend, **not on a phone**.

## 6. Hosting, storage and ongoing cost design

**Shared infrastructure:** one production BAM backend serving multiple isolated business tenants, a durable transactional relational database, independent private object/media storage, background job workers and monitoring. The present local SQLite/WSGI setup is a development environment, **not** a deployed architecture. No paid hosting or third-party service is authorized by this plan alone.

**Where content lives:** drafts, verified business facts, approval/audit records, calendar/job states, analytics references, memberships and billing usage in the managed database. Original uploads and necessary derived files in private durable media storage. Published items also exist on the destination social platform. Provide encrypted backups, restore drills, retention/deletion policies, quotas and access logging as appropriate.

**Expected cost drivers:** hosted compute, managed database, media capacity/egress, backups, observability, domain/email infrastructure, maintenance labor and real OpenAI API consumption. Team membership itself should have little marginal server cost; **AI requests and media use are the more variable portions**. No mandatory Metricool fees; avoid running a separate service per employee or per small business.

Define per-business/per-user storage and AI quotas; use deduplication/retention and rate limits; meter usage and alerts; let actual observed demand trigger scaling. Any future seat/subscription fees are commercial choices, not inherent technical requirements. No claim of zero operating cost or approved end-user pricing.

**Deployment scenarios:**
- **Owner-only:** target roughly two content posts/day without requiring a separate AI payment from that owner; BAM bears explicitly capped API cost.
- **Private invited users:** around 5–10 known users, varied activity up to about two posts/day per user, with controlled sponsored costs.
- **Potential public Google Play product:** subscription or usage pricing considered later, without a pre-approved price, free quota, payment provider or launch date.

## 7. Phased implementation roadmap

### Gate A — Preserve and verify offline alpha (current)

- Keep existing tenant/session boundaries, review notes, draft conflict protection, private media quarantine and no-publishing invariant.
- Re-run the full CI Python, JavaScript and compilation suite against the **exact branch commit** before marking recent security changes verified. Treat queued/unverified runs as pending.
- Preserve README as product description, CHANGELOG as historical changes and DEVELOPMENT_CONTINUITY as a resume checkpoint.

**Exit evidence:** green exact-SHA regression run, reviewed security fixes and no accidental external/paid operation.

### Gate B — Hosted identity, persistence, media and collaboration foundations

- With **separate owner authorization**, select production hosting, budget, database, encrypted token vault, secrets, backups and service-monitoring policies.
- Migrate SQLite/offline state with transaction, concurrency and recovery guarantees. Use TLS, verified Google identity, secure password enrollment/recovery, session revocation and abuse controls.
- Complete real business invitations, membership management and private multi-device collaboration. Validate local and cross-business isolation, draft conflicts and content ownership.
- Complete trusted media validation/scanning/rights workflow before accepting content as publishable.

**Exit evidence:** two separate real accounts plus same-business team members successfully use a hosted private workspace without cross-tenant exposure, with rollback and restore tested. No publication required yet.

### Gate C — Direct provider connections and read-only analytics

- Implement verified Meta authorization for eligible Facebook Pages and safe encrypted credential lifecycle.
- Connect, list, refresh, disconnect and revoke Pages without exposing credentials or inheriting BAM login privileges.
- Test provider response validation, rate-limit handling and permissions changing/revoking.
- Import real available Page performance and audience measurements; show freshness/source, and indicate unavailable metrics.

**Exit evidence:** reviewed OAuth scopes, provider eligibility, secure credential management, live data provenance and explicit **no Metricool dependency**. Remain read-only/no posting until Gate E.

### Gate D — Reliable internal scheduling and editorial controls

- Build a durable worker/queue with business-scoped idempotency, immutable publication intents, content/media/fact/approval rechecks, timezone safety, retries, failure reconciliation and emergency pause.
- Complete optional per-business human approval policies with authoritative owner permissions and complete publication audit traces.
- Test duplicate requests, clock changes, revoked connections, expired promotions, media rejection, network ambiguity and stale drafts under concurrency.

**Exit evidence:** supervised dry runs and test doubles consistently refuse unauthorized jobs, not merely render a calendar preview.

### Gate E — Explicitly authorized Facebook Page publishing

- Require a new, unambiguous owner decision to activate live publishing, plus provider approval, integration tests and a controlled limited rollout.
- Use current eligible Page access, actual supported endpoints and platform-policy-compliant formats.
- Reconcile provider results and failed/duplicate attempts; stop on permission loss or ambiguous outcomes instead of claiming success.

**Exit evidence:** limited opt-in posts with confirmed platform receipts and audit records; tested disable/rollback. No other platform is implicitly enabled.

### Gate F — AI production activation and measured optimization

- Separately authorize a spend budget, provider credentials/plan, vault and reconciliation controls before paid OpenAI traffic.
- Connect verified OpenAI requests to structured drafts and targeted edits, record usage reliably and hold factual/media-risk outputs.
- Evaluate local templates, per-post combined requests, targeted revisions and batch generation on real cost, quality, accuracy and reliability.
- Use available first-party analytics to compare manual timing to Smart timing; never overstate confidence.

**Exit evidence:** quotas and spending limits fail closed; output quality and factual accuracy are measured; users see real provider-cost status, not fabricated invoices.

### Gate G — Broader platform support, Android and commercialization

- Add new direct providers only after independent feasibility and API-policy reviews.
- Build/release native Android UX after backend and identity/security validation; preserve one-login/multi-business boundaries.
- Consider public subscriptions, packaging, sales, seat policies and Google Play publishing only after explicit commercial decisions.

**Exit evidence:** separately verified feature permissions, reliability, privacy and economics for each new provider and launch surface.

Gates are **capability and authorization gates, not release dates**. Independent work may run in parallel, but no paid-provider access, public hosting, real social connection or publication is enabled merely because code or documentation exists.

## 8. Always-on requirements

- **Publish disabled by default.** Only the owner and an authorized production workflow can enable specifically supported account/campaign posting after separate approval.
- **No fabricated claims or analytics.** Missing or stale facts and insights are displayed as unknown/held.
- **No cross-tenant or cross-user data leaks.** Scope every business, social token, AI preference, draft, attachment and report to trusted server-side identities.
- **No secrets in GitHub, browsers, logs, client-created prompts or content fields.**
- **Do not silently charge the operator or customer.** External calls must be authorized, bounded and reconciled.
- **Do not equate a green unit test with a deployed or platform-approved service.**
- **No mandatory Metricool/third-party scheduler subscription for the core BAM experience.**

## 9. Source-of-truth documents

- [README — product overview and actual alpha status](README.md)
- [AI architecture](AI_ARCHITECTURE.md)
- [Alpha/private beta acceptance checklist](ALPHA_BETA_READINESS.md)
- [Development continuity](DEVELOPMENT_CONTINUITY.md)
- [Detailed implementation milestones](DEVELOPMENT_MILESTONES.md)
- [Changelog](CHANGELOG.md)

When a historical document mentions Metricool, treat that mention as **superseded architecture**, not an open requirement. Preserve historical notes for traceability, but implement **direct official platform integrations** as the only approved core publishing direction.
