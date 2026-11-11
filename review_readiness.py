"""Tenant-private editorial readiness preview for unpublished held drafts.

A complete asset set is not TruthGuard review or publication permission.
This service is only a current, authenticated snapshot; nothing is approved,
scheduled, queued, dispatched or charged.
"""
from access_policy import Action, Resource, require_permission

class ReviewReadiness:
    def __init__(self, *, sessions, directory, content_service):
        self.sessions=sessions
        self.directory=directory
        self.content_service=content_service

    def list_current_business(self, *, token, now):
        if type(now) is not int or now<0:
            raise ValueError('Trusted server time required')
        session=self.sessions.resolve_current(
            token,directory=self.directory,now=now)
        if session is None:
            raise PermissionError('Active BAM session required')
        principal=session.principal
        require_permission(principal,Action.READ_DRAFTS,
                           Resource(principal.tenant_id))
        tenant=principal.tenant_id
        drafts=self.content_service.list_for_business(
            token=token,tenant_id=tenant,now=now)
        if len(drafts)>200:
            raise ValueError('Review preview too large')
        items=[]
        ready=0
        for draft in drafts:
            required=draft['required_items']
            provided=draft['provided_items']
            if (type(required) is not list or type(provided) is not dict
                    or not required or len(required)>20
                    or draft['status'] not in (
                        'needs_content','ready_for_review',
                        'postponed','unavailable')
                    or type(draft['revision']) is not int
                    or draft['revision']<1):
                raise ValueError('Inconsistent held draft state')
            missing=[item for item in required if item not in provided]
            unverified=[]
            for item in required:
                if item not in provided:
                    continue
                ref=provided[item]
                if type(ref) is not str or not ref.startswith('verified-attachment:'):
                    unverified.append(item)
                    continue
                aid=ref[len('verified-attachment:'):]
                if not aid or self.content_service.attachments.resolve_verified(
                        tenant_id=tenant,request_id=draft['request_id'],
                        item=item,attachment_id=aid)!=aid:
                    unverified.append(item)
            complete=(draft['status']=='ready_for_review'
                      and not missing and not unverified
                      and set(required)==set(provided))
            blockers=[]
            if draft['status'] in ('postponed','unavailable'):
                blockers.append('draft_held')
            if missing:
                blockers.append('missing_required_content')
            if unverified or set(required)!=set(provided):
                blockers.append('unverified_or_unexpected_content')
            if not complete and not blockers:
                blockers.append('not_ready_for_editorial_review')
            # These remain required regardless of asset completeness or
            # what heuristics say about apparently safe draft language.
            blockers.extend(('truthguard_review_required',
                             'owner_approval_not_implemented',
                             'social_publishing_disabled'))
            ready+=int(complete)
            items.append({
                'request_id':draft['request_id'],
                'revision':draft['revision'],
                'channel':draft['channel'],
                'status':draft['status'],
                'missing_items':missing,
                'unverified_items':unverified,
                'editorial_material_complete':complete,
                'blockers':blockers,
                'approved':False,
                'publishing_enabled':False
            })
        return {
            'tenant_id':tenant,'status':'review_preview_only',
            'held_count':len(items),
            'editorial_material_complete_count':ready,
            'items':items,'approved_count':0,
            'publishing_enabled':False
        }
