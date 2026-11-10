# BAM authenticated UI integration runbook

Updated 2026-11-10. Development branch: `development/phase-3-5-account-directory`.

## Current verified design boundaries

- BAM is a multi-business application, not limited to Belenos Creations or Busy B Cleaning.
- Email/password and Google sign-in are approved, but production login and Google token validation infrastructure are not deployed.
- The sample-data HTML prototype is a design demonstration. It is **not** the authenticated app.
- `AccountReadAPI` derives tenant and role from a server session. Never trust browser-supplied tenant IDs or roles.
- `dashboard_view.py` returns only safe, authorized presentation data.
- `bam_read_wsgi.py` exposes GET-only dashboard, held drafts and posting preference routes.
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
11. Run the complete Python and Node CI suite and review GitHub Actions outcomes. Current CI outcomes have not been independently verified through available tooling.

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
```

Do not expose `bam_read_wsgi.py` directly to the public internet without a trusted HTTPS proxy, authentication and rate limits. Do not treat the demo's sample metrics as production data. Do not store BAM or social provider credentials in GitHub, client source, screenshots or logs.
