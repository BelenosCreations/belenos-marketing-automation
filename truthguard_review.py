"""TruthGuard fail-closed claim matching and draft review.

Only exact normalized claims backed by a current approved fact can pass.
Claim extraction must be comprehensive and server-owned before use in a gate.
"""
import re

def normalize(text):
    if not isinstance(text,str):
        raise ValueError('Claim must be text')
    return ' '.join(text.casefold().split())

class TruthGuardReviewer:
    def __init__(self,knowledge):
        self.knowledge=knowledge

    def review_claims(self,*,tenant_id,claims,now):
        if not isinstance(claims,(list,tuple)):
            raise ValueError('Claims must be a list')
        results=[]
        for claim in claims:
            if not isinstance(claim,dict) or set(claim)!={'key','text'}:
                raise ValueError('Claims require key and text')
            key,text=claim['key'],claim['text']
            if not isinstance(key,str) or not key.strip() or not normalize(text):
                raise ValueError('Nonempty claim required')
            facts=self.knowledge.lookup(tenant_id=tenant_id,claim_key=key,now=now)
            matches=[fact for fact in facts if normalize(fact['value'])==normalize(text)]
            results.append({'key':key,'text':text,
                'status':'verified' if matches else 'unsupported',
                'sources':[{'fact_id':f['fact_id'],'source':f['source']}
                           for f in matches]})
        return {'status':'verified' if results and all(
            result['status']=='verified' for result in results) else 'held',
            'claims':results,'publishing_enabled':False}

    def review_draft(self,*,tenant_id,draft_text,claims,now,
                     extraction_complete=False):
        if not isinstance(draft_text,str) or not draft_text.strip():
            raise ValueError('Draft text required')
        report=self.review_claims(tenant_id=tenant_id,claims=claims,now=now)
        # A client/LLM claim list is not proof all factual claims were extracted.
        # No production publish eligibility can be established here.
        return {**report,'status':'held',
            'extraction_complete_asserted':bool(extraction_complete),
            'reason':'Full server-owned claim extraction and approval gates not implemented'}
