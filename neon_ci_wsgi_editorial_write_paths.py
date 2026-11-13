"""Manually reviewed source paths for offline editorial and AI state."""

SOURCE_HASHES = {
    "ai_batch_preview.py": "66736683d24f478dc60b5bd234e5a3afe846e89ae964513ed215ba3c4bae41ab",
    "bam_ai_batch_preview_wsgi.py": "cd3491d394050cb58dcf01fc45d6101a98edc7cd7bec88191da4ffeb34b44136",
    "bam_ai_draft_edit_wsgi.py": "0760510e40799690a0527cd6c6fa2f407e8c6123c59ff168effa7ce8f74334b9",
    "bam_ai_facts_write_wsgi.py": "01670d5269269c66cb0ecb4f123714117feb6a65c1b2e33fda39644e4500f7a6",
    "bam_ai_memory_wsgi.py": "c62b0876b4498fb97ee007c4b6775e8105c545da058244c2a561d31770364aad",
    "bam_calendar_proposals_wsgi.py": "7e2ca1baca89df6f33c046eec050b6d4fea4999a63cedcd70d22d2586cac2f7d",
    "bam_posting_preferences_wsgi.py": "a4c548e207c0f9e155faed8859dc781c07262f918606c43eba3afc7f26ed124d",
    "bam_review_feedback_wsgi.py": "ce6f44a6da29b59194d16fb07d5a2d635af9631cdec46f6592ff137eae6ccd89",
    "bam_review_readiness_wsgi.py": "1a885cdc916f1eafba95f6dce5c876f11f5af71d2e6d97b89216aecb0baf8280",
    "calendar_proposals.py": "4a6b4442958d0f5ff5e9735c626d142e4d642c26e6a05b7516f557ad70b6caf0",
    "posting_preferences.py": "718a9e79ec12e81243968b974b499c79c98552446068daf615039b7f1a2a67d8",
    "posting_time_preview.py": "66536e9a54ae12fdae1f68e4bf000f21ba3df742baaca6ca64bac344127117dd",
    "review_feedback.py": "66aa124e0e973f8fcd1a533e8f6d19c7b5f74ad3fe0e0621e0f96a742c54cb53",
    "review_readiness.py": "b39a229b21bc848cf7f9a608af6427a22e9514d0d9835aac5945e346ab2996b3",
}

HANDLERS = {
    "ai_batch_preview_wsgi": ("bam_ai_batch_preview_wsgi", "BAMAIBatchPreviewWSGI"),
    "ai_draft_edit_wsgi": ("bam_ai_draft_edit_wsgi", "BAMAIDraftEditWSGI"),
    "ai_memory_wsgi": ("bam_ai_memory_wsgi", "BAMAIMemoryWSGI"),
    "calendar_wsgi": ("bam_calendar_proposals_wsgi", "BAMCalendarProposalsWSGI"),
    "facts_write_wsgi": ("bam_ai_facts_write_wsgi", "BAMAIFactsWriteWSGI"),
    "preference_write_wsgi": ("bam_posting_preferences_wsgi", "BAMPostingPreferencesWSGI"),
    "review_feedback_wsgi": ("bam_review_feedback_wsgi", "BAMReviewFeedbackWSGI"),
    "review_readiness_wsgi": ("bam_review_readiness_wsgi", "BAMReviewReadinessWSGI"),
}

WRITE_PATHS = {
    ("preference_write_wsgi", "api", "set_posting_preferences"): (
        ("account_read_api.AccountReadAPI.set_posting_preferences",
         "posting_preferences.PostingPreferences.set"),
        (("sql_upsert", "posting_preferences.py", 66, 65),),
    ),
    ("calendar_wsgi", "service", "propose"): (
        ("calendar_proposals.CalendarProposals.propose",),
        (("sql_insert", "calendar_proposals.py", 144, 142),
         ("sql_update", "calendar_proposals.py", 156, 142)),
    ),
    ("calendar_wsgi", "service", "discard"): (
        ("calendar_proposals.CalendarProposals.discard",),
        (("sql_delete", "calendar_proposals.py", 267, 266),),
    ),
    ("review_feedback_wsgi", "service", "save"): (
        ("review_feedback.ReviewFeedback.save",),
        (("sql_insert", "review_feedback.py", 131, 125),
         ("sql_update", "review_feedback.py", 138, 125),
         ("sql_insert", "review_feedback.py", 148, 125)),
    ),
    ("review_feedback_wsgi", "service", "discard"): (
        ("review_feedback.ReviewFeedback.discard",),
        (("sql_delete", "review_feedback.py", 174, 166),
         ("sql_insert", "review_feedback.py", 179, 166)),
    ),
    ("facts_write_wsgi", "registry", "confirm"): (
        ("ai_business_facts.AIBusinessFacts.confirm",),
        (("sql_upsert", "ai_business_facts.py", 44, 38),),
    ),
    ("ai_memory_wsgi", "api", "edit_ai_memory"): (
        ("account_read_api.AccountReadAPI.edit_ai_memory",
         "ai_account_policy.AIPolicyStore.replace_memory_checked"),
        (("sql_insert_if_missing", "ai_account_policy.py", 135, 134),
         ("sql_update", "ai_account_policy.py", 139, 134)),
    ),
    ("ai_draft_edit_wsgi", "api", "edit_ai_draft_component"): (
        ("account_read_api.AccountReadAPI.edit_ai_draft_component",
         "ai_content_drafts.AIContentDraftStore.revise"),
        (("sql_update", "ai_content_drafts.py", 103, 102),
         ("sql_delete_on_image_prompt_edit", "ai_content_drafts.py", 114, 102)),
    ),
}

READ_PATHS = {
    ("ai_batch_preview_wsgi", "api", "preview_ai_batch"): (
        "account_read_api.AccountReadAPI.preview_ai_batch",
        "ai_batch_preview.AIBatchPreview.preview",
    ),
    ("calendar_wsgi", "service", "list_mine_business"): (
        "calendar_proposals.CalendarProposals.list_mine_business",
    ),
    ("calendar_wsgi", "service", "readiness_digest"): (
        "calendar_proposals.CalendarProposals.readiness_digest",
    ),
    ("calendar_wsgi", "service", "suggest_unassigned"): (
        "calendar_proposals.CalendarProposals.suggest_unassigned",
    ),
    ("review_feedback_wsgi", "service", "list_current_business"): (
        "review_feedback.ReviewFeedback.list_current_business",
    ),
    ("review_feedback_wsgi", "service", "history_current_business"): (
        "review_feedback.ReviewFeedback.history_current_business",
    ),
    ("review_readiness_wsgi", "service", "list_current_business"): (
        "review_readiness.ReviewReadiness.list_current_business",
    ),
}
