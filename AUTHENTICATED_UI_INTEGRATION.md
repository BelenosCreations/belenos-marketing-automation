# BAM authenticated UI integration runbook

Updated 2026-11-10. Development branch: `development/phase-3-5-account-directory`.

See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) for the approved OpenAI-only three-scenario content-generation plan. The future Settings view should expose BAM-sponsored versus personal OpenAI key mode without displaying raw credentials. User/business AI memories must remain isolated; combined post/image-prompt output and component-targeted revisions must remain unpublished drafts.

## Explicit CSV bulk held draft import

Content Studio's Advanced panel can read a local CSV file in the user's browser, parse a strict 1–20 row draft schema and preview the unpublished copy/guidance before a separate **Confirm import** button is enabled. It uses existing authenticated draft-create calls sequentially—no new OAuth token, model API call, batch server privilege or publication capability is required. The user is told that partial server failures may leave confirmed draft requests created; the UI stops automatically and never retries without explicit new confirmation. Malformed rows, duplicate copy and stale tenant/session state fail closed. Images and permissions remain missing until the usual trust checks occur.

**Verified:** [run 43038527274](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43038527274), 813 Python and 47 JavaScript scripts.

## Read-only marketing claim-risk preview

From each versioned Content Studio draft, **Check marketing claim risks** makes an authenticated GET to `/api/v1/content/risk-preview?request_id=<opaque-id>`. The backend resolves the current tenant and reads the stored draft; the browser accepts only bounded, version-matched, nonpublishing heuristic risk signals, displays them as safe text, and clears them when the draft revision changes or the session is invalidated. The analysis can flag pricing, scarcity, warranties, hours and testimonials but neither the presence nor absence of flags grants factual verification or publishing authorization.

**Verified:** [run 43037661505](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43037661505), 813 Python and 45 JavaScript tests.

## Confirmed sign-out on all devices

The signed-in shell exposes the existing `POST /api/v1/auth/logout-everywhere` session revocation via a separate warning, Confirm and Cancel UI. On confirmation the in-memory session is cleared before network delivery. Success is reported only when the server confirms the revoked-session count; otherwise the user is told that other devices may still have valid sessions. This is not social OAuth token revocation or a device enrollment manager. **Verified:** [run 43036158603](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43036158603).

## Owner-only Team Access panel

The Team Access panel reads `GET /api/v1/team-overview` only for a trusted active-business owner. The server checks `MANAGE_TEAM`, returns strictly aggregate active role counts and inactive membership count and never exposes member IDs, email addresses, invitations or permission-changing actions. The browser validates all totals and discards stale data on business/session change. An optional failed count read does not require sign-out. **Verified:** [run 43035508617](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43035508617) (809 Python, 44 JavaScript).

## Zero-cost advance AI topic preview

An authorized creator can input 1–14 future topics in AI Drafts and call `POST /api/v1/ai/batch-preview` with only those topics, the selected platform and whether a future prompt may be needed. The backend resolves the business from the current session, checks CREATE_DRAFT permission and owner-confirmed facts, and returns only metadata about hypothetical individual model requests. The browser rejects any response implying provider execution, quota reservation, draft creation, known charges or publication. The AI Preview remains a read-only-in-effect operation, with no OpenAI API calls; it is not a scheduling queue or discounted batch execution. The UI discards late results after switching businesses or losing edit capability.

**Verified:** [GitHub Actions run 43058003130](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43058003130), 845 Python and 55 JavaScript tests.

## Private AI writing preferences in Settings

Authorized users can edit their own per-business AI writing guidance through separate label/value rows. The browser sends exactly `memory` and `expected_memory` to `PUT /api/v1/ai-memory`. The server resolves current session identity/business, authorizes draft creation, validates bounded nonsecret values, and compares the prior state before saving. A conflict requires the user to refresh; it does not silently overwrite another browser's preferences. Viewers do not see the editor; changing business or signing out invalidates late UI actions. This is not an owner fact-verification screen, provider key store, automatic AI generation or publishing control.

**Verified:** [run 43056197885](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43056197885) — 836 Python tests and 53 JavaScript UI test scripts.

## Opt-in targeted AI regeneration UI (disabled in ordinary preview)

`ui/ai_draft_view.js` can optionally render two-step **Prepare / Confirm** controls to regenerate exactly one AI draft component, post text or an existing image prompt. The user supplies a topic/instruction and reviews an explicit notice about potential sponsored or personal-key API usage before confirmation. The private `ui/ai_targeted_revision_client.js` sends only the current draft/revision/component and an opaque cryptographically generated idempotency key. `ui/ai_workspace.js` discards stale business responses and refreshes the draft after confirmed success; held/failed responses cannot masquerade as successful revisions. This feature is **off by default** and is not enabled in the normal offline shell. It does not approve media or publish.

**Verified:** [GitHub Actions run 43054882416](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43054882416), 830 Python and 50 JavaScript tests.

## Independent held-draft copy and guidance editing

The business-scoped Content Studio GET response now includes a monotonically increasing held-draft revision. Each draft exposes a separate explicit Save for `draft_text` or `suggestion`, sending only `request_id`, `target`, `revised_text` and `expected_revision` via `PUT /api/v1/content/drafts`. The disabled-by-default backend verifies current business and editor permission, checks the expected revision atomically, and returns a version-confirmed result; the browser re-reads tenant content. Stale revisions reject the change rather than silently overriding a coworker's edit, and logout or business switching invalidates pending actions.

A changed draft does not become approved or publishable. Edits to previously reviewed copy invalidate the prior owner review intent. Old local SQLite records are migrated to include the revision without deleting drafts. **Verified:** [GitHub Actions run 43034533473](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43034533473), 807 Python tests and 42 JavaScript scripts.

## Scheduling and review details inside the large-card dashboard

The Scheduled card loads `GET /api/v1/posting-time-preview` only after explicit drilldown navigation. It displays possible Manual-mode clock slots with the IANA timezone, flags skipped DST hours, and labels Smart timing as awaiting verified audience evidence. It does not show fake scheduled posts or create jobs. The Settings link navigates to the already-connected owner-controlled time editor.

The Approvals card filters business-verified dashboard drafts for `ready_for_review`, explains that they are not approved/scheduled, and links to Content Studio. Both views use `textContent` rendering and lifecycle checks to stop old business controls and late network responses from appearing after token rotation. **Verified:** [run 43032704184](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43032704184).

## Read-only connected-account drilldown

The dashboard's Connections card optionally opens `GET /api/v1/connections`, which lists provider account status only when the current BAM session permits analytics-read access. The response is current-business scoped; account aliases, effective status and read-only scope are the only per-account fields beyond update/expiry timestamps. No OAuth tokens, vault references, permissions to publish, or mutable social configuration may be returned.

`ui/connections_contract.js` validates a strict response, and `ui/live_dashboard_cards.js` loads detail only on explicit navigation. Restricted roles do not fetch the endpoint. A failed request displays unavailability, not an invented empty connection list; stale promises and old buttons are ignored after switching businesses or signing out. Provider status is for information only and never authorizes scheduling or publishing.

**Verified:** [GitHub Actions run 43031957718](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43031957718): 797 Python tests, 40 JavaScript scripts.

## Local-only image receipt — pending and quarantined, not verified

An opt-in `pending_media_dir` on `BAMOfflineGateway`, or `--pending-media-dir` on the loopback TLS runner, permits a separately guarded `PUT /api/v1/content/media-bytes` route after the existing authenticated metadata preflight. The request must carry a valid server-issued pending attachment ID and raw image bytes of the matching PNG/JPEG/WebP type and SHA-256 digest. A fresh session/membership check is enforced before reading and again before storing bytes. The local store is outside the source repository with private permissions and no download route.

The response is explicitly `pending_scan`, `media_verified:false`, `publishing_enabled:false`; neither the attachment registry nor the content request changes to approved/ready. This protects against users assuming that uploading an image grants rights, passes malware checks or authorizes a marketing post. A separate trusted scanner, decoded-media processor, rights confirmation and a later owner-reviewed workflow remain mandatory.

**Verified [run 43016103634](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43016103634): 779 Python tests and 35 JS scripts.**

## Multi-business journey over actual loopback HTTPS

`bam_local_preview.py add-business` requires an existing local owner's password and membership before enrolling another local-only test tenant under the **same BAM identity**. The local CLI cannot be invoked through an HTTP endpoint, cannot bypass public email verification or claim a different user role, and refuses duplicate businesses.

The ephemeral real-TLS smoke test covers password login, first-business held draft creation, switching to another owned business over `POST /api/v1/businesses/activate`, source session revocation, second-business data isolation and final sign-out. The test does not reach any external provider or API. **Verified [run 43015125493](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43015125493): 770 Python and 35 UI tests.**

## Local-only test runner for authenticated shell

`python bam_local_preview.py bootstrap` provisions one local test owner in an external/private SQLite file using an interactive password prompt. This trusted local CLI explicitly marks the test email as verified **without real email proof** and must never be reused as a remote signup API or production account enrollment. `python bam_local_preview.py serve ... --i-understand-local-only` additionally requires external TLS cert/key paths and serves the opted-in gateway and browser assets on 127.0.0.1 only. Exact localhost Host and remote-address checks prevent DNS-rebinding or accidental exposure. All forwarded protocol headers are ignored, and the TLS socket is the sole HTTPS trust boundary. There is no public interface, forwarding or tunneling support.

See [Local HTTPS preview guide](LOCAL_PREVIEW.md) for usage and separate security limits. [Run 43014114797](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43014114797) verified 768 Python tests and 35 JavaScript scripts. This is not production hosting.

## Restricted browser delivery composition (no hosted server)

`BAMOfflineGateway(db, enabled=True, serve_browser_assets=True)` explicitly opts the **local WSGI direct-call integration fixture** into delivering `GET /ui/bam_signed_in_shell.html`, its referenced browser scripts and styles, and the canonical `/branding/source/app_icon.svg`. Neither switch has an internet-facing listener, TLS management, or production authentication enrollment. The asset adapter rejects all other resources, demo HTML, files and insecure WSGI schemes. A trusted reverse proxy must set `wsgi.url_scheme` independently of user-controlled `X-Forwarded-Proto`.

The supplied Content Security Policy permits scripts and API connections only from the same origin, disallows unsafe eval, frames, plugins and external connections, and hashes the single inline stylesheet. A regression executes the browser scripts in HTML order in a JS VM to detect browser/global dependency problems not caught by Node module imports. This is a structural readiness milestone, **not deployment approval or actual browser e2e verification**.

See [GitHub Actions run 43013333985](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43013333985) for **764 Python and 35 JS test scripts** plus compilation.

## Current verified design boundaries

- BAM is a multi-business application, not limited to Belenos Creations or Busy B Cleaning.
- Email/password and Google sign-in are approved, but production login and Google token validation infrastructure are not deployed.
- The sample-data HTML prototype is a design demonstration. The separate `ui/bam_signed_in_shell.html` is a read-only authenticated-shell integration artifact; neither is deployed.
- `AccountReadAPI` derives tenant and role from a server session. Never trust browser-supplied tenant IDs or roles.
- `dashboard_view.py` returns only safe, authorized presentation data.
- `bam_read_wsgi.py` exposes GET-only dashboard, held drafts, AI draft components, OpenAI settings and posting preference routes.
- `ui/dashboard_http_client.js` can retrieve read-only HTTPS data using a session token supplied in memory.
- `ui/dashboard_data_contract.js` rejects malformed/unauthorized-looking data and fabricated counts.
- `ui/dashboard_live_view.js` renders safe text and unavailable states without raw HTML insertion.
- Posting preferences are tenant-scoped, owner-editable, stored in SQLite and have no effect on publishing.
- Content attachments are references to externally validated items; real upload/scanning does not exist.
- Publishing, auto-posting and scheduler execution remain disabled.

## Local service-business drafts

Alongside product spotlight templates, the disabled-by-default `POST /api/v1/ai/local-service-draft` route and `LocalDraftTemplates.service_spotlight` create a literal, owner-fact-grounded service draft. Its optional image prompt must be a clearly conceptual illustration and not a claimed photograph of actual employees, customers, properties or completed work. The UI offers only product or service types with currently confirmed facts, never manufacturing a missing field. Template creation makes **zero BAM OpenAI API requests**, but ChatGPT account limits for manual image creation are separate.

**Verified [GitHub Actions run 42962115509](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42962115509): 760 Python tests and 35 JS scripts.**

## Manual single-component AI draft edits

The signed-in AI Drafts panel offers separate explicit Save controls for the post copy and existing image-generation prompt. `ui/ai_draft_edit_client.js` sends only the draft ID, selected component, revised text and expected revision to the disabled-by-default `PUT /api/v1/ai-drafts` backend. `AccountReadAPI.edit_ai_draft_component` checks the authenticated current user/business and `AIContentDraftStore.revise` enforces edit permission and an optimistic revision guard. A changed image prompt invalidates a prior verified-media match; it cannot imply that fresh media was uploaded.

No AI request, owner fact change, automatic approval or social publishing occurs. The browser discards any late response after business rotation/logout and performs a fresh authenticated read before showing revised content.

**Verified [GitHub Actions run 42961746379](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42961746379): 757 Python tests and 34 UI test scripts, plus compilation.**

## Business-role-driven editing affordances

`GET /api/v1/dashboard` already returns the active business's current membership role, determined by `AccountDashboard.overview` after live membership/session validation. The normalized browser role is restricted to `owner`, `marketing_manager`, `content_creator`, `employee` or `viewer`; missing role defaults to read-only. `ui/authenticated_workspace_controller.js` uses the current dashboard response to set UI-only permissions before refreshing dependent panels. Owner-only fact confirmations and posting time save controls are hidden from nonowners; employees and viewers cannot see held-content or local-template create/edit actions. All flags are discarded on business switch and logout.

Client permission flags are not authorization tokens: all corresponding HTTPS write endpoints enforce current server-side tenant membership and role. **Verified in [run 42961295058](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42961295058): 750 Python tests and 32 UI tests.**

## Explicit no-API-request product draft

The authenticated AI Drafts panel offers a **manual** zero-API-cost product spotlight creation action only when the active business has owner-confirmed `business_name` and `product` facts. `ui/local_product_draft_client.js` sends just the social platform and optional image prompt choice to `POST /api/v1/ai/local-product-draft`. The backend resolves current business and facts, uses a zero-API-request local template, then stages an unpublished user/business-isolated AI draft. The user can use the optional image prompt separately in their own ChatGPT account; BAM does not generate, upload, inspect or approve that image.

The route is mounted in `bam_offline_gateway.py` and is disabled by default except direct-call test composition. A browser or user cannot claim verified facts, choose a model/API key, set a publish state or infer real billing from the zero generation-call marker. On tenant switch or logout, pending UI results are discarded.

**Verified in [GitHub Actions run 42960676199](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42960676199): 750 Python tests and 31 UI script tests.**

## Explicit owner business facts editor

The `bam_offline_gateway.py` direct-call integration fixture now routes `PUT /api/v1/ai-business-facts` to the existing owner-authorized fact confirmation adapter. The signed-in Settings page mounts the prebuilt `ui/ai_facts_editor.js`, with a save callback capturing only the active in-memory BAM business session. The backend independently checks actual owner permission, validates the expected revision and stores confirmed facts scoped to the current business. On a successful save the AI panels reload. A logout/business switch invalidates pending callbacks. Nonowners cannot save even if a control appears in the integration-stage shell.

The browser never transmits tenant/role/approval claims and never enables actual publishing. Confirmed owner statements must still pass factual content review before any future publication.

## Quarantined image status and explicit removal

With the local-only pending media store opted in, `GET /api/v1/content/media-status` returns the authenticated current tenant's `awaiting_file` or `pending_scan` statuses for required checklist items. It returns no file bytes, storage locations, attachment IDs or media-verified claims. Content Studio hides repeated transfers when a pending file was already received.

An editor can explicitly confirm `DELETE /api/v1/content/media-pending` with only a request ID and required item name. The backend resolves current business and edit permission from the BAM session, removes matching pending-only quarantine records and their private files, and never affects verified media or publication. The browser then reloads status before allowing a replacement. This local test workflow is not a production scanner, media gallery or content approval flow.

**Verified [GitHub Actions run 43020735001](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43020735001): 789 Python tests and 37 JavaScript test scripts.**

## Pending media metadata — not an upload

`POST /api/v1/content/upload-preflight` is deliberately disabled by default and exposed only through the offline gateway. It accepts metadata for an existing required content item in the session's current business. Authorization is server-side and no uploaded bytes, storage keys, presigned URLs or permissions are returned. The response contains an unverified `pending` attachment ID and `publishing_enabled:false`. An attachment remains unusable until a separately trusted storage, inspection, malware/consent verification and acceptance pipeline is implemented. Do not add an Upload button that implies a file has been transferred merely because metadata preflight succeeded.

## Owner-only Smart/Manual posting preferences

`bam_posting_preferences_wsgi.py` exposes a disabled-by-default `PUT /api/v1/posting-preferences` route through the offline BAM gateway, parallel to its existing authenticated GET endpoint. The only accepted client fields are `mode` (Smart/Manual), a valid server-checked IANA timezone and up to 24 unique 24-hour local posting times. Manual requires times; Smart must not include them. The trusted account read API checks current tenant membership and the business owner role before any update.

`ui/posting_preferences_workspace.js` mounts a nested Settings editor, with explicit Save, verified server-refresh, and stale-business clearing. The browser write client rejects mismatched tenants, fabricated published state and unexpected response fields. A saved preference never activates scheduling or publishing. The approved smart-time algorithm must later use actual audience evidence and explicit owner/business controls.

Verified together with the Content Studio in [GitHub Actions run 42959720838](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42959720838): 735 Python tests, 30 JavaScript scripts and Python compilation.

## Signed-in Content Studio (held drafts only)

The signed-in HTML shell includes a separate `Content Studio` tab, wired by `ui/held_draft_workspace.js` to the existing read-only `GET /api/v1/drafts` and held-only WSGI write routes `POST /api/v1/content/drafts` and `POST /api/v1/content/hold`. No browser field can claim a tenant, user role, schedule or publish permission. Every write response must match the expected signed-in tenant and `publishing_enabled:false`; every successful write is followed by an authenticated list refresh. Server-side authorization checks the current session and role.

The Content overview card can open this panel directly. A session switch invalidates pending UI updates and destroys the old tenant's private Content Studio DOM. This only operates where the trusted disabled-by-default offline API fixture is deliberately enabled for direct-call tests; it is not a hosted interface, production enrollment flow, media upload or publishing integration.

## Disabled-by-default sign-in boundary

`bam_auth_wsgi.py` now has five strict HTTPS-only POST routes: `/api/v1/auth/password`, `/api/v1/auth/google-challenge`, `/api/v1/auth/google`, `/api/v1/auth/logout`, and `/api/v1/auth/logout-everywhere`. Authentication requires `enabled=True` plus a trusted `AuthLoginAPI` with a throttle, a real server-side Google signature/issuer/audience/nonce verifier, and business membership checks. The existing localhost HTTP developer server does not mount these routes. `ui/auth_login_client.js` uses same-origin JSON POST, no cookies or retries, and gives the eventual authenticated shell a validated token and tenant context held in memory. Explicit logout calls are implemented via an injected trusted read/logout service, with the authenticated client clearing its private DOM before network completion. It does not implement Google OAuth browser redirects or production enrollment. A complete authentication service must still provide TLS, rate limits by IP, monitoring, account recovery, secure session revocation, and real-browser testing.

## Read-only authenticated shell checkpoint

The [signed-in shell](ui/bam_signed_in_shell.html) composes an HTTPS-only password form with the authenticated workspace controller. A four-card Overview leads to deeper, read-only AI Drafts and Settings; no analytics are fabricated, no media are uploaded and no posts publish. The sample-data [prototype](ui/bam_dashboard_prototype.html) remains separate. The DOM integration test validates password field clearing, sign-in views, navigation, appearance, refresh and logout. **Verified in [GitHub Actions run 42952514922](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42952514922): 693 Python and 25 JavaScript tests passed**. The shell is not a deployed website or Android app; a trusted HTTPS hosting/service composition is still required.

## Verified business switching and offline service composition

The signed-in header renders the business names returned by the authenticated dashboard, not a client-invented membership list. `ui/business_switch_client.js` sends only `target_tenant_id` with the in-memory session token to `POST /api/v1/businesses/activate`. The strict `bam_business_switch_wsgi.py` uses the trusted `AccountReadAPI.activate_business` to verify active membership and role, creates a replacement session, revokes the source session and returns only a session token and selected business ID. The UI clears the old business data before requesting new data, discards stale asynchronous responses and refuses to store tokens in localStorage/cookies. No social posting is triggered by switching.

`bam_offline_gateway.py` is a disabled-by-default integration composition for *direct* WSGI calls: real SQLite identity checks, a trusted login throttle, dashboard, owner-confirmed AI data and session rotation can be tested end-to-end. It is not a server startup script, cannot be used as production authentication without additional controls, and has no live Google provider, social network, OpenAI connection or publishing capability. The branded shell uses canonical `branding/source/app_icon.svg` and the repository includes Android adaptive icon templates, but no APK is built.

**Verified [GitHub Actions run 42954241030](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/42954241030): 717 Python tests and 26 JavaScript test scripts passed.**

## Remaining steps before real authenticated GUI

1. Establish a production database with migrations, backups, transactional consistency and secure key management.
2. Deploy the HTTPS service behind a trusted TLS termination layer. Ensure the WSGI HTTPS scheme is set by the trusted server configuration, never by client headers.
3. Add rate limiting, operational observability, security audit events without credentials, request-size limits and production error handling.
4. Implement verified email delivery, password recovery and Google OAuth/ID-token verification with configured audience, issuer, nonce and account linking.
5. Build secure browser sign-in and logout, with session token lifecycle confined to memory and protected against cross-site requests. Decide on a production session model before exposing authenticated writes.
6. Connect the read client to the live dashboard renderer and build responsive CSS, keyboard navigation and real-browser accessibility tests.
7. Connect business switching to the server-issued replacement session and refresh all views atomically. Call `BAMLiveView.clear({container})` **before** requesting or rendering a newly selected business; pass `expectedTenantId` to both `BAMReadClient.read` and `BAMLiveView.render` to reject stale responses. Never retain prior business data on failed switching.
8. Connect Content Studio read and write operations to authorized backend APIs, preserving held-content and approval safeguards.
9. Build a trusted media upload, ownership/permission verification and malware-scanning pipeline before allowing users to complete content requests with real files.
10. Implement real scheduling and platform integration only after explicit publishing approvals, API permissions and separate release security review.
11. Wire the OpenAI-only generation service through server-verified business facts, per-user AI memory, trusted encrypted credentials, sponsored usage controls and held-draft review. Support optional external ChatGPT-created image uploads without requiring another signup.\n12. Run the complete Python and Node CI suite and review GitHub Actions outcomes. Current CI outcomes have not been independently verified through available tooling.

## Safe manual validation commands

```sh
python -m compileall -q .
python -m unittest discover -s . -p 'test_*.py' -v
node ui/dashboard_smoke_test.js
node ui/dashboard_data_contract_test.js
node ui/dashboard_live_view_test.js
node ui/dashboard_http_client_test.js
node ui/content_studio_contract_test.js
node ui/content_studio_view_test.js
node ui/posting_preferences_contract_test.js
node ui/ai_draft_contract_test.js
node ui/ai_draft_view_test.js
node ui/ai_settings_contract_test.js
node ui/ai_settings_view_test.js
```

Do not expose `bam_read_wsgi.py` directly to the public internet without a trusted HTTPS proxy, authentication and rate limits. Do not treat the demo's sample metrics as production data. Do not store BAM or social provider credentials in GitHub, client source, screenshots or logs.

### Authenticated AI workspace coordinator

`ui/ai_workspace.js` accepts an authenticated in-memory token and active tenant from the future sign-in/business-switch shell, then fetches AI drafts and AI settings via HTTPS. It discards late results after a tenant switch or sign-out, and clears private views on current-session errors. Do not wire it to sample/demo credentials or browser storage. The corresponding `ui/ai_workspace_test.js` runs in Node CI. This is not a complete deployed authentication or AI generation workflow.

### AI fact provenance read

`GET /api/v1/ai-business-facts` returns the active business's owner-confirmed fact snapshot and revision. Browser consumers must use `ui/ai_facts_contract.js` and reject tenant mismatches. Owner confirmation is provenance, not independent verification. This route cannot edit facts, approve drafts or publish.

### AI fact provenance panel

The optional `factsContainer` argument to `ui/ai_workspace.js` renders `ui/ai_facts_view.js` from the authenticated `/api/v1/ai-business-facts` route. It is read-only and rejects stale business responses. If fact confirmation is absent, it shows a hold warning rather than treating AI generation as factually ready. Do not present owner confirmation as independent verification.

### AI cost summary

`GET /api/v1/ai-cost-summary` returns the current authenticated user's operator-priced token/cost estimates for the active business. `ui/ai_cost_contract.js` validates the response; `ui/ai_cost_view.js` is an optional read-only Settings panel. The panel must never imply that estimates are real invoices or verified charges.

### AI draft generation write endpoint

`bam_ai_write_wsgi.py` exposes a separate disabled-by-default `POST /api/v1/ai-generate` adapter. It accepts only `topic`, `platform`, `needs_media`, and `include_image_prompt` in JSON, plus an idempotency header and bearer session over HTTPS. Business identity, UTC billing month, sponsorship plan, model, API credentials and publish permissions remain server-owned. This adapter is not mounted or enabled in the development server.

### Owner-confirmed fact updates

`bam_ai_facts_write_wsgi.py` provides a disabled-by-default owner-authorized `PUT /api/v1/ai-business-facts` endpoint. The client supplies `facts` and `expected_revision` only. Tenant identity and owner permission are determined from the bearer session. Conflicting revisions require refreshing the fact snapshot before resubmission. This is not mounted in the current app.

### Explicit-action browser writes

`ui/ai_write_client.js` supplies `generate` and `confirmFacts` calls for the future authenticated UI. Both require a bearer session, strict HTTPS origin and injected fetch. Generation requires a 32-character random idempotency key from the authenticated shell; no automatic retries or publishing are allowed. The browser does not choose business, model, quota or API key. These calls are not wired to the sample-data GUI.

### Authenticated large-card dashboard

`ui/live_dashboard_cards.js` reads `GET /api/v1/dashboard` using the existing strict data contract and renders large overview cards plus read-only drilldowns. Add `ui/live_dashboard_cards.css` to the authenticated shell. Call `activate({token,tenantId})` after sign-in/business switch and `clear()` before logout or token disposal. This controller deliberately does not invent analytics or allow publishing. It is distinct from the sample-data HTML prototype.

### Combined signed-in workspace

`ui/authenticated_workspace_controller.js` coordinates the live dashboard and AI workspace with a single `activate({token,tenantId})`, `refresh()`, and `clear()` lifecycle. Call `clear()` before logout or business change, then `activate` with the newly issued business-specific session. A failed refresh clears all private panels; no token is stored persistently. It is a browser controller awaiting production sign-in integration.

## Unassigned held-draft slot suggestions — preview only

`GET /api/v1/calendar-suggestions` returns a read-only, tenant-scoped snapshot of at most 20 potential slots for eligible held drafts, based solely on confirmed Manual-mode times. It does not reserve slots or mutate saved proposals. The exact response contract requires `status: suggestion_preview_only`, `posts_scheduled: 0`, `publishing_enabled: false`, unique request IDs and UTC times, bounded counts and draft revisions. `ui/calendar_proposals_client.js` rejects anything else; the signed-in Scheduled drilldown shows this separately from saved proposals and actual scheduled posts. A viewer may read only if its current business role permits draft reads. No user input can inject a tenant, schedule a post or trigger an OpenAI request. **Verified:** [run 43078999350](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43078999350).

## Stale tab and concurrent editor protection for held-draft dates

Calendar proposals now return `proposal_token` (an opaque write-version string) for each saved entry. A first-time `POST /api/v1/calendar-proposals` must send `expected_proposal_token: null`; editing an existing date must send the last confirmed version, and `DELETE` must always send that version. The server compares the current version before changing or removing any proposal, rotates the token on every edit, and returns `409 Conflict` for stale requests. Content Studio uses the token in its exact tenant-scoped browser contract while still requiring current business edit permissions and draft revision. A previously saved proposed date cannot be silently overwritten by another user's stale browser state. SQLite existing proposal tables are migrated in place. **Verified:** [run 43080077237](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43080077237).

## Approvals card: review-preparation details (read-only)

When the signed-in user opens **Approvals**, the new `ui/review_readiness_client.js` requests `GET /api/v1/review-readiness` over current-session same-origin HTTPS. Strict shape validation checks business identity, item IDs/revisions, allowed statuses, counts, missing/unverified material labels, and mandatory nonapproval blockers. The card displays separate editorial-material completeness and content gaps, and explicitly says nothing is approved or published. The backend obtains the active business from the verified session; no query can select another tenant. The frontend clears the panel and invalidates pending responses when signing out or switching businesses. This feature can be turned off independently of saved calendar proposals. **Verified:** [GitHub Actions run 43081725025](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43081725025).

## Team editorial feedback and local draft filters

The Approvals detail page now reads `GET /api/v1/review-feedback` separately from editorial-readiness status and shows the currently saved private note per held draft. Owners and marketing managers can explicitly save or remove notes through versioned `PUT` and `DELETE`; read-only staff never see write controls. Delete requires a second in-page confirmation. The editor always submits the active, server-confirmed business bearer session, exact expected draft revision, and current saved note token (or `null` for first creation). Network errors and stale versions do not claim success.

The Content Studio independently displays these notes in read-only form beside the corresponding draft and warns when feedback refers to an older revision. It does not permit creators to change reviewer notes. Search/status/channel filters are purely local UI state, do not change backend scopes and reset on sign-out/business switch. The entire interface continues to refuse social publishing, final approval and automatic scheduling. **Verification:** [GitHub Actions run 43088917850](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43088917850).

## Two-step suggested-date selection in Scheduled

Manual-mode suggestions remain unreserved previews until an authorized content editor explicitly chooses a time and confirms it a second time. The confirmation calls the same strict, non-executable proposed-date endpoint used by Content Studio; conflict or stale-draft failures do not claim success and invoke a new server-sourced preview. The original suggestion buttons are invalidated by sign-out, business switching, session epoch changes and preview replacement. This never invokes any social scheduler or publishing API. **Verified:** [GitHub Actions run 43089512284](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43089512284).

## Redacted reviewer activity in Approvals

Owners and marketing managers can open the **Recent reviewer note activity** section underneath the editorial checklist. The UI uses `ui/review_feedback_history_client.js` to read strictly validated metadata from `GET /api/v1/review-feedback-history` for the currently active business. No historical note bodies or actor identities are returned to the browser. The display includes a short chronological event list (max 10), truncation guidance and explicit no-approval language. Viewers, employees and content creators do not receive history controls or fetches; sign-out/business changes clear the panel and invalidate in-flight reads. It never sends a write request. **Verification:** [GitHub Actions run 43090679750](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43090679750).

## Mobile-first Content Studio priority and queue views

New held drafts may be given a visible drafting priority when saved (default Normal, integer 0). These values are validated by the already-existing tenant-scoped backend writer. The Content Studio summary shows real, current-business counts and outstanding checklist items without external analytics; the visible filters now include urgency/priority in addition to channel, status and copy search, with one-tap shortcuts for high-priority missing-content tasks and human review candidates. Filter choices are local and are reset on sign-out or business switch. This UI never sends filter terms to a server or changes server-side content without the separate explicit create/edit workflows. The priority display does not mean an earlier social publish time. **Verified:** [GitHub Actions run 43091924513](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43091924513).
