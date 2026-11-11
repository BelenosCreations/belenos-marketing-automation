/* Explicit no-API-cost, confirmed-fact product template action.
 * No browser-supplied business facts, model, API credential or publish flag.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMLocalProductDraftClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const token=/^[A-Za-z0-9_-]{32,2048}$/;
  const draftId=/^[a-f0-9]{32}$/;
  const platforms=new Set(['facebook','instagram','linkedin','pinterest','tiktok','youtube']);
  async function create({origin,fetchImpl,sessionToken,expectedTenantId,
                         platform,includeImagePrompt}){
    if(typeof origin!=='string'||
       !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
       typeof fetchImpl!=='function'||!token.test(sessionToken)||
       typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
       expectedTenantId.length>128||
       !platforms.has(platform)||typeof includeImagePrompt!=='boolean')
      throw new TypeError('Trusted local draft creation required');
    const response=await fetchImpl(origin+'/api/v1/ai/local-product-draft',{
      method:'POST',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{'Content-Type':'application/json',Accept:'application/json',
        Authorization:'Bearer '+sessionToken},
      body:JSON.stringify({platform,
        include_image_prompt:includeImagePrompt})
    });
    if(!response||!response.ok)
      throw new Error('Local draft could not be created');
    const body=await response.json();
    if(!body||typeof body!=='object'||Array.isArray(body)||
       Object.keys(body).some(k=>!['tenant_id','draft_id','platform',
         'post_text','image_prompt','needs_media','media_attached','status',
         'revision','publishing_enabled','generation_method',
         'openai_requests'].includes(k))||
       body.tenant_id!==expectedTenantId||!draftId.test(body.draft_id)||
       body.platform!==platform||typeof body.post_text!=='string'||
       !body.post_text.trim()||body.post_text.length>4000||
       body.needs_media!==includeImagePrompt||body.media_attached!==false||
       body.status!==(includeImagePrompt?'needs_media':'draft_pending_verification')||
       (includeImagePrompt?
         (typeof body.image_prompt!=='string'||
          !body.image_prompt.trim()||body.image_prompt.length>2000):
         body.image_prompt!==null)||
       body.revision!==1||body.publishing_enabled!==false||
       body.generation_method!=='local_template'||body.openai_requests!==0)
      throw new TypeError('Invalid zero-cost local draft response');
    return Object.freeze({tenantId:body.tenant_id,id:body.draft_id,
      status:body.status,openaiRequests:0,publishingEnabled:false});
  }
  return Object.freeze({create});
});
