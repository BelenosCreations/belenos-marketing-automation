# BAM authenticated UI integration runbook

Updated 2026-11-10. Development branch: `development/phase-3-5-account-directory`.

See [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) for the approved OpenAI-only three-scenario content-generation plan. The future Settings view should expose BAM-sponsored versus personal OpenAI key mode without displaying raw credentials. User/business AI memories must remain isolated; combined post/image-prompt output and component-targeted revisions must remain unpublished drafts.\n\n## Current verified design boundaries

- BAM is a multi-business application, not limited to Belenos Creations or Busy B Cleaning.
- Email/password and Google sign-in are approved, but production login and Google token validation infrastructure are not deployed.
- The sample-data HTML prototype is a design demonstration. It is **not** the authenticated app.
- `AccountReadAPI` derives tenant and role from a server session. Never trust browser-supplied tenant IDs or roles.
- `dashboard_view.py` returns only safe, authorized presentation data.
- `bam_read_wsgi.py` exposes GET-only dashboard, held drafts, AI draft components, OpenAI settings and posting preference routes.
- `ui/dashboard_http_client.js` can retrieve read-only HTTPS data using a session token supplied in memory.
- `ui/dashboard_data_contract.js` rejects malformed/unauthorized-looking data and fabricated counts.
- `ui/dashboard_live_view.js` renders safe text and unavailable states without raw HTML insertion.
- Posting preferences are tenant-scoped, owner-editable, stored in SQLite and have no effect on publishing.
- Content attachments are references to externally validated items; real upload/scanning does not exist.
- Publishing, auto-posting and scheduler execution remain disabled.

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
