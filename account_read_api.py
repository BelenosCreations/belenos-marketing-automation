"""Fail-closed request adapter for BAM account and held-draft workflows.

This is not an HTTP server. A future HTTPS transport must authenticate the
caller, provide a bearer session token and perform rate limiting/CSRF controls.
The adapter never accepts tenant IDs or roles from client body claims.
"""
from account_dashboard import AccountDashboard
from dashboard_cards import build_dashboard_cards
from dashboard_view import build_dashboard_view
from content_upload_preflight import ContentUploadPreflight
from ai_local_templates import LocalDraftTemplates
from ai_draft_request import AIDraftRequestBuilder
from posting_time_preview import build_posting_time_preview
from access_policy import Action, Resource, require_permission

class AccountReadAPI:
    def __init__(self, dashboard: AccountDashboard, posting_preferences=None,
                 ai_content_drafts=None,ai_policy=None,
                 ai_business_facts=None,ai_cost_ledger=None,
                 pending_media_available=False):
        self.dashboard=dashboard
        self.posting_preferences=posting_preferences
        self.ai_content_drafts=ai_content_drafts
        self.ai_policy=ai_policy
        self.ai_business_facts=ai_business_facts
        self.ai_cost_ledger=ai_cost_ledger
        if type(pending_media_available) is not bool:
            raise ValueError('Trusted pending media capability required')
        self.pending_media_available=pending_media_available

    @staticmethod
    def _token(value):
        if not isinstance(value,str) or not value.strip() or len(value)>2048:
            raise PermissionError('Valid BAM session required')
        return value

    @staticmethod
    def _now(value):
        if type(value) is not int or value<0:
            raise ValueError('Server timestamp required')
        return value

    def get_overview(self, *, session_token, server_now):
        """Read-only current business overview; no caller-supplied tenant."""
        overview=self.dashboard.overview(
            token=self._token(session_token),now=self._now(server_now))
        overview['dashboard_cards']=build_dashboard_cards(overview)['cards']
        return overview

    def get_dashboard_view(self, *, session_token, server_now):
        """Minimal presentation payload from authenticated tenant data."""
        overview=self.get_overview(session_token=session_token,server_now=server_now)
        data=build_dashboard_view(overview)
        data['pending_media_available']=self.pending_media_available
        return data

    def activate_business(self, *, session_token, target_tenant_id, server_now):
        """Change business only after verifying target membership.

        Return a replacement session token only through a trusted transport.
        """
        if (not isinstance(target_tenant_id,str)
                or not target_tenant_id.strip()
                or len(target_tenant_id)>128):
            raise ValueError('Valid target business required')
        result=self.dashboard.switch_and_overview(
            token=self._token(session_token),
            target_tenant_id=target_tenant_id,now=self._now(server_now))
        result['overview']['dashboard_cards']=build_dashboard_cards(result['overview'])['cards']
        return result

    def get_ai_cost_summary(self, *, session_token, server_now):
        """Read only this user's estimated AI costs for the active business."""
        if self.ai_cost_ledger is None or self.ai_policy is None:
            raise RuntimeError('AI cost reporting not configured')
        principal=self.ai_policy._principal(
            self._token(session_token),self._now(server_now))
        summary=self.ai_cost_ledger.summary_trusted(
            tenant_id=principal.tenant_id,subject_id=principal.subject_id)
        return {'tenant_id':principal.tenant_id,**summary,
                'publishing_enabled':False}

    def get_ai_business_facts(self, *, session_token, server_now):
        """Return only owner-confirmed facts for the active business."""
        if self.ai_business_facts is None:
            raise RuntimeError('AI business facts not configured')
        return self.ai_business_facts.snapshot(
            token=self._token(session_token),now=self._now(server_now))

    def get_ai_settings(self, *, session_token, server_now):
        """Read only the caller's OpenAI mode and safe memory preferences."""
        if self.ai_policy is None:
            raise RuntimeError('AI policy not configured')
        token=self._token(session_token)
        now=self._now(server_now)
        mode=self.ai_policy.get_mode(token=token,now=now)
        memory=self.ai_policy.get_memory(token=token,now=now)
        if (mode['tenant_id']!=memory['tenant_id'] or
                mode['subject_id']!=memory['subject_id']):
            raise PermissionError('AI settings scope mismatch')
        return {'tenant_id':mode['tenant_id'],'provider':'openai',
                'mode':mode['mode'],
                'own_key_configured':mode['own_key_configured'],
                'memory':memory['memory'],
                'key_exposed':False,'publishing_enabled':False}

    def edit_ai_draft_component(self, *, session_token, server_now,
                                draft_id, target, revised_text,
                                expected_revision):
        """Manually edit exactly one private, unpublished AI draft component.

        No model call, tenant selection, media upload or publish authorization.
        """
        if self.ai_content_drafts is None:
            raise RuntimeError('AI draft store not configured')
        return self.ai_content_drafts.revise(
            token=self._token(session_token),now=self._now(server_now),
            draft_id=draft_id,target=target,revised_text=revised_text,
            expected_revision=expected_revision)

    def list_ai_content_drafts(self, *, session_token, server_now):
        """Read only the authenticated user's drafts in the active business."""
        if self.ai_content_drafts is None:
            raise RuntimeError('AI Content Studio not configured')
        return self.ai_content_drafts.list_mine(
            token=self._token(session_token),now=self._now(server_now))

    def get_team_overview(self, *, session_token, server_now):
        """Owner-only counts for current business; no member IDs or email leaks."""
        token=self._token(session_token)
        now=self._now(server_now)
        dashboard=self.dashboard
        session=dashboard.sessions.resolve_current(
            token,directory=dashboard.directory,now=now)
        if session is None:
            raise PermissionError('BAM session required')
        tenant=session.principal.tenant_id
        actual=dashboard.directory.resolve(
            tenant,session.principal.subject_id)
        require_permission(actual,Action.MANAGE_TEAM,Resource(tenant))
        roles={'owner':0,'marketing_manager':0,'content_creator':0,
               'employee':0,'viewer':0}
        rows=dashboard.directory.db.execute(
            """SELECT role,active,COUNT(*) FROM members WHERE tenant_id=?
               GROUP BY role,active""",(tenant,)).fetchall()
        inactive=0
        for role,active,count in rows:
            if (role not in roles or type(count) is not int or count<0
                    or active not in (0,1)):
                raise RuntimeError('Invalid stored team membership')
            if active==1:
                roles[role]+=count
            else:
                inactive+=count
        if roles['owner']<1:
            raise RuntimeError('Owner membership missing')
        return {'tenant_id':tenant,'roles':roles,
                'active_members':sum(roles.values()),
                'inactive_members':inactive,
                'invitation_status':'not_connected',
                'publishing_enabled':False}

    def get_social_connections(self, *, session_token, server_now):
        """Read current-business connection status metadata, never provider secrets.

        The underlying connection directory independently requires READ_ANALYTICS.
        This is not an OAuth exchange or a publishing eligibility check.
        """
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        tenant=session.principal.tenant_id
        response=self.dashboard.social_connections.list_connections(
            token=token,tenant_id=tenant,now=now)
        if (type(response) is not dict or response.get('tenant_id')!=tenant
                or response.get('publishing_enabled') is not False
                or type(response.get('connections')) is not list
                or len(response['connections'])>250):
            raise RuntimeError('Invalid social connection directory')
        allowed_states={'pending','connected','refresh_required','revoked','expired'}
        results=[]
        seen=set()
        for row in response['connections']:
            if (type(row) is not dict
                    or set(row)!={'platform','account_id','status','scope',
                                   'updated_at','expires_at','publishing_enabled'}
                    or any(type(row[key]) is not str or not row[key].strip()
                           or len(row[key])>128
                           for key in ('platform','account_id','scope'))
                    or 'write' in row['scope'].lower()
                    or 'publish' in row['scope'].lower()
                    or row['status'] not in allowed_states
                    or type(row['updated_at']) is not int or row['updated_at']<0
                    or (row['expires_at'] is not None
                        and (type(row['expires_at']) is not int
                             or row['expires_at']<0))
                    or row['publishing_enabled'] is not False):
                raise RuntimeError('Invalid social account metadata')
            key=(row['platform'],row['account_id'])
            if key in seen:
                raise RuntimeError('Duplicate social account metadata')
            seen.add(key)
            results.append({
                'platform':row['platform'],
                'account_id':row['account_id'],
                'status':row['status'],
                'scope':row['scope'],
                'updated_at':row['updated_at'],
                'expires_at':row['expires_at'],
                'publishing_enabled':False})
        return {'tenant_id':tenant,'visibility':'authorized',
                'connections':results,'publishing_enabled':False}

    def get_posting_preferences(self, *, session_token, server_now):
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        if self.posting_preferences is None:
            raise RuntimeError('Posting preferences not configured')
        return self.posting_preferences.get(token=token,
            tenant_id=session.principal.tenant_id,now=now)

    def get_posting_time_preview(self, *, session_token, server_now):
        """Propose informational next-week slots; never schedule or publish."""
        now=self._now(server_now)
        preferences=self.get_posting_preferences(
            session_token=session_token,server_now=now)
        return build_posting_time_preview(preferences,server_now=now)

    def set_posting_preferences(self, *, session_token, server_now,
                                mode, timezone, manual_times):
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        if self.posting_preferences is None:
            raise RuntimeError('Posting preferences not configured')
        return self.posting_preferences.set(token=token,
            tenant_id=session.principal.tenant_id,mode=mode,
            timezone=timezone,manual_times=manual_times,now=now)

    def logout(self, *, session_token, server_now):
        token=self._token(session_token)
        self._now(server_now)
        self.dashboard.sessions.revoke(token,now=server_now)
        return {'signed_out':True,'publishing_enabled':False}

    def logout_everywhere(self, *, session_token, server_now):
        """Revoke only the authenticated identity's sessions across businesses."""
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        count=self.dashboard.sessions.revoke_identity(
            session.principal.subject_id,now=now)
        return {'signed_out':True,'sessions_revoked':count,
                'publishing_enabled':False}

    def list_held_drafts(self, *, session_token, server_now, status=None):
        """List authorized tenant drafts, including postponed/unavailable.

        Never expose attachment storage references or vault credentials.
        """
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        if status is not None and status not in (
                'needs_content','ready_for_review','postponed','unavailable'):
            raise ValueError('Invalid draft status')
        service=self.dashboard.content_service
        if service is None:
            raise RuntimeError('Content Requests not configured')
        requests=service.list_for_business(token=token,
            tenant_id=session.principal.tenant_id,status=status,now=now)
        return {'tenant_id':session.principal.tenant_id,
            'drafts':[{
                'request_id':request['request_id'],
                'channel':request['channel'],
                'draft_text':request['draft_text'],
                'suggestion':request['suggestion'],
                'status':request['status'],
                'missing_items':[item for item in request['required_items']
                                 if item not in request['provided_items']],
                'priority':request['priority'],
                'revision':request['revision']
            } for request in requests],
            'publishing_enabled':False}

    def create_local_service_draft(self, *, session_token, server_now,
                                   platform, include_image_prompt):
        """Explicit owner-confirmed service spotlight with no OpenAI calls."""
        return self._create_local_spotlight(
            session_token=session_token,server_now=server_now,
            platform=platform,include_image_prompt=include_image_prompt,
            kind='service')

    def create_local_product_draft(self, *, session_token, server_now,
                                   platform, include_image_prompt):
        """Explicit zero-OpenAI-call product draft from confirmed owner facts.

        No client-supplied facts, tenant, model or publication claims.
        """
        return self._create_local_spotlight(
            session_token=session_token,server_now=server_now,
            platform=platform,include_image_prompt=include_image_prompt,
            kind='product')

    def _create_local_spotlight(self, *, session_token, server_now,
                                platform, include_image_prompt, kind):
        if kind not in ('product','service'):
            raise ValueError('Unsupported local template')
        token=self._token(session_token)
        now=self._now(server_now)
        if self.ai_business_facts is None or self.ai_content_drafts is None or self.ai_policy is None:
            raise RuntimeError('Local draft services unavailable')
        snapshot=self.ai_business_facts.snapshot(token=token,now=now)
        if snapshot['provenance']!='owner_confirmed':
            raise ValueError('Owner-confirmed business facts required')
        template=LocalDraftTemplates(
            request_builder=AIDraftRequestBuilder(policy_store=self.ai_policy))
        local=(template.product_spotlight if kind=='product'
               else template.service_spotlight)(
            token=token,now=now,verified_facts=snapshot['facts'],
            platform=platform,include_image_prompt=include_image_prompt)
        if local['tenant_id']!=snapshot['tenant_id'] or local['openai_requests']!=0:
            raise RuntimeError('Unsafe local draft provenance')
        staged=self.ai_content_drafts.stage(
            token=token,now=now,platform=platform,
            response={'post_text':local['post_text'],
                      'image_prompt':local['image_prompt']},
            include_image_prompt=include_image_prompt,
            needs_media=include_image_prompt)
        if staged['tenant_id']!=snapshot['tenant_id']:
            raise RuntimeError('Local draft business mismatch')
        return {**staged,'generation_method':'local_template',
                'openai_requests':0}

    def revise_held_draft(self, *, session_token, server_now,
                          request_id, target, revised_text, expected_revision):
        """Revise one unpublished held draft field, never approve or publish."""
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        service=self.dashboard.content_service
        if service is None:
            raise RuntimeError('Content Requests not configured')
        updated=service.revise(token=token,
            tenant_id=session.principal.tenant_id,
            request_id=request_id,target=target,
            revised_text=revised_text,
            expected_revision=expected_revision,now=now)
        return {'tenant_id':session.principal.tenant_id,
                'request_id':request_id,'status':updated['status'],
                'revision':updated['revision'],
                'publishing_enabled':False}

    def create_held_draft(self, *, session_token, server_now,
                          channel, draft_text, suggestion, required_items,
                          priority=0):
        """Create a business-scoped content request, never a scheduled post."""
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        service=self.dashboard.content_service
        if service is None:
            raise RuntimeError('Content Requests not configured')
        if (not isinstance(channel,str) or channel not in
                ('facebook','instagram','linkedin','pinterest','tiktok','youtube')):
            raise ValueError('Unsupported content channel')
        for value in (draft_text,suggestion):
            if not isinstance(value,str) or not value.strip() or len(value)>2000:
                raise ValueError('Invalid draft or content suggestion')
        if (not isinstance(required_items,list) or not 1<=len(required_items)<=12
                or any(not isinstance(item,str) or not item.strip()
                       or len(item)>80 for item in required_items)
                or len(set(required_items))!=len(required_items)):
            raise ValueError('Invalid required content items')
        if type(priority) is not int or not -10<=priority<=10:
            raise ValueError('Invalid priority')
        request_id=service.create(token=token,tenant_id=session.principal.tenant_id,
            channel=channel,draft_text=draft_text,suggestion=suggestion,
            required_items=required_items,priority=priority,now=now)
        return {'tenant_id':session.principal.tenant_id,
                'request_id':request_id,'status':'needs_content',
                'publishing_enabled':False}

    def begin_content_upload_preflight(self, *, session_token, server_now,
                                       request_id, item, media_type, sha256,
                                       byte_count):
        """Register pending-only, tenant-scoped metadata. No bytes or upload URL.

        Requires a separately trusted object-store integration and scanner
        before any media can be supplied to a held content request.
        """
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        service=self.dashboard.content_service
        if service is None:
            raise RuntimeError('Content Requests not configured')
        preflight=ContentUploadPreflight(service=service)
        result=preflight.begin(token=token,
            tenant_id=session.principal.tenant_id,
            request_id=request_id,item=item,media_type=media_type,
            sha256=sha256,byte_count=byte_count,now=now)
        if result.get('status')!='pending' or result.get('upload_url') is not None:
            raise RuntimeError('Unsafe upload metadata result')
        return {'tenant_id':session.principal.tenant_id,
                'request_id':request_id,'item':item,
                'attachment_id':result['attachment_id'],
                'status':'pending','max_bytes':result['max_bytes'],
                'upload_url':None,'publishing_enabled':False}

    def supply_verified_content(self, *, session_token, server_now,
                                request_id, item, attachment_id):
        """Attach already-scanned and permission-verified content.

        This API does not upload or validate files. The attachment registry's
        trusted validation worker must approve an item before it can be used.
        """
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        if (not isinstance(request_id,str) or len(request_id)!=32
                or any(c not in '0123456789abcdef' for c in request_id)):
            raise ValueError('Invalid request ID')
        if not isinstance(item,str) or not item.strip() or len(item)>80:
            raise ValueError('Invalid required item')
        if (not isinstance(attachment_id,str) or len(attachment_id)!=32
                or any(c not in '0123456789abcdef' for c in attachment_id)):
            raise ValueError('Invalid verified attachment ID')
        service=self.dashboard.content_service
        if service is None:
            raise RuntimeError('Content Requests not configured')
        status=service.provide(token=token,
            tenant_id=session.principal.tenant_id,request_id=request_id,
            item=item,attachment_id=attachment_id,now=now)
        return {'tenant_id':session.principal.tenant_id,
                'request_id':request_id,'status':status,
                'publishing_enabled':False}

    def update_draft_hold(self, *, session_token, server_now, request_id, status):
        """Postpone, mark unavailable or reopen an incomplete draft."""
        token=self._token(session_token)
        now=self._now(server_now)
        session=self.dashboard.sessions.resolve_current(
            token,directory=self.dashboard.directory,now=now)
        if session is None:
            raise PermissionError('Valid BAM session required')
        service=self.dashboard.content_service
        if service is None:
            raise RuntimeError('Content Requests not configured')
        if (not isinstance(request_id,str) or len(request_id)!=32
                or any(char not in '0123456789abcdef' for char in request_id)):
            raise ValueError('Invalid request ID')
        if status not in ('postponed','unavailable','needs_content'):
            raise ValueError('Invalid hold status')
        result=service.set_hold(token=token,tenant_id=session.principal.tenant_id,
                                request_id=request_id,status=status,now=now)
        return {'tenant_id':session.principal.tenant_id,'request_id':request_id,
                'status':result,'publishing_enabled':False}
