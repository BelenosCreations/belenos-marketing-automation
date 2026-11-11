/* Owner/manager-only review-note activity; metadata, never note bodies. */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMReviewFeedbackHistoryClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const id=/^[a-f0-9]{32}$/;
 const bearer=/^[A-Za-z0-9_-]{32,2048}$/;
 function exact(x,keys){
  return x!==null&&typeof x==='object'&&!Array.isArray(x)&&
    Object.keys(x).length===keys.length&&
    keys.every(key=>Object.prototype.hasOwnProperty.call(x,key));
 }
 async function read({origin,fetchImpl,token,expectedTenantId}){
  if(typeof origin!=='string'||
    !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
    typeof fetchImpl!=='function'||typeof token!=='string'||
    !bearer.test(token)||typeof expectedTenantId!=='string'||
    !expectedTenantId.trim()||expectedTenantId.length>128)
    throw new TypeError('Trusted reviewer history session required');
  const response=await fetchImpl(
    origin+'/api/v1/review-feedback-history',{
      method:'GET',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{Authorization:'Bearer '+token,Accept:'application/json'}
    });
  if(!response||!response.ok||response.status!==200)
    throw new Error('Private review history unavailable');
  const result=await response.json();
  if(!exact(result,['tenant_id','status','events','truncated',
        'approval_granted','publishing_enabled'])||
     result.tenant_id!==expectedTenantId||
     result.status!=='feedback_history_only'||
     !Array.isArray(result.events)||result.events.length>50||
     typeof result.truncated!=='boolean'||
     (result.truncated&&result.events.length!==50)||
     result.approval_granted!==false||
     result.publishing_enabled!==false)
    throw new TypeError('Untrusted review history response');
  const seen=new Set();
  let previous=null;
  const events=result.events.map(event=>{
    if(!exact(event,['event_id','request_id','action',
                      'draft_revision','occurred_at'])||
       typeof event.event_id!=='string'||!id.test(event.event_id)||
       seen.has(event.event_id)||
       typeof event.request_id!=='string'||!id.test(event.request_id)||
       !['created','updated','removed'].includes(event.action)||
       !Number.isSafeInteger(event.draft_revision)||event.draft_revision<1||
       !Number.isSafeInteger(event.occurred_at)||event.occurred_at<0||
       (previous!==null&&previous<event.occurred_at))
       throw new TypeError('Untrusted private review event');
    seen.add(event.event_id);previous=event.occurred_at;
    return Object.freeze({
      eventId:event.event_id,requestId:event.request_id,
      action:event.action,draftRevision:event.draft_revision,
      occurredAt:event.occurred_at
    });
  });
  return Object.freeze({tenantId:result.tenant_id,
    status:'feedback_history_only',
    events:Object.freeze(events),truncated:result.truncated,
    approvalGranted:false,publishingEnabled:false});
 }
 return Object.freeze({read});
});
