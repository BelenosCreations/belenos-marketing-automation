"""Immutable read-only TruthGuard review receipts.

Receipts describe an observed review, not an approval or publishing permit.
"""
import hashlib
import json

def create_review_receipt(*, tenant_id, request_id, draft_text, review, reviewed_at):
    if not all(isinstance(v,str) and v.strip()
               for v in (tenant_id,request_id,draft_text)):
        raise ValueError('Complete review identity required')
    if type(reviewed_at) is not int or not isinstance(review,dict):
        raise ValueError('Invalid review')
    if review.get('business_id')!=tenant_id or review.get('request_id')!=request_id:
        raise ValueError('Review does not belong to request')
    if review.get('publishing_enabled') is not False or review.get('status')!='held':
        raise ValueError('Only held review reports can be receipted')
    span=review.get('span_audit')
    digest=hashlib.sha256(draft_text.encode('utf-8')).hexdigest()
    if not isinstance(span,dict) or span.get('draft_sha256')!=digest:
        raise ValueError('Review draft fingerprint mismatch')
    payload={'tenant_id':tenant_id,'request_id':request_id,
             'draft_sha256':digest,'reviewed_at':reviewed_at,
             'review':review}
    serialized=json.dumps(payload,sort_keys=True,separators=(',',':'),
                          ensure_ascii=False,allow_nan=False)
    return {'receipt_sha256':hashlib.sha256(serialized.encode('utf-8')).hexdigest(),
            'payload':payload,'approval_granted':False,
            'publishing_enabled':False}

def validate_review_receipt(*, receipt, tenant_id, request_id, draft_text):
    if not isinstance(receipt,dict) or not isinstance(receipt.get('payload'),dict):
        return False
    payload=receipt['payload']
    if payload.get('tenant_id')!=tenant_id or payload.get('request_id')!=request_id:
        return False
    if not isinstance(draft_text,str):
        return False
    if payload.get('draft_sha256')!=hashlib.sha256(draft_text.encode('utf-8')).hexdigest():
        return False
    if receipt.get('approval_granted') is not False or receipt.get('publishing_enabled') is not False:
        return False
    try:
        serialized=json.dumps(payload,sort_keys=True,separators=(',',':'),
                              ensure_ascii=False,allow_nan=False)
    except (TypeError,ValueError):
        return False
    return receipt.get('receipt_sha256')==hashlib.sha256(serialized.encode('utf-8')).hexdigest()
