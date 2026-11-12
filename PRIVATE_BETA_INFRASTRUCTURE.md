# BAM private beta infrastructure — proposed, not authorized

**November 12, 2026 | Planning only.** This document does not create hosting, authorize charges, enable publishing or mark BAM Beta-ready.


## Selected initial hosting design — November 12, 2026

The owner selected **one new, separate Render Starter web service ($7/month base compute)** paired with **one new Neon Free PostgreSQL project ($0/month under its usage limits)**. This is the engineering target for BAM's eventual private beta, **not authorization to create either service, incur a charge, expose BAM publicly, or deploy code**. The existing EdgePilot web service, database, tokens and credentials must remain segregated and unchanged. Use Render's Hobby workspace pricing assumption where eligible; independently confirm the actual billing workspace before provisioning.

**Planning estimate:** $7/month in base web+database compute only. The Render Starter instance has **512 MB RAM** and a small CPU allocation. Neon Free currently provides **1 GB storage and 100 compute-unit hours per project per month**; usage and plan limits can change. Render's Hobby workspace includes finite bandwidth/build allowances and charges can arise from overages; Neon Free is quota constrained. The $7 figure is **not a provider-enforced hard spending cap**.

**Unapproved, excluded extras ($0 authorized):** additional servers/background workers, scheduled/cron execution, extra databases or instance upgrades, disk/object storage, paid backups, email/OTP delivery, paid Google/Meta integrations, OpenAI API traffic, paid monitoring, bandwidth/build overages, custom domains and any other non-base charge. Each needs explicit approval or a tested free-tier alternative. Provider OAuth may not itself be billable, but connecting real accounts is still gated.

**Database strategy:** current BAM source is SQLite-oriented and cannot just be pointed at Neon's PostgreSQL URL. Create a separate, reviewed PostgreSQL persistence adapter/migration workstream; migrate identity, tenant memberships, sessions, content, invites, audits and calendar without losing atomic isolation. No real connection string is stored in GitHub. Future TLS/verified server-only credentials must use Render secrets; Neon and Render are separate projects/services.

**Reliability tradeoffs:** Render service filesystem is ephemeral; never persist production uploads, credentials or SQLite files there. Neon Free sleeps compute when idle, has quota/restore constraints and cannot replace a verified encrypted off-site backup/restore design. A single Starter web service is for a small supervised beta, not a demonstrated scalable publisher or guaranteed uninterrupted scheduler; final job execution needs a separate reliability and cost decision.

**Deployment safety:** no `render.yaml` blueprint, deployment trigger, configured service ID, Neon project ID, hosted API entrypoint or automatic deploy was introduced. `BAM_HOSTING_PLAN.json` is a read-only planning record with all activation flags disabled; `hosting_plan_contract.py` and its tests flag unauthorized drift in CI, but **do not** control Render billing or deployment actions. Explicit owner approval plus a reviewed staging rollout is still required.

**Official planning sources (checked November 12, 2026):**
- Render pricing: https://render.com/pricing
- Render ephemeral filesystem: https://render.com/docs/deploys
- Render environment variables: https://render.com/docs/configure-environment-variables
- Neon free plan limits: https://neon.com/docs/introduction/plans
- Neon Oct 2026 free-plan update: https://neon.com/blog/neon-free-plan-1-gb-per-project

## Architecture target

One trusted HTTPS API/backend serves multiple BAM users, businesses and team members. Isolate all records and permissions by **verified identity and server-selected business**. Use a durable transactional relational database for membership, sessions, drafts, reviews, audit and calendar; private object storage with scanning/quarantine for user media; a separately controlled durable work queue and worker; and a server-side encrypted credential vault, monitoring and encrypted backups. Shared resources avoid one paid server per employee, but do not grant cross-business access.

BAM should publish directly via supported official Meta/Facebook Page APIs once provider review and **separate owner activation** are complete. Metricool is not a required scheduling dependency. OpenAI API spending also needs a separately approved model, budget and key-management policy.

## Explicit trust separation

The current `BAMOfflineGateway` and `dev_http_gateway.py` are local development fixtures. BAMOfflineGateway now rejects detectable remote addresses, public Host and reverse-proxy headers before any route. **This is defense in depth, not a security guarantee**: a proxy can strip metadata, and a direct WSGI server could be misconfigured. Never deploy the offline app publicly. Create a distinct, reviewed production application factory after hosting decisions; enforce real TLS/origin/CSRF, provider verification, durable IP/global throttles, credential secrecy, restart safety and tenant isolation.

## Still-unapproved decisions before deployment

Render Starter and Neon Free are selected for *design only*. Before actual service creation, obtain an explicit authorization for the $7 recurring Render charge, confirm eligible billing workspace, identify region and domain/subdomain, decide private-beta user count, and obtain a safe plan for any necessary media storage, email delivery, encrypted backups, monitoring, scheduler and overages. None of those other services has an approved cost or activation. EdgePilot's live deployment, database, tokens and secrets are out of scope.

## Beta verification gates

- Two separately authenticated people and at least two businesses work on separate real devices; cross-business reads/writes and stale sessions are denied.
- Verified Google and email enrollment, recovery, invites, anti-abuse and revocation all work with real provider configuration.
- Durable migrations, encrypted backup/off-site retention, restore and rollback are demonstrated.
- Media is private, scanned and explicitly approved; posting remains off regardless of a stored draft or calendar proposal.
- Read-only official provider connection and analytics permission checks precede a later **separately authorized** publishing launch.
- Actual resource use, costs and data protection are measured rather than inferred from offline green CI.

**Next work before authorization:** independent production-runtime design and offline threat/regression tests. **No new paid service is added by this milestone.**

## Account-throttle shared-state hardening (offline)

The alpha login-failure counter uses one SQLite write per failed attempt and tests independent concurrent clients; this prevents an avoidable lost-update issue. The next hosted admission layer must still enforce atomic request attempt reservation, trusted client IP/device and global quotas, distributed or database-backed consistent enforcement, safe account enumeration responses and rollback/monitoring. Neither these offline tests nor a passing CI run constitute production identity security or owner authorization to deploy.
