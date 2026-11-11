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
