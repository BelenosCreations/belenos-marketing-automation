# Offline identity, membership and local draft writes

The CI source report extends the [held-draft and media boundary review](MIGRATION_WSGI_WRITE_BOUNDARY_REVIEW.md).
It records the SQLite context or explicit commit for each reviewed mutation.
Local product and service drafts use a manually reviewed alias mapping tied to
both the gateway and handler source. Drift withdraws reviewed mappings.
Unknown delegates and injected implementations stay visible.

| Offline entry point | Reviewed writes and commit order |
| --- | --- |
| `POST /api/v1/ai/local-product-draft` and `/api/v1/ai/local-service-draft` | The [gateway selects the template](bam_offline_gateway.py#L223-L226) and the [handler invokes the local callable](bam_local_draft_wsgi.py#L124-L126). Both branches call `AccountReadAPI._create_local_spotlight` and [insert a draft](ai_content_drafts.py#L49-L57) after reading confirmed facts. |
| `POST /api/v1/auth/password` | [Password sign-in](auth_login_api.py#L30-L43) commits [session issuance](sessions.py#L38-L55) before clearing the throttle. A denied credential attempt can [update the throttle](login_throttle.py#L44-L69) separately. |
| `POST /api/v1/auth/google-challenge` and `/api/v1/auth/google` | [Challenge creation and consumption](google_login_challenges.py#L24-L51) each use a SQLite context. [Sign-in](auth_login_api.py#L93-L103) consumes the challenge before the injected verifier runs. Session issuance follows successful verification and membership resolution in a separate commit. |
| `POST /api/v1/auth/logout` and `/api/v1/auth/logout-everywhere` | Separate session revocation paths use [explicit commits](sessions.py#L75-L113). The latter covers one identity across businesses. |
| `POST /api/v1/businesses/activate` | [Business activation](business_switcher.py#L40-L53) commits a destination session before the [WSGI handler revokes the source session](bam_business_switch_wsgi.py#L98-L140). Error paths can separately revoke the new session in the [dashboard](account_dashboard.py#L50-L59) or the handler. |
| `POST /api/v1/team/membership` | The [team service](team_membership_admin.py#L114-L147) changes membership, revokes the member's tenant sessions and records the audit event in the same SQLite context. Owner resolution occurs before that context. |
| `POST /api/v1/team/invitations/create` and `/api/v1/team/invitations/cancel` | [Creation](business_invitations.py#L162-L207) commits pending state, calls injected delivery and then records delivery outcome in a separate transaction. [Cancellation and its audit event](business_invitations.py#L128-L140) share one context. |
| `POST /api/v1/team/invitations/accept-password` and `/api/v1/team/invitations/accept-google` | [Redemption](business_invitations.py#L256-L286) claims the invitation, creates membership and writes the audit event together. The [login service](auth_login_api.py#L45-L91) writes throttle state separately and consumes a challenge before verification for Google redemption. Redemption creates no session. |

The checked-in gateway is local and disabled by default. Google verification
defaults to refusal. The verifier and invitation delivery are injected
dependencies. Their actual implementations, retries and side effects require
independent review. Read-only handler methods, other WSGI groups and generic
dynamic dispatch remain outside the mapped write paths.

## Alternative and startup writers

| Entry point | Source evidence |
| --- | --- |
| Legacy loopback HTTP | [Demo requests](dev_http_gateway.py#L81-L121) reach held-draft creation, hold, business activation and both logout methods. Activation there invokes `AccountReadAPI.activate_business` directly. Source-session revocation in the newer WSGI adapter is absent from this transport. |
| Demo startup | The [in-memory demo](dev_server.py#L22-L59) bootstraps owners, sets a membership, creates profiles and held drafts, and issues a session before serving. |
| HTTPS preview startup | The [preview listener](bam_local_preview.py#L166-L202) opens SQLite and constructs the gateway before serving. Constructors may [upgrade members](accounts.py#L10-L25), [backfill draft versions](content_requests.py#L30-L46), or [upgrade invitation records](business_invitations.py#L25-L66) when configured. |
| Preview owner provisioning | The [local provisioning command](bam_local_preview.py#L91-L127) exclusively creates a private file, then registers credentials, sets verification, bootstraps membership and creates a business profile across separate commits. |
| Preview add-business command | The [local setup command](bam_local_preview.py#L47-L87) issues a temporary session, creates owner membership and a profile in separate commits, and revokes the temporary session in cleanup. |
| Trusted Python identity methods | [Password change and identity disable](identity_auth.py#L197-L235) commit the identity change before revoking sessions. [Google registration and linking](identity_auth.py#L84-L104) and [provider-link writes](identity_auth.py#L153-L169) also need review wherever mounted. |

These startup and alternative paths are manually documented. The CI gateway
report does not enumerate the full set of constructor, CLI or deployed writes.

## Inactive migration design implications

- Route completion is an unreliable write boundary. Authenticate and check the
  original generation at every committing transaction. Review whether a
  transition needs one transaction or durable intermediate records for
  sign-in, switching and invitation delivery.
- Rehearse a freeze between challenge consumption and session issuance,
  membership authorization and session issuance, destination session issuance
  and old-session revocation, and external invitation delivery and outcome
  recording. A stale continuation must fail its write check. A retry needs
  the original operation identity and durable progress evidence.
- Verify that startup schema upgrades, local admin commands and callback
  processes are drained or transaction-fenced before taking a snapshot.
  An epoch check on WSGI requests alone leaves those writers outside the fence.

Deployed inventory, shared generation enforcement, authenticated operator
transitions and independent recovery evidence remain required for cutover.
