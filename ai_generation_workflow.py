"""Offline OpenAI draft generation orchestration with fail-closed execution.

The executor is a trusted server-side dependency, NOT a browser callback.
No OpenAI network client, raw key handling, media generation or publishing is
provided by this module. Sponsored attempts consume a quota reservation
before the executor is invoked, including failed attempts.
"""
from ai_content_plan import AIContentPlan
from ai_sponsorship import SponsorshipPlan

class AIDraftGenerationWorkflow:
    def __init__(self, *, plan, facts, quota, drafts, executor):
        if not isinstance(plan,AIContentPlan):
            raise TypeError('Structured content planner required')
        if not callable(executor):
            raise TypeError('Trusted server-side executor required')
        self.plan=plan
        self.facts=facts
        self.quota=quota
        self.drafts=drafts
        self.executor=executor

    def generate_sponsored(self, *, token, now, topic, platform,
                           month, sponsorship_plan,
                           include_image_prompt=True,needs_media=False):
        if not isinstance(sponsorship_plan,SponsorshipPlan):
            raise ValueError('Server-configured sponsorship plan required')
        if type(needs_media) is not bool or type(include_image_prompt) is not bool:
            raise ValueError('Explicit media options required')
        if needs_media and not include_image_prompt:
            raise ValueError('Media-required draft needs an image prompt')
        # Fail before consuming quota if facts or permissions are missing.
        request=self.plan.create_from_confirmed_facts(
            token=token,now=now,registry=self.facts,topic=topic,
            platform=platform,include_image_prompt=include_image_prompt)
        if request['mode']!='bam_sponsored':
            raise ValueError('Personal OpenAI key requires a separate vault-backed executor')
        reservation=self.quota.reserve(token=token,now=now,
            plan=sponsorship_plan,month=month)
        if not reservation['reserved']:
            return {'created':False,'reason':reservation['reason'],
                    'publishing_enabled':False}
        # The trusted executor must apply the reserved token cap and resolve
        # only the server-owned OpenAI key; it must never accept a client key.
        raw=self.executor(request=request,
            max_output_tokens=reservation['max_output_tokens'])
        # If facts were edited during execution, the output was grounded in
        # an obsolete snapshot. Hold it out of the draft queue.
        latest=self.facts.snapshot(token=token,now=now)
        if (latest['tenant_id']!=request['tenant_id'] or
                latest['revision']!=request['fact_revision'] or
                latest['provenance']!='owner_confirmed'):
            raise ValueError('Business facts changed during generation')
        parsed=self.plan.parse_response(raw,
            include_image_prompt=include_image_prompt)
        if needs_media and parsed['image_prompt'] is None:
            raise ValueError('Generated draft is missing required image prompt')
        staged=self.drafts.stage(token=token,now=now,platform=platform,
            response={'post_text':parsed['post_text'],
                      'image_prompt':parsed['image_prompt']},
            include_image_prompt=include_image_prompt,needs_media=needs_media)
        return {'created':True,'draft':staged,
                'fact_revision':request['fact_revision'],
                'remaining_sponsored_requests':reservation['remaining'],
                'publishing_enabled':False}
