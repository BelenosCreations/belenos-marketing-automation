# BAM private beta infrastructure — proposed, not authorized

**November 12, 2026 | Planning only.** This document does not create hosting, authorize charges, enable publishing or mark BAM Beta-ready.

## Architecture target

One trusted HTTPS API/backend serves multiple BAM users, businesses and team members. Isolate all records and permissions by **verified identity and server-selected business**. Use a durable transactional relational database for membership, sessions, drafts, reviews, audit and calendar; private object storage with scanning/quarantine for user media; a separately controlled durable work queue and worker; and a server-side encrypted credential vault, monitoring and encrypted backups. Shared resources avoid one paid server per employee, but do not grant cross-business access.

BAM should publish directly via supported official Meta/Facebook Page APIs once provider review and **separate owner activation** are complete. Metricool is not a required scheduling dependency. OpenAI API spending also needs a separately approved model, budget and key-management policy.

## Explicit trust separation

The current `BAMOfflineGateway` and `dev_http_gateway.py` are local development fixtures. BAMOfflineGateway now rejects detectable remote addresses, public Host and reverse-proxy headers before any route. **This is defense in depth, not a security guarantee**: a proxy can strip metadata, and a direct WSGI server could be misconfigured. Never deploy the offline app publicly. Create a distinct, reviewed production application factory after hosting decisions; enforce real TLS/origin/CSRF, provider verification, durable IP/global throttles, credential secrecy, restart safety and tenant isolation.

## Required owner choices before deployment

Approve provider/account, maximum additional recurring monthly spend, private beta user estimate, domain/subdomain, data-storage/backup and email-delivery options, and whether any existing infrastructure may be shared. In particular, do not reuse the existing EdgePilot deployment or its database, tokens or secrets without a separate, informed approval.

## Beta verification gates

- Two separately authenticated people and at least two businesses work on separate real devices; cross-business reads/writes and stale sessions are denied.
- Verified Google and email enrollment, recovery, invites, anti-abuse and revocation all work with real provider configuration.
- Durable migrations, encrypted backup/off-site retention, restore and rollback are demonstrated.
- Media is private, scanned and explicitly approved; posting remains off regardless of a stored draft or calendar proposal.
- Read-only official provider connection and analytics permission checks precede a later **separately authorized** publishing launch.
- Actual resource use, costs and data protection are measured rather than inferred from offline green CI.

**Next work before authorization:** independent production-runtime design and offline threat/regression tests. **No new paid service is added by this milestone.**
