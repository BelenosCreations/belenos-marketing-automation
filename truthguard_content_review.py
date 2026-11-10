"""Read-only authenticated TruthGuard review of existing content requests.

This is a review report, not an approval or publishing authorization.
"""
from truthguard_review import TruthGuardReviewer
from truthguard_span_audit import ClaimSpanAudit

class TruthGuardContentReview:
    def __init__(self,*,content_service,reviewer):
        self.content_service=content_service
        self.reviewer=reviewer

    def review(self,*,token,tenant_id,request_id,claims,now=None,annotations=None):
        request=self.content_service.get(token=token,tenant_id=tenant_id,
                                         request_id=request_id,now=now)
        if request is None:
            raise KeyError('Content request not found')
        timestamp=self.content_service._now(now)
        span_audit=ClaimSpanAudit.audit(draft_text=request['draft_text'],
            annotations=annotations if annotations is not None else [])
        result=self.reviewer.review_draft(
            tenant_id=tenant_id,draft_text=request['draft_text'],
            claims=claims,now=timestamp)
        return {'business_id':tenant_id,'request_id':request_id,
                'content_status':request['status'],
                'content_complete':request['status']=='ready_for_review',
                'truthguard':result,'span_audit':span_audit,
                'status':'held',
                'publishing_enabled':False,
                'reason':'Review only; approval and comprehensive claim extraction are not established'}
