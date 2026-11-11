"""Strict, read-only UI payload derived from authenticated BAM account overview.

Never accept tenant, role, session or counts from a browser payload. This
module is called only after AccountReadAPI has authorized the session.
No social secrets, session tokens, or publication privileges are returned.
"""
from dashboard_cards import build_dashboard_cards

def build_dashboard_view(overview):
    if not isinstance(overview,dict):
        raise ValueError('Authorized overview required')
    tenant=overview.get('tenant_id')
    if not isinstance(tenant,str) or not tenant:
        raise ValueError('Authorized business required')
    businesses=overview.get('businesses')
    if not isinstance(businesses,list):
        raise ValueError('Business directory required')
    requests=overview.get('pending_content_requests')
    if not isinstance(requests,list):
        raise ValueError('Authorized content list required')
    drafts=[]
    for request in requests:
        if request.get('status') not in ('needs_content','ready_for_review'):
            raise ValueError('Unexpected draft status')
        draft={
            'request_id':request['request_id'],
            'channel':request['channel'],
            'draft_text':request['draft_text'],
            'suggestion':request['suggestion'],
            'status':request['status'],
            'missing_items':list(request['missing_items']),
            'priority':request['priority']
        }
        drafts.append(draft)
    cards=overview.get('dashboard_cards')
    if cards is None:
        cards=build_dashboard_cards(overview)['cards']
    if not isinstance(cards,list):
        raise ValueError('Dashboard cards required')
    return {
        'schema_version':1,
        'tenant_id':tenant,
        'role':overview['role'],
        'businesses':businesses,
        'cards':cards,
        'drafts':drafts,
        'publishing_enabled':False,
        'analytics':{'availability':'not_connected','series':None},
        'schedule':{'availability':'not_connected','posts':None}
    }
