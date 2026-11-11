/* Manual editing of one existing AI draft component at a time.
 * Saves require the current user session and expected revision. No AI call.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMAIDraftEditClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const token=/^[A-Za-z0-9_-]{32,2048}$/;
  const id=/^[a-f0-9]{32}$/;
  const platforms=new Set(['facebook','instagram','linkedin','pinterest','tiktok','youtube']);
  async function revise({origin,fetchImpl,sessionToken,expectedTenantId,
                         draftId,target,revisedText,expectedRevision}){
    if(typeof origin!=='string'||
       !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
       typeof fetchImpl!=='function'||!token.test(sessionToken)||
       typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
       expectedTenantId.length>128||!id.test(draftId)||
       !['post_text','image_prompt'].includes(target)||
       typeof revisedText!=='string'||!revisedText.trim()||
       revisedText.length>(target==='post_text'?4000:2000)||
       !Number.isSafeInteger(expectedRevision)||expectedRevision<1)
      throw new TypeError('Invalid authenticated single-component revision');
    const response=await fetchImpl(origin+'/api/v1/ai-drafts',{
      method:'PUT',mode:'same-origin',credentials:'omit',cache:'no-store',
      redirect:'error',
      headers:{'Content-Type':'application/json',Accept:'application/json',
        Authorization:'Bearer '+sessionToken},
      body:JSON.stringify({
        draft_id:draftId,target,revised_text:revisedText,
        expected_revision:expectedRevision})
    });
    if(!response||!response.ok)
      throw new Error('Draft revision was not confirmed');
    const result=await response.json();
    if(!result||typeof result!=='object'||Array.isArray(result)||
       Object.keys(result).some(k=>!['tenant_id','draft_id','platform',
         'post_text','image_prompt','needs_media','media_attached','status',
         'revision','publishing_enabled'].includes(k))||
       result.tenant_id!==expectedTenantId||
       result.draft_id!==draftId||!platforms.has(result.platform)||
       typeof result.post_text!=='string'||!result.post_text.trim()||
       result.post_text.length>4000||
       (result.image_prompt!==null&&
        (typeof result.image_prompt!=='string'||!result.image_prompt.trim()||
         result.image_prompt.length>2000))||
       typeof result.needs_media!=='boolean'||
       typeof result.media_attached!=='boolean'||
       (result.media_attached&&!result.needs_media)||
       result.status!==(result.needs_media&&!result.media_attached
          ?'needs_media':'draft_pending_verification')||
       result.revision!==expectedRevision+1||
       result[target]!==revisedText||
       result.publishing_enabled!==false)
      throw new TypeError('Invalid edited draft response');
    return Object.freeze({tenantId:result.tenant_id,id:result.draft_id,
      revision:result.revision,status:result.status,
      publishingEnabled:false});
  }
  return Object.freeze({revise});
});
