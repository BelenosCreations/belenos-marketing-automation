# BAM — Belenos Automatic Marketing

**BAM (Belenos Automatic Marketing) is a general-purpose, multi-tenant marketing management and automation platform for businesses of any industry.** Belenos is the software brand, not a restriction on which businesses can use BAM.

The platform is being designed to support independent organizations, multiple businesses under one owner login, and eventually separate business owners and employee teams. Each business maintains isolated branding, industry topics, creator recommendations, competitor exclusions, campaigns, social accounts, content approvals, schedules, analytics, and access permissions.

**Belenos Creations and Busy B Cleaning Service are initial development and testing examples only.** They are not hard-coded target industries, required tenants, or the intended limits of the product.

> **Development status:** Offline prototype with owner approval-intent recording through Phase 7.8. Publishing is disabled. The platform is not yet a deployed multi-user service or finished Android application.

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

## Phase 5.2 — Content Requests attachment validation boundary

`content_attachments.py` introduces tenant- and request-scoped attachment metadata with pending, verified, and rejected states. The authenticated Content Request service now requires a **verified attachment ID matching the exact business, request and checklist item** before marking a requirement supplied. Pending, rejected, cross-tenant, cross-request and wrong-item references cannot satisfy a requirement. A SHA-256 format check and supported media-type allowlist are included; finalized attachment decisions cannot be silently reversed. Ten new attachment tests and two service tests cover these controls.

**Security and product limitations:** This is a database-backed *validation boundary*, not an implemented uploader or real scanner. The `validate_trusted` method is an internal privileged operation and must not be exposed to mobile clients. A production worker must actually inspect bytes, verify hashes, scan media, validate permissions/consent and protect private storage before it can mark an attachment verified. The lower-level `ContentRequests.provide` method is also internal-only; external callers must use the authenticated service. No posts can be scheduled or published from this feature. Tests are committed but have not yet been independently executed.

## Phase 5.3 — Content Requests dashboard read model

`content_request_dashboard.py` provides a read-only, authenticated dashboard projection using the existing Content Request service rather than querying tenant data directly. It returns business-scoped counts by hold/review status and per-draft cards with prepared post text, capture suggestions, missing versus supplied checklist items, priority and timestamps. Each card explicitly indicates that it **cannot publish or schedule**, and the overall projection keeps publishing disabled. Five additional tests cover missing-item tracking, partial completion, cross-business isolation, revoked sessions and postponed drafts. This is a backend dashboard view model, **not a rendered Android UI**. Tests are committed but execution remains unverified. Actual uploads, scanner/consent verification, and deployment are not yet implemented.

## Phase 5.4 — authenticated upload preflight

`content_upload_preflight.py` adds a preflight boundary for future mobile attachments. It checks the current session, business membership, edit permission, active content request, required checklist item, allowed MIME type, SHA-256 format and per-type size cap (20 MiB images/PDF, 250 MiB MP4, 1 MiB text). A private storage identifier and attachment ID are generated by the server; the attachment remains **pending**, and the response deliberately contains **no upload URL** until a trusted storage adapter exists. Ten tests cover authorization, limits, held drafts, invalid items, session revocation and pending-only behavior. **This does not transfer or inspect any file bytes**, and user-supplied MIME/hash metadata is not treated as verified. Next work: real authenticated storage adapter, streaming byte/hash verification, malware/media inspection, customer-consent evidence and actual Android UI. Tests are committed but not independently run. No publishing is enabled.

## Phase 5.5 — offline attachment byte integrity inspection

`content_byte_inspector.py` adds an offline byte-inspection layer for future trusted private-storage workers. It checks a file's actual SHA-256 against the expected digest, rejects empty/oversized files, checks simple PNG/JPEG/WebP/PDF/MP4 signatures, and requires UTF-8 for text. Inspection of pending attachment records is tenant-scoped and **does not approve the attachment**. Ten additional tests cover successful hash checks, mismatches, invalid signatures, wrong-tenant access and nonapproval after inspection.

**Important limits:** File signatures and hashes do not prove a file is safe, accurately labeled, fully parseable, or authorized for publication. Real uploads, robust media decoding, malware scanning, permission/consent verification, storage isolation and a trusted verifier workflow are still required. The existing internal `validate_trusted` method must never be exposed directly to clients. Tests are committed but have not been independently executed; publishing remains disabled.

## Phase 5.6 — Manual or Smart posting-time selection

Each business will be able to choose **Manual** (explicit weekday/time slots in its own timezone) or **Smart** (explainable suggestions using post subject, intended audience, preferred hours and any supplied engagement-by-hour observations). `posting_schedule_policy.py` introduces the offline planning engine, including exact-minute manual slots, local timezone handling, daylight-saving gap rejection, and an explicit per-post time override that takes precedence over either mode. Manual times are not moved by engagement heuristics. Smart results are suggestions, not claims of measured best posting times; there is no platform analytics connector yet. The planner **holds incomplete or unapproved posts regardless of mode**, and only returns a proposed time; it never publishes or queues a job. Twelve regression tests were added. This policy is not yet persisted in account settings or exposed through Android screens. Tests are committed but not independently executed.

**Future UI:** Settings → Scheduling → Manual / Smart for each business; weekly time editor for Manual; audience, subject and platform-aware recommendations for Smart; per-post override; transparent explanation for suggested times. A business may use Smart as its default while pinning time-sensitive announcements to exact manual times.

## Phase 5.7 — persistent per-business scheduling settings

`scheduling_settings.py` persists the approved Manual/Smart mode, business timezone, exact weekday/time slots and preferred smart hours in a tenant-scoped SQLite table. Reads and writes recheck current business membership through `AccountDirectory`; viewers can read, but only users with draft-edit privileges may change settings. An optional revision check prevents accidental overwrites from stale editing sessions. Nine regression tests cover round-trips, role restrictions, cross-business isolation, revoked membership and edit conflicts. This is an internal offline repository, **not an authenticated HTTP API or Android settings screen**. The calling server must authenticate identity and construct principals; client claims must never be trusted. The planner still only proposes times, and publishing remains disabled. Tests committed, execution not yet verified.

## Phase 5.8 — authenticated scheduling settings boundary

`scheduling_settings_service.py` wraps saved scheduling preferences in session-token verification and fresh business membership resolution. Expired or revoked tokens, cross-business requests, removed members and viewer write attempts are denied. Owners and other authorized draft editors can update settings; viewers may read them. Optimistic revision checks continue to protect concurrent edits. Seven regression tests cover these scenarios. The service is offline application logic, not an HTTP endpoint or mobile screen. No job scheduling or publishing has been enabled; tests committed but not independently executed.

## Phase 5.9 — saved scheduling preferences integrated into planning

`business_scheduling_planner.py` now connects the authenticated business scheduling settings service to the offline posting-time planner. It retrieves the correct tenant's saved Manual/Smart mode, exact weekly times, timezone and preferred hours, then produces a proposal with mode, settings revision, reason and explicit `publishing_enabled=False`. Businesses without configured settings receive a `not_configured` result; missing-content and unapproved posts remain held. Cross-business and expired-session requests are denied by the settings service. Seven regression tests cover these paths. No job queue, platform integration, network API, or Android UI exists in this milestone. Tests committed; execution remains unverified.

## Phase 6.0 — scheduling settings screen data contract

`scheduling_settings_view.py` exposes a strict, JSON-compatible data contract for a future Android Manual/Smart scheduling screen. It presents available modes, exact weekly posting times, business timezone, preferred smart hours and settings revision, and accepts validated edits through the authenticated settings service. Unexpected fields are rejected, including attempts to inject publishing controls. Viewers remain read-only and other businesses remain isolated. Seven additional tests cover round-trips, mode switching, stale edits and authorization. **This is not a rendered screen, HTTP API, or connected publishing scheduler.** Tests are committed but not independently executed. Publishing remains disabled.

## Phase 6.1 — authenticated multi-post schedule preview

`scheduling_preview.py` uses a business's saved Manual/Smart settings to generate a **read-only preview** of up to 30 proposed post times. It preserves the configured exact manual slots, advances a cursor so proposed posts do not share a slot, and visibly holds incomplete or unapproved drafts. The preview reuses authenticated business settings and returns the settings revision, mode and an explicit `publishing_enabled=False` marker. Six regression tests cover manual times, multiple posts, held drafts, expired sessions and tenant isolation.

**Trust boundary:** The current preview accepts in-memory `PostContext` values supplied by its server caller. Their approval/readiness booleans are **not verified against authoritative content or approval records**. This is acceptable only for an illustrative preview, never for a publishing decision. Future production scheduling must re-read server-owned approval, attachment and policy state immediately before creating any job. No jobs, HTTP endpoints, Android screen or live platform actions are implemented. Tests committed, execution not independently verified.

## Verification checkpoint — executed baseline and release gate

The archived Phase 3.2 offline package was independently extracted and its unit tests executed locally: **26 tests passed, 0 failures, 0 errors**. This confirms only the archived Phase 3.2 engine/optimizer/workflow baseline; it **does not** verify the newer Phase 3.5–6.1 GitHub development modules. The existing GitHub Actions test workflow was identified, but no passing current-branch CI result was confirmed. See [VERIFICATION.md](VERIFICATION.md) for the command, scope, result and remaining release gates. BAM remains a nonpublishing development prototype until the current-branch suite and security/integration checks are complete.

## Phase 6.2 — TruthGuard approved fact foundation

**TruthGuard** is an approved anti-hallucination feature. The first offline milestone adds `truthguard_knowledge.py` (per-business approved facts with source, approver, approval time, optional expiration and revocation) and `truthguard_review.py` (strict normalized claim-to-fact matching with evidence references). Unsupported, expired, revoked or cross-business claims are held. The reviewer is deliberately conservative: an entire draft **always remains held**, even when all supplied claims match, because supplied claim lists do not prove that every factual statement was extracted. Twelve regression tests cover provenance, exact matching, expiry, revocation, tenant separation and fail-closed behavior.

**Security limitations:** Fact approval/revocation functions are internal trusted-server primitives and must not be exposed to untrusted clients. Authentication, source authenticity, automated complete claim extraction, external source retrieval, consent and the final server-owned publish eligibility gate remain to be implemented. TruthGuard cannot guarantee hallucination-free output. No live publishing is enabled. Tests are committed but not independently executed.

## Phase 6.3 — authenticated TruthGuard fact administration

`truthguard_fact_service.py` adds session-token and fresh membership checks around the approved business fact registry. The conservative initial rule allows only a current business **owner** to approve, inspect or revoke authoritative facts. An expired/revoked session, cross-business request or nonowner cannot modify the verified knowledge base. Eight regression tests cover these boundaries. The underlying knowledge registry remains an internal trusted-server component and must not be exposed directly. Source accuracy still depends on the owner's confirmation; this does not independently validate external facts. No HTTP endpoint, Android screen, complete claim extraction or publishing integration exists. Tests committed but not independently executed; publishing remains disabled.

## Phase 6.4 — TruthGuard content-request review integration

`truthguard_content_review.py` connects authenticated, tenant-scoped Content Requests to TruthGuard claim review. The integration reads the server-stored draft text and content status, verifies any supplied claim statements against current business-approved facts, and returns a read-only review report with supporting evidence and missing-content visibility. It never mutates approvals or publishes; the entire draft remains held even if the submitted claim list matches approved facts, because complete claim extraction has not been established. Seven regression tests cover verified/unsupported claims, missing content, expired sessions, cross-business access and missing requests. Tests committed but not independently executed. Publishing remains disabled.

## Phase 6.5 — TruthGuard source-span integrity audit

`truthguard_span_audit.py` checks that claim annotations refer to **exact character spans in the stored draft**. It rejects mismatched, malformed, overlapping and out-of-bounds annotations; records unannotated text and a SHA-256 fingerprint of the draft. The authenticated `truthguard_content_review.py` now includes this audit in read-only review results. Ten dedicated tests and two integration tests were committed. This catches claim-list manipulation and omissions visible as uncovered text, but **does not identify which uncovered passages are factual**, prove extraction completeness or validate claims by itself. Even complete annotation coverage does not authorize publication. All posts remain held. Current-branch test execution has not been confirmed.

## Phase 6.6 — TruthGuard draft-grounding boundary

TruthGuard now distinguishes **a fact that exists in the approved knowledge base** from **a factual claim actually present in the server-stored draft**. A claim can be labeled verified against the knowledge base while still being *detached* from the draft if no matching exact source-span annotation exists. The authenticated content review reports `detached_claims` and `claims_grounded_in_draft`; detached claims do not count as grounded evidence. Three regression tests cover detached, exact-span and mismatched-span cases. This is a conservative review improvement, not complete factual-claim extraction. Drafts remain held; publishing is disabled. These tests are committed but have not yet been independently executed.

## Phase 6.7 — TruthGuard high-risk marketing claim signals

`truthguard_risk_signals.py` performs a deterministic, conservative scan for potential price/discount, guarantee, time-sensitive availability, business-hour and testimonial statements. It returns matching source spans for editorial review. Authenticated TruthGuard Content Request reports now include these signals alongside approved-fact matches, exact claim-span integrity, and unannotated text. Ten regression tests were committed. **Important:** this is a heuristic warning layer, not comprehensive claim extraction, independent fact verification or a publishing authorization. An empty signal list does not prove accuracy. Drafts remain held, and publishing stays disabled. Current-branch test execution is not yet verified.

## Phase 6.8 — TruthGuard untrusted-input hardening

The authenticated Content Request review now validates the full caller-supplied claim collection before draft-span comparison: at most 100 entries, exact `key` and `text` fields, and nonempty string values. This prevents malformed nested or unhashable values from triggering unexpected errors and keeps the review boundary fail-closed. Two regression cases cover malformed and oversized claim inputs. The existing review remains nonpublishing and tenant-scoped. The GitHub connector can commit source and tests but does not expose a workflow-dispatch operation; no production release is implied.

## Phase 6.9 — Temporal validity of approved facts

TruthGuard knowledge lookup now requires `approved_at <= review_time` in addition to non-revocation and unexpired validity. This prevents a fact with a future approval timestamp from being treated as already authorized evidence. Five regression cases cover future approvals, boundary-time activation, expiration, tenant separation and revocation. Review reports remain nonpublishing; no live publishing integration is enabled.

## Phase 7.0 — Risk-signal review coverage

Authenticated TruthGuard content review now correlates heuristic high-risk phrases with source-span annotations in the **stored draft**. The report includes `uncovered_risk_signals` and `risk_signals_annotated`, allowing an editor to distinguish flagged pricing, urgency, availability and other risk signals that have not been annotated. Annotation coverage is not evidence of accuracy, complete factual extraction, owner approval or publishing eligibility. Two regression tests cover uncovered statements and covered-but-still-held statements. Publishing remains disabled. The existing GitHub Actions workflow runs offline unit tests on push and pull requests; an independently confirmed current-branch result is not available from the connected workflow-run interface.

## Phase 7.1 — Draft-bound review receipts

`truthguard_review_receipt.py` creates deterministic SHA-256 review receipts binding a **held** TruthGuard report to its business, Content Request ID, draft fingerprint, and review timestamp. Validation rejects stale draft text, wrong tenant/request, changed report contents, and altered receipt flags. Eight regression tests cover these boundaries. Receipts are **integrity checks, not cryptographic signatures or proof of authentic approval**: a party able to replace both payload and digest can forge them. Production use requires trusted server-side persistence, access control, immutable audit storage and a separate owner-approval workflow. Receipt generation never enables scheduling or publishing.

## Phase 7.2 — Authenticated owner approval intent (nonpublishing)

The offline `approval_intent_service.py` records owner-authenticated **approval intent** only when a Content Request has all required content and a draft-bound, held TruthGuard review receipt validates. It stores tenant/request/draft/receipt identifiers, acting owner and timestamp; the owner can revoke the record. Inspection compares the current draft fingerprint to the recorded one and exposes whether the intent is active and draft unchanged. Cross-tenant sessions and non-owner identities are denied. Five regression tests cover incomplete content, owner recording, cross-tenant denial, stale receipts and revocation. **This is not final marketing approval or a publishing/scheduling permission.** Review completeness, full factual extraction, trusted persistence and publication authorization remain separate future gates. No live publishing is enabled.

## Phase 7.3 — Approval-intent lifecycle safety

Inspection of an existing owner approval-intent record now checks both the draft fingerprint **and the current Content Request readiness status**. A postponed, unavailable, or otherwise incomplete request is flagged `content_complete: false` and `requires_new_review: true`, even if its text has not changed. The additional regression case covers a completed draft that is later postponed. The intent ledger remains read-only for downstream automation: neither an active intent nor a complete request authorizes scheduling or publishing. Future work must also bind approval to current verified attachment identities and immutable revision history before any execution gate is enabled.

## Phase 7.4 — Supporting-content change detection

Owner approval-intent records now store a deterministic SHA-256 snapshot of the request channel, required content items, and supplied attachment references at the time intent is recorded. Inspection compares the current snapshot with the recorded one. Replacing a photo or other supporting item flags `content_unchanged: false` and `requires_new_review: true` even when the marketing copy remains identical and all required items remain present. Existing databases migrate by adding the snapshot column; older records without a snapshot fail closed and require a new review. Three regression cases cover replacement, unchanged content and legacy records. This compares metadata references, **not file bytes or permission validity**; a production execution gate must also revalidate verified media, permissions and authoritative review provenance. Publishing remains disabled.

## Phase 7.5 — Registry-backed attachment verification

The owner approval-intent boundary now verifies every required content reference against the trusted attachment registry for the **same business, request and required item**, rather than accepting a string that merely looks like a verified attachment. Intent recording rejects missing, unregistered, cross-request or no-longer-verified references. Later inspection rechecks registry status and reports `attachments_verified`; failed verification forces `requires_new_review` even if draft and reference strings are unchanged. Existing approval-intent tests now use actual registered and verified attachments, and three new regression cases cover fake references, cross-request references and withdrawn verification. The offline registry remains metadata-only: actual file integrity, content permissions and scanner authentication must be implemented before production publishing. No scheduling or publishing rights are granted.

## Phase 7.6 — Read-only scheduling readiness

The new `schedule_readiness.py` assesses a proposed post time against the authenticated, tenant-scoped approval-intent ledger. It reports explicit blockers for revoked intent, changed draft, incomplete or changed supporting content, unverified attachments and nonfuture timestamps. Even with no such blockers, it **always holds** the request because final approval, complete TruthGuard publication gating and live integration are not implemented. It neither creates a scheduled job nor invokes social platforms. Seven regression tests cover held status, blocker reporting, access isolation and invalid time input. A green-looking review or recorded intent is never treated as publishing authorization.

## Phase 7.7 — Manual and smart scheduling preview

`schedule_preview.py` provides a nonexecuting scheduling preview for either an owner-supplied manual local time or a bounded set of candidate times from a future smart-scheduling engine. All inputs are interpreted in an explicitly selected IANA timezone. The preview rejects nonexistent daylight-saving transition times and ambiguous repeated local times, as well as duplicate candidates and mixed manual/smart input. Smart preview currently selects the **earliest supplied candidate** for deterministic demonstration, **not an optimized engagement window**. The selected UTC timestamp is assessed by the fail-closed scheduling readiness layer; no scheduled job, publication authorization, or social platform request is created. Eight regression tests cover both modes, daylight-saving boundaries, tenant isolation and invalid inputs. Real audience-aware ranking and owner publishing permissions remain future work.

## Phase 7.8 — Observed-audience scheduling prototype

`audience_schedule_ranker.py` provides a bounded, offline ranking of up to 20 candidate posting windows using only explicitly supplied engagement-rate observations for the requested tenant. It rejects cross-tenant observations, invalid rates and unmatched candidates. With at least five observations **for every candidate**, it selects the highest observed mean (lexical tie-break); otherwise it reports insufficient data without inventing performance estimates. The smart preview optionally uses this ranking, falling back to the earliest candidate only as a clearly labeled preview when evidence is insufficient. Manual times never use analytics. This is a simple empirical ranking, not a predictive model: observations must eventually come from authorized, comparable, platform-specific metrics with validated provenance and a well-defined measurement window. The result always remains held and cannot schedule or publish. Seven regression tests cover ranking, insufficient data, tenant isolation, invalid metrics and preview boundaries.
