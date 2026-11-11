"""Offline, single-component OpenAI revision orchestration.

A trusted server-injected executor may revise only one existing AI draft field.
Quota is reserved before a provider request, idempotency prevents duplicate
charges on replay, and both draft/fact revisions must remain current. This
module does not fetch credentials, call OpenAI, scan images, approve or publish.
"""
import hashlib
import json

from ai_content_plan import AIContentPlan
from ai_sponsorship import SponsorshipPlan


class AITargetedRevisionWorkflow:
    def __init__(self, *, plan, facts, quota, drafts, executor,
                 idempotency=None):
        if not isinstance(plan, AIContentPlan):
            raise TypeError('Structured content planner required')
        if not callable(executor):
            raise TypeError('Trusted server-side executor required')
        self.plan=plan
        self.facts=facts
        self.quota=quota
        self.drafts=drafts
        self.executor=executor
        self.idempotency=idempotency

    def revise_sponsored(self, *, token, now, draft_id, expected_revision,
                         target, instruction, topic, month,
                         sponsorship_plan, request_key=None):
        if not isinstance(sponsorship_plan,SponsorshipPlan):
            raise ValueError('Server-configured sponsorship plan required')
        if type(expected_revision) is not int or expected_revision<1:
            raise ValueError('Current draft revision required')
        if target not in ('post_text','image_prompt'):
            raise ValueError('Only one component may be regenerated')
        if type(instruction) is not str or not instruction.strip() or len(instruction)>500:
            raise ValueError('Bounded revision instruction required')
        if self.idempotency is not None and request_key is None:
            raise ValueError('Idempotency key required')
        if request_key is not None and self.idempotency is None:
            raise ValueError('Request deduplication store not configured')
        # Resolve current session, subject, tenant and existing draft before
        # making any quota reservation or provider request.
        current=self.drafts.get(token=token,now=now,draft_id=draft_id)
        if current['revision']!=expected_revision:
            raise ValueError('Draft changed; refresh before revising')
        if target=='image_prompt' and current['image_prompt'] is None:
            raise ValueError('Draft has no existing image prompt to revise')
        snapshot=self.facts.snapshot(token=token,now=now)
        if (snapshot['provenance']!='owner_confirmed' or
                not snapshot['facts'] or
                snapshot['tenant_id']!=current['tenant_id']):
            raise ValueError('Current owner-confirmed business facts required')
        request=self.plan.revision_request(
            token=token,now=now,verified_facts=snapshot['facts'],
            topic=topic,platform=current['platform'],current=current,
            target=target,instruction=instruction)
        if request['mode']!='bam_sponsored':
            raise ValueError('Personal key requires separate vault-backed execution')
        if request['tenant_id']!=current['tenant_id']:
            raise PermissionError('Revision business mismatch')
        if request_key is not None:
            fingerprint=hashlib.sha256(json.dumps({
                'kind':'targeted_revision_v1',
                'tenant':request['tenant_id'],
                'subject':request['subject_id'],
                'draft_id':draft_id,
                'draft_revision':expected_revision,
                'facts_revision':snapshot['revision'],
                'platform':current['platform'],
                'topic':topic,
                'target':target,
                'instruction':instruction,
                'month':month,
                'input_json':request['input_json']
            },ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
            claim=self.idempotency.claim(
                token=token,now=now,request_key=request_key,
                fingerprint=fingerprint)
            if not claim['claimed']:
                return {'revised':False,'reason':'already_'+claim['status'],
                        'tenant_id':current['tenant_id'],
                        'publishing_enabled':False}
        try:
            reservation=self.quota.reserve(token=token,now=now,
                plan=sponsorship_plan,month=month)
            if not reservation['reserved']:
                result={'revised':False,'reason':reservation['reason'],
                        'tenant_id':current['tenant_id'],
                        'publishing_enabled':False}
            else:
                raw=self.executor(
                    request=request,
                    max_output_tokens=reservation['max_output_tokens'])
                # A changed fact registry, stale draft, or revoked membership
                # must not lead to a staged revision based on an old snapshot.
                latest=self.facts.snapshot(token=token,now=now)
                if (latest['tenant_id']!=snapshot['tenant_id'] or
                        latest['revision']!=snapshot['revision'] or
                        latest['provenance']!='owner_confirmed'):
                    raise ValueError('Business facts changed during revision')
                revised_text=self.plan.parse_revision_response(
                    raw,target=target)
                updated=self.drafts.revise(
                    token=token,now=now,draft_id=draft_id,target=target,
                    revised_text=revised_text,
                    expected_revision=expected_revision)
                result={'revised':True,'tenant_id':current['tenant_id'],
                        'draft':updated,
                        'fact_revision':snapshot['revision'],
                        'remaining_sponsored_requests':reservation['remaining'],
                        'publishing_enabled':False}
        except Exception:
            if request_key is not None:
                self.idempotency.finish(
                    token=token,now=now,request_key=request_key,
                    status='failed')
            raise
        if request_key is not None:
            self.idempotency.finish(
                token=token,now=now,request_key=request_key,
                status='completed' if result['revised'] else 'failed',
                draft_id=draft_id if result['revised'] else None)
        return result
