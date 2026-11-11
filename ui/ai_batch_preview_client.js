/* Zero-provider-call future draft topic planning; no billing, queue or publish. */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMAIBatchPreviewClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const bearer=/^[A-Za-z0-9_-]{32,2048}$/;
 const platforms=new Set(['facebook','instagram','linkedin',
                          'pinterest','tiktok','youtube']);
 function exact(value,keys){
   return value!==null&&typeof value==='object'&&!Array.isArray(value)&&
      Object.keys(value).length===keys.length&&
      keys.every(key=>Object.prototype.hasOwnProperty.call(value,key));
 }
 function validTopics(topics){
   return Array.isArray(topics)&&topics.length>=1&&topics.length<=14&&
     topics.every(t=>typeof t==='string'&&t.trim()===t&&!!t&&t.length<=300)&&
     new Set(topics.map(t=>t.toLocaleLowerCase())).size===topics.length;
 }
 async function preview({origin,fetchImpl,token,expectedTenantId,topics,
                         platform,includeImagePrompt}){
   if(typeof origin!=='string'||
      !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
      typeof fetchImpl!=='function'||!bearer.test(token)||
      typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
      expectedTenantId.length>128||!validTopics(topics)||
      !platforms.has(platform)||typeof includeImagePrompt!=='boolean')
     throw new TypeError('Trusted BAM advance plan request required');
   const response=await fetchImpl(origin+'/api/v1/ai/batch-preview',{
     method:'POST',mode:'same-origin',credentials:'omit',cache:'no-store',
     redirect:'error',headers:{Authorization:'Bearer '+token,
       'Content-Type':'application/json',Accept:'application/json'},
     body:JSON.stringify({topics,platform,
       include_image_prompt:includeImagePrompt})
   });
   if(!response||!response.ok||response.status!==200)
     throw new Error('Advance topic plan is not available');
   const result=await response.json();
   if(!exact(result,['tenant_id','mode','fact_revision','fact_provenance',
       'items','planned_individual_requests','provider_requests_made',
       'quota_reserved','actual_cost_known','drafts_created','status',
       'publishing_enabled'])||
      result.tenant_id!==expectedTenantId||
      !['bam_sponsored','own_openai_key'].includes(result.mode)||
      !Number.isSafeInteger(result.fact_revision)||result.fact_revision<1||
      result.fact_provenance!=='owner_confirmed'||
      !Array.isArray(result.items)||result.items.length!==topics.length||
      result.planned_individual_requests!==topics.length||
      result.provider_requests_made!==0||
      result.quota_reserved!==false||
      result.actual_cost_known!==false||
      result.drafts_created!==0||
      result.status!=='planning_only'||
      result.publishing_enabled!==false)
     throw new TypeError('Untrusted advance marketing plan');
   const items=result.items.map((item,i)=>{
     if(!exact(item,['topic','platform','image_prompt_planned'])||
        item.topic!==topics[i]||item.platform!==platform||
        item.image_prompt_planned!==includeImagePrompt)
       throw new TypeError('Plan topic or media mismatch');
     return Object.freeze({topic:item.topic,platform:item.platform,
       imagePromptPlanned:item.image_prompt_planned});
   });
   return Object.freeze({
     tenantId:result.tenant_id,mode:result.mode,
     factRevision:result.fact_revision,
     items:Object.freeze(items),
     plannedIndividualRequests:topics.length,
     providerRequestsMade:0,quotaReserved:false,
     actualCostKnown:false,draftsCreated:0,
     status:'planning_only',publishingEnabled:false
   });
 }
 return Object.freeze({preview,validTopics});
});
