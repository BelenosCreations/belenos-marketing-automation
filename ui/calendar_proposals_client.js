/* Calendar proposals are *not* scheduled or approved posts. */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMCalendarProposalsClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const id=/^[a-f0-9]{32}$/;
 const bearer=/^[A-Za-z0-9_-]{32,2048}$/;
 const utc=/^\d{4}-\d\d-\d\dT(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\+00:00$/;
 const date=/^\d{4}-\d\d-\d\d$/;
 const clock=/^(?:[01]\d|2[0-3]):[0-5]\d$/;
 function exact(value,keys){
  return value!==null&&typeof value==='object'&&!Array.isArray(value)&&
   Object.keys(value).length===keys.length&&
   keys.every(key=>Object.prototype.hasOwnProperty.call(value,key));
 }
 function context({origin,fetchImpl,token,expectedTenantId}){
  if(typeof origin!=='string'||
     !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
     typeof fetchImpl!=='function'||!bearer.test(token)||
     typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
     expectedTenantId.length>128)
    throw new TypeError('Trusted BAM calendar session required');
 }
 async function request(options,method,body){
  context(options);
  const response=await options.fetchImpl(
    options.origin+'/api/v1/calendar-proposals',{
      method,mode:'same-origin',credentials:'omit',cache:'no-store',
      redirect:'error',headers:{Authorization:'Bearer '+options.token,
       Accept:'application/json',
       ...(body===null?{}:{'Content-Type':'application/json'})},
      ...(body===null?{}:{body:JSON.stringify(body)})
    });
  if(!response||!response.ok||
     response.status!==(method==='POST'?201:200))
    throw new Error('Private calendar request unavailable');
  return response.json();
 }
 function safeEnvelope(value,tenant,keys){
  if(!exact(value,keys)||value.tenant_id!==tenant||
     value.status!=='proposal_only'||value.posts_scheduled!==0||
     value.publishing_enabled!==false)
    throw new TypeError('Untrusted calendar proposal response');
 }
 async function list(options){
  const body=await request(options,'GET',null);
  safeEnvelope(body,options.expectedTenantId,
    ['tenant_id','status','items','posts_scheduled','publishing_enabled']);
  if(!Array.isArray(body.items)||body.items.length>200)
   throw new TypeError('Invalid private proposal list');
  let previous='';
  const entries=body.items.map(row=>{
    if(!exact(row,['request_id','draft_revision','current_revision',
      'utc_at','local_date','local_time','timezone','content_changed',
      'slot_current','publishing_enabled'])||
      !id.test(row.request_id)||
      !Number.isSafeInteger(row.draft_revision)||row.draft_revision<1||
      (row.current_revision!==null&&
       (!Number.isSafeInteger(row.current_revision)||row.current_revision<1))||
      typeof row.utc_at!=='string'||!utc.test(row.utc_at)||
      typeof row.local_date!=='string'||!date.test(row.local_date)||
      typeof row.local_time!=='string'||!clock.test(row.local_time)||
      typeof row.timezone!=='string'||!row.timezone.trim()||
      row.timezone.length>80||
      typeof row.content_changed!=='boolean'||
      typeof row.slot_current!=='boolean'||
      row.publishing_enabled!==false||
      (previous&&previous>row.utc_at))
      throw new TypeError('Untrusted proposal item');
    previous=row.utc_at;
    return Object.freeze({
      requestId:row.request_id,draftRevision:row.draft_revision,
      currentRevision:row.current_revision,utcAt:row.utc_at,
      localDate:row.local_date,localTime:row.local_time,
      timezone:row.timezone,contentChanged:row.content_changed,
      slotCurrent:row.slot_current,publishingEnabled:false});
  });
  return Object.freeze({tenantId:body.tenant_id,
    items:Object.freeze(entries),
    status:'proposal_only',postsScheduled:0,publishingEnabled:false});
 }
 async function propose(options){
  const {requestId,expectedRevision,utcAt}=options;
  if(!id.test(requestId)||!Number.isSafeInteger(expectedRevision)||
     expectedRevision<1||typeof utcAt!=='string'||!utc.test(utcAt))
    throw new TypeError('Current draft and trusted future slot required');
  const result=await request(options,'POST',{
    request_id:requestId,expected_revision:expectedRevision,utc_at:utcAt});
  safeEnvelope(result,options.expectedTenantId,
    ['tenant_id','request_id','utc_at','status',
     'posts_scheduled','publishing_enabled']);
  if(result.request_id!==requestId||result.utc_at!==utcAt)
    throw new TypeError('Proposal mismatch');
  return Object.freeze({tenantId:result.tenant_id,
    requestId,utcAt,status:'proposal_only',
    postsScheduled:0,publishingEnabled:false});
 }
 async function discard(options){
  const {requestId}=options;
  if(!id.test(requestId))throw new TypeError('Valid draft ID required');
  const result=await request(options,'DELETE',{request_id:requestId});
  safeEnvelope(result,options.expectedTenantId,
    ['tenant_id','request_id','removed','status',
     'posts_scheduled','publishing_enabled']);
  if(result.request_id!==requestId||
     !Number.isSafeInteger(result.removed)||
     ![0,1].includes(result.removed))
    throw new TypeError('Untrusted proposal removal');
  return Object.freeze({tenantId:result.tenant_id,requestId,
    removed:result.removed,status:'proposal_only',
    postsScheduled:0,publishingEnabled:false});
 }
 return Object.freeze({list,propose,discard});
});
