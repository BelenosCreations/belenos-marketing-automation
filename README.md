# BAM — Belenos Automatic Marketing

**BAM (Belenos Automatic Marketing) is a general-purpose, multi-tenant marketing management and automation platform for businesses of any industry.** Belenos is the software brand, not a restriction on which businesses can use BAM.

The platform is being designed to support independent organizations, multiple businesses under one owner login, and eventually separate business owners and employee teams. Each business maintains isolated branding, industry topics, creator recommendations, competitor exclusions, campaigns, social accounts, content approvals, schedules, analytics, and access permissions.

**Belenos Creations and Busy B Cleaning Service are initial development and testing examples only.** They are not hard-coded target industries, required tenants, or the intended limits of the product.

> **Approved AI direction:** Three usage scenarios (owner-only two posts/day, 5–10 invited users, and potential paid public Google Play release), OpenAI-only generation, default BAM-sponsored AI with optional personal OpenAI API key, and independent per-user AI memories. See [AI architecture and approved requirements](AI_ARCHITECTURE.md). Exact public pricing and quotas are not finalized.

> **Development status:** Offline development prototype with email/password and Google authentication foundations, a responsive sample-data GUI demonstration, and an authenticated large-card HTML shell that can now be served by an **explicitly opted-in, restricted HTTPS WSGI asset adapter** for direct-call integration tests (not yet hosted). Publishing is disabled. The platform is not yet a deployed multi-user service or finished Android application.

## Current functional capabilities (offline development build)

BAM now has a runnable **local account and content-workflow demonstration**, built from the same multi-business authorization services intended for later mobile and hosted interfaces. The current capabilities are:

- **Loopback-only HTTPS app preview:** an optional local preview runner can serve the authenticated BAM interface and API over TLS on `127.0.0.1` after an explicit local-only acknowledgement and an externally provided certificate. A separate one-time local bootstrap command creates a private test owner and password hash in an outside-repository SQLite database. Host and loopback checks protect against remote access or DNS rebinding. A full ephemeral-TLS integration test verifies real HTTPS page/asset delivery, password sign-in, authorized dashboard reads, held-draft creation and token revocation through a loopback socket. It is not production enrollment, verified email delivery, public hosting or an Android APK. See [Local HTTPS preview guide](LOCAL_PREVIEW.md).
- **Browser shell delivery foundation:** the integration-only gateway can serve the signed-in app's exact HTML/JS/CSS/brand-icon resources on one HTTPS origin, behind a separate opt-in switch. The resource list is restricted to assets actually referenced by the shell, with defensive security headers and a hash-restricted inline stylesheet; source/configuration files stay inaccessible. The test suite also executes the complete browser script graph outside CommonJS to catch dependency-order errors. **This is not an internet-facing server or a deployed application.**
- **Role-aware account interface:** the signed-in dashboard passes its server-authorized, active-business role to the AI facts, Content Studio and posting-time panels. Only owners see fact-confirmation and posting-time save controls; owners, managers and content creators can edit held content or create local AI drafts; viewers and regular employees receive read-only panels. All write APIs still independently recheck permissions.
- **Independent BAM identity sessions:** short-lived, hashed-token sessions, role freshness checks, business-scoped switching, per-session logout, and identity-wide logout. A disabled-by-default HTTPS-only sign-in adapter and in-memory browser login client now cover password and verified-Google pathways, without enabling production enrollment.
- **Multiple businesses under one identity:** isolated business profiles, current roles, social connection metadata, and content request queues. The authenticated shell lists only accessible businesses and changes business by issuing a replacement server-validated session, revoking the old one and clearing the previous business's private UI.
- **Social platform preparation:** account connection metadata, offline OAuth-state/PKCE scaffolding, read-only analytics import boundaries, scheduling previews, and audience-window ranking. **No live social account is connected by the demo.**
- **Posting time preferences:** signed-in business owners can explicitly save Smart or Manual mode with an IANA timezone and up to 24 unique local time slots. The Settings editor reads active-business preferences and validates owner-only writes via a disabled-by-default HTTPS gateway. Saving never schedules or publishes a post, and Smart mode does not invent audience recommendations.
- **Held marketing content:** authorized users can create manual drafts, request photos/permissions or other supporting materials, see what is missing, postpone unavailable content, and reopen incomplete drafts. The signed-in Content Studio supports explicit creation and hold updates through a server-authorized HTTPS adapter, with fresh tenant-scoped reads after changes. All drafts remain unscheduled and unpublished.
- **Media preflight, not actual upload:** a disabled-by-default authenticated metadata endpoint can register a pending attachment against a valid business draft using file type, byte count and SHA-256. It provides **no upload URL, file transfer or verified-media status**. Private storage, malware scanning, consent checks and trusted approval are still required.
- **Independently editable AI draft components:** after AI content is stored, a permitted creator can manually revise the post copy or the existing image prompt without regenerating the other component, making an OpenAI call, or changing the publication state. Revision numbers prevent stale overwrites; changing an image prompt invalidates any previously verified image association and returns the draft to a media-needed hold.
- **Zero-API-request local product/service drafts:** after the owner confirms `business_name` and at least one of `product` or `service`, an authenticated content creator can explicitly generate a simple factual product or service spotlight draft from a local template, optionally creating a conceptual ChatGPT image prompt for manual use. This path consumes **zero BAM OpenAI API generation requests**, stores the result in that user's unpublished AI drafts, and holds it for media and factual review. A local template does not generate an actual image or bypass review.
- **Owner-confirmed AI business facts:** business owners can explicitly confirm and edit fact dictionaries from the authenticated Settings panel, with server-enforced current owner permissions, revision checking and per-business isolation. Fact confirmation is provenance for draft grounding, not independent external verification.
- **Content safeguards:** approved-fact evidence, TruthGuard review receipts, attachment verification metadata, owner approval-intent records, and a scheduling readiness gate that explicitly refuses publishing.
- **Local developer interface:** `dev_server.py` plus `dev_client.py` inspect business accounts and held drafts over loopback HTTP. Separately, `bam_offline_gateway.py` assembles real SQLite identity, password login, tenant-isolated dashboard/AI reads, explicit sign-out and business rotation behind a disabled-by-default WSGI gateway for direct-call integration tests. Neither starts a hosted service.
- **Interactive graphical preview:** `ui/bam_dashboard_prototype.html` demonstrates large mobile-first cards, drilldown content screens, sample analytics, business switching, and light/dark appearance, using sample data only.
- **Backend card contract:** `dashboard_cards.py` supplies permission-aware content counts and explicitly unavailable scheduling values for eventual live UI integration.
- **AI draft backend:** owner-confirmed business fact registry, OpenAI-only structured draft planning, sponsored quota reservations, optional idempotency protection, held drafts, verified-image references and targeted revisions. Drafts are not approved or published.
- **AI provider boundary:** disabled-by-default OpenAI HTTPS transport and a strict structured Responses adapter, with operator-configured token cost estimates. No real provider connection or billing is enabled.
- **Authenticated large-card interface:** `ui/bam_signed_in_shell.html` and its browser controller compose password sign-in, verified-session dashboard reads, a permission-aware business switcher, AI drafts, deeper Settings, light/dark preferences and sign-out. The UI uses the approved BAM app-icon SVG and bundled branding sources. Its pages use server-validated data, not fabricated analytics; Google sign-in awaits a configured provider flow. The interface is not deployed.

**Not yet implemented:** production account enrollment and recovery, native Android app, deployed multi-user backend, real social provider token exchange, production media uploads, live OpenAI generation, production scheduling, or automatic social posting. Authenticated WSGI and UI integration components are available but not assembled into a deployed service. GitHub Actions verified **760 passing Python tests and 35 passing JavaScript UI regression scripts** at commit `4ceed04c` on 2026-11-10 (Eastern). This is offline regression verification, not production approval.

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

The target experience is a native Android application (Kotlin / Jetpack Compose) backed by a separately hosted Python automation service. The server will own identities, permissions, approval decisions, audit logs, and integration credentials; the phone is a client, not the unattended scheduler. The initial owner account is the pilot; the architecture supports multiple independent owners and per-business employee roles. `access_policy.py` is the initial **offline authorization policy**, not a login system or a working Android application. Biometric sign-in is a planned client capability subject to secure server-side session management.

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

The imported baseline package contains:
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

## Current implementation architecture

The repository contains a growing set of offline Python modules, strict authenticated API boundaries, and JavaScript browser components. The current mobile-first HTML demonstration remains sample-data only.

**Identity and access.** `sessions.py`, `accounts.py`, `business_switcher.py`, and related authentication modules provide hashed server-side sessions, per-business roles, identity-level logout, email/password and Google sign-in foundations, and invitation/account-directory scaffolding. These are development components, not a deployed login service.

**Business configuration and content.** Business curation, Content Requests, attachment validation, owner-approved facts, TruthGuard checks, approval-intent receipts, held drafts, and content-specific revision services enforce separation between unverified material, review, and publication eligibility. Drafts remain unpublished.

**Scheduling and analytics.** Posting preferences support Smart or Manual time choices per business. Audience-window ranking and analytics ingestion boundaries can operate on explicitly supplied data; they are not connected to live social providers. Unavailable scheduling/analytics values must display as unavailable rather than invented.

**AI content generation.** The approved hybrid architecture uses OpenAI-only structured responses containing independent post copy and optional image-generation prompts. It supports targeted component revisions, owner-confirmed business facts, sponsored usage quotas, request idempotency, and optional manual ChatGPT image creation. For a media-held draft, the UI can show an explicit **Copy image prompt** and **Open ChatGPT** handoff, with the finished artwork returned to BAM for verified upload; it never generates, uploads or publishes images automatically. The Responses adapter, HTTPS transport and generation endpoints are disabled by default. `bam_ai_offline_factory.py` assembles these components into a deliberately disabled service graph for integration testing; production enabling requires a separate reviewed composition root. No OpenAI API key is bundled or live billing enabled. See [AI architecture](AI_ARCHITECTURE.md).

**Cost and account privacy.** Token counts and estimated costs use explicit operator-supplied prices and are scoped by user and business. Estimates are not invoices. Credentials and raw provider secrets must remain server-side, never in the browser, logs or repository.

**UI.** The [sample dashboard](ui/bam_dashboard_prototype.html) is an unauthenticated sample-data concept. The distinct [signed-in HTML shell](ui/bam_signed_in_shell.html), `ui/bam_signed_in_shell.js` and `ui/authenticated_session_controller.js` connect the real authenticated workspace with login/logout, verified multi-business switching, large cards, AI draft viewing with explicit no-API-request product/service template creation and manual single-component edits, an explicitly write-capable **unpublished Content Studio**, owner-only Smart/Manual posting-time settings, explicit owner-confirmed AI fact editing and appearance selection. The approved [BAM icon and wordmarks](branding/README.md) are bundled as vector assets, with [Android launcher resource templates](android/branding/README.md). No live server, Google browser credential flow or deployed Android application is supplied. They clear on logout/business switch and do not publish.

**Auth transport.** `bam_auth_wsgi.py` offers disabled-by-default strict JSON HTTPS routes for password login, one-time Google sign-in challenges, and single/all-session sign-out, backed by trusted `AuthLoginAPI`, an explicit logout service and a required sign-in throttle. `ui/auth_login_client.js` validates responses and retains sessions only in the authenticated shell's memory. Real provider verification and production gateway policies still require configuration. Neither component is activated by the existing HTTP demo server.

**API boundaries.** `bam_read_wsgi.py` provides read-only HTTPS endpoints. `bam_business_switch_wsgi.py` handles permission-checked business changes and old-token revocation; `bam_offline_gateway.py` composes these with login for offline integration tests and is disabled by default. The optional `bam_signed_in_assets_wsgi.py` serves only the signed-in frontend's allowlisted same-origin resources over a trusted HTTPS WSGI environment when both explicit gates are enabled; it never starts a listener. `bam_content_write_wsgi.py` separately permits only authorized creation and hold-state changes for unpublished content requests, with no publishing or unverified attachment endpoint. `bam_upload_preflight_wsgi.py` registers only pending, unverified file metadata, with no upload URL or storage access. `bam_posting_preferences_wsgi.py` handles owner-only preference updates under the same disabled-by-default HTTPS gateway, independently of any posting execution. Separate disabled-by-default `bam_ai_write_wsgi.py` and `bam_ai_facts_write_wsgi.py` constrain generation and owner fact confirmation to authenticated, validated requests. The fact confirmation route is mounted for local direct-call testing only; it remains unavailable in a hosted service. None of these should be considered deployed production APIs.

## Development records and verification

- [Detailed implementation milestones](DEVELOPMENT_MILESTONES.md) preserve phase-by-phase notes without turning this product overview into a changelog.
- [Changelog](CHANGELOG.md) records additions, fixes and known limitations.
- [Authenticated UI integration](AUTHENTICATED_UI_INTEGRATION.md) documents session lifecycle and browser contracts.
- [Local HTTPS preview guide](LOCAL_PREVIEW.md) documents the optional loopback-only test runner and its nonproduction trust boundaries.
- [AI architecture](AI_ARCHITECTURE.md) records approved generation design and safety requirements.
- [GitHub Actions tests](.github/workflows/tests.yml) define Python and Node regression checks. The complete **769-test Python suite** and **35 JavaScript UI regression scripts** passed together in [GitHub Actions run 43014624796](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43014624796) on commit `4a6a3d50`. The Python suite includes an actual temporary localhost TLS network smoke test; it is not real-browser automation or production approval. CI checks Python compilation, all `ui/*_test.js` scripts, and Python unit tests on every push. This does not cover production social publishing, real OAuth, or deployment security.

## Operational boundaries

**No live publishing, post scheduling, or automatic reposting is authorized by this repository or its README.** Development, testing, and deployment are separate from authorization to publish. Business-specific promotional content must remain grounded in confirmed facts.

## Documentation and release discipline

Maintain a `CHANGELOG.md` recording each release's version, date, added/changed/fixed items, test status, and known limitations. Use Git history and tagged releases for reproducible versions. Never commit passwords, access tokens, private keys, or customer information.

---

**Pilot businesses:** Belenos Creations and Busy B Cleaning Service · Marion, Ohio (nonexclusive examples)  
**Project:** BAM (Belenos Automatic Marketing)  
**Status:** Active development · publishing disabled

