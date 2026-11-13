"""CI-only signed-manifest disaster scenario planner; NEVER a restore verifier.

No filesystem, network, database, key escrow, offsite storage or deletion.
A signed recovery *manifest* can suggest candidates; it cannot prove the
ciphertext survives host loss or that any encryption key is independently held.
"""
import os
import re

from bam_offline_recovery_manifest import verify_disposable_recovery_chain

_ALLOWED_SCENARIOS = frozenset((
    "archive_corruption", "source_directory_loss", "whole_host_loss",
    "encryption_key_unavailable",
))
_KEY_ID = re.compile(r"[a-z][a-z0-9_-]{0,31}\Z")
_MAX_AGE = 366 * 86400


def plan_disposable_recovery_incident(
        *, chain, expected_head, signer_keys, schema_fingerprint,
        now, incident_at, max_manifest_age_seconds,
        claimed_available_encryption_key_ids, scenario):
    """Recommend only *unverified* metadata candidates under strict bounds.

    Manifest timestamps are not proven recovery point timestamps. The
    difference called manifest age is NOT a measured RPO. Available key IDs
    are unverified caller claims, not key custody or actual decryption.
    """
    if os.environ.get("BAM_EPHEMERAL_PG_TEST") != "1":
        raise PermissionError("Synthetic recovery scenario planning disabled")
    if type(scenario) is not str or scenario not in _ALLOWED_SCENARIOS:
        raise ValueError("Explicit supported synthetic incident type required")
    if (type(now) is not int or now < 0
            or type(incident_at) is not int
            or not 0 <= incident_at <= now
            or type(max_manifest_age_seconds) is not int
            or not 0 <= max_manifest_age_seconds <= _MAX_AGE):
        raise ValueError("Bounded incident clock and manifest age policy required")
    ids = claimed_available_encryption_key_ids
    if (type(ids) not in (tuple, list)
            or len(ids) > 8
            or any(type(k) is not str or _KEY_ID.fullmatch(k) is None
                   for k in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("Unique, bounded, syntactically valid key ID claims required")
    # Authenticated HMAC chain validation happens before considering ANY point.
    verification = verify_disposable_recovery_chain(
        chain=chain, expected_head=expected_head, signer_keys=signer_keys,
        schema_fingerprint=schema_fingerprint, now=now)
    claimed = set(ids)
    eligible = [
        item for item in chain
        if item["issued_at"] <= incident_at
        and item["retain_until"] > now
        and item["encryption_key_id"] in claimed
        and incident_at - item["issued_at"] <= max_manifest_age_seconds
    ]
    # Sequence tie breaker is deterministic; NOT a verification of snapshot age.
    latest = max(eligible, key=lambda x: (x["issued_at"], x["sequence"])) \
        if eligible else None
    blockers = [
        "operator_authentication_and_external_latest_head_custody_not_proven",
        "independent_encryption_key_retrievability_not_proven",
        "physical_ciphertext_survival_and_restore_not_checked",
        "retention_authority_and_disaster_recovery_rto_not_measured",
        "customer_data_and_production_recovery_disabled",
    ]
    if latest is None:
        blockers.append("no_unexpired_signed_point_with_claimed_key_in_age_window")
    if scenario == "whole_host_loss":
        blockers.append("offsite_replica_and_independent_failure_domain_not_proven")
    if scenario == "encryption_key_unavailable":
        blockers.append("key_loss_requires_independent_recovery_review")
    return {
        "status": "disposable_incident_candidate_planning_blocked",
        "scenario": scenario,
        "signed_manifest_head_matches_external_pin": True,
        "signed_manifest_count": verification["manifest_count"],
        "candidate_count_based_on_unverified_key_claims": len(eligible),
        "potential_manifest_archive_name_unverified":
            latest["archive_name"] if latest else None,
        "potential_manifest_age_at_incident_seconds":
            incident_at - latest["issued_at"] if latest else None,
        "candidate_manifest_not_expired_at_review": bool(latest),
        "blockers": blockers,
        "manifest_time_is_not_verified_snapshot_time": True,
        "manifest_age_is_not_measured_rpo": True,
        "encryption_key_ids_are_not_key_custody_proof": True,
        "archive_existence_checked": False,
        "ciphertext_integrity_checked": False,
        "offsite_replica_verified": False,
        "independent_failure_domain_verified": False,
        "decrypt_attempted": False, "restore_executed": False,
        "restoration_time_measured": False,
        "plaintext_read": False, "local_files_modified": False,
        "files_deleted": False, "production_backup_ready": False,
        "customer_backup_proven": False, "publishing_enabled": False,
    }
