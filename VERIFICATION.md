# BAM verification checkpoint — 2026-11-11

## Current GitHub development branch verification

**Repository:** `BelenosCreations/belenos-marketing-automation`  
**Branch:** `development/phase-3-5-account-directory`  
**Verified commit:** `88a9cca1f00f30ac9c38e745befa386f471f20da`  
**CI:** ${link}

**Result:** 877 Python tests, 68 JavaScript test scripts in `ui/*_test.js`, and Python compilation passed. The suite now covers explicit two-step, non-executable draft-calendar suggestion saving with confirmation, current-draft/slot conflict checks, role and session safety, private editorial note collaboration, business-local Content Studio filtering, and prior tenant-isolated workflows. Offline verification is not permission to deploy, schedule or publish.

## Archived original Phase 3.2 package

The earlier supplied `belenos_automation_phase3_2_offline.zip` was extracted into an isolated local working directory. The original 26 Phase 3.2 tests passed. That historical result applies only to the original package and should not be confused with the current development branch.

## Release gate

A fully deployed multiuser BAM service is **not** available. The loopback-only TLS test preview is not safe to expose publicly. Real email verification/enrollment, Google OAuth, encrypted and concurrent production storage, media scanning and rights review, social-provider connections, operational monitoring, scheduling and explicit live-publishing approval remain outstanding.

Run the entire current-branch CI after future changes. Do not claim green verification from tests attached to an older commit. Never commit real passwords, provider tokens, TLS keys or personal customer data.
