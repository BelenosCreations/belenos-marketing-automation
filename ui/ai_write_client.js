/* Explicit-action AI write client; no background generation or auto-retry.
 * Session tokens and idempotency keys must be supplied by authenticated shell.
 * Never stores secrets, business IDs, model choices or API keys in requests.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMAIWriteClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function validate({origin,token,fetchImpl}){
    if(typeof origin!=='string'||!/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
       typeof token!=='string'||!/^[A-Za-z0-9_-]+$/.test(token)||token.length>2048||
       typeof fetchImpl!=='function')
      throw new TypeError('Secure authenticated AI client required');
  }
  async function request({origin,token,fetchImpl,path,method,body,key,
                          expectedTenantId}){
    validate({origin,token,fetchImpl});
    if(typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
       expectedTenantId.length>128)
      throw new TypeError('Active business required');
    const headers={'Authorization':'Bearer '+token,
      'Content-Type':'application/json'};
    if(key!==undefined)headers['Idempotency-Key']=key;
    const response=await fetchImpl(origin+path,{
      method,headers,mode:'same-origin',credentials:'omit',cache:'no-store',
      redirect:'error',body:JSON.stringify(body)});
    if(!response||!response.ok)
      throw new Error('AI request unavailable; refresh before retrying');
    const result=await response.json();
    if(!result||typeof result!=='object'||Array.isArray(result)||
       result.publishing_enabled!==false||
       (result.tenant_id!==undefined&&
        result.tenant_id!==expectedTenantId))
      throw new TypeError('Invalid unpublished AI response');
    return result;
  }
  async function generate({origin,token,fetchImpl,requestKey,
                           topic,platform,needsMedia,includeImagePrompt,
                           expectedTenantId}){
    if(typeof requestKey!=='string'||!/^[0-9a-f]{32}$/.test(requestKey)||
       typeof topic!=='string'||!topic.trim()||topic.length>300||
       !['facebook','instagram','linkedin','pinterest','tiktok','youtube']
         .includes(platform)||
       typeof needsMedia!=='boolean'||typeof includeImagePrompt!=='boolean'||
       (needsMedia&&!includeImagePrompt))
      throw new TypeError('Invalid AI generation request');
    const result=await request({origin,token,fetchImpl,
      path:'/api/v1/ai-generate',method:'POST',key:requestKey,
      expectedTenantId,
      body:{topic,platform,needs_media:needsMedia,
        include_image_prompt:includeImagePrompt}});
    if(typeof result.created!=='boolean')throw new TypeError('Invalid result');
    if(result.created){
      if(typeof result.tenant_id!=='string'||
         typeof result.draft_id!=='string'||
         !/^[0-9a-f]{32}$/.test(result.draft_id)||
         !['needs_media','draft_pending_verification'].includes(result.status))
        throw new TypeError('Invalid held draft response');
    }else if(result.tenant_id!==expectedTenantId||
       !['already_completed','already_failed','already_in_progress',
         'limit_reached','not_entitled',
         'tenant_limit_reached',
         'operator_limit_reached',
         'historical_estimated_cost_unknown',
         'user_estimated_budget_reached',
         'tenant_estimated_budget_reached',
         'operator_estimated_budget_reached',
         'operator_paused'].includes(result.reason))
      throw new TypeError('Invalid generation hold reason');
    return result;
  }
  async function confirmFacts({origin,token,fetchImpl,facts,expectedRevision,
                               expectedTenantId}){
    if(!facts||typeof facts!=='object'||Array.isArray(facts)||
       !Object.keys(facts).length||Object.keys(facts).length>40||
       Object.entries(facts).some(([key,value])=>
         !key.trim()||key.length>80||typeof value!=='string'||
         !value.trim()||value.length>500)||
       !Number.isSafeInteger(expectedRevision)||expectedRevision<0)
      throw new TypeError('Invalid owner-confirmed business facts');
    const result=await request({origin,token,fetchImpl,
      path:'/api/v1/ai-business-facts',method:'PUT',expectedTenantId,
      body:{facts,expected_revision:expectedRevision}});
    if(typeof result.tenant_id!=='string'||
       result.provenance!=='owner_confirmed'||
       !Number.isSafeInteger(result.revision)||
       result.revision!==expectedRevision+1)
      throw new TypeError('Invalid fact confirmation response');
    return result;
  }
  return Object.freeze({generate,confirmFacts});
});
