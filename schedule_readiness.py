"""Read-only scheduling readiness assessment; never schedules or publishes."""
import time

def assess_schedule_readiness(*, ledger, token, tenant_id, intent_id,
                              proposed_at, now=None):
    timestamp=int(time.time()) if now is None else now
    if type(timestamp) is not int or type(proposed_at) is not int:
        raise ValueError('Integer timestamps required')
    # The ledger authenticates current owner membership and tenant scope.
    intent=ledger.inspect(token=token,tenant_id=tenant_id,
                          intent_id=intent_id,now=timestamp)
    blockers=[]
    if not intent['active']:
        blockers.append('approval_intent_revoked')
    if not intent['draft_unchanged']:
        blockers.append('draft_changed')
    if not intent['content_complete']:
        blockers.append('content_incomplete')
    if not intent['content_unchanged']:
        blockers.append('supporting_content_changed')
    if not intent['attachments_verified']:
        blockers.append('attachments_unverified')
    if proposed_at<=timestamp:
        blockers.append('scheduled_time_not_future')
    # Owner intent is not final authorization and TruthGuard coverage is not
    # yet independently validated at the scheduling boundary.
    blockers.extend(('final_approval_not_implemented',
                     'truthguard_publication_gate_not_implemented',
                     'publishing_integration_disabled'))
    return {'tenant_id':tenant_id,'request_id':intent['request_id'],
            'intent_id':intent_id,'proposed_at':proposed_at,
            'status':'held','blockers':blockers,
            'ready_to_schedule':False,'publishing_enabled':False}
