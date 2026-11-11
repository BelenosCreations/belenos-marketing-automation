/* Strict read-only AI draft contract: no attached-media or publication claims. */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMAIDraftData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const id=/^[a-f0-9]{32}$/;
  const platforms=new Set(['facebook','instagram','linkedin','pinterest','tiktok','youtube']);
  function normalize(body){
    if(!body||typeof body!=='object'||Array.isArray(body)||
       typeof body.tenant_id!=='string'||!body.tenant_id||
       body.publishing_enabled!==false||!Array.isArray(body.drafts)||
       body.drafts.length>500)throw new TypeError('Invalid AI draft list');
    const seen=new Set();
    const drafts=body.drafts.map(d=>{
      if(!d||typeof d!=='object'||Array.isArray(d)||
         typeof d.tenant_id!=='string'||d.tenant_id!==body.tenant_id||
         typeof d.draft_id!=='string'||!id.test(d.draft_id)||
         seen.has(d.draft_id)||!platforms.has(d.platform)||
         typeof d.post_text!=='string'||!d.post_text.trim()||
         d.post_text.length>4000||
         (d.image_prompt!==null&&
           (typeof d.image_prompt!=='string'||!d.image_prompt.trim()||
            d.image_prompt.length>2000))||
         typeof d.needs_media!=='boolean'||typeof d.media_attached!=='boolean'||
         (d.media_attached&&!d.needs_media)||
         d.publishing_enabled!==false||
         !Number.isSafeInteger(d.revision)||d.revision<1||
         d.status!==(d.needs_media&&!d.media_attached
           ?'needs_media':'draft_pending_verification'))
        throw new TypeError('Invalid AI draft');
      seen.add(d.draft_id);
      return {id:d.draft_id,platform:d.platform,postText:d.post_text,
        imagePrompt:d.image_prompt,needsMedia:d.needs_media,
        mediaAttached:d.media_attached,status:d.status,revision:d.revision};
    });
    return {tenantId:body.tenant_id,drafts,publishingEnabled:false};
  }
  return Object.freeze({normalize});
});
