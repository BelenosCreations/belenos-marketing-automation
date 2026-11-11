# BAM AI architecture — approved product direction (2026-11-10)

BAM is **Belenos Automatic Marketing**, an industry-independent, multi-business marketing platform. This document distinguishes **approved product requirements** from **implemented offline foundations** and **undecided commercial configuration**.

## Three supported deployment scenarios

1. **Owner-only use:** The owner wants AI to create **two posts per day, every day**, without paying a separate AI fee. BAM centrally sponsors the OpenAI usage. A free end-user experience does **not** mean OpenAI API usage is free to the BAM operator.
2. **Private sharing:** Approximately **5–10 known users** may use BAM, with varied posting frequencies up to **two posts per day**. The preferred experience remains free to these users, without a profit objective. The operator pays sponsored OpenAI usage subject to safe limits.
3. **Public Google Play release:** BAM may become a publicly distributed paid app. Free AI is **not required** in this scenario; subscriptions/usage fees should cover provider costs and potentially produce profit. **No public prices, tiers, trial lengths, or exact allowances are approved yet.** Do not hardcode illustrative prices.

These are deployment scenarios, not identity roles. A user may own multiple businesses; identity, business authorization, subscription entitlement and AI quota are distinct concerns.

## OpenAI-only architecture

- **OpenAI is the only approved AI provider.** No alternative provider integrations are required.
- **Default mode:** BAM-sponsored OpenAI calls are made server-side using BAM-controlled credentials and bounded allowances. End users do not need an OpenAI account, separate signup, or API key.
- **Optional mode:** A user can switch to **their own paid OpenAI API key**, securely stored using an encrypted server-side secret vault, and later switch back to BAM-sponsored AI without losing the stored encrypted-vault reference. An explicit remove-key action must revoke the vault secret and clear its reference; merely changing modes must not reveal or destroy the user's secret. A personal key must not be exposed to the browser, GitHub, logs or another user.
- **Independent memories:** Each business and each user must have isolated AI preference/memory context even when sponsored calls use the same BAM-owned OpenAI credential. Current offline storage is keyed by both business and user; never reuse another user's or business's preferences as prompt context.
- **No fabricated business claims:** Generation should use owner-confirmed or independently verified business facts, supported media and explicit customer-supplied context. Owner confirmation is recorded as provenance, not represented as independent external verification. Missing facts should produce a held draft or content request, not a confident invented claim.
- **Human control:** AI generation creates drafts. Approval, scheduling and social publication remain separate operations with permission checks. Existing disabled-publishing safeguards remain in place.

## Approved content-generation efficiency plan

- **Combined request:** One OpenAI request should produce structured `post_text` and an **optional** `image_prompt`. BAM separates these into independently editable fields. An image prompt is not an image and does not imply one was generated.
- **Targeted revisions:** When the user revises only copy or only the image prompt, request regeneration of that component rather than paying to regenerate everything. Preserve the untouched component.
- **Advance batches:** Generate multiple drafts ahead of time when appropriate, within verified quota and scheduling constraints. Do not automatically publish the resulting drafts.
- **Local templates:** Use a safe local template instead of an OpenAI call when it sufficiently meets the user's request and verified business facts support it. Measure cost, reliability and quality rather than assuming one approach is always best.
- **ChatGPT-assisted free images:** Users may independently create/revise images using ChatGPT Free or paid, then upload/share the resulting images to BAM. This is **optional**, not a required signup or a claim that BAM can invoke ChatGPT Free programmatically. Uploaded media must pass the existing trusted attachment validation workflow.
- **TruthGuard:** The existing per-business verified fact registry, claim review and content approvals remain mandatory. AI drafts, revised drafts and image prompts do not bypass fact verification or approval.

`ai_content_plan.py` provides offline combined-output, targeted-revision and bounded-batch request planning, with tests. `ai_local_templates.py` provides a zero-API-cost, literal verified-fact product spotlight for simple cases. Neither executes OpenAI calls or creates images.

## Simple onboarding and direct social connections

- Sign up once for BAM using **email/password or Google sign-in**.
- Authorize an existing **Facebook business Page directly**; no mandatory Metricool account. Other supported platforms can be connected separately later.
- Facebook Page authorization is distinct from BAM login and from OpenAI API key management.
- The home dashboard uses large cards; detailed controls, appearance mode (Light / Dark / Auto), analytics and scheduling preferences belong in deeper Settings/views.

## Cost and security requirements

The server must enforce request quotas, token limits, concurrency limits, maximum spend/circuit breakers, rate limits, account and business isolation, abuse prevention, and auditable usage without logging private content or credentials. Usage and billing are never inferred from client-supplied claims. Public entitlement checks and payments must be verified server-side. A personal-key mode does not consume the sponsored BAM allowance; personal OpenAI charges belong to the key owner.

A **two-post-per-day** target does not automatically determine a monthly OpenAI request cap: retries, revisions and other generation requests also consume API resources. Exact sponsored quotas, model selection, public prices, and monthly budget remain configuration/decisions for later, not assumed defaults.

## Current implementation

- `ai_account_policy.py`: server-session-scoped AI mode and isolated user/business memory preferences; mode switching supports a **trusted vault reference only**, never raw API key handling.
- `ai_sponsorship.py`: explicit owner/invited/public plan descriptors and SQLite conditional sponsored-request quota reservation.
- `ai_draft_request.py` and `ai_content_plan.py`: verified-facts-only OpenAI request construction, combined post/optional image prompt output, independent component revisions and bounded batch planning.
- `ai_local_templates.py`: authenticated, literal-fact, zero-API-cost draft fallback.
- `ai_content_drafts.py`: versioned, tenant/user-scoped structured draft persistence, held-media status, targeted revisions and association with an existing scanner-verified image; no publishing.
- `ai_generation_workflow.py`: offline trusted-executor orchestration for owner-confirmed facts, sponsored quota, strict output validation and unpublished draft staging. The actual OpenAI executor is not implemented. **Not a payment gateway, complete cost ledger or distributed production rate limiter.**
- `test_ai_account_policy.py` and `test_ai_sponsorship.py`: offline regression coverage for separation, mode changes, invalid credentials and quotas.

**Not implemented:** actual OpenAI API calls, prompt orchestration, encryption vault, billing/Google Play subscriptions, real user onboarding, direct Facebook OAuth/Page publishing, live scheduling or production multi-worker enforcement. Existing BAM work is preserved and publishing remains disabled.

## Future implementation gates

1. Build trusted encrypted secret storage and secure personal-key verification/revocation; never persist plaintext API keys.
2. Implement production-atomic quota and spend ledger with verified plan entitlements, daily caps where appropriate, model/token budgets and rate limiting.
3. Build OpenAI request service that uses verified business facts and per-user memory, logs safe usage metadata, and creates drafts/held requests only.
4. Build simple BAM signup/login and direct Facebook Page authorization, with independent tokens and revocation.
5. Wire authenticated GUI to live data, Settings-based AI mode and quota visibility, Content Studio and manual/smart scheduling.
6. Add subscriptions and Google Play distribution only after pricing and billing policies are explicitly approved.
7. Complete security review, integration tests, real browser tests and staged deployment before enabling publishing.

### Structured Responses executor boundary

`openai_responses_executor.py` constructs a strict OpenAI Responses API envelope and parses only completed assistant text output. It requires a trusted injected transport and does not resolve keys or perform networking. Configure the production transport with OpenAI credentials stored server-side, TLS verification, timeouts, explicit retries, safe request IDs and actual usage/cost accounting before enabling it. The adapter is not a general-purpose agent and cannot invoke tools or publish.
