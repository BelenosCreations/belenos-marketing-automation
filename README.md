# BAM — Belenos Automatic Marketing

**BAM (Belenos Automatic Marketing) is a general-purpose, multi-tenant marketing management and automation platform for businesses of any industry.** Belenos is the software brand, not a restriction on which businesses can use BAM.

The platform is being designed to support independent organizations, multiple businesses under one owner login, and eventually separate business owners and employee teams. Each business maintains isolated branding, industry topics, creator recommendations, competitor exclusions, campaigns, social accounts, content approvals, schedules, analytics, and access permissions.

**Belenos Creations and Busy B Cleaning Service are initial development and testing examples only.** They are not hard-coded target industries, required tenants, or the intended limits of the product.

> **Development status:** Offline prototype through Phase 5.1. Publishing is disabled. The platform is not yet a deployed multi-user service or finished Android application.

## Product identity

- **Official product name:** BAM
- **Expanded name:** Belenos Automatic Marketing
- **Tagline (working):** Your marketing. On autopilot.
- **App display name:** BAM
- **Brand positioning:** An industry-independent marketing automation platform for multiple businesses and independent owners.
- **Existing GitHub repository:** `BelenosCreations/belenos-marketing-automation` (retained to preserve links and development history; repository renaming is not part of this documentation change).
- **Trademark and app-store availability:** Not yet verified; perform checks before public launch.

## Platform-wide design principles

- **Industry-agnostic:** Any business can define its own categories, sources, audience, brand voice, marketing goals, and policies; 3D printing and commercial cleaning are only sample configurations.
- **Multi-tenant isolation:** Data and permissions for one business cannot be reused by another without explicit authorization.
- **Flexible account structure:** One person can manage several businesses; separate owners can have independent accounts and installations; staff roles remain scoped to their business.
- **Creator and competitor safety:** A relevant creator for one industry is not automatically relevant for another, and local competitors are excluded or held for review.
- **Controlled automation:** Business owners control publishing policies; no live publishing is enabled during prototype development.
- **Future-ready architecture:** Mobile and backend components should avoid assumptions about a particular brand, city, industry, or sole operator.

## Project history and examples

The initial pilot businesses are Belenos Creations (custom creations and 3D printing) and Busy B Cleaning Service (commercial cleaning), both in Marion, Ohio. Their existing marketing workflows provide practical test cases for tenant isolation, content relevance, and role-based permissions. Business-specific examples elsewhere in this README are illustrative, not platform requirements.

## Platform goals

- Maintain a consistent, recognizable voice for each business without repetitive or generic posts.
- Support industry-specific product and service highlights, community questions, educational resources, and relevant creator discoveries.
- Use each business's audience engagement data to choose posting windows rather than relying on an owner's availability.
- Protect each business's accuracy: do not invent discounts, prices, special hours, promotions, giveaways, events, or order promises.
- Keep an auditable distinction between drafts, approvals, scheduled posts, and published posts.
- Make future operation reliable, recoverable, and maintainable as marketing needs evolve.

## Planned content streams

| Stream | Intended behavior | Approval policy |
| --- | --- | --- |
| Business-specific products and services | Short, Facebook-first showcases of custom work, 3D prints, tumblers, apparel, and resin-printed artwork | New promotional claims require approval |
| Community engagement | Local, conversational posts and questions for Marion-area followers | Routine non-promotional content can become auto-eligible after activation |
| Authorized promotions and events | Use only terms and dates explicitly supplied or confirmed by the owner | Previously authorized exact terms may be reused within their scope and validity |
| Curated industry-specific content | Mix of impressive prints, creative projects, industry news, and educational tips | Trusted-source, verified link posts may become auto-eligible; unfamiliar, sponsored, or sensitive items require approval |
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
**Project:** BAM (Belenos Automatic Marketing)  
**Status:** Active development · publishing disabled

## Phase 3.4 session prototype

`sessions.py` provides an **offline, server-side** session storage prototype with opaque random bearer tokens, SHA-256 hashes at rest, expiry, and revocation. This is not a login system: identity verification, employee enrollment, role freshness, secure HTTPS transport, credential handling, API middleware, CSRF protection (if cookies are used), and mobile biometric unlock still require implementation and security review. Production access must validate current account membership and role on every request; a session's stored role alone is insufficient. No publishing capability has been enabled.

## Phase 3.5 account directory (development branch)

`accounts.py` introduces an offline tenant-scoped membership directory with owner-managed employee roles and deactivation. Every authorization decision can consult current membership rather than trusting a role embedded in an older session or supplied by a client. The current bootstrap and member management methods are **not HTTP endpoints** and must not be exposed until authenticated server middleware and a secure invitation flow exist. Phase 3.5 is being developed on `development/phase-3-5-account-directory`, separate from `main`. Publishing is still disabled.

## Phase 3.6 approval gateway (development branch)

`approval_gateway.py` combines session validation with current account-directory membership to gate draft approvals and event confirmation. This is an offline integration prototype only. **Security blocker:** the original `posts` and `discovered_events` tables have no tenant ID, so this gateway must not be exposed over HTTP or used in a multi-tenant deployment until resource ownership is enforced in storage and queries. Direct calls to legacy workflow functions also bypass the gateway; production must provide a single enforced authorization boundary. No publishing or scheduling integration is active.

## Phase 3.7 content ownership (development branch)

`tenant_resources.py` introduces immutable tenant ownership for legacy posts and discovered events. The approval gateway now rejects unowned and cross-tenant resources. Trusted ingestion must register ownership; the ownership registry must never be exposed as a client-controlled API. This is a transitional safeguard, not complete multi-tenant storage isolation: production still requires tenant columns, foreign keys, tenant-filtered queries, and a single enforced authorization boundary. Facebook publishing remains disabled.

## Phase 3.8 native tenant storage (development branch)

`tenant_content.py` implements separate tenant-keyed posts, approvals and discovered events. `tenant_approval_service.py` checks session validity and current account permissions before changing these tenant-scoped records. The same post or event ID can exist in different tenants without crossing data. This is a new offline storage path, **not** a migration or production-ready API. Legacy workflow entry points remain unscoped and must be isolated from future external interfaces. Test cases are committed but full execution has not been verified. Publishing is disabled.

## Phase 3.9 employee invitations (draft PR #1)

`invitations.py` provides an offline, owner-authorized invitation lifecycle: single-use bearer token, expiry, revocation, and role-limited enrollment. Invitation tokens are hashed in storage. Redemption is **not** a signup/login system: it must be invoked only after an independent server-side identity verifier has authenticated the intended employee. No invitation email is sent and no employee account has been created outside test fixtures. Draft [pull request #1](https://github.com/BelenosCreations/belenos-marketing-automation/pull/1) is open for review and CI; it is not merged. Production remains disabled.

## Phase 4.0 general-purpose business curation

The platform targets independent businesses and multiple businesses under one owner account. `business_curation.py` stores separate industry/topic/source allowlists for each business; approving a 3D-printing creator for Belenos does not approve that creator for Busy B Cleaning Service. Known competitor source domains can be blocked per business, and unknown or possibly competing local sources require review. This is offline policy scaffolding, not a verified competitor-discovery service. Trusted administration, platform profile identity matching and authenticated APIs remain future work. No automatic content sharing or publishing is enabled.

## Phase 4.1 multiple businesses per login

`business_switcher.py` provides a read-only, server-side business selector for one authenticated identity with different roles across business tenants. It immediately reflects membership deactivation. This is not an Android UI or a finished login flow. Curation remains strictly business-specific; competitor screening status must come from trusted review, not client input. For social networks with shared domains, future blocking must use verified creator/page IDs rather than blanket host blocking. Tests and CI execution remain unverified. Publishing remains disabled.

## Phase 4.2 verified creator identities

`creator_identities.py` adds business-specific allow/review/block decisions keyed by social platform and verified creator account ID. This avoids blocking all of Facebook or YouTube when excluding one local competitor. An identity approved for Belenos does not become approved for Busy B. Missing verification or unknown identities are held. The module is an offline policy only: a trusted identity-verification provider, combination with topic curation, and authorization-gated management are still required. Creator approval is not permission to copy content or to publish automatically. No publishing is enabled.

## Phase 4.3 combined recommendation gate

`recommendation_gate.py` requires both a verified creator account approved for the selected business and an approved source/topic match. Known competitor blocks override approvals, and uncertain local competition remains review-required. The result `eligible_link_only` means *eligible for editorial consideration*, never permission to publish or reproduce media. Integration into real discovery, verified screening, and authenticated administration remain future work. Publishing remains disabled.

## Phase 4.4 editorial discovery inbox

`editorial_inbox.py` adds a tenant-scoped, deduplicated review inbox for curated third-party links. Combined source and creator screening runs before an item is queued; even eligible links are review-only. When re-screening identifies a blocked creator, the prior queued entry is removed. **Outstanding security work:** existing inbox items are not automatically re-evaluated when policies change, so any future approval/scheduling action must perform fresh server-side checks. No live ingestion, publishing, or Android UI is connected.

## Phase 4.5 fresh editorial screening and general-purpose categories

`EditorialInbox.recheck_for_editorial_review` re-evaluates creator identity, tenant/topic, source approval and local competitor screening before a queued link can proceed to **human editorial review**. Changed identity or topic is rejected; a blocked creator removes the queued item. This is not authorization to schedule or publish. The shared-domain competitor blocker now rejects Facebook, Instagram, YouTube and other major social hosts; competitor profiles must be excluded by verified platform account ID. The offline optimizer also recognizes business-neutral categories such as facility care, community, best practices and case studies so Busy B content is not rejected merely for being unrelated to 3D printing. All tests remain unverified pending actual execution; no live posting or production API is enabled.

## Phase 4.6 authenticated editorial review

`editorial_review_service.py` enforces an active owner or marketing-manager role in the requested business before the review-only `EditorialInbox.recheck_for_editorial_review` operation. It checks current membership rather than trusting stale session roles, and a revoked or expired session cannot review. It does **not** approve, schedule or publish content. A trusted backend must resolve and verify creator identity and competitor status independently of client input before exposing any API. Tests were added but have not been confirmed passing in CI. No live publishing is enabled.

## Phase 4.7 server-attested editorial screening

`editorial_attestations.py` stores expiring creator identity and local competitor screening attestations by business and original link. `EditorialReviewService` now looks up current server-side attestations and does not accept client-provided clearance flags. Missing or expired attestations hold content for review. A future trusted verification worker must produce these attestations; this implementation is **not** itself an identity verification service. No scheduling or publishing is authorized. Tests are committed but execution remains unverified.

## Phase 4.8 — authenticated editorial intake

`editorial_intake_service.py` connects the review-only discovery inbox to current tenant membership and expiring server-side creator attestations. An authorized owner or marketing manager can submit a candidate for editorial consideration, but the interface does **not** accept client-provided creator-verification or competitor-clearance flags. Unknown or expired attestations do not enter the queue. A later competitor block removes the matching queued item when re-evaluated. This remains an offline application service, not a public HTTP endpoint or live content crawler. **No scheduling, auto-sharing or publishing is enabled.** Ten additional tests were committed but their execution has not been verified. Future work must supply real trusted attestations and independently re-evaluate policies at publication time.

## Phase 4.9 — review integrity and verification freshness

Editorial inbox entries now persist a SHA-256 digest of the original candidate's source, URL, topic category, summary, claim-verification flags, and content safety flags. Review rechecks fail closed when a candidate has been modified after intake; an existing database row without a digest must be re-enqueued and cannot be silently grandfathered in. This prevents substituting a different summary or source after initial screening. Trusted creator/competitor attestations are capped at **24 hours**, with expiration still enforced at use time. Additional regression tests cover changed summaries, changed source URLs, changed verification flags, and overlong attestation lifetimes. The digest is an integrity comparison, **not** proof that the original claims are true. Test execution and CI status remain unverified; external verification and publishing are not connected.

## Phase 5.0 — Content Requests and held drafts

BAM can now preserve a prepared, business-specific marketing draft while requesting missing user material instead of inventing details or discarding the idea. The offline `content_requests.py` service stores the draft, channel, actionable capture suggestions, required items, content references, priority, and timestamps per tenant. Drafts begin in **needs_content**; supplying some requirements does not unlock them. Only when all required items have nonempty content references does a draft transition to **ready_for_review**—never automatically to scheduled or published. Requests can be postponed or marked unavailable and resumed as appropriate. Other businesses' requests cannot be retrieved or completed through this tenant-scoped storage interface. The implementation has nine committed regression tests, but execution is not yet verified.

**Planned UI:** A Content Requests inbox with cards showing the prepared post, missing photo/video/detail/permission checklist, suggested shots and questions, upload or attach actions, priority, and business filters. Missing-content posts must not block other eligible marketing work. Future integration must validate uploads and permission evidence server-side, enforce authenticated membership on every action, and re-run the publishing policy after completion. The present storage service does not authenticate users, upload media, schedule, or publish posts.

## Phase 5.1 — authenticated Content Requests boundary

The offline `content_request_service.py` now wraps Content Requests creation, retrieval, listing, supplying materials and hold-state updates with session validation and **fresh business membership checks on every operation**. Owners, marketing managers and content creators may prepare and update drafts according to the existing role policy; viewers can read but cannot modify them. Expired or revoked sessions, deactivated staff, role downgrades and cross-business requests are denied. Fourteen regression tests cover these behaviors and confirm that providing all required content results only in `ready_for_review`, not publication. Tests are committed but not yet independently verified. The storage class remains an internal trusted component; no public API, actual media-upload verification or publishing permission is provided.
