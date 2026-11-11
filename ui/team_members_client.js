/* BAM owner-only team membership client; HTTPS same-origin, no tokens stored.
 * Supports a private owner roster and current-revision changes to existing
 * non-owner members only. No invites, owner grants or publishing.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMTeamMembersClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const token=/^[A-Za-z0-9_-]{32,2048}$/;
  const member=/^[A-Za-z0-9_-]{1,128}$/;
  const roles=new Set(['owner','marketing_manager','content_creator','employee','viewer']);
  const mutable=new Set(['marketing_manager','content_creator','employee','viewer']);
  const exact=(obj,keys)=>obj&&typeof obj==='object'&&!Array.isArray(obj)&&
    Object.keys(obj).length===keys.length&&
    keys.every(k=>Object.prototype.hasOwnProperty.call(obj,k));
  function context(options){
    if(!options||!/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(options.origin)||
       typeof options.fetchImpl!=='function'||!token.test(options.token)||
       typeof options.expectedTenantId!=='string'||
       !options.expectedTenantId.trim()||options.expectedTenantId.length>128)
      throw new TypeError('Current BAM team session required');
  }
  function validateRoster(body,expectedTenantId){
    if(!exact(body,['tenant_id','status','members','publishing_enabled'])||
       body.tenant_id!==expectedTenantId||
       body.status!=='private_team_preview'||body.publishing_enabled!==false||
       !Array.isArray(body.members)||body.members.length<1||body.members.length>200)
      throw new TypeError('Untrusted private team roster');
    const found=new Set();let self=0;
    const items=body.members.map(m=>{
      if(!exact(m,['member_id','role','active','revision','email','is_self'])||
         !member.test(m.member_id)||found.has(m.member_id)||
         !roles.has(m.role)||typeof m.active!=='boolean'||
         !Number.isSafeInteger(m.revision)||m.revision<1||
         (m.email!==null&&(typeof m.email!=='string'||
                           m.email.length>254))||
         typeof m.is_self!=='boolean'||
         (m.is_self&&(!m.active||m.role!=='owner')))
        throw new TypeError('Untrusted business member');
      found.add(m.member_id);
      if(m.is_self)self++;
      return Object.freeze({id:m.member_id,role:m.role,
        active:m.active,revision:m.revision,
        email:m.email,isSelf:m.is_self});
    });
    if(self!==1)throw new TypeError('Invalid owner roster');
    return Object.freeze({tenantId:body.tenant_id,
      members:Object.freeze(items),publishingEnabled:false});
  }
  async function list(options){
    context(options);
    const response=await options.fetchImpl(
      options.origin+'/api/v1/team/members',{
      method:'GET',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{Authorization:'Bearer '+options.token,
        Accept:'application/json'}
    });
    if(!response||!response.ok)throw new Error('Private team roster unavailable');
    return validateRoster(await response.json(),options.expectedTenantId);
  }
  function validateActivity(body,expectedTenantId){
    if(!exact(body,['tenant_id','status','events','publishing_enabled'])||
       body.tenant_id!==expectedTenantId||
       body.status!=='private_team_activity'||body.publishing_enabled!==false||
       !Array.isArray(body.events)||body.events.length>30)
      throw new TypeError('Untrusted private team activity');
    let previous=null;
    const events=body.events.map(item=>{
      if(!exact(item,['event_id','member_id','actor_id','previous_role',
                      'resulting_role','action','changed_at','revision_after'])||
         !Number.isSafeInteger(item.event_id)||item.event_id<1||
         (previous!==null&&item.event_id>=previous)||
         !member.test(item.member_id)||!member.test(item.actor_id)||
         !roles.has(item.previous_role)||!roles.has(item.resulting_role)||
         !['change_role','deactivate'].includes(item.action)||
         (item.action==='deactivate'&&
          item.previous_role!==item.resulting_role)||
         (item.action==='change_role'&&
          item.previous_role===item.resulting_role)||
         !Number.isSafeInteger(item.changed_at)||item.changed_at<0||
         !Number.isSafeInteger(item.revision_after)||item.revision_after<2)
        throw new TypeError('Untrusted team change event');
      previous=item.event_id;
      return Object.freeze({id:item.event_id,memberId:item.member_id,
        actorId:item.actor_id,fromRole:item.previous_role,
        toRole:item.resulting_role,action:item.action,
        changedAt:item.changed_at,revision:item.revision_after});
    });
    return Object.freeze({tenantId:body.tenant_id,
      events:Object.freeze(events),publishingEnabled:false});
  }
  async function activity(options){
    context(options);
    const response=await options.fetchImpl(
      options.origin+'/api/v1/team/activity',{
      method:'GET',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{Authorization:'Bearer '+options.token,
        Accept:'application/json'}
    });
    if(!response||!response.ok)
      throw new Error('Private team history unavailable');
    return validateActivity(await response.json(),options.expectedTenantId);
  }
  async function change(options){
    context(options);
    const {memberId,action,role,expectedRevision}=options;
    if(!member.test(memberId)||
       !['change_role','deactivate'].includes(action)||
       !Number.isSafeInteger(expectedRevision)||expectedRevision<1||
       (action==='change_role'?!mutable.has(role):role!==undefined))
      throw new TypeError('Invalid team membership change');
    const body={member_id:memberId,action,expected_revision:expectedRevision};
    if(action==='change_role')body.role=role;
    const response=await options.fetchImpl(
      options.origin+'/api/v1/team/membership',{
      method:'POST',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{Authorization:'Bearer '+options.token,
        Accept:'application/json','Content-Type':'application/json'},
      body:JSON.stringify(body)
    });
    if(!response||!response.ok)throw new Error('Membership change not confirmed');
    const result=await response.json();
    if(!exact(result,['tenant_id','member_id','status','revision',
                     'sessions_revoked','publishing_enabled'])||
       result.tenant_id!==options.expectedTenantId||
       result.member_id!==memberId||
       result.status!==(action==='deactivate'?'deactivated':'updated')||
       result.revision!==expectedRevision+1||
       !Number.isSafeInteger(result.sessions_revoked)||
       result.sessions_revoked<0||result.sessions_revoked>100000||
       result.publishing_enabled!==false)
      throw new TypeError('Untrusted team update result');
    return Object.freeze({tenantId:result.tenant_id,
      memberId:result.member_id,status:result.status,
      revision:result.revision,sessionsRevoked:result.sessions_revoked,
      publishingEnabled:false});
  }
  return Object.freeze({list,activity,change});
});
