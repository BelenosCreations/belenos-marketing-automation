"""Deterministic offline candidate ranking using tenant-scoped observed metrics.

No synthetic engagement estimates, external analytics or publishing.
"""
import math

def rank_candidates(*, tenant_id, candidates, observations, minimum_samples=5):
    if not isinstance(tenant_id,str) or not tenant_id.strip():
        raise ValueError('Tenant required')
    if not isinstance(candidates,(list,tuple)) or not 1<=len(candidates)<=20:
        raise ValueError('One to twenty candidates required')
    if len(set(candidates))!=len(candidates) or any(
            not isinstance(c,str) or not c for c in candidates):
        raise ValueError('Unique candidate labels required')
    if not isinstance(observations,(list,tuple)) or len(observations)>1000:
        raise ValueError('Bounded observations required')
    if type(minimum_samples) is not int or not 1<=minimum_samples<=1000:
        raise ValueError('Invalid minimum samples')
    buckets={candidate:[] for candidate in candidates}
    for record in observations:
        if not isinstance(record,dict):
            raise ValueError('Invalid observation')
        if record.get('tenant_id')!=tenant_id:
            raise PermissionError('Cross-business analytics prohibited')
        candidate=record.get('candidate')
        if candidate not in buckets:
            raise ValueError('Observation does not match a candidate')
        value=record.get('engagement_rate')
        if (type(value) not in (int,float) or not math.isfinite(value)
                or not 0<=value<=1):
            raise ValueError('Observed engagement rate must be between 0 and 1')
        buckets[candidate].append(float(value))
    results=[]
    for candidate in candidates:
        values=buckets[candidate]
        enough=len(values)>=minimum_samples
        results.append({'candidate':candidate,'sample_count':len(values),
                        'observed_mean':round(sum(values)/len(values),6)
                        if enough else None,'sufficient_data':enough})
    if not all(item['sufficient_data'] for item in results):
        return {'selection':None,'selection_policy':'insufficient_observations',
                'ranked':results,'publishing_enabled':False}
    ranked=sorted(results,key=lambda item:(-item['observed_mean'],item['candidate']))
    return {'selection':ranked[0]['candidate'],
            'selection_policy':'highest_observed_mean',
            'ranked':ranked,'publishing_enabled':False}
