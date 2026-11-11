# BAM development continuity checkpoint

**Date:** 2026-11-11, America/New_York.
**Repository:** `BelenosCreations/belenos-marketing-automation` (private).
**Active branch:** `development/phase-3-5-account-directory`.
**Most recent verified code commit:** `91d0e0cbddf7907d456b6beff69f278b25f72436`.
**Verification:** [GitHub Actions run 43081725025](https://github.com/BelenosCreations/belenos-marketing-automation/actions/runs/43081725025): 867 Python tests, 62 JavaScript regression scripts and compilation **passed**.
**Document-only checkpoint:** This file and companion README/CHANGELOG/milestone updates are committed after the verified code commit; confirm their own CI result before treating the new documentation commit as a verified head.

## Safe resume procedure

1. Verify the branch head and most recent full green GitHub Actions run. If a chat froze mid-edit, discard unverified assumptions and compare the branch's actual commits, tests and files before making changes.
2. Continue on `development/phase-3-5-account-directory`. Keep `main` unchanged until a separate review/merge decision.
3. Work in larger useful batches; update README, CHANGELOG and DEVELOPMENT_MILESTONES at verified milestones rather than every small patch. Never commit credentials, customer media, secrets or private session tokens.
4. Preserve strict per-user/per-business access, session invalidation, version-checked draft and calendar changes, non-executable status flags, no spoofed live analytics and no unverified promotional claims.

## What is built and tested

- Email/password and Google sign-in backend scaffolding, verified current membership, multi-business switching, logout and least-privilege business roles (not publicly deployed).
- Mobile-first large-card signed-in HTML UI, Content Studio drafts and revision-safe edits, CSV import, private pending-image quarantine and status, owner-confirmed AI facts and manual image-prompt handoff.
- OpenAI structured/draft and targeted-revision architecture, local zero-API-cost product/service draft templates, AI quotas, privacy and token-cost ledger foundations. Paid external calls remain disabled.
- Owner-configured Manual/Smart posting preferences, DST-safe Manual preview, saved unpublished draft-calendar proposals, read-only suggested slots, and version tokens preventing stale editor date changes.
- Private, GET-only `/api/v1/review-readiness` with content/material verification flags, a deeper Approvals checklist and tests for isolation and fail-closed nonapproval.

## Non-negotiable active limits

No social publishing or true scheduled jobs, public hosting, production OAuth token exchange, external image generation, paid OpenAI traffic, automated approval, or actual verified media-scanning service is authorized or enabled. Existing SQLite composition and WSGI browser test adapter are for isolated local development only. Google sign-in needs real trusted provider verification/configuration before use.

## Candidate next work (no authorization required)

Deepen private review preparation with safe owner-led human review UX, manual draft filtering and claim-readiness cues, and security/compatibility tests; improve Android/backend architecture documents and migration tests; extend topic planning and cost-free local previews. Maintain complete zero-publishing and zero-paid-call safety.

## Major decisions requiring user input

Public backend hosting (provider, credentials, persistence, budget and security), Google sign-in provider verification, production media scanning/storage and consent workflow, AI spending limits and real OpenAI activation, social provider OAuth permissions, and any live scheduling/automatic publication all require separate user authorization. Never infer consent from an offline green test.
