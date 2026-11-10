# Belenos Marketing Automation

A custom marketing automation system for **Belenos Creations**, a 3D-printing and personalized-products business in Marion, Ohio. The project is designed to coordinate Facebook marketing, community engagement, relevant third-party 3D-printing content, and performance-informed scheduling while preserving clear human control over promotional claims and publishing.

> **Development status:** Offline prototype through Phase 3.2. **Publishing is disabled.** The Phase 3.2 offline prototype source and tests are now imported into this repository. Nothing in this README indicates a deployed or connected publishing service.

## Project goals

- Maintain a consistent, recognizable Belenos voice without repetitive or generic posts.
- Share original product highlights, creative projects, community questions, and useful 3D-printing discoveries.
- Use audience engagement data to choose better posting windows rather than relying on the owner's availability.
- Protect business accuracy: do not invent discounts, prices, special hours, promotions, giveaways, events, or order promises.
- Keep an auditable distinction between drafts, approvals, scheduled posts, and published posts.
- Make future operation reliable, recoverable, and maintainable as marketing needs evolve.

## Planned content streams

| Stream | Intended behavior | Approval policy |
| --- | --- | --- |
| Belenos products and services | Short, Facebook-first showcases of custom work, 3D prints, tumblers, apparel, and resin-printed artwork | New promotional claims require approval |
| Community engagement | Local, conversational posts and questions for Marion-area followers | Routine non-promotional content can become auto-eligible after activation |
| Authorized promotions and events | Use only terms and dates explicitly supplied or confirmed by the owner | Previously authorized exact terms may be reused within their scope and validity |
| Curated 3D-printing content | Mix of impressive prints, creative projects, industry news, and educational tips | Trusted-source, verified link posts may become auto-eligible; unfamiliar, sponsored, or sensitive items require approval |
| Operational reminders | Store openings, pickup expectations, order deadlines, and closures | Bound to confirmed operational facts and relevant times |

Curated content must credit its creator, distinguish outside work from Belenos work, avoid copying media without permission, and respect the capabilities and restrictions of Facebook and any scheduling provider.

## Scheduling philosophy

The system is designed to use engagement data, including Metricool audience-activity recommendations, to rank candidate publishing windows. It should account for content relevance, existing scheduled posts, spacing, deadlines, and America/New_York daylight-saving transitions.

Fixed times remain appropriate when a message is operational (for example, an opening reminder). Audience-activity scores are directional indicators, **not guaranteed engagement forecasts**. Scheduling changes should be tested against actual post performance over time.

Historical drafting schedule used during planning:
- Daily morning marketing drafts around 10:00 AM Eastern.
- Community engagement drafts Monday, Wednesday, Friday, and Saturday around 6:30 PM Eastern.
- Store reminders aligned with actual opening hours.

These are planning baselines, not promises of active automatic publishing.

## Android application and account architecture

The target experience is a native Android application (Kotlin / Jetpack Compose) backed by a separately hosted Python automation service. The server will own identities, permissions, approval decisions, audit logs, and integration credentials; the phone is a client, not the unattended scheduler. The first account will be the sole Belenos owner, with additional employee roles available later. `access_policy.py` is the initial **offline authorization policy**, not a login system or a working Android application. Biometric sign-in is a planned client capability subject to secure server-side session management.

## Safety and approval model

The intended workflow is **discover → validate → draft → review when required → schedule → reconcile → audit**.

Key safeguards:
1. **Publishing disabled by default**; separate explicit authorization is required before activation.
2. New discounts, pricing, promotions, giveaways, and event claims are never invented by the system.
3. Previously approved claims are reusable only within their confirmed terms, dates, and scope.
4. Source credibility and fact verification are distinct from content popularity.
5. Sponsored, sensitive, unfamiliar, or ambiguous third-party content is held for review.
6. Media reuse requires appropriate rights; link-and-commentary is the preferred fallback.
7. Duplicate prevention, cancellation, expiry, and an audit trail are core requirements.
8. A production integration must authenticate approvers and use least-privilege credentials.

## Technical direction

- **Language:** Python for the current offline prototype.
- **State:** SQLite in the prototype; production persistence and multi-process safety to be evaluated.
- **Scheduling:** Timezone-aware ranking using externally supplied activity scores.
- **Integration target:** Metricool and supported Facebook publishing workflows, subject to verified provider capabilities.
- **Testing:** Unit tests, followed by integration tests, failure recovery, and dry-run verification before activation.
- **Source control:** This private GitHub repository is intended to become the primary source of truth.

### Phase 3.2 prototype (imported)

The current offline package contains:
- `engine.py`: basic post staging, authorization records, deduplication, and publishing gate.
- `workflow.py`: audit log, draft approvals, discovered-event decisions, pause controls, and dry-run preparation.
- `optimizer.py`: candidate slot ranking, minimum spacing, deadline handling, and conservative third-party curation.
- `test_engine.py`, `test_workflow.py`, `test_optimizer.py`: **26 passing offline unit tests** at the time of packaging.
- `README.md`: implementation notes and known limitations.

The prototype **does not** yet implement live discovery, secure approval identity, remote scheduling, real Metricool write integration, or production-grade verification of caller-provided trust flags. A green unit-test run does not imply production readiness.

## Development roadmap

1. **Import and baseline (completed):** Phase 3.2 source, changelog, and GitHub Actions test workflow committed. Verify the first remote CI run.
2. **Validation and authorization:** Replace naive text matching and caller-controlled trust indicators with structured, authenticated facts and approval evidence.
3. **Content discovery:** Implement vetted source feeds, creator whitelisting, deduplication, attribution, and rights-aware rendering.
4. **Analytics and optimization:** Retrieve Metricool timing and performance data, score windows, and measure outcomes with controlled adjustments.
5. **Scheduling integration:** Verify provider capabilities, build idempotent scheduling and reconciliation, and test cancellation, retries, and outage recovery.
6. **Controlled rollout:** Require explicit owner approval before enabling any unattended publishing; start with limited, observable categories.

## Operational boundaries

**No live publishing, post scheduling, or automatic reposting is authorized by this repository or its README.** Development, testing, and deployment are separate from authorization to publish. Business-specific promotional content must remain grounded in confirmed facts.

## Documentation and release discipline

Maintain a `CHANGELOG.md` recording each release's version, date, added/changed/fixed items, test status, and known limitations. Use Git history and tagged releases for reproducible versions. Never commit passwords, access tokens, private keys, or customer information.

---

**Business:** Belenos Creations · Marion, Ohio  
**Project:** Belenos Marketing Automation  
**Status:** Active development · publishing disabled

## Phase 3.4 session prototype

`sessions.py` provides an **offline, server-side** session storage prototype with opaque random bearer tokens, SHA-256 hashes at rest, expiry, and revocation. This is not a login system: identity verification, employee enrollment, role freshness, secure HTTPS transport, credential handling, API middleware, CSRF protection (if cookies are used), and mobile biometric unlock still require implementation and security review. Production access must validate current account membership and role on every request; a session's stored role alone is insufficient. No publishing capability has been enabled.

## Phase 3.5 account directory (development branch)

`accounts.py` introduces an offline tenant-scoped membership directory with owner-managed employee roles and deactivation. Every authorization decision can consult current membership rather than trusting a role embedded in an older session or supplied by a client. The current bootstrap and member management methods are **not HTTP endpoints** and must not be exposed until authenticated server middleware and a secure invitation flow exist. Phase 3.5 is being developed on `development/phase-3-5-account-directory`, separate from `main`. Publishing is still disabled.

## Phase 3.6 approval gateway (development branch)

`approval_gateway.py` combines session validation with current account-directory membership to gate draft approvals and event confirmation. This is an offline integration prototype only. **Security blocker:** the original `posts` and `discovered_events` tables have no tenant ID, so this gateway must not be exposed over HTTP or used in a multi-tenant deployment until resource ownership is enforced in storage and queries. Direct calls to legacy workflow functions also bypass the gateway; production must provide a single enforced authorization boundary. No publishing or scheduling integration is active.

## Phase 3.7 content ownership (development branch)

`tenant_resources.py` introduces immutable tenant ownership for legacy posts and discovered events. The approval gateway now rejects unowned and cross-tenant resources. Trusted ingestion must register ownership; the ownership registry must never be exposed as a client-controlled API. This is a transitional safeguard, not complete multi-tenant storage isolation: production still requires tenant columns, foreign keys, tenant-filtered queries, and a single enforced authorization boundary. Facebook publishing remains disabled.
