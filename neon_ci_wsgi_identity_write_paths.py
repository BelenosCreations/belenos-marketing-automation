"""Manually reviewed source paths for the offline draft and identity adapters."""

SOURCE_HASHES = {
    "ai_account_policy.py": "f75044e06e7664608f3bc86503ffcca49910cc6ca3f1e2d857ebda6cf7141eee",
    "ai_business_facts.py": "2a83d06dee710e1dc810905023b61970f5c86c33061205ec30288d4bd961e63a",
    "ai_content_drafts.py": "02e965939a35b6a6335641382f517e2144bc7646625f42d8e3bd4f6720ab54cf",
    "ai_content_plan.py": "537861dacb313a0b4766b76ef1fbaf352ae536db31c8c289ae7d1e127b9d92b8",
    "ai_draft_request.py": "1b51248ae212902bd9abf43497ba655d7baf149a1a376718f5af306c243e8169",
    "ai_local_templates.py": "9c4b2b87fa3bbc81138c5927861045ba1395316de660f5e36b60da888b4bde49",
    "auth_login_api.py": "20e9368fc5867111511042dcda47dfcfdaae0fa39a94f324ff7cd5c2b2813c58",
    "bam_auth_wsgi.py": "9e7d4fc959d1fb9e790687debf7c301bc91a112db1041743223ba0a1eec5073d",
    "bam_business_switch_wsgi.py": "c2d01e6f34ae893ca958ba821a3d77be66bfa9cd67d5f1e1c4708c981f1fdb5c",
    "bam_invitation_accept_wsgi.py": "b02b64b0675dfb3ea41e6dcfcf6bc3050fced9fd455ae676e03ea2e68cf921c3",
    "bam_local_draft_wsgi.py": "b530d63cdc8cb95bce14141ff2adad22c502660fa25edb0cee8215feb21fa8d9",
    "bam_team_invitations_wsgi.py": "1465c0c6cd36cd5dd43048213f7e69764e4da729eb3cb386a02fe191af8463ff",
    "bam_team_membership_wsgi.py": "2ea067498caf5ac9573ff6e813841a194f405b379bc97ff09bde839d7c6d1d1e",
    "business_invitations.py": "038fa587e9652b3e5a2765c55c7e40051a490c5bebaca5659f80701dccc75b7b",
    "business_switcher.py": "406365f2b684a5ed864c712e59587b88177c7b229aaa2ca5815e74e2ffab7f1a",
    "google_login_challenges.py": "3291d438f297b9e6f4591ff62d6a6d15047e354416e76ef0231025ee1b31357e",
    "identity_auth.py": "009e18a70c7c616cd8d1e5b5bb62fbc4c81e08580ca7da82654df714f45ea954",
    "login_throttle.py": "10dc170c4b1ad372b5a726c2ef44c432122ac9603f58a541c35e3993a559611f",
    "team_membership_admin.py": "04eb8b56d4bae5b3eedce75a7e631c033da706f5e3132aa29f760e44854aa877",
}

HANDLERS = {
    "auth_wsgi": ("bam_auth_wsgi", "BAMAuthWSGI"),
    "switch_wsgi": ("bam_business_switch_wsgi", "BAMBusinessSwitchWSGI"),
    "team_wsgi": ("bam_team_membership_wsgi", "BAMTeamMembershipWSGI"),
    "invitation_wsgi": ("bam_team_invitations_wsgi", "BAMTeamInvitationsWSGI"),
    "invitation_accept_wsgi": ("bam_invitation_accept_wsgi", "BAMInvitationAcceptWSGI"),
    "local_draft_wsgi": ("bam_local_draft_wsgi", "BAMLocalProductDraftWSGI"),
    "local_service_wsgi": ("bam_local_draft_wsgi", "BAMLocalProductDraftWSGI"),
}

# These methods are selected by the two reviewed gateway constructor arguments
# and the handler's local callable at line 126. This is a manual mapping.
LOCAL_DRAFT_METHODS = {
    "local_draft_wsgi": "create_local_product_draft",
    "local_service_wsgi": "create_local_service_draft",
}

_ISSUE = ("sql_insert", "sessions.py", 50, None, 54)
_REVOKE = ("sql_update", "sessions.py", 79, None, 83)
_CONSUME_CHALLENGE = ("sql_update", "google_login_challenges.py", 46, 40)
_THROTTLE_FAILURE = ("sql_upsert_on_failure", "login_throttle.py", 52, 51)
_THROTTLE_SUCCESS = ("sql_delete_on_success", "login_throttle.py", 68, 67)
_ACCEPT_INVITATION = (
    ("sql_update", "business_invitations.py", 257, 256),
    ("sql_insert", "business_invitations.py", 281, 256),
    ("sql_insert", "business_invitations.py", 283, 256),
)

# Call chains list candidate methods across success and failure paths. Site
# order does not imply the branches all execute in the same request.
WRITE_PATHS = {
    ("auth_wsgi", "api", "password_login"): (
        ("auth_login_api.AuthLoginAPI.password_login",
         "identity_auth.IdentityAuth.login_password",
         "identity_auth.IdentityAuth._issue_for_member",
         "sessions.SessionStore.issue", "login_throttle.LoginThrottle.success",
         "login_throttle.LoginThrottle.failure"),
        (_ISSUE, _THROTTLE_SUCCESS, _THROTTLE_FAILURE),
    ),
    ("auth_wsgi", "api", "begin_google"): (
        ("auth_login_api.AuthLoginAPI.begin_google",
         "google_login_challenges.GoogleLoginChallenges.begin"),
        (("sql_insert", "google_login_challenges.py", 31, 30),),
    ),
    ("auth_wsgi", "api", "google_login"): (
        ("auth_login_api.AuthLoginAPI.google_login",
         "google_login_challenges.GoogleLoginChallenges.consume",
         "identity_auth.IdentityAuth.login_google_verified",
         "identity_auth.IdentityAuth._issue_for_member",
         "sessions.SessionStore.issue"),
        (_CONSUME_CHALLENGE, _ISSUE),
    ),
    ("auth_wsgi", "logout_api", "logout"): (
        ("account_read_api.AccountReadAPI.logout", "sessions.SessionStore.revoke"),
        (_REVOKE,),
    ),
    ("auth_wsgi", "logout_api", "logout_everywhere"): (
        ("account_read_api.AccountReadAPI.logout_everywhere",
         "sessions.SessionStore.revoke_identity"),
        (("sql_update", "sessions.py", 107, None, 112),),
    ),
    ("switch_wsgi", "api", "activate_business"): (
        ("account_read_api.AccountReadAPI.activate_business",
         "account_dashboard.AccountDashboard.switch_and_overview",
         "business_switcher.BusinessSwitcher.activate_business",
         "sessions.SessionStore.issue", "sessions.SessionStore.revoke"),
        (_ISSUE, ("sql_update_on_overview_failure", "sessions.py", 79, None, 83)),
    ),
    ("switch_wsgi", "api", "logout"): (
        ("account_read_api.AccountReadAPI.logout", "sessions.SessionStore.revoke"),
        (_REVOKE,),
    ),
    ("team_wsgi", "service", "change_current"): (
        ("team_membership_admin.TeamMembershipAdmin.change_current",),
        (("sql_update", "team_membership_admin.py", 131, 114),
         ("sql_update", "team_membership_admin.py", 139, 114),
         ("sql_insert", "team_membership_admin.py", 142, 114)),
    ),
    ("invitation_wsgi", "service", "invite_current"): (
        ("business_invitations.BusinessInvitations.invite_current",
         "business_invitations.BusinessInvitations.invite"),
        (("sql_insert", "business_invitations.py", 163, 162),
         ("sql_update_on_failure", "business_invitations.py", 187, 186),
         ("sql_insert_on_failure", "business_invitations.py", 192, 186),
         ("sql_update_on_success", "business_invitations.py", 198, 197),
         ("sql_insert_on_success", "business_invitations.py", 204, 197)),
    ),
    ("invitation_wsgi", "service", "cancel_current"): (
        ("business_invitations.BusinessInvitations.cancel_current",),
        (("sql_update", "business_invitations.py", 129, 128),
         ("sql_insert", "business_invitations.py", 136, 128)),
    ),
    ("invitation_accept_wsgi", "api", "redeem_invitation_password"): (
        ("auth_login_api.AuthLoginAPI.redeem_invitation_password",
         "business_invitations.BusinessInvitations.accept_password_trusted",
         "business_invitations.BusinessInvitations.accept_trusted",
         "login_throttle.LoginThrottle.success", "login_throttle.LoginThrottle.failure"),
        (*_ACCEPT_INVITATION, _THROTTLE_SUCCESS, _THROTTLE_FAILURE),
    ),
    ("invitation_accept_wsgi", "api", "redeem_invitation_google"): (
        ("auth_login_api.AuthLoginAPI.redeem_invitation_google",
         "google_login_challenges.GoogleLoginChallenges.consume",
         "business_invitations.BusinessInvitations.accept_trusted",
         "login_throttle.LoginThrottle.success", "login_throttle.LoginThrottle.failure"),
        (_CONSUME_CHALLENGE, *_ACCEPT_INVITATION, _THROTTLE_SUCCESS, _THROTTLE_FAILURE),
    ),
}

for handler, method in LOCAL_DRAFT_METHODS.items():
    WRITE_PATHS[handler, "api", method] = (
        ("account_read_api.AccountReadAPI." + method,
         "account_read_api.AccountReadAPI._create_local_spotlight",
         "ai_content_drafts.AIContentDraftStore.stage"),
        (("sql_insert", "ai_content_drafts.py", 50, 49),),
    )

UNRESOLVED_DEPENDENCIES = {
    ("auth_wsgi", "api", "google_login"): ("AuthLoginAPI.google_verifier.verify",),
    ("invitation_accept_wsgi", "api", "redeem_invitation_google"): (
        "AuthLoginAPI.google_verifier.verify",),
    ("invitation_wsgi", "service", "invite_current"): (
        "BusinessInvitations.deliver",),
}
