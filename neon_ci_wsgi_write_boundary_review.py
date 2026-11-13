"""CI-only source evidence for selected offline WSGI write paths."""

from pathlib import Path

from neon_ci_wsgi_binding_review import _read
from neon_ci_wsgi_delegate_review import _fingerprint, inspect_ci_wsgi_delegated_calls
from neon_ci_wsgi_identity_write_paths import (
    HANDLERS, LOCAL_DRAFT_METHODS, SOURCE_HASHES, UNRESOLVED_DEPENDENCIES, WRITE_PATHS,
)


# Pin the inspected source, including authorization and data-store dependencies.
# Review changes to the source paths before replacing these pins.
_REVIEWED_SOURCE = {
    **SOURCE_HASHES,
    "access_policy.py": "1a0e6d513a5921a037a2d059f7aef360206340be83f4605af0ba982affa6a257",
    "account_dashboard.py": "4dca5cc7366e66b0c6eb65ea4c34f3ef493fac00ce090b00493c251234385539",
    "account_read_api.py": "bf7c56fff210d7a05d4d64cade17ae8b91efe42d727e0eb75aab9a602913a516",
    "accounts.py": "c88fff2f854311440a1adb509c7c4ac0c3455076a9aa2a1fed4f2b73f15f4929",
    "bam_content_priority_wsgi.py": "9511bfa0d9a685836c118312977c7f0b62b51382a16cb66327409f08a817ea53",
    "bam_content_revise_wsgi.py": "11a489810e067745a2c1e5a855858afab2d19f62fa1b09de7bba772e72997eec",
    "bam_content_write_wsgi.py": "d6912704b0f0bd28139da4b02f83631f76c86223b0a7180402a3358e270a0b84",
    "bam_offline_gateway.py": "2468897be42cf2b9357a9ccf6b92c08831fb4d40e28e2362515e9b0f2314d7c0",
    "bam_pending_media_discard_wsgi.py": "d3a4223c1474abaf2ec22cefa74edadf16352b21a29caa3dd0c9e9c870f355cf",
    "bam_pending_media_status_wsgi.py": "95442bc8da6075b024aa4daf36b8c4cc71788626f23f734a28d44cf9d2b990e9",
    "bam_pending_media_store.py": "4e5ef2759dfc96069e180e2e976cdfbb6d8516fdfe3ff8b379567a8e6ba57f42",
    "bam_pending_media_wsgi.py": "3777552d0bd482c4fc527060c7afd6b8bd317d3fc8e161dab3943faca7d4a4e7",
    "bam_upload_preflight_wsgi.py": "2a27dc84728a825b719e49caf6a2971f1ebb6f0661f85ef26fed5f62b56fd6dd",
    "content_attachments.py": "6356809a7426483a8552c28a392ea317bc586a16182015d2c652ba035401c90c",
    "content_byte_inspector.py": "4dd4e5543e102f6917ab29ab1acfa54d0d4e685a91b54402d8e0fb09847dec8c",
    "content_request_service.py": "6deff32463fae9d74b1a933912f0dcf3dd40479747d189ac5206e32c62373b92",
    "content_requests.py": "0ef771da9d8500cc65db32f81bc454172c20834b80885b96acf9098c8d0b23b9",
    "content_upload_preflight.py": "230a540fbbd137f22844199b8efe5d89ee91e09768773cc328b04ab0cd33cca7",
    "sessions.py": "23034d3abfbee8f2a1c7ada1e23a73df0ccf101e1665ee0ca9b6960d8971fa2f",
}


# These links are from a manual source walk. Identical method names in other
# classes, constructors or handlers confer no mapping.
_DRAFT_WRITES = (
    ("content_write_wsgi", "create_held_draft", "create", "insert", 64, 65),
    ("content_write_wsgi", "update_draft_hold", "set_hold", "update", 177, 178),
    ("content_revise_wsgi", "revise_held_draft", "revise", "update", 199, 200),
    ("content_priority_wsgi", "update_held_priority", "set_priority", "update", 115, 116),
)

_MEDIA_WRITES = {
    ("upload_preflight_wsgi", "api", "begin_content_upload_preflight"): (
        ("account_read_api.AccountReadAPI.begin_content_upload_preflight",
         "content_upload_preflight.ContentUploadPreflight.begin",
         "content_attachments.AttachmentRegistry.register_pending"),
        (("sql_insert", "content_attachments.py", 40, 39),),
    ),
    ("pending_media_wsgi", "store", "receive"): (
        ("bam_pending_media_store.BAMPendingMediaStore.receive",),
        (("file_create", "bam_pending_media_store.py", 198, None),
         ("file_write", "bam_pending_media_store.py", 201, None),
         ("file_fsync", "bam_pending_media_store.py", 203, None),
         ("file_unlink_on_error", "bam_pending_media_store.py", 205, None)),
    ),
    ("pending_discard_wsgi", "store", "discard"): (
        ("bam_pending_media_store.BAMPendingMediaStore.discard",),
        (("file_unlink", "bam_pending_media_store.py", 162, None),
         ("sql_delete", "bam_pending_media_store.py", 166, 165)),
    ),
}

_MEDIA_READS = {
    ("pending_media_wsgi", "store", "authorize_slot"),
    ("pending_status_wsgi", "store", "statuses"),
}

_HANDLER_BINDINGS = {
    **HANDLERS,
    "content_write_wsgi": ("bam_content_write_wsgi", "BAMContentWriteWSGI"),
    "content_priority_wsgi": ("bam_content_priority_wsgi", "BAMContentPriorityWSGI"),
    "content_revise_wsgi": ("bam_content_revise_wsgi", "BAMContentReviseWSGI"),
    "upload_preflight_wsgi": ("bam_upload_preflight_wsgi", "BAMUploadPreflightWSGI"),
    "pending_media_wsgi": ("bam_pending_media_wsgi", "BAMPendingMediaWSGI"),
    "pending_status_wsgi": ("bam_pending_media_status_wsgi", "BAMPendingMediaStatusWSGI"),
    "pending_discard_wsgi": ("bam_pending_media_discard_wsgi", "BAMPendingMediaDiscardWSGI"),
}


def _mutation_site(kind, module, line, context, commit=None):
    return {"kind": kind, "module": module, "line": line,
            "sqlite_context_line": context, "sqlite_explicit_commit_line": commit}


def _review_delegate(handler, call, drifted_files, writes):
    key = (handler["gateway_attribute"], call["dependency_attribute"],
           call["candidate_method"])
    constructor = "constructor_parameter:" + call["dependency_attribute"]
    binding = (handler["handler_module"], handler["handler_class"])
    result = {**call, "boundary_status": "unreviewed_delegate",
              "unresolved_dependencies": list(UNRESOLVED_DEPENDENCIES.get(key, ())),
              "source_chain": [], "mutation_sites": []}
    if key not in writes and key not in _MEDIA_READS:
        return result
    if drifted_files:
        return {**result, "boundary_status": "reviewed_source_drift"}
    if (handler["gateway_class"] != "BAMOfflineGateway" or
            handler["handler_source_status"] != "candidate" or
            binding != _HANDLER_BINDINGS[key[0]] or
            call["constructor_dependency_hint"] != constructor):
        return {**result, "boundary_status": "unresolved_binding"}
    if key in _MEDIA_READS:
        return {**result, "boundary_status": "no_direct_mutation_in_reviewed_body",
                "source_chain": [
                    "bam_pending_media_store.BAMPendingMediaStore." + key[2]]}
    chain, sites = writes[key]
    return {
        **result,
        "boundary_status": "reviewed_source_write_path",
        "source_chain": list(chain),
        "mutation_sites": [
            _mutation_site(*site) for site in sites
        ],
    }


def inspect_ci_wsgi_write_boundaries(*, source_root=None):
    """Return pinned source paths and unresolved delegates for local BAM.

    Only checked-in source is read. The delegated-call report enforces the
    existing CI gate and source-file safety checks. No application is imported.
    """
    upstream = inspect_ci_wsgi_delegated_calls(source_root=source_root)
    root = Path(__file__).resolve().parent if source_root is None else Path(source_root)
    observed = {}
    for name in sorted(_REVIEWED_SOURCE):
        try:
            _, observed[name] = _read(root / name)
        except FileNotFoundError:
            observed[name] = None

    drifted = [name for name in observed if observed[name] != _REVIEWED_SOURCE[name]]
    for module, digest in upstream["handler_source_sha256"].items():
        name = module + ".py"
        if name in observed and observed[name] != digest:
            raise ValueError("Handler changed during source inspection: " + name)

    writes = {**_MEDIA_WRITES, **WRITE_PATHS}
    for handler, api_method, method, sql, transaction, line in _DRAFT_WRITES:
        writes[handler, "api", api_method] = (
            ("account_read_api.AccountReadAPI." + api_method,
             "content_request_service.ContentRequestService." + method,
             "content_requests.ContentRequests." + method),
            (("sql_" + sql, "content_requests.py", line, transaction),),
        )

    handlers = []
    for handler in upstream["handler_candidates"]:
        delegates = handler["syntactic_delegate_calls"]
        alias_method = LOCAL_DRAFT_METHODS.get(handler["gateway_attribute"])
        alias_review = []
        if alias_method:
            # Keep the original AST result visible. Only the exact pinned
            # composition can attribute this separate manually reviewed call.
            alias_review.append(_review_delegate(handler, {
                "line": 126, "dependency_attribute": "api",
                "source_evidence": "manual_pinned_alias",
                "candidate_method": alias_method,
                "constructor_dependency_hint": "constructor_parameter:api",
                "actual_service_or_write_proven": False,
            }, drifted, writes))
        handlers.append({
            **handler,
            "boundary_scope": "syntactic_delegates" if delegates else "unresolved_no_delegate",
            "manually_reviewed_alias_calls": alias_review,
            "syntactic_delegate_calls": [
                _review_delegate(handler, call, drifted, writes) for call in delegates
            ],
        })
    evidence = {
        "format": "bam-ci-wsgi-write-boundaries-v2",
        "source_delegate_review_sha256": upstream["review_sha256"],
        "observed_source_sha256": observed,
        "drifted_reviewed_source": drifted,
        "handler_candidates": handlers,
    }
    return {**evidence, "review_sha256": _fingerprint(evidence),
            "runtime_binding_verified": False,
            "deployed_writer_inventory_complete": False,
            "transaction_generation_fencing_proven": False}
