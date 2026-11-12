# BAM — public repository readiness

Status (2026-11-12): **PUBLIC**, changed by the repository owner after PR #35. PR #35 merged at `5c283175df06c77a529df2ed1ab62a1beb6e98ba`; post-merge Actions `43225430354` succeeded. Earlier steps below are retained as historical review expectations, not an instruction to change visibility back to private. The automated history scan is heuristic; continue manual credential review and rotate any exposed production credentials. BAM hosting and social publishing remain unprovisioned/disabled. BAM hosting and social publishing remain unprovisioned/disabled.

## Motivation
GitHub-hosted standard-runner Actions compute is free on public repositories. Private monthly minutes are currently scarce. Public status does not reduce Render, Neon, OpenAI, Meta, bandwidth, or storage expenses, and it does not authorize paid services.

## Mandatory checks before switching visibility
- [ ] Review the public-release-history-preflight check from a full-history checkout. A PASS is only a heuristic result, not proof that historical content is safe.
- [ ] Inspect all past commits/branches, removed files, old Actions logs, releases and artifacts for passwords, service keys, API tokens, URLs carrying credentials, private data and test credentials reused in production.
- [ ] Confirm no Google OAuth client secret, Meta account token, OpenAI API key, Render/Neon database URL or real user record appears in tracked files or historical commits. Rotate any leaked key before going public.
- [ ] Confirm the offline development server is NOT exposed as a public hosted service and publishing remains disabled.
- [ ] Keep minimal GitHub Actions permissions and first-time/fork contributor workflow approvals. Current CI uses standard Ubuntu runners.
- [ ] Monitor Actions artifact/package storage, cache use, LFS and other billable quotas; prevent overages in GitHub budgets. Public minutes are not unlimited free storage.
- [ ] Confirm desired license and public README wording. A public repository does not automatically license code reuse.
- [ ] Only after clearance, an authorized administrator changes repository visibility via GitHub Settings > General > Danger Zone.

## Going private later
A later private conversion is supported, but downloaded copies and public forks can remain; private Actions usage again counts toward plan limits.

## Development independence
No changes to BAM's approved separate Render Starter + Neon Free plan, and no creation of hosting, domains, paid providers, live analytics, OAuth connections, or social publishing. Active main/development branches remain untouched until reviewed.
