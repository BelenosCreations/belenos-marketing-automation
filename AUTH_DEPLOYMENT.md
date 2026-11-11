# BAM authentication integration and release gates

Status: **backend foundations only**, 2026-11-10. Nothing in this document
authorizes deployment, Google account access, or social publishing.

## Supported identity methods

1. **Email/password:** create a BAM identity with a unique email, salted
   PBKDF2-HMAC-SHA256 hash, then prove email ownership with an expiring,
   single-use verification link delivered by a trusted provider. Login requires
   a verified email and active membership in the selected business.
2. **Google sign-in:** a trusted backend verifies Google's ID-token signature,
   configured audience, issuer, expiry, issued-at time, verified email, and
   a server-issued single-use nonce. Existing BAM users must explicitly link
   their Google identity with password reauthentication. Google-only signup
   creates a BAM identity but grants **no business access** automatically.
3. **Business access:** a verified BAM identity receives tenant membership only
   through an authorized owner or trusted enrollment/invitation. A member's
   session role is rechecked on every privileged operation.

Social account OAuth is a **separate** connection process and never substitutes
for BAM authentication.

## Production dependencies requiring configuration

- Google Cloud OAuth consent and platform-specific client IDs, correctly
  configured for the hosted backend and future Android application.
- `google-auth` in the backend environment for Google ID-token verification;
  a test-injected verifier is not acceptable in production.
- HTTPS-only API and secure session transport; never publish `dev_server.py`
  or `dev_http_gateway.py` to a public network.
- A transactional database with concurrency-safe nonce, reset-token,
  invitation and session operations.
- An authenticated, abuse-protected email provider for verification, invitations,
  security notices and password recovery. Do not log tokenized links.
- Mandatory per-IP, per-device, per-account and global rate limits; account
  enumeration and automated credential attacks must be tested.
- Secure client token storage, device sign-out, session expiration, recovery,
  CSRF and replay protections appropriate to the chosen login flow.
- Clear Google linking and unlinking UX, account recovery and access revocation.
- Database migrations, encrypted backups, secret rotation, monitoring, and
  security incident response procedures.

## API trust boundaries

`IdentityAuth.register_password`, `IdentityAuth.register_google_verified`,
`IdentityAuth.link_google_verified`, `BusinessInvitations.accept_trusted`,
and `EmailCredentialRecovery` delivery callbacks are **server-only** methods.
They must never accept unverified subject IDs, claims or email-verified flags
directly from mobile or browser clients.

`AuthLoginAPI` is an application service, **not** an HTTP server. A future
production transport must validate and normalize requests, configure a
mandatory throttle, check credentials or verified Google tokens, and return
generic authentication failures without disclosing account existence.

No Google token, password, verification token, session token or OAuth client
secret should be committed to GitHub or included in README examples.

## Release checklist

- [ ] Create and review real Google OAuth client configuration
- [ ] Verify Google tokens with real provider-issued credentials in staging
- [ ] Configure email provider and verify end-to-end ownership and recovery
- [ ] Add trusted new-business enrollment and invitation acceptance UX
- [ ] Implement mandatory concurrency-safe throttling and audit logging
- [ ] Implement secure Android login UI and encrypted credential storage
- [ ] Connect the dashboard frontend to authenticated business-scoped HTTPS APIs
- [ ] Implement media upload, trusted verification worker and held-draft approval UX
- [ ] Confirm IANA timezone, DST handling, smart-time evidence and manual-time precedence before scheduling
- [ ] Execute full current-branch tests with confirmed CI results
- [ ] Security-test replay, CSRF, nonce, expiry, account linking, role changes,
      tenant isolation, and recovery
- [ ] Deploy a separate HTTPS staging backend and conduct an end-to-end review
- [ ] Obtain explicit approval before enabling any live social publishing

This checklist is deliberately fail-closed: the presence of authentication
modules alone does not establish production readiness.
