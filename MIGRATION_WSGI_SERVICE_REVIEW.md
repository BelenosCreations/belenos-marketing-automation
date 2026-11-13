# CI-only WSGI handler-to-service method review

## Selected SQL and filesystem boundaries

The [held-draft and pending-media review](MIGRATION_WSGI_WRITE_BOUNDARY_REVIEW.md)
links selected local gateway delegates to their transaction and file sites.
It also records startup and alternative loopback writers, unresolved paths and
the remaining design work for database and media fencing.

PR #108 builds on independently verified #107. This non-executing AST module
adds a single downstream source hop for candidate gateway handler bindings.
It identifies direct self.dependency.method calls inside candidate handler
__call__ methods, recording method names and whether the dependency attribute
was assigned directly from a constructor parameter.

For example, synthetic source review of the offline content writer may expose
method-call names such as create_held_draft and update_draft_hold; pending
media source may expose authorize_slot and receive. These are *candidate*
source facts, not evidence that a route is reachable in a deployed server or
that any database commit is fenced. The tool does not execute or inspect actual
tenant records, provider credentials or runtime objects.

The deterministic digest binds to the preceding #107 gateway review digest
and source-file digests for candidate handler modules. The digest is not
operator approval. Ambiguous/undiscovered constructors and missing source
modules remain explicitly unresolved, not classified safe. No proof of a
service-layer commit, tenant authorization, WSGI middleware, provider callback,
queued worker, schedule, retry semantics, or real generation fencing exists.

Run only in disposable checkout:
BAM_EPHEMERAL_PG_TEST=1 python -m unittest test_neon_ci_wsgi_delegate_review -v

Production migrations and publishing remain disabled. No Render, Neon,
EdgePilot or paid AI activation, no new infrastructure or billing, no customer
data reads. Requires exact-head and independently successful merged-main
Actions before verification. Private Beta requires explicit owner approval
after all independent security, backup, scanner and rights blockers.
