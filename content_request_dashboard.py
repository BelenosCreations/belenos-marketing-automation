"""Read-only dashboard projection for Content Requests.

No publishing controls. All data comes from the authenticated request service.
"""
from collections import Counter

class ContentRequestDashboard:
    def __init__(self, service):
        self.service=service

    def overview(self, *, token, tenant_id, now=None):
        entries=self.service.list_for_business(token=token,tenant_id=tenant_id,now=now)
        counts=Counter(entry['status'] for entry in entries)
        cards=[]
        for entry in entries:
            supplied=set(entry['provided_items'])
            required=entry['required_items']
            cards.append({
                'request_id':entry['request_id'],
                'business_id':tenant_id,
                'channel':entry['channel'],
                'draft_text':entry['draft_text'],
                'content_suggestion':entry['suggestion'],
                'required_items':required,
                'missing_items':[item for item in required if item not in supplied],
                'completed_items':[item for item in required if item in supplied],
                'status':entry['status'],
                'priority':entry['priority'],
                'created_at':entry['created_at'],
                'updated_at':entry['updated_at'],
                'can_publish':False,
                'can_schedule':False,
            })
        return {
            'business_id':tenant_id,
            'counts':{status:counts[status] for status in
                ('needs_content','ready_for_review','postponed','unavailable')},
            'cards':cards,
            'publishing_enabled':False,
        }
