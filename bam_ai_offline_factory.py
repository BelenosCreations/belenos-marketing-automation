"""Safe, disabled-by-default composition root for BAM AI development.

Creates the complete offline AI service graph without loading credentials,
making network calls or exposing write endpoints. A production composition
root must be separate and explicitly reviewed before enabling paid generation.
"""
from dataclasses import dataclass
from ai_account_policy import AIPolicyStore
from ai_business_facts import AIBusinessFacts
from ai_content_drafts import AIContentDraftStore
from ai_draft_request import AIDraftRequestBuilder
from ai_content_plan import AIContentPlan
from ai_sponsorship import SponsoredAIQuota
from ai_generation_idempotency import AIGenerationIdempotency
from ai_generation_workflow import AIDraftGenerationWorkflow
from ai_targeted_revision_workflow import AITargetedRevisionWorkflow
from ai_cost_ledger import AICostLedger
from openai_responses_executor import OpenAIResponsesExecutor
from openai_https_transport import OpenAITransport
from bam_ai_write_wsgi import BAMAIWriteWSGI
from bam_ai_revision_wsgi import BAMAIRevisionWSGI
from bam_ai_facts_write_wsgi import BAMAIFactsWriteWSGI

@dataclass(frozen=True)
class DisabledAIBundle:
    policy: AIPolicyStore
    facts: AIBusinessFacts
    drafts: AIContentDraftStore
    quota: SponsoredAIQuota
    idempotency: AIGenerationIdempotency
    costs: AICostLedger
    workflow: AIDraftGenerationWorkflow
    revision_workflow: AITargetedRevisionWorkflow
    revision_app: BAMAIRevisionWSGI
    generate_app: BAMAIWriteWSGI
    facts_app: BAMAIFactsWriteWSGI

def build_disabled_ai_bundle(*, db,sessions,directory,plan_resolver):
    if not callable(plan_resolver):
        raise TypeError('Trusted plan resolver required')
    policy=AIPolicyStore(db=db,sessions=sessions,directory=directory)
    facts=AIBusinessFacts(db=db,policy_store=policy)
    drafts=AIContentDraftStore(db=db,policy_store=policy)
    quota=SponsoredAIQuota(db=db,policy_store=policy)
    idempotency=AIGenerationIdempotency(db=db,policy_store=policy)
    costs=AICostLedger(db)
    # The default transport refuses before accessing credentials or opener.
    transport=OpenAITransport(key_resolver=lambda:None,
        opener=lambda *args,**kwargs:None,enabled=False)
    executor=OpenAIResponsesExecutor(transport=transport)
    workflow=AIDraftGenerationWorkflow(
        plan=AIContentPlan(request_builder=AIDraftRequestBuilder(
            policy_store=policy)),facts=facts,quota=quota,drafts=drafts,
        executor=executor,idempotency=idempotency)
    revision_workflow=AITargetedRevisionWorkflow(
        plan=workflow.plan,facts=facts,quota=quota,drafts=drafts,
        executor=executor,idempotency=idempotency)
    revision_app=BAMAIRevisionWSGI(workflow=revision_workflow,
        plan_resolver=plan_resolver,enabled=False)
    return DisabledAIBundle(policy,facts,drafts,quota,idempotency,costs,
        workflow,revision_workflow,revision_app,
        BAMAIWriteWSGI(workflow=workflow,
            plan_resolver=plan_resolver,enabled=False),
        BAMAIFactsWriteWSGI(registry=facts,enabled=False))
