# BAM — Development Milestones and Historical Implementation Notes

This document preserves detailed phase-by-phase development notes originally appended to the README. For the product overview, architecture and current state, see [README](README.md). For chronological changes, see [CHANGELOG](CHANGELOG.md).

## Zero-spend advance AI topic batch planning (2026-11-11)

`AIBatchPreview` and a strict `POST /api/v1/ai/batch-preview` gateway route let an authenticated editor preview 1–14 distinct future topic requests using current owner-confirmed facts, their business, and the account's AI mode, without sending or charging any OpenAI API requests. The service generates **metadata only**: a list of topics/platform/image-prompt intentions, owner-facts revision and count of proposed per-topic model requests. It refuses to claim that a provider job ran, a discount was calculated, quota was reserved, a draft was created, or a post was scheduled. The AI Drafts page exposes this as a cost-free **Plan future marketing topics** section; viewers do not see it and session/business-switch checks stop stale responses. The legacy internal memory replacement is also hardened to apply the same credential-resistant validation as external preference writes.

**Verified:** [GitHub Actions run 43058003130](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43058003130), commit `97f8f2de`: 845 Python and 55 JavaScript test scripts, plus compilation.

## Current-user, current-business AI writing preference editing (2026-11-11)

BAM Settings now lets an authorized creator edit their own AI writing preferences, such as tone, target audience and desired length, without modifying another user's preferences even within the same business. `AIPolicyStore.replace_memory_checked` enforces the prior-state optimistic check under the server-resolved subject/business scope; stale writes fail with a conflict instead of overwriting another device's updates. `bam_ai_memory_wsgi.py` provides a strict HTTPS PUT adapter with bounded text and no client-selected tenant or publication fields. `ui/ai_memory_client.js` and the Settings editor validate and persist only these preferences, with role-aware controls, stale-response handling and no model API calls. This remains separate from owner-confirmed business facts and is unsuitable for passwords or credentials.

**Verified:** [GitHub Actions run 43056197885](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43056197885), commit `c1f31d52`: 836 Python tests and 53 JavaScript UI test scripts, plus compilation.

## Explicit, opt-in targeted AI revision interface (2026-11-11)

The AI Content Drafts panel now has optional separate controls to prepare and confirm an AI copy revision or existing image-prompt revision. A usage warning explains that the request may consume sponsored quota or charge the key owner; there is no implicit AI request. `ui/ai_targeted_revision_client.js` requires cryptographic idempotency keys, verifies the current business and expected draft revision and rejects provider/publishing/approval claims. The workspace sends only one request per confirmed action, refreshes trusted draft data on success and discards stale session results. The normal signed-in app does **not** enable the opt-in flag, and the offline gateway has no active paid provider route.

**Verified:** [GitHub Actions run 43054882416](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43054882416), commit `6ebe7d86`, 830 Python tests and 50 JavaScript scripts, plus compilation. This is readiness scaffolding, not a live paid capability.

## Strict targeted AI revision HTTP integration (2026-11-11)

`bam_ai_revision_wsgi.py` exposes a separately disabled HTTPS endpoint for an authenticated targeted AI draft revision. Its strict request shape permits only draft ID, expected revision, component, instruction, topic and idempotency key. The server selects sponsorship policy and UTC month. The offline AI composition factory shares the existing per-user, per-business facts, draft store, sponsored quota and idempotency, and keeps OpenAI transport disabled. Injected-executor WSGI/E2E tests confirm single-component changes, stale/replayed request rejection, cross-tenant isolation and invalidation of earlier media matches on image-prompt edits. An API metadata mismatch was discovered and corrected before successful CI verification.

**Verified:** [GitHub Actions run 43053763455](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43053763455), commit `1187b467`: 830 Python and 47 JavaScript test scripts, plus compilation. No live provider billing, scheduling or publication is authorized.

## Structured targeted AI revision executor (offline only) (2026-11-11)

`AITargetedRevisionWorkflow` now assembles an existing user's structured draft, current owner-confirmed business facts and a single requested component into the already approved targeted OpenAI request shape. The injected trusted executor receives only a bounded token cap from a server-configured sponsored quota. An idempotency request key is claimed before quota use. Before applying the one-component result, the workflow checks that fact provenance/revision remains unchanged and that the exact draft revision is current. Success increments revision, preserves the other component verbatim and invalidates old verified image attachment associations when the image prompt changes. Provider responses with duplicate JSON keys fail closed. Failed or ambiguous keys are held for explicit reconciliation, not automatically retried. No external OpenAI call, provider key, billing or social publication is enabled.

**Verified:** [GitHub Actions run 43052414192](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43052414192), commit `2f540470`, **824 Python tests and 47 JavaScript UI scripts**, plus compilation.

## Advanced, manually confirmed batch import of held drafts (2026-11-11)

Content Studio can now preview and import 1–20 unpublished marketing drafts from a local CSV file. `ui/held_draft_csv_import.js` parses bounded RFC-style quoted fields, requires known channels and factual guidance, rejects duplicate rows and uses `image` as the default missing content. The browser scans the current business's existing drafts for exact repeated copy and offers a separate explicit confirmation. Each item is created through the existing session-authorized `POST /api/v1/content/drafts` route without new endpoints or OpenAI usage. If a request fails, no remaining rows are sent; the operator sees the count that was confirmed and is warned to check for partial additions. Business/session changes cancel subsequent writes.

**Verified:** [run 43038527274](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43038527274), commit `0b98f105`, 813 Python and 47 JavaScript scripts, plus compilation.

## Read-only marketing claim-risk hints in Content Studio (2026-11-11)

`BAMContentRiskWSGI` now serves a bounded GET review for a specific existing held draft; `AccountReadAPI.get_content_risk_preview` derives the tenant from the authenticated session and scans stored copy with `truthguard_risk_signals.py`. The response discloses only flagged text snippets/categories and the draft revision, and explicitly asserts that claim extraction is incomplete, review is required and publishing is disabled. A dedicated browser client validates this contract and Content Studio displays warnings only after user action. Revision mismatches, business switches and sign-out invalidate previous risk reports. A clean heuristic preview does not verify content.

**Verified:** [run 43037661505](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43037661505), commit `4b92f5c3`, 813 Python tests and 45 JavaScript UI tests, plus compilation.

## Explicit global BAM session sign-out (2026-11-11)

The signed-in Settings page now offers a separate warning, Confirm and Cancel for signing out on all BAM devices. Confirmation clears the browser's private workspace and token before requesting the already-tested backend session revocation route; only a trusted server response can confirm the number of sessions revoked. An unavailable response must never imply that other sessions were revoked. This does not touch provider OAuth or publishing rights.

**Verified:** [run 43036158603](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43036158603), commit `c13fb91e`, 809 Python and 44 JavaScript tests.

## Owner-only aggregate team access in Settings (2026-11-11)

The signed-in Settings page now shows current-business membership counts only to owners. The strict `GET /api/v1/team-overview` service derives tenant identity from the live session and requires server-checked `MANAGE_TEAM` permission. It aggregates roles and inactive memberships without exposing employee emails, IDs, or invitation tokens. The UI clears data after business switching, role change or sign-out and treats failures as unavailable rather than fabricated zeros. Invitations and role management remain intentionally disconnected.

**Verified:** [run 43035508617](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43035508617), commit `65f7663c`: 809 Python tests, 44 JavaScript UI scripts, Python compilation.

## Independent, revision-safe held Content Studio draft editing (2026-11-11)

The held content request table now supports a monotonic `revision`, including an in-place local SQLite migration for older databases. The backend can atomically revise exactly one field—`draft_text` or `suggestion`—only after current business membership and edit permission checks, with an expected-revision compare-and-update. Hold transitions and attachment completion also advance revision. `bam_content_revise_wsgi.py` accepts only these bounded revision fields through an explicitly enabled HTTPS-only local gateway and returns `409 Conflict` for stale writes, without allowing tenant, role, publishing or approval claims. The signed-in Content Studio shows separate manual text editors and refreshes the trusted tenant view after each confirmed save. Existing review-intent records become stale if approved copy changes, requiring renewed human review.

**Verified:** [GitHub Actions run 43034533473](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43034533473), commit `19ac808b`, **807 Python tests and 42 JavaScript test scripts**, plus compilation. This milestone does not enable AI regeneration, media verification, scheduling or publication.

## Detailed Scheduled and Approvals dashboard cards (2026-11-11)

The authenticated large-card overview now has useful drilldowns for scheduling and human-review readiness, in addition to the already verified Content and Connections panels. The Scheduled panel calls the existing `GET /api/v1/posting-time-preview` route only for read-only possible Manual-mode local clock times, respects DST ambiguity notes, and links to business-owner posting preferences. No queued or published items are implied. The Approvals panel lists only business-scoped `ready_for_review` requests from the trusted dashboard, explicitly stating that these are not yet approved; it links to Content Studio without adding an approval or publication action. Both panels guard against stale responses after logout or business switching.

**Verified:** [GitHub Actions run 43032704184](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43032704184), commit `03d1495a`, **797 Python tests, 41 JavaScript test scripts**, plus compilation.

## Business-scoped social account status drilldown (2026-11-11)

The signed-in dashboard Connections card now opens a deeper read-only view, using an authenticated `GET /api/v1/connections` route backed by `SocialConnectionDirectory`. The endpoint derives the tenant from a fresh session and separately checks analytics-read permission. Responses contain only provider platform, account alias, permitted read-only scope, effective connection state and timestamps; no vault references, tokens, publish scopes or user-selected business IDs. Strict browser contracts reject unexpected or forged metadata. Restricted roles are not permitted to fetch the details. The dashboard handles loading/error states without fabricating an account connection, and discards results after logout or business switch.

**Verified:** [GitHub Actions run 43031957718](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43031957718), commit `badf0ac6`, **797 Python tests, 40 JavaScript UI scripts**, plus compilation. This is a mock-registry workflow, not real provider OAuth or publishing.

## Tenant-scoped, DST-safe posting-time preview (2026-11-11)

A dedicated `posting_time_preview.py` service now derives a read-only seven-day list of possible Manual-mode local times from a business's saved posting preferences, omitting ambiguous fall-back hours and nonexistent spring-forward hours. It also reports an evidence hold for Smart mode rather than inventing peak-engagement suggestions. `GET /api/v1/posting-time-preview` resolves the tenant through the authenticated BAM session, disallows tenant query overrides, and cannot mutate content or schedule posts. The Settings UI displays and validates this response as informational only, including on business switches. No production queue, approval, social-token exchange or publishing permission is created.

**Verified:** [GitHub Actions run 43023029480](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43023029480), commit `9a2eee75`, **795 Python tests and 38 JavaScript test scripts**, plus compilation.

## Full local TLS image receipt-to-discard smoke (2026-11-11)

The existing single-process ephemeral HTTPS socket integration test now exercises real request bytes through BAM's loopback gateway: password login, creation of a held draft needing an image, private upload-preflight registration, image-byte receipt, persistent `awaiting_file` / `pending_scan` status reads, unchanged draft hold, explicit pending deletion, and separate-business isolation after a session switch. The disposable file is constructed in the test and remains unverified throughout. No public network, real customer data, scanner, social provider or paid model API is contacted.

**Verified [GitHub Actions run 43021239317](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43021239317): 789 Python tests and 37 JavaScript test scripts passed with Python compilation, commit `c5501af8`.**

## Discarding and replacing private pending images (2026-11-11)

The optional local-only image receipt workflow now supports explicit discard of the **unverified** image for an individual tenant-scoped request and required item. `BAMPendingMediaStore.discard` checks the authenticated current edit role, restricts file names to registry-issued opaque identifiers, unlinks only private pending files without following symlinks, and removes pending metadata. It does not touch verified/approved files or change draft readiness. The disabled-by-default `bam_pending_media_discard_wsgi.py` enforces strict JSON and HTTPS request boundaries. A two-step confirmation in Content Studio initiates the deletion, refreshes trusted receipt status, and exposes the replacement file picker only after removal is confirmed. Stale business controls are ignored.

**Verified [GitHub Actions run 43020735001](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43020735001): 789 Python tests and 37 JavaScript test scripts, plus compilation, commit `4baf5528`.**

## Persistent pending-media visibility and session-safe transfer (2026-11-11)

The optional local media receipt path now has a strict read-only `GET /api/v1/content/media-status` route and tenant-scoped store summarization. Valid media metadata appears as `awaiting_file`; a private, regular, owner-readable quarantine file with the expected server-generated name appears as `pending_scan`. Results exclude raw media, hashes, attachment IDs and storage paths. Missing checklist items remain missing and are not approved. The UI refreshes these statuses as part of Content Studio reads; it hides the picker when a file is already awaiting review and fails closed when status cannot be confirmed. An upload client session validity callback prevents late bytes being sent after a logout or business switch between asynchronous request stages. This is not a media scanner or trusted approval pathway.

**Verified:** [GitHub Actions run 43019581144](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43019581144): 784 Python tests and 37 JavaScript tests passed, plus compilation, commit `2618f139`.

## Content Studio capability redraw fix (2026-11-11)

The private media capability toggle now re-renders Content Studio immediately, including revocation, rather than waiting for another read. This corrects a failing browser DOM regression without enabling any media approval or publishing. Verify the full GitHub Actions suite before considering the milestone complete.

## Private pending-only image-byte receipt (2026-11-11)

The approved ChatGPT user-generated image return path now has a default-off **local-only** byte receipt service, `BAMPendingMediaStore`, behind the authenticated `BAMPendingMediaWSGI` endpoint. An allowed editor must already have a server-created pending attachment ID for an active request and a checklist image item. The actual file must be PNG/JPEG/WebP, fit a capped size, match the declared SHA-256 and file signature, and be stored in an explicitly configured private directory outside the source tree. Storage filenames derive only from server-generated attachment IDs and are not exposed to browsers. The registry remains pending and the request still needs content; there is no file download, gallery, malware inspection, content approval or publishing.

The local TLS preview can opt into pending storage only with `--pending-media-dir`; it remains completely disabled by default. A browser file picker and pending-status display are outstanding integration steps. No file is externally served, no verified permission is asserted and no live social posting is possible.

**Verified [GitHub Actions run 43016103634](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43016103634): 779 Python tests, 35 JS test scripts, plus compilation.**

## Verified two-business local account journey over TLS (2026-11-11)

The preview CLI now includes `add-business` for an existing password-verified **owner** identity to create another business in its own trusted local SQLite database, without opening any user or business enrollment HTTP route. A second-business setup requires a valid current owner login and rejects duplicate tenants, unsafe file access and arbitrary role grants.

The real HTTPS socket smoke test was expanded: a signed-in local owner creates a held content request in one business, rotates the session to another business, verifies that the prior token is revoked, sees only the second business's own data and finally signs out of the replacement session. The CLI and gateway keep the same BAM identity across two tenant workspaces without sharing draft data or authorization.

**Verified [GitHub Actions run 43015125493](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43015125493): 770 Python tests and 35 JS scripts, plus compilation.**

## Actual HTTPS socket end-to-end integration (2026-11-11)

A new `test_bam_local_tls_smoke.py` starts the development gateway behind an ephemeral localhost-only TLS socket with a short-lived self-signed test certificate, not an external HTTP service. It retrieves the signed-in HTML, actual browser JS and branded icon, signs in through the real WSGI password endpoint, reads the authenticated dashboard, saves and retrieves a held unpublished content request, verifies inaccessible project-source and non-existent publication routes, and confirms logout immediately invalidates the token. No actual external network or paid AI is used.

**Verified [GitHub Actions run 43014624796](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43014624796): 769 Python tests and 35 JS tests, plus compilation.** This is network-level TLS/WGSI smoke testing, not real-browser end-to-end automation or production sign-off.

## Loopback-only HTTPS preview runner and local test-owner bootstrap (2026-11-11)

`bam_local_preview.py` now provides an explicitly opted-in, local-only WSGI TLS server for the authenticated BAM shell and gateway. It binds only `127.0.0.1`, requires an external TLS certificate/private key and a local-only acknowledgement, restricts browser Host values to exact localhost/loopback hosts with a matching port, and ignores externally supplied forwarded-protocol claims. No public route can create, verify or assign BAM identities. The separate `bootstrap` command prompts locally for a password, creates a private `0600` SQLite file outside the source repository, and establishes exactly one **test** owner. Marking email verified is a deliberate local demonstration shortcut, not a production verification implementation.

This is a material step toward running the real authenticated dashboard in a local browser rather than viewing raw HTML files. It remains outside production operations: no Internet listener, mobile APK, real Google sign-in, production account recovery, media upload, OpenAI charges or social publishing.

**Verified [GitHub Actions run 43014114797](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43014114797): 768 Python tests and 35 JavaScript scripts, plus compilation.** See [Local HTTPS preview guide](LOCAL_PREVIEW.md).

## Restricted same-origin browser asset delivery (2026-11-11)

The authenticated large-card HTML shell is now served by a separate `bam_signed_in_assets_wsgi.py` adapter under the offline gateway's independent, default-off `serve_browser_assets` option. The adapter derives its allowlist from the shell's own referenced JavaScript, CSS and branded icon and returns only these assets over a trusted WSGI HTTPS scheme. A strict Content Security Policy limits scripts, connections, frames and styles; the single inline stylesheet is cryptographically hashed rather than globally allowing inline code. No sample prototype, README, environment or backend source file is served.

This creates an end-to-end *resource-delivery* composition that can later be mounted behind a properly engineered trusted HTTPS staging server without altering the current UI. It does not start a listener, provide production TLS/account enrollment, enable paid OpenAI calls, upload media or publish. A new browser-global Node regression loads all page scripts in the actual HTML order, rather than relying only on CommonJS tests.

**Verified [GitHub Actions run 43013333985](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43013333985): 764 Python tests and 35 JavaScript tests, plus compilation.**

## Zero-OpenAI-cost templates for product and service businesses (2026-11-10)

The confirmed-fact local draft workflow now supports both product and service spotlights. `LocalDraftTemplates.service_spotlight` assembles short literal service copy and an optional clearly conceptual, non-photographic image prompt from only owner-confirmed `business_name` and `service` facts. `POST /api/v1/ai/local-service-draft` is separately disabled by default, scoped to the active user's business and edit role, and saves only a review-pending AI draft. The signed-in AI workspace shows only the applicable template types for that business, with manual ChatGPT image handoff remaining optional. No platform-neutral factual claims, staff identity, equipment details, customer guarantees, prices or hours are invented.

**Verified [GitHub Actions run 42962115509](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42962115509): 760 Python tests and 35 JS scripts, plus compilation.**

## Independent manual AI draft component revisions (2026-11-10)

The disabled-by-default `bam_ai_draft_edit_wsgi.py` adds a strict `PUT /api/v1/ai-drafts` route to edit one existing user/business-scoped AI draft component. It requires the authenticated session, a draft ID, target (`post_text` or existing `image_prompt`), revised text and matching revision. The `AIContentDraftStore` stores the updated component only, increments the revision and returns an unpublished draft status; a changed image prompt deletes its old verified image match. The signed-in AI Drafts UI has explicit separate Save controls and reloads the trusted draft after each edit.

The route never invokes OpenAI, changes the other component, approves, schedules, publishes or grants media permission. Stale revisions and cross-business/user edits fail closed, and the creator role is checked on the backend regardless of UI controls. **Verified [GitHub Actions run 42961746379](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42961746379): 757 Python tests and 34 JS scripts, plus compilation.**

## Role-aware editing controls in each business (2026-11-10)

The signed-in dashboard now accepts the authorized active-business role from the server. `ui/dashboard_data_contract.js` permits only known membership roles and defaults a missing role to read-only, rather than granting edit access. The authenticated workspace derives presentation capabilities only from this trusted response, resetting them on activation, logout and business switching. Owners see AI fact confirmation and Smart/Manual posting preference editors; owners, marketing managers and content creators can create/edit held content requests and create zero-API-cost drafts. Employees/viewers see only read-only information. Backend role and tenant checks remain authoritative and are not bypassed by browser flags.

**Verified [GitHub Actions run 42961295058](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42961295058): 750 Python tests and 32 JavaScript UI scripts, plus compilation.**

## Zero-OpenAI-call owner-confirmed product drafts (2026-11-10)

BAM now stages a product spotlight draft from only the current tenant's owner-confirmed `business_name` and `product`. The disabled-by-default `bam_local_draft_wsgi.py` route checks the active BAM session, rejects client-supplied facts/tenant/model/publish claims, and delegates literal assembly to `LocalDraftTemplates`. The result is staged in the user's private AI draft component store as `draft_pending_verification` or `needs_media`; it is never published. The optional local conceptual image prompt is clearly distinguished from an actual product photograph, carries no invented details, and is intended for user-operated ChatGPT creation and review.

The signed-in AI Drafts view exposes an explicit no-API-request product action only after the current business has required confirmed facts. Logout and business rotation clear the UI before late network responses can return. This milestone does not execute OpenAI requests, incur BAM model-generation expense, upload media or bypass verification.

**Verified [GitHub Actions run 42960676199](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42960676199): 750 Python tests and 31 JS test scripts, plus compilation.**

## Authenticated owner-confirmed business fact editing (2026-11-10)

The existing owner-only `bam_ai_facts_write_wsgi.py` is now mounted in the disabled-by-default offline BAM gateway for HTTPS direct-call tests. The signed-in nested Settings section mounts `ui/ai_facts_editor.js` with a scoped `ui/ai_write_client.js` callback. Only the user's current business session may confirm an explicit dictionary of facts; a server role check rejects nonowners and revision checks prevent stale overwrites. Successful saves reread the owner-confirmed snapshot and refresh the AI panel. Confirmation is provenance, not a guarantee of truth and not permission to schedule or publish.

**Verified [GitHub Actions run 42960261912](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42960261912): 743 Python tests and 30 JS scripts, plus compilation.**

## Pending-only media metadata preflight (2026-11-10)

A new disabled-by-default `bam_upload_preflight_wsgi.py` route delegates file **metadata** registration to the existing authenticated `ContentUploadPreflight`. It validates a server-derived tenant, the specific held content request and required checklist item, permitted MIME family, SHA-256 hash, and bounded size before recording a private `pending` attachment. It does not receive file bytes, reveal the storage key, authorize upload, mark verification, grant publishing or satisfy a content request. This is only groundwork for the approved user-controlled ChatGPT media return path, pending real private storage and trusted scanning.

**Verified [GitHub Actions run 42959953634](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42959953634): 742 Python tests and 30 JS scripts, plus Python compilation.**

## Owner-only Smart/Manual posting time Settings (2026-11-10)

The signed-in Settings panel now includes `ui/posting_preferences_workspace.js`, an explicit owner-editable interface for Smart or Manual posting time preferences and an IANA timezone. Only a current business owner can save these through the disabled-by-default `bam_posting_preferences_wsgi.py` PUT endpoint, wired into the offline BAM composition root. The server derives the business from its authorized session and rejects any client-supplied role, tenant, schedule or publication claim. The browser validates strict response structure and confirms writes with a fresh tenant-scoped GET. User interface state is invalidated on sign-out and business switch. These preferences never schedule or publish content.

**Verified in [GitHub Actions run 42959720838](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42959720838): 735 Python tests and 30 JavaScript UI test scripts, plus Python compilation.** The prior Content Studio navigation smoke additions separately passed in run 42959453544.

## Authenticated held-draft Content Studio (2026-11-10)

The signed-in workspace now mounts `ui/held_draft_workspace.js` in a dedicated Content Studio tab beside the approved overview-first large-card navigation. Its strict `ui/held_draft_write_client.js` sends only permitted fields to the existing unpublished-content WSGI API and rejects tenant mismatches, forged publishing states, extra response fields and dangerous operations. A successful mutation reloads server-authorized tenant content; a failed or stale response never displays an optimistic success. Logout and business changes immediately clear the Content Studio along with the other private panels.

Direct navigation from the dashboard Content card and a browser-level held-draft form/hold-state smoke test were also added. No verified media upload, review approval, scheduled publishing or AI calls were activated.

**Verified core integration in [GitHub Actions run 42959259493](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42959259493): 727 Python tests and 28 JavaScript UI test scripts, plus Python compilation.** The subsequent navigation/form end-to-end additions will be verified independently in CI.

## Tenant-switching security and approved branding (2026-11-10)

Added a strict, disabled-by-default `bam_business_switch_wsgi.py` that uses the trusted account-directory membership checks to issue a replacement session scoped to the chosen business. It revokes the old session before returning the new token and attempts to revoke any orphaned replacement after failures. The browser's `ui/business_switch_client.js` and `ui/authenticated_session_controller.js` enforce in-memory token rotation, private workspace clearing, stale result protection and sign-out during in-flight switching. A business selector appears in the signed-in header only when the trusted dashboard returns multiple permitted businesses.

Integrated the already-approved BAM icon, wordmarks, color palette, adaptive launcher XML and source SVGs from `main` into the active development branch without overwriting its README, changelog or CI workflow; the signed-in page now renders the real BAM icon rather than a placeholder monogram. The new `bam_offline_gateway.py` uses a disabled-by-default WSGI composition of actual SQLite password login, session checking, read-only dashboard, AI panels and account rotation for offline end-to-end tests. A real hosted site, signup and provider configuration still do not exist.

**Verified [GitHub Actions run 42954241030](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42954241030): 717 Python tests and 26 JavaScript UI test scripts, plus compilation.**

## Authenticated responsive shell and explicit logout (2026-11-10)

The new `ui/bam_signed_in_shell.html` is distinct from the earlier sample-data dashboard prototype. Its `ui/bam_signed_in_shell.js` controller wires the approved overview-first large cards to authenticated data, AI draft panels, deeper Settings and local Light/Dark/Auto appearance preferences. Email/password form authentication, explicit per-session and identity-wide logout, retry-free session cleanup, stale login rejection and security-disabled HTTP/file loading are exercised through `ui/authenticated_session_controller.js`, `ui/auth_login_client.js`, and a DOM smoke test. Python's disabled-by-default `bam_auth_wsgi.py` now supports WSGI logout routes backed by injected trusted session revocation. GitHub Actions [run 42952514922](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42952514922) validated **693 Python and 25 JavaScript tests**, including the signed-in shell. The UI is not hosted; Google provider configuration, real signup, integration service assembly, security review and native Android packaging remain pending.

## Disabled-by-default authentication transport (2026-11-10)

`bam_auth_wsgi.py` wraps the existing trusted `AuthLoginAPI` for strict JSON-over-HTTPS password login, Google challenge issuance and Google token verification via configured server-side verifier, while enforcing the presence of an account login throttle before the endpoint can be enabled. `ui/auth_login_client.js` is a same-origin browser transport with no cookies or persistent token storage. The gateway remains unmounted and does not create a hosted service or Android login screen. A real integration/regression check on commit `9ef6e73` passed **689 Python unit tests and 23 JavaScript test scripts** in [GitHub Actions run 42951600141](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42951600141). Production security and sign-out lifecycle work remain.

## Verified CI recovery and UI privacy regression (2026-11-10)

The recovered development branch was checked against the actual GitHub Actions logs instead of relying on previously unverified test claims. The initial blocker was a Python syntax error in `bam_ai_write_wsgi.py`. After fixing it, the complete suite exposed four failing assertions: one family-audience smart-schedule bug and three regression expectations inconsistent with current viewer permission, competitor blocking, and invitation TTL semantics. These were corrected without relaxing cross-tenant checks or publication gates. A new UI test verifies the owner facts editor is cleared after read failures. The CI workflow discovers all JavaScript UI scripts automatically and cancels superseded runs. **Verified run 42951059295:** 676 Python tests and 22 JavaScript UI regression scripts passed, plus Python compilation. [Successful run](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42951059295). This is an offline test milestone; it does not activate social publishing, paid AI calls or a hosted Android app.


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

## Phase 7.9 — Offline analytics observation ledger

`audience_observation_store.py` adds a SQLite-backed, platform-scoped record of observed post engagement rates. Each record carries a business ID, platform, external post identifier, candidate posting window, measured engagement rate, measurement timestamp, and source label. Uniqueness by business/platform/post ID prevents duplicate ingestion, and bounded date-range queries return only observations for the requested business, platform, and candidate windows. Query results can be passed to the existing empirical smart-scheduling ranker; seven regression cases cover ingestion, deduplication, isolation, invalid inputs, and ranking integration.

**Security and provenance boundary:** `ingest_trusted` is an offline server-side interface only; its name is a contract for a future authenticated provider adapter, **not evidence that source authenticity is verified today**. The store has no provider OAuth, signed webhook, remote API synchronization, metric normalization across platforms, retention policy, or production access-control boundary. Never expose ingestion or raw tenant queries to mobile clients. Engagement observations must be validated against authorized platform accounts and a consistent measurement definition before production use. Scheduling and publishing remain disabled.

## Phase 8.0 — Authenticated offline analytics import boundary

`analytics_import_boundary.py` provides a server-side import boundary that requires a tenant/platform-specific configured account identifier and an injected import secret before accepting an engagement observation. The caller supplies integer engagement and impression counts; the boundary validates them, computes a bounded engagement/impression ratio, and records the observation through the tenant/platform-isolated store. It rejects unknown accounts, missing/wrong secrets, impossible counts, malformed source post identifiers, and duplicate post IDs. Nine regression tests cover those cases.

**Important distinction:** This authenticates a configured **import caller**, not a social platform. It does not verify that imported metrics genuinely came from Facebook or another provider. The server must obtain account bindings and secrets from trusted configuration/secret management, never from mobile app input or source control. A production connector still needs provider OAuth, account ownership checks, trusted API fetching, consistent metric definitions, error/retry handling and authorization to read analytics. No publishing or scheduling is enabled.

## Phase 8.1 — Transactional analytics synchronization groundwork

`analytics_sync_coordinator.py` adds a bounded offline batch-import coordinator and per-business/platform/account synchronization checkpoints. Each batch requires the configured import credentials, the exact previous cursor, a new cursor and 1–100 observations. A SQLite write transaction protects the observations and checkpoint together: a duplicate source post, malformed observation or stale cursor prevents checkpoint advancement; partially imported batches roll back. The import boundary now exposes a reusable authorization check, and the observation store respects transactions opened by the caller. Seven regression cases cover checkpoint progression, credential isolation, stale cursors, duplicate batches, partial rollback, invalid batches and cross-business access.

This is **not** a connected provider sync service. Cursors are opaque adapter-provided values; no external requests, provider OAuth, retry/backoff scheduler, token storage or webhook verification exist yet. The prototype assumes the coordinator and store share the same SQLite connection and must not be exposed as a public API. Publishing remains disabled.

## Phase 8.2 — Provider-neutral analytics page adapter

`analytics_page_adapter.py` defines an offline integration seam between a future trusted social analytics fetcher and BAM's transactional import coordinator. The adapter authorizes the configured tenant/platform/account **before** invoking the injected fetcher, reads the existing checkpoint, validates a bounded page of post metrics, and normalizes each post's publication timestamp into a business-local weekday/hour bucket using an IANA timezone. It supports preview without writing and an import operation that delegates to the atomic checkpoint coordinator. Seven regression cases cover authorization-before-fetch, tenant separation, local-time bucketing, malformed pages, future timestamps, and checkpoint advancement.

The fetcher is injected for testing; **no Facebook, Instagram, Metricool or other live provider connector exists yet**. A real integration must verify account ownership, fetch metrics using provider-issued read-only credentials, define engagement metrics per platform, handle page exhaustion and retries, validate source authenticity, and protect credentials using server-side secret management. Weekday/hour buckets are a preliminary normalization, not proof of an optimal posting time. This adapter cannot publish posts or create scheduled jobs.

## Phase 8.3 — Synchronization health and recovery visibility

`analytics_sync_health.py` adds an authenticated, read-only assessment of a business/platform/account's last synchronization checkpoint. The assessment distinguishes imports that have not started, current checkpoints, stale checkpoints, and invalid future-dated checkpoints. A configurable age threshold controls freshness; stale records prompt review of the provider connection, rather than silently claiming the data is current. Credential authorization happens before checkpoint lookup. The assessment does not reveal import secrets or raw checkpoint cursor values, trigger retries, contact external providers, schedule posts, or publish. Eight regression cases cover missing/current/stale/invalid states, authorization and input validation.

**Remaining integration prerequisites:** Provider-issued read-only OAuth permissions, secure token lifecycle and rotation, real account ownership verification, API quota handling, backoff/retries, metric provenance and comparability, and operational monitoring. A stale checkpoint may reflect an inactive account or lack of new posts, so it is a prompt for review rather than proof of provider failure.

## Phase 8.4 — Provider connection metadata and credential lifecycle states

`provider_connection_registry.py` introduces an offline, tenant/platform/account-scoped registry for **metadata** about analytics connections. It stores a reference intended for a future server-side secret vault (not the OAuth token), declared analytics scope, connection state, expiry and update timestamps. Status reports distinguish not-connected, pending, connected, refresh-required, expired and revoked connections; they omit the vault reference and cannot enable publishing. The prototype rejects scopes containing publishing or write permissions. Nine regression cases cover lifecycle status, isolation, metadata validation and nonpublishing behavior.

**Security boundary:** This registry does not implement OAuth, token encryption, token refresh, a secret vault, provider permission verification or authenticated caller access. `register_trusted` must only be invoked behind a trusted server authorization layer. Its scope validation is a defensive prototype check, not a provider-specific allowlist; production integration must explicitly allowlist the exact read-only scopes for each provider. Never place actual tokens or passwords in the registry or GitHub. No live connections were created.

## Phase 8.5 — Connection-state enforcement for offline analytics

`connection_gated_analytics.py` adds a fail-closed wrapper for the existing offline provider-neutral page adapter. Before previewing or importing any analytics, it authenticates the configured import caller, checks the business/account binding, and requires a registry status of `connected` with an unexpired credential reference. Unconnected, pending, refresh-required, revoked and expired connections are denied before the fetcher is invoked. Eight regression cases cover allowed connected access and denial of inactive, expired, revoked, cross-tenant and unauthorized attempts.

**Deployment boundary:** Callers must use the gated adapter rather than invoking the underlying `AnalyticsPageAdapter` directly. The registry and import boundary remain internal server components and must not be exposed to clients. The check is performed before fetching, not atomically with provider-side revocation; production integrations require provider OAuth validation, credential vault, account ownership verification, concurrent revocation handling and network-level protections. This is still an offline prototype with injected fake fetchers, no live provider connection, no scheduled jobs and no publishing.

## Phase 8.6 — Offline OAuth authorization attempt protection

`oauth_attempt_ledger.py` implements a backend-only OAuth attempt ledger with cryptographically random one-time state and a PKCE S256 code challenge. Each attempt is scoped to a business, provider and expected account; it expires after a bounded interval (60–900 seconds) and may be consumed only once. Only SHA-256 hashes of state and code verifier are persisted in SQLite. Consumption uses a serialized SQLite write transaction to prevent replay. Ten regression cases cover successful one-time use, tenant/platform/account mismatches, expiry, invalid verifiers, unknown state, PKCE challenge computation and absence of raw secrets in the database.

**Important:** This is an offline prerequisite, not a functioning OAuth flow. A production server must bind the state to an authenticated user session, securely retain the verifier until callback, validate the exact redirect URI and provider response, perform the authorization-code exchange over HTTPS, confirm the returned account identity and read-only permissions, and store access/refresh tokens in an actual secret vault. The returned verifier must never be logged or placed in a public client URL. No live provider connection, scheduled job or publishing is enabled.

## Phase 8.7 — Independent BAM accounts and multi-platform connection directory

BAM sign-in is independent of Facebook or any other social provider. Businesses may link multiple supported social platforms under their BAM membership, and a user may have separate business memberships. Social-provider authorization is an optional integration step, **not** the way users authenticate to BAM.

`social_connection_directory.py` provides a read-only, tenant-scoped connection listing backed by the existing provider metadata registry. It resolves the BAM session, revalidates current membership and the `READ_ANALYTICS` role permission, and returns platform/account connection status without exposing vault references or provider credentials. Seven regression cases cover multiple platforms for one business, isolation between businesses, session expiry, content-creator denial, viewer analytics permission and non-disclosure of credential references.

This is an offline directory, not a production identity provider, account switching interface, or live OAuth integration. The existing session prototype remains tenant-scoped; a future BAM identity layer must explicitly enumerate the businesses a verified person can access and issue separately authorized business sessions. Connecting Facebook, Instagram or other services does not grant access to BAM itself. No social login, provider token exchange or publishing is implemented.

## Phase 8.8 — Authorized business activation and scoped sessions

The existing `BusinessSwitcher` already listed businesses available to an authenticated BAM user and selected a business role. Phase 8.8 extends it with `activate_business`: after validating the current session, current membership and target membership, BAM issues a **new tenant-scoped session** carrying the target business's actual current role. The source session remains valid, so the app can support switching back without using Facebook or other social sign-in. A removed current-business membership now prevents listing, selecting or activating a different business through that stale session. Three additional regression cases cover target session issuance, unauthorized target denial and revoked source membership.

**Limitations:** BAM user authentication and account recovery are still prototypes, and `activate_business` is an internal server operation, not a finished UI. Production must protect session issuance, consider session revocation on membership changes, bind verified identities across businesses and avoid exposing tokens in logs. This phase does not grant publishing access or create provider connections.

## Phase 8.9 — Session freshness and identity-wide sign-out

BAM's offline session store now supports `resolve_current`, which checks both the session and the latest business membership, rejecting sessions whose roles have changed or whose membership has been removed. Business switching and social connection listings use this stricter check to avoid relying on stale session roles. `revoke_identity` provides a trusted administrative primitive to invalidate one person's sessions across every business, useful for global sign-out or compromised-credential response. These actions are independent of social platform sign-in.

Three additional regression cases cover identity-wide revocation, stale-role and inactive-member denial, and stale source-role denial during business switching. **Production limitations:** BAM still requires verified identity login, trusted administrator authorization for global revocation, token storage protections on devices, and independent session invalidation on account recovery. `resolve` remains available for legacy internal paths and must not be used alone as proof of current authorization. No publishing is enabled.

## Account dashboard integration milestone — 2026-11-10

`account_dashboard.py` composes existing BAM session, business-switching, and social-connection services into a single read-only dashboard model for a future mobile/web client. Every request rechecks current membership and session role. The active business determines which social connections are visible; content creators and other roles lacking analytics access see a restricted status rather than account metadata. Switching businesses issues a separately scoped session and immediately renders the target business's actual role and permissions. The response cannot enable publishing. Five focused regression tests cover tenant-scoped listings, role-filtered connection visibility, unauthorized switching, revoked sessions and stale roles.

A security review also corrected `BusinessSwitcher.select_business` to require a current-role session rather than merely an unexpired one. This closes a stale-role bypass of the source-business membership check. The dashboard is an **offline service composition**, not a running API, authenticated web UI, or Android app. Before deployment, implement secure transport, CSRF/session protections where applicable, user identity verification, authorization at every endpoint, and integration tests against the real runtime. The test files are committed but have not been independently executed in this session.

## Account read API boundary — 2026-11-10

`account_read_api.py` is a transport-neutral adapter for a future authenticated HTTPS interface. It exposes three deliberately narrow operations: `get_overview` (the active business and authorized social connections), `activate_business` (switch to another authorized business and receive a new scoped session), and `logout` (revoke the current session). The API derives tenant and role from validated server sessions, never client claims, and requires a server-supplied timestamp. Six additional regression tests cover business isolation, role changes on switch, logout, malformed credentials, unauthorized target selection and invalid timestamps.

**Deployment boundary:** This adapter does not start a web server or implement password authentication, HTTPS, request throttling, secure client token storage, OAuth callback handling or publishing. A real server must supply trusted session tokens and timestamps, validate origin and CSRF where appropriate, prevent token logging, and enforce access controls at every API route. The Python test files are committed to GitHub's existing CI workflow, but this milestone has not been independently verified as a passing CI run. BAM remains read-only for account operations and publishing remains disabled.

## Local account workflow prototype — 2026-11-10

BAM now includes a **runnable, isolated loopback-only account workflow**, beyond individual backend service calls. `dev_server.py` creates disposable example business memberships, starts a local-only HTTP service, and prints a short-lived **demo** bearer token. `dev_client.py` is an interactive terminal interface that accepts that token without echoing it, shows the current business and permitted social connection metadata, and switches between authorized businesses. Exiting the client invokes authenticated logout across all sessions for that demo identity. This proves the intended separation between a BAM user account and future social platform connections without implementing actual provider sign-in.

To try the local demo in two terminals with Python 3.12 and the repository checkout:

```sh
python dev_server.py
# In another terminal, substitute the port printed by dev_server.py:
python dev_client.py --port 12345
```

The gateway provides `GET /api/account/overview`, `POST /api/account/activate`, `POST /api/account/logout`, and `POST /api/account/logout-everywhere`. POST endpoints accept JSON objects; all operations require a bearer session header. The demo server accepts **only loopback bindings**, rejects cross-origin browser requests and unexpected hostnames, limits request sizes, omits request logging, and returns `Cache-Control: no-store`. It has no public deployment mode, account enrollment, password login, social OAuth, scheduler, or publishing. It is **not suitable for public or LAN deployment**. Disposable credentials printed for the demo must never be reused for real accounts.

New tests cover the transport boundary, browser-origin and DNS-rebinding rejection, self-service global logout, and full HTTP account switching against actual BAM services. A failed account switch dashboard rendering now revokes its newly issued token to avoid leaving an orphaned session. The committed tests still require a verified passing run before considering this workflow validated. A production app will need a proper HTTPS service, persistent database with concurrency controls, verified user login, secure Android token storage, authorization at all routes, and real social integrations.

## Cross-workflow authorization hardening — 2026-11-10

The fresh-session role check introduced for account switching is now also applied to **Content Requests** and **owner approval intent**. A role promotion cannot silently turn an old lower-privilege session into an owner approval credential, and a role change invalidates existing Content Request access until the user obtains a session with their current role. Regression cases explicitly cover stale viewer-to-creator and viewer-to-owner promotion. A preexisting Content Request test fixture was corrected to use a verified attachment ID rather than the removed free-form content-reference argument. These are defensive consistency fixes; they do not activate final approval or publishing.

## Local held-draft workflow integration — 2026-11-10

The account dashboard and terminal demo now surface each business's **held marketing drafts**, the suggested user-supplied materials, and the exact missing content items. Drafts are retrieved through the authenticated `ContentRequestService` and filtered by the currently selected business; switching businesses changes both the visible drafts and the available permissions. Attachment storage references are deliberately omitted from the dashboard response. Drafts remain held for content or review; none are automatically scheduled or published.

The local gateway now accepts `POST /api/content/drafts` to create a new held draft. The server derives the business from the authenticated BAM session, checks the user's current role and creation permission, validates channel, draft text, content suggestion, required items and priority, and refuses unexpected tenant or role claims. The terminal client exposes this as **[n]ew held draft**. This is a manual draft-entry workflow, not an AI text-generation engine or automatic photo upload. Example held drafts are seeded separately for the two demo businesses. Integration tests cover creating a draft through HTTP, seeing it only in the correct business, and denying caller-supplied tenant fields.

**How to exercise:** start `python dev_server.py`, then `python dev_client.py --port <printed-port>` in a second terminal. Paste the disposable token, inspect held drafts, switch businesses, create a new held draft, and exit to revoke demo sessions. The loopback demo is not remotely accessible, is not production-ready, and uses no real social accounts. Full current-branch tests still need an independently verified run.

## Held-draft lifecycle controls — 2026-11-10

The local demo now supports **postpone**, **mark unavailable**, and **reopen incomplete draft** operations through `POST /api/content/hold`. Only an authenticated user with current edit permissions in the draft's business can change its status. The API derives tenant identity from the session, requires an existing 32-character request ID, rejects extra client-supplied fields, and returns not-found for requests belonging to other businesses. Postponed/unavailable requests disappear from the active pending queue but remain in the business's underlying Content Request ledger. Reopening returns an incomplete draft to `needs_content`; a completed draft cannot be reopened into an invalid incomplete state. Tests cover the hold/reopen flow, cross-business denial, viewer denial and malformed fields.

These actions affect **draft holding state only**. No content is uploaded, no TruthGuard approval is bypassed, and no posts are scheduled or published. Current-branch tests still require independent execution.

## Verification workflow update — 2026-11-10

The existing GitHub Actions offline test workflow now compiles all Python files with `python -m compileall -q .` before running `python -m unittest discover -s . -p 'test_*.py' -v`. This catches syntax errors in new modules as well as behavioral regressions when CI actually runs. **No passing CI result has been independently confirmed for the latest development commit.** Until then, the integrated local account demo is an unverified prototype, not a release candidate.

## Authentication foundation — email/password and Google (approved, 2026-11-10)

BAM's approved sign-in architecture supports **both email/password and Google sign-in**, independent of connecting Facebook, Instagram or other social media accounts. The initial backend foundation has been committed:

- `identity_auth.py` stores unique BAM identities, PBKDF2-HMAC-SHA256 password hashes with 600,000 iterations and random salts, verified-email state, explicit Google subject-to-BAM identity links, and active account state. Registration **does not automatically verify email, assign a business role, or issue a session**. A password login succeeds only after email verification and current membership in the requested business. Password changes require the existing password and revoke all BAM sessions.
- `google_token_verifier.py` uses Google's `google-auth` verification library in a trusted server environment and independently checks issuer, configured OAuth client ID/audience, expiration, issued-at time, verified email, and an expected nonce. No unverified Google profile data is accepted as proof of identity. The optional dependency must be installed in a future hosted backend.
- `google_login_challenges.py` issues short-lived, one-use random challenges and nonces; `auth_login_api.py` joins those challenges to verified Google ID tokens and BAM membership. Google accounts are **never automatically linked solely because their email matches**. Explicit linking requires an existing BAM session and fresh password reauthentication.
- Tests cover verified versus unverified accounts, wrong passwords, missing business membership, Google claim tampering, nonce mismatch/replay/expiry, explicit linking, disabled identities, and password rotation.

**Implementation boundary:** These are backend service modules and offline tests, **not a working Google sign-in button or publicly available login endpoint**. The existing loopback demo still uses disposable development sessions. Real user enrollment, verification emails, password recovery, Google OAuth client configuration, secure mobile sign-in, request throttling, production-grade database concurrency, and deployment security remain separate required work. No live social account authorization or publishing has been enabled. The latest current-branch test suite has not yet been independently verified as passing.

## Account enrollment and recovery primitives — 2026-11-10

BAM now includes additional offline account lifecycle services. `email_credential_recovery.py` creates cryptographically random, **one-use, 15-minute** email verification and password-reset tokens, stores only their SHA-256 digests, and passes the raw token solely to a **trusted out-of-band delivery callback**. Unknown email addresses receive the same generic request response, preventing direct account enumeration. A successful reset revokes existing BAM sessions. The callback is not an email service: a real mail provider, delivery controls, rate limiting, and verification UX are still required.

Google-only signup is also supported at the service layer: a server-verified Google ID token with a one-use nonce may create a new BAM identity **without a password**. The new identity receives **no business membership or usable business session** until a separate trusted enrollment or invitation flow grants access. Existing BAM identities are never silently merged with Google identities based on matching email; an existing password account must explicitly link Google using fresh password reauthentication. This supports both Google-first and email-first users while retaining strict business separation.

Security regression tests cover verification and reset token replay/expiry, password reset session revocation, Google-only signup without business access, and rejection of email-only identity merging. These modules are not yet wired to public HTTP routes, Android UI, or real delivery providers; current-branch tests still need a confirmed run.

## Password login throttling — 2026-11-10

`login_throttle.py` adds a persistent per-identity failed-login counter with a bounded lockout window. Identifiers are SHA-256 hashed rather than storing raw email addresses in the throttle ledger. `AuthLoginAPI` can enforce the throttle before password verification, count failed credential attempts, and clear failures after successful login. Regression tests cover lockout, expiry, account isolation, hashed identifiers, and API-level behavior.

**Production security note:** the throttle is an injectable service dependency, not an Internet-grade abuse-prevention system. The production backend must make throttling mandatory and add per-IP/device and global request limits, database-safe concurrency, monitoring, HTTPS, abuse-resistant email delivery and secure Google OAuth setup before exposing authentication endpoints. No public authentication route has been enabled.

## Business invitation foundation — 2026-11-10

`business_invitations.py` provides a trusted backend service for inviting an existing, verified BAM identity into a specific business. A currently authenticated business owner chooses the email and non-owner role (marketing manager, content creator, employee or viewer); the system creates a one-use seven-day invitation token, stores only its SHA-256 hash, and passes the token to a trusted out-of-band delivery callback. Acceptance requires **independently verified BAM identity proof**, an exact verified email match, a still-authorized inviting owner, and a token that has not expired or been used. The grant is scoped to the invited business only. Invitations cannot assign owner privileges or automatically connect social accounts.

This is a server-side invitation primitive, not a public invitation acceptance URL or delivered email. Production needs a verified user-authentication handoff, mail service, rate limits, transactional database concurrency and owner invitation-management UX. Tests cover authorized acceptance, tenant isolation, owner-role restriction, identity mismatch, expiry, token hashing and replay.

## Authentication integration checklist

See [AUTH_DEPLOYMENT.md](AUTH_DEPLOYMENT.md) for the current security trust boundaries, provider configuration requirements, and fail-closed release checklist for the approved email/password plus Google authentication architecture. It identifies the remaining production decisions without requiring Google credentials or other secrets in the repository.

## Mobile-first dashboard GUI prototype — 2026-11-10

BAM now includes an **interactive responsive graphical prototype** at [`ui/bam_dashboard_prototype.html`](ui/bam_dashboard_prototype.html). This implements the approved interface hierarchy: **large, attention-oriented cards on the home screen**, with individual posts, content requirements, sample performance charts, scheduling summaries and controls deeper in each section. The layout uses BAM's navy, teal and gold direction; on narrow screens it switches to a four-item bottom navigation, while larger screens use a sidebar. The prototype supports keyboard focus, semantic navigation, reduced-motion preferences and responsive sizing.

The standalone prototype contains **clearly labeled sample data only**, with example Belenos Creations and Busy B Cleaning Service businesses. Switching businesses changes the visible content and summary counts. Users can open individual held drafts, see missing photographs/permissions, create a draft, postpone it, mark it unavailable, and reopen it. These changes affect only temporary in-browser sample data; refreshing resets them. The sample analytics bars and scheduled counts are illustrative, not real measurements. No login, provider API, external network request, account access, or publishing is wired into this HTML file.

To preview locally, download the HTML file from GitHub and open it in a modern desktop or mobile browser. To exercise the complete experience, switch between the two sample businesses, open Content Needed, drill into a draft, change its hold status, create a new draft, and inspect the Analytics section. The prototype is **not yet connected to BAM's account API**, so it is a UX milestone rather than a deployable application. Static regression checks in `test_dashboard_prototype.py` verify required landmarks, drilldown sections, tenant-specific client state and absence of network/publishing calls. Browser-level accessibility testing and full CI verification are still pending.

The next integration milestone is to implement a secure authenticated hosted frontend-to-backend boundary, replace sample metrics with authorized business-scoped API responses, and connect the GUI's actions to the existing Content Request services without weakening the publishing gate.

## Authenticated dashboard card contract — 2026-11-10

The backend now exposes `dashboard_cards.py`, a **truthful presentation model** derived from the existing authenticated, tenant-scoped account overview. `AccountReadAPI.get_overview` and business activation responses include `dashboard_cards`: content-needed and ready-for-review counts are calculated from authorized held drafts; social connection count is returned only where the user's role permits it. The scheduled-post count is explicitly `null` with `availability: not_connected` until a real scheduler is integrated, rather than pretending that unknown scheduling data equals zero. Restricted connection data is likewise represented as unavailable instead of leaking counts.

The standalone HTML GUI continues to use visibly labeled sample data. The new backend card contract is the bridge for a later secure frontend integration; it is **not yet connected** to the HTML prototype. Regression tests cover known counts, unavailable scheduling, restricted connection visibility, and publishing remaining disabled. The GUI's JavaScript was syntax-checked in a V8 environment and its initial rendering, theme toggle and sample-business switching were smoke-tested with a minimal DOM stub; these are **not** substitutes for real-browser and full CI verification.

## Automated GUI smoke-test gate — 2026-11-10

The offline GitHub Actions workflow now includes Node.js 22 and runs `node ui/dashboard_smoke_test.js` before Python unit-test discovery. This dependency-free smoke test parses the standalone GUI's embedded JavaScript and exercises initial home rendering, demo-business isolation, content and draft drilldowns, analytics/calendar navigation, and light/dark theme switching with a minimal DOM stub. A matching subset was executed successfully in the development V8 environment. **The committed Node script and full GitHub Actions workflow have not yet been independently confirmed as passing.** A real browser accessibility and responsive-layout test remains a separate release gate.

## Settings and appearance UX — 2026-11-10

The approved mobile-first design keeps appearance controls out of the main dashboard. A small **Settings** entry opens **Settings → Appearance**, with explicit **Light**, **Dark**, and **Auto (device)** choices. Auto is the default and follows the device's color preference; when supported, the prototype responds to device theme changes. Settings also reserves space for future account, notification, business and connection preferences. Prototype appearance selection is intentionally in-memory only and resets on reload. The UI JavaScript was smoke-checked for Settings navigation and theme selection. The Node CI smoke test was updated; its workflow outcome is not independently verified.

## Authenticated dashboard view contract — 2026-11-10

The authenticated `AccountReadAPI` now **actually populates** the dashboard-card list in both `get_overview` and business activation responses. The new `get_dashboard_view` service returns a minimal read-only payload (`schema_version: 1`) containing the authorized business list, active tenant, user role, safe card summaries, pending content requests and explicit `not_connected` markers for analytics and scheduling. It does **not** return credentials, provider vault references, live publication permission or a session token. Tests cover business-scoped draft visibility, role-restricted connection counts, missing analytics/scheduling, and invalid sessions. This resolves a discrepancy where earlier documentation described a card integration that had not yet been wired into `AccountReadAPI`.

The static HTML prototype remains a **separate demonstration** with sample data. Connecting it to a hosted HTTPS endpoint requires an authenticated transport, secure session handling and production API implementation. A read-only data contract does not authorize posting or scheduling.

## Complete held-draft list API — 2026-11-10

`AccountReadAPI.list_held_drafts` now returns a sanitized, authorized list of the active business's content requests, optionally filtered by `needs_content`, `ready_for_review`, `postponed` or `unavailable`. This supplements the attention-focused dashboard overview, which intentionally includes only actionable drafts. The list omits raw attachment references, includes missing-item names and keeps publication disabled. It revalidates the session and current business membership, never accepts an arbitrary tenant ID from the client, and delegates to the content service's existing permission checks. Tests cover postponement disappearing from dashboard attention but remaining available in Content Studio, cross-business isolation and invalid status rejection.

## Verified content and frontend data adapter — 2026-11-10

The authenticated content API now supports `supply_verified_content`, which attaches a previously registered, **trusted-worker-verified** attachment to a held draft. Unverified or mismatched attachments are rejected by the existing tenant-scoped registry; completing all required items changes a draft to `ready_for_review`, never `published`. The API returns only the request ID, status and a disabled-publishing flag, not the attachment storage key. Regression tests exercise unverified denial, verified completion and updated dashboard counts.

A separate dependency-free JavaScript adapter, `ui/dashboard_data_contract.js`, validates the authorized `schema_version: 1` payload before a future live frontend renders it. It rejects missing or duplicated businesses/cards/drafts, unknown statuses, fabricated counts for unavailable integrations, unexpected analytics/schedule data, and any claim that publishing is enabled. It projects only safe presentation fields. The CI workflow includes `ui/dashboard_data_contract_test.js` to cover normal and malformed payloads. This is an **integration contract, not a live browser API client**: there is no endpoint fetch, authentication token storage, or social publishing in the prototype.

## Smart and manual posting-time controls — 2026-11-10

The Calendar prototype now contains the approved **Smart times / Manual times** selector, with preferences held separately for each selected business. Manual mode lets users add and remove explicit 24-hour posting times; Smart mode explains that future recommendations will depend on the post subject, audience and connected platform performance. No fabricated recommended times are shown. All choices are in-memory demonstration settings only: they do not survive reload, alter backend scheduling or enable automatic publishing. The UI smoke test now covers mode switching, manual time entry and business isolation; the 24-hour input validator was corrected after an interaction smoke check exposed an escaping error.

## Persistent posting preference service — 2026-11-10

The approved Smart/Manual choice now has an offline backend foundation in `posting_preferences.py`. Each business has its own persisted mode, explicit IANA timezone and (for Manual mode) a sorted, unique set of valid 24-hour `HH:MM` times. The default is unconfigured Smart mode with no assumed timezone or recommended times. An authenticated business member may read the preference, but only the current business owner can change it. `AccountReadAPI.get_posting_preferences` and `set_posting_preferences` derive the business from the current verified session, not an untrusted client tenant field. Regression tests cover role changes, cross-business isolation, timezone and time validation, and the invariant that publishing remains disabled.

The standalone GUI's time settings are **still temporary demonstration state** and are not wired to this service. Production scheduling must separately handle daylight saving time, platform-specific constraints, verified performance evidence, conflict resolution, and explicit publishing permissions. Saving preferences does not schedule or publish any posts.

## Persistent posting-time preferences — 2026-11-10

`posting_preferences.py` now stores **per-business**, owner-controlled Smart/Manual posting-time preferences in SQLite, using an explicit IANA timezone and validated, sorted local `HH:MM` values. `AccountReadAPI.get_posting_preferences` and `set_posting_preferences` derive the active business from a revalidated session; clients cannot supply a different tenant or elevate their role. Read access is allowed to active business members; mutation requires the business owner. Unconfigured businesses report `configured: false` and `timezone: null`, avoiding an invented timezone. Manual mode requires at least one valid time; Smart mode must have no manual times and never returns fabricated recommendations. Neither mode schedules or publishes posts. Regression tests cover validation, revocation, cross-business isolation, role enforcement and reloading stored preferences. A durable database deployment and authenticated HTTPS transport are still required before a real client can use these settings.

## Read-only authenticated dashboard renderer — 2026-11-10

`ui/dashboard_live_view.js` is a dependency-free DOM renderer for the validated `dashboard_view.py` payload. It renders the active business name, four large cards, and content needing attention, distinguishing **Not connected** and **Restricted** from a real zero. All draft text and suggestions are inserted using `textContent` (never raw HTML), and payload validation occurs before the existing dashboard is replaced. This prevents malformed server responses from partially updating the interface. A Node DOM-stub regression test covers normal cards, restricted metrics, malicious-looking text treated as text, and fail-closed rendering; it is included in the CI workflow. The renderer is a reusable UI component, not a deployed app or an authenticated HTTP client. It does not store credentials, submit approvals, schedule, or publish.

## Read-only HTTPS transport foundation — 2026-11-10

The new `bam_read_wsgi.py` provides **GET-only** WSGI routes for `/api/v1/dashboard`, `/api/v1/drafts` and `/api/v1/posting-preferences`. It requires an HTTPS WSGI scheme, accepts a bearer token in the Authorization header, derives the business exclusively from the authenticated server session, and returns JSON with `no-store`, `nosniff`, no-referrer and restrictive CSP headers. No CORS headers, cookie authentication, write endpoints or publication functions are enabled. Errors use generic responses that do not reveal internal records or credentials. This is a reusable application component, **not** a running/deployed server. Production requires trusted TLS termination, secure proxy configuration, operational rate limiting, audit logging without secrets, and authenticated sign-in UI.

The matching `ui/dashboard_http_client.js` performs read-only HTTPS GETs with a memory-supplied bearer token and explicitly disables cookies, caching and redirects. It validates dashboard responses through the strict frontend data contract and has no persistent credential storage. Both WSGI and browser-client regression tests are in the offline test workflow. The frontend still requires a secure login flow and deployment wiring before real users can access their data.

## Authenticated UI integration checkpoint — 2026-11-10

An end-to-end offline WSGI integration test now exercises the real account/session directory, dashboard view, HTTPS adapter and business switching. It checks that authorized connection counts appear only in the correct business, restricted roles do not see counts, and private vault references are never returned. The detailed [authenticated UI integration runbook](AUTHENTICATED_UI_INTEGRATION.md) records the safe integration sequence, local test commands, production security requirements and remaining blockers. These commits do not establish that GitHub Actions has passed, that an HTTP service is deployed, or that the sample GUI is connected to the backend.

## Business-switch response isolation hardening — 2026-11-10

The browser read client and DOM renderer now accept an optional `expectedTenantId` to reject responses for a different business. The renderer exposes `clear({container})` so a future business-switch flow can immediately remove the previous tenant's information before requesting the next view. The integration runbook now requires this ordering. Tests cover rejecting stale cross-business responses and clearing prior-business content. The authenticated switch orchestration itself is still not connected to the HTML prototype.

## Read-only Content Studio browser components — 2026-11-10

The browser now has a strict `ui/content_studio_contract.js` validator and `ui/content_studio_view.js` renderer for all four held draft states: content needed, ready for review, postponed and unavailable. The HTTPS read client validates draft-list responses before returning them. The renderer groups held drafts by state, uses text-only DOM insertion and rejects mismatched business IDs; it deliberately exposes no publish/approve/media-upload actions. Node tests cover state grouping, invalid statuses, unsafe-looking text treated as text, and stale-business rejection; the CI workflow includes them. These components still require secure browser authentication and wiring to the real UI shell.

## Posting preference browser validation — 2026-11-10

`ui/posting_preferences_contract.js` now validates read-only scheduling preference responses. It distinguishes an unconfigured business (no timezone, no times) from configured Smart and Manual modes; rejects invalid, duplicated or fabricated posting times; and rejects any publication-enabled response. The HTTPS read client applies this contract to preference reads. Regression tests are included in the Node CI suite. This does not enable a real scheduler.

## AI architecture integration milestone — 2026-11-10

The approved OpenAI-only model is represented in new offline foundations: `ai_account_policy.py` (BAM-sponsored or own OpenAI key mode, reversible switching, user/business-isolated AI memory), `ai_sponsorship.py` (server-defined owner/invited/public allowance descriptors and atomic SQLite quota reservation), and `ai_draft_request.py` (verified-facts-only draft request assembly using the current user's memory). The matching `test_ai_*.py` modules cover tenant/user isolation, rejection of raw keys, request quotas, and unverified facts. Existing login, business isolation, Content Studio, GUI, scheduling and disabled-publishing work are preserved.

**Important:** No OpenAI requests are made by these offline components; there is no deployed encrypted secret vault, live generation, Google Play billing, direct Facebook Page authorization or automatic publication. The sponsored experience is free to the end user but still incurs OpenAI API costs for BAM's operator. Exact sponsorship allowances and public prices are intentionally not hardcoded. See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) for approved scenarios, implementation gates and outstanding commercial decisions.

## Structured AI content efficiency milestone — 2026-11-10

The approved content workflow is now represented in offline `ai_content_plan.py`: a single planned OpenAI request returns structured post copy and an optional image prompt; copy and image prompts can be revised independently without changing the other component; and advance generation batches are bounded. `ai_local_templates.py` supplies a no-API-cost product spotlight draft from literal verified business facts when that simple format is sufficient. All output remains pending verification and never triggers publishing. The matching `test_ai_content_plan.py` and `test_ai_local_templates.py` cover component preservation, malformed output rejection, batch limits and zero-cost template behavior.

**Images:** Users may optionally create images in ChatGPT Free or paid and upload them to BAM after the future trusted-media workflow is implemented. BAM does not programmatically access a user's ChatGPT Free plan or generate images through these offline modules. See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md).

## Reversible AI key-mode safeguard — 2026-11-10

Switching from a personal OpenAI key to BAM-sponsored mode now retains only the trusted encrypted-vault **reference**, allowing the user to switch back without reentering the key. An explicit `forget_personal_key_reference` action clears the reference and returns to sponsored mode; a future vault service must separately delete/revoke the underlying secret. No raw key is returned or logged. Offline regression tests cover reversible switching and explicit reference removal. Production encrypted vault integration remains pending.

## Persistent AI draft staging milestone — 2026-11-10

`ai_content_drafts.py` now stores independently editable post text and optional image prompts in a tenant- and user-scoped SQLite draft table. Each draft has a revision counter and rejects stale concurrent edits. A media-required draft is explicitly held as `needs_media`, with `media_attached: false`, until a future trusted media-upload/verification flow exists. Drafts can be read only by their creator within the active business; no draft staging or revision path schedules or publishes. The `test_ai_content_drafts.py` regression suite covers isolation, media holds, persistence and targeted revisions. This remains offline development infrastructure, not live AI generation or a completed Content Studio integration.

## AI Content Studio read-only integration milestone — 2026-11-10

The authenticated read adapter and HTTPS-only WSGI component now support `GET /api/v1/ai-drafts` for the current user's business-isolated, unpublished AI drafts. `ui/ai_draft_contract.js`, `ui/ai_draft_view.js` and the HTTPS read client validate and display the separate post copy, optional ChatGPT image prompt, and explicit media-needed hold. They reject mismatched business IDs and any response claiming attached media or enabled publishing. Corresponding Python and Node regression tests were added to the CI workflow. The read-only pieces are reusable building blocks, not yet wired to the deployed GUI; live OpenAI generation and trusted media uploads are still absent.

## Secret-free OpenAI Settings read milestone — 2026-11-10

The authenticated read API and HTTPS WSGI adapter now expose `GET /api/v1/ai-settings` for the signed-in user's current business. The response includes only OpenAI mode, whether a personal key is configured, and the user's isolated memory preferences; it never returns a raw API key or encrypted-vault reference. `ui/ai_settings_contract.js` and the HTTPS client validate this response and reject unexpected secret-bearing fields or mismatched business IDs. Regression tests are included in CI. This is read-only infrastructure; the future Settings screen must still implement safe, server-validated mode changes and vault integration.

## Nested AI Settings presentation milestone — 2026-11-10

`ui/ai_settings_view.js` provides a read-only Settings → AI panel showing the active OpenAI funding mode, hidden personal-key configured status, and the current user's content preferences. All values use text-only DOM insertion; the renderer validates business identity before replacing its container. No key values, edit controls, or publishing actions are exposed. `ui/ai_settings_view_test.js` is included in the CI workflow. The view is a reusable component, not yet connected to a deployed Settings navigation shell.

## AI settings and draft business-switch regression checkpoint — 2026-11-10

The existing account API integration tests now exercise real AI policy memory, persistent AI drafts, authenticated reads and business switching together. The test verifies that a second business does not inherit the first business's AI memory or draft content, and that no key reference is exposed. This expands regression coverage for the approved multi-business architecture; CI completion is still unverified.

## Authenticated AI workspace coordination milestone — 2026-11-10

`ui/ai_workspace.js` now coordinates the read-only AI drafts and AI Settings components using an in-memory bearer session, the active business identity and two validated HTTPS reads. A generation counter discards late responses when the user switches businesses or signs out; failed current-session loads clear both sensitive views. `ui/ai_workspace_test.js` exercises cross-business stale-response handling, logout, successful rendering and error cleanup. The existing HTTP client test was also corrected to count all requests it actually performs. This is a reusable integration controller, not a connected sign-in flow or deployed GUI. No publishing or credential storage has been added.

## Verified image attachment to AI draft milestone — 2026-11-10

AI drafts that require an image can now be associated with a previously registered, **trusted-scanner-verified** image through `AIContentDraftStore.attach_verified_media`. The attachment must match the current business, draft ID and `image` item; pending, unrelated or cross-business attachments are rejected. Verified media changes the held draft to `draft_pending_verification`, **not** approved or published. Neither private storage keys nor attachment IDs are returned in the draft list. The AI draft browser contract, view and workspace now distinguish missing media from verified attached media. Python and Node regression coverage was extended. **This does not implement actual file upload, scanning, image generation or publishing**; the existing attachment registry requires a separate trusted worker to mark a file verified.

## AI permission and structured-output hardening — 2026-11-10

AI preference writes (mode switching, saved-memory edits and key-reference removal) now require an active business role authorized to create drafts; read-only Viewer access cannot mutate those settings. `AIContentPlan.parse_revision_response` rejects malformed or extra-field AI revision responses, including attempted approval/publishing claims. Regression tests cover viewer denial and strict one-component revision output. No new live AI or publishing capability was enabled.

## AI workspace refresh ordering safeguard — 2026-11-10

The authenticated AI workspace coordinator now rejects older in-flight refreshes even within the same signed-in business, preventing delayed API responses from overwriting more recent content. The workspace race-condition tests now cover both business-switch/logout invalidation and out-of-order same-session reads.

## Owner-confirmed AI business facts milestone — 2026-11-10

`ai_business_facts.py` adds an owner-confirmed, business-isolated fact registry with revision checks and provenance labels. Content creators can use these confirmed facts but cannot edit them. `AIContentPlan.create_from_confirmed_facts` creates a structured, unpublished OpenAI draft request only when the active business has an owner-confirmed fact snapshot, recording its revision. This reduces reliance on arbitrary client-supplied claims; **owner confirmation is not independent external fact verification** and drafts still require TruthGuard/factual review before approval. `test_ai_business_facts.py` covers access control, business isolation and stale updates.

## Authenticated AI fact provenance read milestone — 2026-11-10

The account read adapter and HTTPS WSGI component now expose `GET /api/v1/ai-business-facts`, returning only the active business's owner-confirmed fact snapshot, revision and explicit provenance. `ui/ai_facts_contract.js` and the HTTPS client reject mismatched businesses, invalid confirmation claims and enabled-publishing responses. Python and Node tests cover business switching and route validation. This endpoint is read-only; owner fact confirmation is not exposed as an unauthenticated or public browser write, and independent factual verification remains future work.

## AI fact provenance in the authenticated workspace — 2026-11-10

The AI workspace controller can now optionally fetch and render the business's owner-confirmed fact snapshot alongside AI Settings and held drafts. Its read-only fact panel clearly distinguishes unconfigured facts from owner-confirmed facts and explicitly avoids claiming independent verification. Business-switch/logout invalidation, out-of-order refresh rejection and failed-load cleanup also apply to the fact panel. Added safe-DOM and workspace integration tests to CI. The authenticated GUI shell and write-side owner-confirmation interface are still pending.

## AI image revision/media hold safeguard — 2026-11-10

Revising only the post copy now preserves a verified image association, while revising the image prompt invalidates the previous association and returns a media-required draft to `needs_media`. This prevents BAM from silently treating an older image as satisfying a newly revised image brief. The behavior is covered by Python regression tests. A production trusted-media worker must still confirm that a newly supplied image is appropriate for the revised draft.

## Quota-gated AI draft generation orchestration milestone — 2026-11-10

`ai_generation_workflow.py` now coordinates owner-confirmed business facts, structured OpenAI-only draft planning, sponsored quota reservation, a **trusted server-side executor interface**, strict structured-response validation, and staging of unpublished drafts. It rejects unconfigured facts, personal-key mode without its future encrypted-vault executor, exhausted sponsorship, and malformed provider output. Quota is reserved before execution and is not silently refunded on failures. `test_ai_generation_workflow.py` covers successful held drafts, missing facts, allowance exhaustion, personal-key isolation and invalid output. **The executor remains a dependency to be implemented**: this milestone does not make real OpenAI requests, incur charges, generate images or publish posts.

## Generation-time fact revision guard — 2026-11-10

The offline generation workflow now checks the business's fact revision again after the trusted executor returns. If the owner updated the fact snapshot while generation was in progress, BAM rejects the obsolete result instead of staging potentially outdated claims. The sponsored request remains consumed because execution was attempted. Regression coverage was added.

## OpenAI Responses adapter boundary — 2026-11-10

`openai_responses_executor.py` adds a strictly bounded, keyless adapter for OpenAI's structured Responses payload format. It isolates untrusted business input in a user message, requests a strict `post_text` + optional `image_prompt` JSON schema, disables server-side response storage and tool calls, caps output tokens, and rejects incomplete, unexpected, or publishing-related provider output. A **trusted HTTPS transport must still be supplied** by production infrastructure; this module does not access the network, load keys, incur charges, or publish. `test_openai_responses_executor.py` checks the request envelope, model allowlist, secret avoidance and fail-closed parsing. The model allowlist is a provisional engineering configuration, not a deployment pricing decision.

## Disabled-by-default OpenAI HTTPS transport and offline integration — 2026-11-10

`openai_https_transport.py` adds a transport that **refuses all requests by default**. Only a trusted production composition root may explicitly enable it and inject a server-side key resolver plus TLS-verifying HTTPS opener. It enforces the fixed OpenAI endpoint, model and token caps, disabled response storage, no tools, bounded request/response bodies, a timeout and sanitized network errors. The transport never reads keys from a browser, environment or repository. `test_openai_https_transport.py` checks disabled mode, credential isolation and error sanitization. `test_ai_generation_e2e.py` exercises owner-confirmed facts through sponsored quota and the structured OpenAI response adapter into an unpublished, media-held draft **using a fake transport**. No actual API call or charge occurred; deployment, key management, rate/cost accounting and external provider integration still require separate verification.

## AI token usage and estimated-cost ledger — 2026-11-10

`ai_cost_ledger.py` now records tenant/user-scoped provider token counts and **estimated** micro-USD costs using explicit operator-supplied Decimal prices per million input/output tokens; no model prices are assumed. The OpenAI Responses adapter can require a trusted usage observer and rejects successful-looking responses lacking valid provider token counts when accounting is enabled. The offline end-to-end test now exercises provider usage, cost recording and held draft staging. These figures are estimates only, not OpenAI invoices or proof of payment; failures and reservations still require reconciliation before commercial deployment. Tests cover scope isolation and invalid usage/pricing.

## AI request idempotency and duplicate-charge protection — 2026-11-10

`ai_generation_idempotency.py` adds durable, per-business/per-user request-key claims with SHA-256 fingerprints and terminal statuses. The sponsored generation workflow can use this ledger to prevent a repeated request from consuming quota, calling the provider or staging another draft. Reusing a key with changed inputs is rejected; failed or ambiguous requests are **not automatically replayed**. Tests cover successful replay, changed-input rejection, failure holds and tenant isolation. This is an optional foundation for current offline callers; the eventual production HTTP endpoint must require request keys and use shared durable storage. Crash recovery and billing reconciliation remain pending.

## Private AI usage dashboard panel — 2026-11-10

The authenticated account adapter and read-only HTTPS WSGI now expose `GET /api/v1/ai-cost-summary`, scoped to the signed-in user's current business. The browser client, strict data contract and optional AI Settings panel display recorded token counts and operator-priced estimated costs, always labeled **not an invoice or verified charge**. Business-switch/logout and failed-load cleanup clear this panel alongside AI drafts, facts and settings. Python route/scope tests and Node UI tests were added; selected Node tests passed in an isolated JavaScript harness, while complete GitHub Actions/Python verification is still pending. No actual provider charges or publishing were initiated.

## Idempotency enforcement hardening — 2026-11-10

When an idempotency ledger is configured, sponsored generation now **requires** a request key rather than silently bypassing deduplication if a caller omits one. Additional tests cover missing keys and independent users sharing the same business. This safeguard reduces accidental duplicate quota usage; provider retries and ambiguous crashes still need explicit reconciliation.

## Disabled-by-default AI draft generation HTTPS endpoint — 2026-11-10

`bam_ai_write_wsgi.py` now provides a separate **disabled-by-default** `POST /api/v1/ai-generate` endpoint for a future authenticated deployment. It requires HTTPS, bearer authentication, a bounded JSON body, an idempotency key and a trusted server-side sponsorship-plan resolver. The client cannot choose business, model, quota, provider, API key, approval or publishing state. The billing month is derived from server UTC time, and the endpoint returns only a minimal held-draft reference. Tests cover disabled mode, request integrity, authentication, and exclusion of client-supplied scope/publishing claims. **This endpoint is not mounted into a deployed server, and enabling it requires verified secrets, cost controls, provider integration and operational approval.**

## Owner-confirmed business facts HTTPS editing boundary — 2026-11-10

`bam_ai_facts_write_wsgi.py` provides a separate **disabled-by-default** `PUT /api/v1/ai-business-facts` adapter for future owner-facing Settings. It accepts only a bounded facts dictionary and expected revision, derives the business and confirming identity from the active bearer session, and rejects unauthorized creators, stale revisions and client-supplied tenant claims. Tests cover permission checks, optimistic concurrency and disabled/HTTPS safeguards. It is not mounted in the deployed app; owner confirmation remains distinct from independent external factual verification.

## Explicit-action AI browser write client — 2026-11-10

`ui/ai_write_client.js` provides two narrowly scoped authenticated HTTPS operations for a future UI: owner-confirming a business fact snapshot, and requesting an unpublished AI draft using an externally supplied idempotency key. The browser cannot supply tenant IDs, publishing controls, model choices, quota plans or API secrets; requests use bearer authorization, no cookies, no caching and no automatic retries. The operations are **not** automatically invoked by the dashboard and require explicit user actions once the sign-in shell and disabled-by-default endpoints are safely connected. Its security tests passed in an isolated JavaScript harness and were added to CI.

## End-to-end AI HTTPS request replay regression — 2026-11-10

`test_ai_generation_http_e2e.py` now exercises the complete **offline** generation path: HTTPS WSGI request, authenticated session, server-configured sponsorship, idempotency claim, owner-confirmed business facts, structured OpenAI adapter with a fake provider response, and a held unpublished draft. Repeating the same request key must return an already-completed status without a second provider call or duplicate draft. This test is included in the existing Python unittest discovery workflow; complete CI execution has not yet been independently verified.

## Authenticated live-data dashboard cards — 2026-11-10

`ui/live_dashboard_cards.js` and `ui/live_dashboard_cards.css` provide the first live-data counterpart to the sample-data home screen: **four large mobile-first overview cards** with drilldowns, including held content requests and explicit unavailable-state messaging for unconnected scheduling. The controller reads only validated authenticated backend responses, renders via DOM text nodes rather than raw HTML, clears on business change/logout and discards stale asynchronous responses. No fabricated analytics, scheduling or publishing actions are displayed. The JavaScript regression test passed in an isolated harness and was added to CI. **Integration into a production login shell remains pending; the existing HTML demo remains sample-only.**

## Coordinated signed-in dashboard and AI workspace lifecycle — 2026-11-10

`ui/authenticated_workspace_controller.js` coordinates the large-card live dashboard with AI drafts, Settings, confirmed business facts and usage estimates under a single active business/session. It clears both views on logout or business switch, invalidates stale responses and clears all private panels if either part of a refresh fails. This controller does not persist bearer tokens or publish anything. Its integration regression test passed in an isolated JavaScript harness and was added to CI. The real authentication and deployment shell must still supply and revoke sessions; the existing HTML demo is not replaced.

## AI generation hold response business binding — 2026-11-10

Both newly created drafts and idempotent/non-entitled generation holds now carry the authenticated business identifier. The browser rejects responses for a different active business, including successful-looking held results. This closes a cross-business display ambiguity during account switches. Regression coverage was extended for the offline HTTP integration and browser write client; the selected JavaScript test passed in the isolated harness.

## AI request reconciliation and strict JSON hardening — 2026-11-10

The idempotency ledger now supports a private read-only status lookup for the same authenticated user and business, returning completed/failed/in-progress state without triggering a retry or exposing another user's draft. Both AI write endpoints now reject duplicate JSON keys, including nested owner-confirmed facts, to prevent ambiguous request interpretation. Regression tests cover request status isolation, failed request holds and duplicate-key rejection. No retry, external billing reconciliation or provider calls were enabled.

## Optional manual ChatGPT image handoff — 2026-11-10

`ui/ai_manual_image_handoff.js` and the AI draft view now offer explicit, separate Copy Prompt and Open ChatGPT actions only for media-held drafts with an image brief, when trusted browser callbacks are provided. Neither action runs automatically. The user creates and revises the image in their own ChatGPT account and returns to BAM for later verified upload. No API key is required for this optional manual flow; ChatGPT account usage limits remain separate. The selected JavaScript tests passed in an isolated harness and were added to CI.

## Disabled-by-default AI service composition — 2026-11-10

`bam_ai_offline_factory.py` now assembles policy, business facts, structured content planning, quota reservations, request idempotency, held draft storage, cost ledger, OpenAI Responses executor and both WSGI write endpoints into a deliberately disabled service bundle. No credentials are read, no network requests are possible through the default transport, and neither write endpoint is enabled. An offline regression test checks these boundaries. Production enabling requires a separately reviewed composition root, secrets, cost limits and full verification.

## Explicit owner-confirmed business facts editor — 2026-11-10

`ui/ai_facts_editor.js` adds an optional nested Settings editor for authorized business owners. Facts are never invented or autosaved: an owner must explicitly confirm and save them, with the current revision and active business attached to the request. Duplicate or incomplete fields are rejected. The authenticated AI workspace can mount this editor using a trusted `onSaveFacts` callback; the backend independently checks ownership and revision. Selected JavaScript tests passed in an isolated harness and were added to CI. The production sign-in and write API are not mounted.
