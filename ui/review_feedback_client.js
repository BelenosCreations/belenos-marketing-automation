/* Explicit private editorial notes; no approval, scheduling or publication. */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMReviewFeedbackClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const id=/^[a-f0-9]{32}$/;
 const bearer=/^[A-Za-z0-9_-]{32,2048}$/;
 const endpoint='/api/v1/review-feedback';
 function exact(x,keys){
  return x!==null&&typeof x==='object'&&!Array.isArray(x)&&
   Object.keys(x).length===keys.length&&
   keys.every(k=>Object.prototype.hasOwnProperty.call(x,k));
 }
 function context(options){
  const {origin,fetchImpl,token,expectedTenantId}=options||{};
  if(typeof origin!=='string'||
     !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
     typeof fetchImpl!=='function'||typeof token!=='string'||
     !bearer.test(token)||typeof expectedTenantId!=='string'||
     !expectedTenantId.trim()||expectedTenantId.length>128)
    throw new TypeError('Active trusted business feedback session required');
 }
 async function request(options,method,payload){
  context(options);
  const response=await options.fetchImpl(options.origin+endpoint,{
   method,mode:'same-origin',credentials:'omit',redirect:'error',
   cache:'no-store',headers:{
    Authorization:'Bearer '+options.token,Accept:'application/json',
    ...(payload===null?{}:{'Content-Type':'application/json'})},
   ...(payload===null?{}:{body:JSON.stringify(payload)})
  });
  if(!response||!response.ok||response.status!==200)
   throw new Error('Private feedback request unavailable; refresh required');
  return response.json();
 }
 function envelope(data,tenant,fields){
  if(!exact(data,fields)||data.tenant_id!==tenant||
     data.status!=='feedback_only'||data.approval_granted!==false||
     data.publishing_enabled!==false)
    throw new TypeError('Unsafe review feedback response');
 }
 function validNote(value){
  return typeof value==='string'&&value.length>=1&&value.length<=1000&&
   value.trim()===value&&
   ![...value].some(char=>char.charCodeAt(0)<32&&
                      char!=='\n'&&char!=='\t');
 }
 async function list(options){
  const data=await request(options,'GET',null);
  envelope(data,options.expectedTenantId,
   ['tenant_id','status','items','approval_granted','publishing_enabled']);
  if(!Array.isArray(data.items)||data.items.length>200)
   throw new TypeError('Unsafe private feedback list');
  const seen=new Set();
  const items=data.items.map(row=>{
   if(!exact(row,['request_id','draft_revision','current_revision','stale',
        'note','feedback_token','updated_at','approval_granted',
        'publishing_enabled'])||
      typeof row.request_id!=='string'||!id.test(row.request_id)||
      seen.has(row.request_id)||!id.test(row.feedback_token)||
      !Number.isSafeInteger(row.draft_revision)||row.draft_revision<1||
      !Number.isSafeInteger(row.current_revision)||row.current_revision<1||
      typeof row.stale!=='boolean'||
      row.stale!==(row.current_revision!==row.draft_revision)||
      !validNote(row.note)||!Number.isSafeInteger(row.updated_at)||
      row.updated_at<0||row.approval_granted!==false||
      row.publishing_enabled!==false)
    throw new TypeError('Unsafe individual review feedback');
   seen.add(row.request_id);
   return Object.freeze({
    requestId:row.request_id,draftRevision:row.draft_revision,
    currentRevision:row.current_revision,stale:row.stale,
    note:row.note,feedbackToken:row.feedback_token,
    updatedAt:row.updated_at,approvalGranted:false,
    publishingEnabled:false});
  });
  return Object.freeze({tenantId:data.tenant_id,status:'feedback_only',
   items:Object.freeze(items),approvalGranted:false,publishingEnabled:false});
 }
 async function save(options){
  const {requestId,expectedRevision,expectedFeedbackToken,note}=options||{};
  if(typeof requestId!=='string'||!id.test(requestId)||
     !Number.isSafeInteger(expectedRevision)||expectedRevision<1||
     !(expectedFeedbackToken===null||
       (typeof expectedFeedbackToken==='string'&&id.test(expectedFeedbackToken)))||
     !validNote(note))
    throw new TypeError('Current draft, feedback version and note required');
  const data=await request(options,'PUT',{
   request_id:requestId,expected_revision:expectedRevision,
   expected_feedback_token:expectedFeedbackToken,note});
  envelope(data,options.expectedTenantId,
   ['tenant_id','request_id','draft_revision','feedback_token',
    'status','approval_granted','publishing_enabled']);
  if(data.request_id!==requestId||
     data.draft_revision!==expectedRevision||
     typeof data.feedback_token!=='string'||!id.test(data.feedback_token))
    throw new TypeError('Untrusted saved review feedback');
  return Object.freeze({requestId,revision:expectedRevision,
   feedbackToken:data.feedback_token,tenantId:data.tenant_id,
   approvalGranted:false,publishingEnabled:false});
 }
 async function discard(options){
  const {requestId,expectedFeedbackToken}=options||{};
  if(typeof requestId!=='string'||!id.test(requestId)||
     typeof expectedFeedbackToken!=='string'||!id.test(expectedFeedbackToken))
    throw new TypeError('Current feedback version required');
  const data=await request(options,'DELETE',{
   request_id:requestId,expected_feedback_token:expectedFeedbackToken});
  envelope(data,options.expectedTenantId,
   ['tenant_id','request_id','removed','status',
    'approval_granted','publishing_enabled']);
  if(data.request_id!==requestId||data.removed!==1)
   throw new TypeError('Untrusted feedback removal');
  return Object.freeze({requestId,removed:1,
   tenantId:data.tenant_id,approvalGranted:false,publishingEnabled:false});
 }
 return Object.freeze({list,save,discard});
});
