# Proposed BAM Business Knowledge & ChatGPT Export Import

**Approved product decision:** November 15, 2026  
**Status:** Future capability; design agreement, **not implemented** in BAM Personal Android and not permission to import user data now.  
**Priority:** Behind functioning owner-facing Android draft, approval, manual sharing and phone reliability verification. Keep $0 additional spending.

## Goal and business boundaries

One BAM user should manage **multiple distinct businesses under one account**. A single user-selected ChatGPT export may contain knowledge relevant to several businesses. The user wants to assign reviewed content into independent business profiles, not train one shared model that blends all information.

Each business profile has a stable internal `business_id`, an owner-set name, custom marketing guidance and discrete business knowledge. Switching the active business changes **every** source of brand/product facts, reusable snippets, generated content, schedules, approval queue, saved drafts, social connections, memory retrieval and any future AI quota. No business-scoped input may enter a different business's prompt, including from "recent captions" or imported conversations. The same person can own both Belenos Creations and Busy B Cleaning Service without their content or permissions being mixed. Do not assume the presence of one business authorizes another.

The current BAM Personal app remains intentionally **Belenos Creations only**. Its current hard-coded `Schedule.prompt` and local storage are **not** a multi-business implementation. Do not expose a business switch until these paths are genuinely scoped, migrated and tested.

## Why knowledge retrieval, not model training

For the first import, keep BAM's downloaded offline model unchanged. Store a reviewed, concise, retrievable knowledge base locally and pass only relevant business-approved facts into the selected business's generation prompt. This is retrieval/context injection, **not weight training or fine-tuning**. It avoids a separate model download per business and works with the existing $0 on-device architecture once built.

Do not put the raw ChatGPT export or extracted personal/private data into GitHub, GitHub Actions logs, previews, third-party analytics, paid AI APIs, or generated post text. A public repository may contain only synthetic fixtures. Never auto-connect or auto-read the owner's ChatGPT account to perform this import.

## User-visible import flow

1. **Create/select destination profiles.** The owner can manually create a business or select existing profiles. Do not infer a new business from an ambiguous chat without review.
2. **Choose a local export.** The owner explicitly selects a ChatGPT data-export ZIP (or supported conversation JSON) through Android's picker. Start with local files; source-format changes must have versioned parser tests. A compressed export may contain additional files, so only selected supported entries are parsed.
3. **Preview and classify.** Extract candidate business facts, product lines, selling channels, tone rules, pricing, hours, closures, event/deadline notes, and sources. Each candidate is **unassigned, proposed for business X, ambiguous, private/personal, or excluded**. No candidate becomes approved knowledge automatically, even if a classifier is confident. The owner can assign to another profile, edit, merge duplicates, reject, or mark outdated.
4. **Review before save.** The owner sees the excerpt's source conversation/title or local reference, category, possible business, and date. Mark uncertain/contradictory information for manual resolution; never treat the latest sentence as automatically correct. Time-sensitive prices, promotions, store hours, and holiday deadlines require current confirmation and optionally expiration.
5. **Commit per profile.** Only accepted candidates are saved to an isolated, on-device business knowledge store. Each accepted item records business ID, source provenance, verified/edited timestamp, category, status, optional expiration, and an owner-editable value. Unassigned/rejected/personal candidates are not added to AI context.
6. **Manage and erase.** The owner can edit facts without reimporting the file, disable/remove one item, export accepted knowledge per business, delete an entire business knowledge profile, or delete importer staging. Disabling/deleting must prevent future retrieval, not merely hide the UI.

Import only information relevant to business marketing. An entire export can include personal conversations, staff issues, protected/customer details, health, financial information, and credentials. **Default-exclude** private/personal chats and secrets, personal identifiers, customer data, and any uncertain cross-business material. Ask the user before retaining exceptional sensitive information. Avoid leaking private contact details into drafted posts.

## Security and isolation contract

- All extracted candidates carry explicit `destination_business_id` or remain unassigned; neither missing nor ambiguous IDs may default to whichever business is active.
- A retrieval query must include the active verified business ID, not just filter displayed UI afterward. Prompts for Business A must not include anything from Business B, including cited snippets, style guidance, recent drafts, local model cache, or imported files.
- Switching businesses during import or generation invalidates stale active-workspace actions. A business owner must explicitly approve and commit assignments. Later multi-user access is constrained by membership and per-business permission, not a shared owner export.
- Parse ZIP safely: bounded size, per-entry decompression limits, bounded counts, reject traversal paths, symlinks, unsupported formats, malformed JSON and zip bombs, and avoid logging private passages. Provide a dry-run preview and a clear cancel path. No training, publishing or account connection is triggered by choosing an export.
- Data retention: temporary staging has clear local cleanup after acceptance, rejection or cancel. Raw export stays in the original user-chosen location unless the user deliberately copies it; BAM does not silently upload or back it up to external hosting. Later local encryption, device loss/restore and export permissions require separate verification.
- Time-sensitive or contradicted facts should remain *owner-confirmed input required*. A model must not fabricate prices, discounts, store hours or events from an incomplete export.
- Allow empty profiles and manual knowledge entry so the feature does not require a ChatGPT export.

## Candidate storage/interface contract (future)

A candidate import row should contain at minimum:
`import_id`, `source_record_id`, `source_timestamp?`, `proposed_business_id?`, `category`, `candidate_text`, `status` (unassigned / proposed / approved / excluded / needs_review), `verification_reason?`, and provenance needed for review.

Approved knowledge rows should contain `business_id`, `knowledge_id`, `category`, `text`, `owner_confirmed_at`, `source_reference?`, `expires_at?`, `updated_at`, `disabled_at?`. Use a separate domain model from imported raw chat, with an explicit migration path from BAM Personal's current single-business drafts and campaign settings.

Knowledge retrieval should prefer a compact, relevant subset and enforce a strict prompt-size budget on-device. Order fact use by topical relevance, owner confirmation and freshness; preserve global brand safety rules and profile-level instructions. If retrieval finds no confirmed facts for a claim, omit it rather than guessing.

## Acceptance tests before enabling for customers

- A synthetic mixed export contains Belenos Creations facts, Busy B Cleaning Service facts, ambiguous statements, personal data, and a malicious path. Only owner-approved candidates enter their selected profile; forbidden/ambiguous entries never appear in either prompt.
- Import twice, cancel halfway, edit a fact, move a candidate to the other business, mark a price expired, then delete a profile. No duplicate, stale, or cross-business information persists in retrieval.
- Change the active business during a staged import or concurrent generation. Stale references cannot write or retrieve under the newly active business.
- A shared-owner setup with distinct per-business writing rules produces independent generation prompts and recent-caption histories. Team invitations and external publishing are not implicitly enabled.
- A compressed attack fixture (zip bomb, malformed JSON, traversal, excessive size, unexpected format) fails safely without exporting raw excerpts or creating business facts.
- Actual phone import and retrieval tests use an explicitly chosen sample export after the owner approves the feature. No personal export belongs in the public repository.

## Phasing

**Now:** Keep the user-approved design in product plan and continuity. Continue verifying 0.12.0 Android branding, manual lead-time drafting, regular approval, image sharing, and real unattended timing.

**Phase 1, after owner-visible app flows work:** Local, editable business profile and knowledge records; manual entry; explicit business switch with isolated recent captions and drafts. Only then enable business-aware prompt retrieval.

**Phase 2:** Offline export picker, safe parsing, classified candidate review/assignment, dedupe and expiration. Start with `conversations.json` where present, after inspecting real format and synthetic parser tests.

**Phase 3:** Multiple authenticated users, server-side tenant permissions, optional backup/restore and business sharing, only after explicitly approved hosting/security gates.

This is a roadmap, not a claim that BAM currently imports exports, has separate business profiles, or continually learns from ChatGPT.
