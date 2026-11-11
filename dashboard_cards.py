"""Presentation-ready BAM dashboard cards from authorized server overview.

Only computes counts backed by known records. Missing scheduler and analytics
integrations remain unavailable, never fabricated as zero or success.
"""
def build_dashboard_cards(overview):
    if not isinstance(overview,dict):
        raise ValueError('Authorized overview required')
    requests=overview.get('pending_content_requests')
    if not isinstance(requests,list):
        raise ValueError('Pending request list required')
    missing=sum(1 for item in requests if item.get('status')=='needs_content')
    approvals=sum(1 for item in requests if item.get('status')=='ready_for_review')
    social=overview.get('social_connections')
    connection_count=len(social) if isinstance(social,list) else None
    return {
        'tenant_id':overview['tenant_id'],
        'cards':[
            {'id':'scheduled','label':'Scheduled posts','value':None,
             'availability':'not_connected','route':'calendar'},
            {'id':'approvals','label':'Needs review','value':approvals,
             'availability':'available','route':'content/review'},
            {'id':'content','label':'Content needed','value':missing,
             'availability':'available','route':'content/needed'},
            {'id':'connections','label':'Social connections',
             'value':connection_count,
             'availability':'available' if connection_count is not None else 'restricted',
             'route':'connections'},
        ],
        'publishing_enabled':False
    }
