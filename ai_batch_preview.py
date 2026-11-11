"""Zero-provider-call, owner-fact-grounded advance marketing draft planning.

A preview cannot reserve quota, charge a model, create a draft, generate
artwork, schedule a post or authorize publishing. It describes the validated
request shape for later separately authorized generation.
"""
from ai_content_plan import AIContentPlan


class AIBatchPreview:
    def __init__(self, *, plan, facts):
        if not isinstance(plan, AIContentPlan):
            raise TypeError('Trusted AI content plan required')
        self.plan=plan
        self.facts=facts

    def preview(self, *, token, now, topics, platform,
                include_image_prompt=True):
        if type(include_image_prompt) is not bool:
            raise ValueError('Explicit image-prompt preference required')
        if (type(topics) is not list or not 1<=len(topics)<=14
                or any(type(topic) is not str or not topic.strip()
                       or topic!=topic.strip() or len(topic)>300
                       for topic in topics)
                or len({topic.casefold() for topic in topics})!=len(topics)):
            raise ValueError('One to fourteen distinct campaign topics required')
        facts=self.facts.snapshot(token=token,now=now)
        if (facts['provenance']!='owner_confirmed' or
                not facts['facts'] or type(facts['revision']) is not int
                or facts['revision']<1):
            raise ValueError('Owner-confirmed business facts required')
        requests=self.plan.batch_requests(
            token=token,now=now,verified_facts=facts['facts'],
            topics=topics,platform=platform,
            include_image_prompt=include_image_prompt)
        first=requests[0]
        if (first['tenant_id']!=facts['tenant_id'] or
                first['provider']!='openai' or
                first['mode'] not in ('bam_sponsored','own_openai_key') or
                any(record['tenant_id']!=facts['tenant_id'] or
                    record['subject_id']!=first['subject_id'] or
                    record['mode']!=first['mode'] or
                    record['publishing_enabled'] is not False
                    for record in requests)):
            raise PermissionError('Cross-account batch plan prohibited')
        return {
            'tenant_id':facts['tenant_id'],
            'mode':first['mode'],
            'fact_revision':facts['revision'],
            'fact_provenance':'owner_confirmed',
            'items':[{'topic':topic,'platform':platform,
                      'image_prompt_planned':include_image_prompt}
                     for topic in topics],
            'planned_individual_requests':len(requests),
            'provider_requests_made':0,
            'quota_reserved':False,
            'actual_cost_known':False,
            'drafts_created':0,
            'status':'planning_only',
            'publishing_enabled':False,
        }
