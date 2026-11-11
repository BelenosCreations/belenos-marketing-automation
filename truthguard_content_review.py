"""Read-only authenticated TruthGuard review of existing content requests.

This is a review report, not an approval or publishing authorization.
"""
from truthguard_review import TruthGuardReviewer
from truthguard_span_audit import ClaimSpanAudit
from truthguard_risk_signals import scan_risk_signals

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
        # Validate untrusted claims before using their values in a hash lookup.
        # This avoids type errors from nested/unhashable attacker input.
        if not isinstance(claims,(list,tuple)) or len(claims)>100:
            raise ValueError('Claims must be a bounded list')
        for claim in claims:
            if (not isinstance(claim,dict) or set(claim)!={'key','text'}
                    or not isinstance(claim['key'],str) or not claim['key'].strip()
                    or not isinstance(claim['text'],str) or not claim['text'].strip()):
                raise ValueError('Claims require nonempty key and text')
        # Caller-provided claims must match exact spans in the stored draft.
        matched={(entry['key'],entry['text']) for entry in span_audit['accepted']}
        detached=[{'key':claim['key'],'text':claim['text']}
                  for claim in claims
                  if (claim['key'],claim['text']) not in matched]
        risk_signals=scan_risk_signals(request['draft_text'])
        # Signal coverage is an editorial indicator only. A spanning annotation
        # does not establish that its contents are true.
        uncovered_signals=[signal for signal in risk_signals['signals']
            if not any(span['start']<=signal['start']
                       and span['end']>=signal['end']
                       for span in span_audit['accepted'])]
        result=self.reviewer.review_draft(
            tenant_id=tenant_id,draft_text=request['draft_text'],
            claims=claims,now=timestamp)
        return {'business_id':tenant_id,'request_id':request_id,
                'content_status':request['status'],
                'content_complete':request['status']=='ready_for_review',
                'truthguard':result,'span_audit':span_audit,
                'risk_signals':risk_signals,
                'uncovered_risk_signals':uncovered_signals,
                'risk_signals_annotated':not uncovered_signals and span_audit['annotation_integrity'],
                'detached_claims':detached,
                'claims_grounded_in_draft':not detached and bool(claims)
                    and span_audit['annotation_integrity'],
                'status':'held',
                'publishing_enabled':False,
                'reason':'Review only; approval and comprehensive claim extraction are not established'}
