/* Owner-only pending invitation preview/cancellation. No sending, enrollment,
 * activation, invitation bearer token, persistence or publish operation.
 * Feature must stay opt-in until trusted server delivery is configured.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMTeamInvitationsClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const token=/^[A-Za-z0-9_-]{32,2048}$/;
  const id=/^[a-f0-9]{32}$/;
  const roles=new Set(['marketing_manager','content_creator','employee','viewer']);
  function exact(obj,keys){
    return obj!==null&&typeof obj==='object'&&!Array.isArray(obj)&&
      Object.keys(obj).length===keys.length&&
      keys.every(key=>Object.prototype.hasOwnProperty.call(obj,key));
  }
  function context(options){
    if(!options||typeof options.origin!=='string'||
       !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(options.origin)||
       typeof options.fetchImpl!=='function'||!token.test(options.token)||
       typeof options.expectedTenantId!=='string'||
       !options.expectedTenantId.trim()||
       options.expectedTenantId.length>128)
      throw new TypeError('Current owner session required');
  }
  async function list(options){
    context(options);
    const res=await options.fetchImpl(options.origin+'/api/v1/team/invitations',{
      method:'GET',mode:'same-origin',credentials:'omit',cache:'no-store',
      redirect:'error',headers:{Authorization:'Bearer '+options.token,
                               Accept:'application/json'}
    });
    if(!res||!res.ok)throw new Error('Invitation preview not configured');
    const body=await res.json();
    if(!exact(body,['tenant_id','status','items','publishing_enabled'])||
       body.tenant_id!==options.expectedTenantId||
       body.status!=='private_pending_invitations'||
       body.publishing_enabled!==false||
       !Array.isArray(body.items)||body.items.length>50)
      throw new TypeError('Untrusted invitation preview');
    const seen=new Set();
    const items=body.items.map(item=>{
      if(!exact(item,['invitation_id','email','role','expires_at'])||
         !id.test(item.invitation_id)||seen.has(item.invitation_id)||
         typeof item.email!=='string'||!item.email.includes('@')||
         !roles.has(item.role)||!Number.isSafeInteger(item.expires_at)||
         item.expires_at<0)
        throw new TypeError('Invalid invitation preview item');
      seen.add(item.invitation_id);
      return Object.freeze({id:item.invitation_id,
        email:item.email,role:item.role,expiresAt:item.expires_at});
    });
    return Object.freeze({tenantId:body.tenant_id,
      items:Object.freeze(items),publishingEnabled:false});
  }
  async function cancel(options){
    context(options);
    if(!id.test(options.invitationId))
      throw new TypeError('Invitation identifier required');
    const res=await options.fetchImpl(
      options.origin+'/api/v1/team/invitations/cancel',{
      method:'POST',mode:'same-origin',credentials:'omit',cache:'no-store',
      redirect:'error',
      headers:{Authorization:'Bearer '+options.token,Accept:'application/json',
               'Content-Type':'application/json'},
      body:JSON.stringify({invitation_id:options.invitationId})
    });
    if(!res||!res.ok)throw new Error('Invitation cancellation not confirmed');
    const body=await res.json();
    if(!exact(body,['tenant_id','invitation_id','status','publishing_enabled'])||
       body.tenant_id!==options.expectedTenantId||
       body.invitation_id!==options.invitationId||
       body.status!=='cancelled'||body.publishing_enabled!==false)
      throw new TypeError('Untrusted cancellation response');
    return Object.freeze({tenantId:body.tenant_id,
      invitationId:body.invitation_id,cancelled:true,publishingEnabled:false});
  }
  async function history(options){
    context(options);
    const res=await options.fetchImpl(
      options.origin+'/api/v1/team/invitations/activity',{
      method:'GET',mode:'same-origin',credentials:'omit',cache:'no-store',
      redirect:'error',headers:{Authorization:'Bearer '+options.token,
                               Accept:'application/json'}
    });
    if(!res||!res.ok)throw new Error('Private invitation history unavailable');
    const body=await res.json();
    if(!exact(body,['tenant_id','status','events','publishing_enabled'])||
       body.tenant_id!==options.expectedTenantId||
       body.status!=='private_invitation_activity'||
       body.publishing_enabled!==false||
       !Array.isArray(body.events)||body.events.length>30)
      throw new TypeError('Untrusted invitation history');
    const seen=new Set();
    const events=body.events.map(row=>{
      if(!exact(row,['invitation_id','action','occurred_at'])||
         !id.test(row.invitation_id)||
         !['delivered','delivery_failed','cancelled','accepted']
           .includes(row.action)||
         !Number.isSafeInteger(row.occurred_at)||row.occurred_at<0||
         seen.has(row.invitation_id+':'+row.action))
        throw new TypeError('Invalid invitation activity');
      seen.add(row.invitation_id+':'+row.action);
      return Object.freeze({invitationId:row.invitation_id,
        action:row.action,occurredAt:row.occurred_at});
    });
    return Object.freeze({tenantId:body.tenant_id,
      events:Object.freeze(events),publishingEnabled:false});
  }
  async function issue(options){
    context(options);
    if(typeof options.email!=='string'||
       options.email.length<3||options.email.length>254||
       options.email!==options.email.trim()||
       !/^[^\\s@]+@[^\\s@]+$/.test(options.email)||
       !roles.has(options.role))
      throw new TypeError('Valid invitation recipient and non-owner role required');
    const res=await options.fetchImpl(
      options.origin+'/api/v1/team/invitations/create',{
      method:'POST',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{Authorization:'Bearer '+options.token,
               Accept:'application/json',
               'Content-Type':'application/json'},
      body:JSON.stringify({email:options.email,role:options.role})
    });
    if(!res||!res.ok)
      throw new Error('Invitation creation not confirmed');
    const body=await res.json();
    if(!exact(body,['tenant_id','invitation_created','invitation_id',
                    'expires_at','publishing_enabled'])||
       body.tenant_id!==options.expectedTenantId||
       body.invitation_created!==true||
       !id.test(body.invitation_id)||
       !Number.isSafeInteger(body.expires_at)||body.expires_at<0||
       body.publishing_enabled!==false)
      throw new TypeError('Untrusted invitation creation receipt');
    return Object.freeze({tenantId:body.tenant_id,
      invitationId:body.invitation_id,expiresAt:body.expires_at,
      issued:true,publishingEnabled:false});
  }
  return Object.freeze({list,cancel,history,issue});
});
