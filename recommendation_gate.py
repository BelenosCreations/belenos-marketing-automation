"""Conservative combined source/creator recommendation gate.

A candidate is eligible for editorial consideration only if BOTH the
business-topic source policy and verified platform-account policy allow it.
This is not a publishing or copyright permission.
"""
from business_curation import BusinessCuration
from creator_identities import CreatorIdentityPolicy

class RecommendationGate:
    def __init__(self, db):
        self.sources=BusinessCuration(db)
        self.creators=CreatorIdentityPolicy(db)

    def evaluate(self, *, tenant_id, topic, candidate, platform, account_id,
                 identity_verified=False, local_competitor_risk='unknown'):
        identity_status, identity_reason=self.creators.screen(
            tenant_id=tenant_id,platform=platform,account_id=account_id,
            identity_verified=identity_verified)
        if identity_status=='blocked':
            return 'blocked',identity_reason
        source_status,source_reason=self.sources.evaluate(
            tenant_id=tenant_id,topic=topic,candidate=candidate,
            local_competitor_risk=local_competitor_risk)
        if source_status=='blocked':
            return 'blocked',source_reason
        if identity_status!='eligible':
            return 'approval_required',identity_reason
        if source_status!='eligible_link_only':
            return source_status,source_reason
        return 'eligible_link_only','editorial_review_eligible_not_publish_authorized'
