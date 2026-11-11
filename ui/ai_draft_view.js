/* Safe, read-only AI draft component view.
 * No publish, approve, media-upload or raw HTML execution.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./ai_draft_contract.js'),
      require('./ai_manual_image_handoff.js'));
  else root.BAMAIDraftView=factory(root.BAMAIDraftData,
    root.BAMManualImageHandoff);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract,handoff){
  'use strict';
  function el(document,tag,text){
    const node=document.createElement(tag);
    node.textContent=text;
    return node;
  }
  function render({document,container,payload,expectedTenantId,
                   copyText,openUrl}){
    if(!document||!container||typeof container.replaceChildren!=='function')
      throw new TypeError('Valid AI draft mount required');
    if((copyText!==undefined||openUrl!==undefined)&&
       (typeof copyText!=='function'||typeof openUrl!=='function'))
      throw new TypeError('Manual image handoff actions required');
    const model=contract.normalize(payload);
    if(expectedTenantId!==undefined&&model.tenantId!==expectedTenantId)
      throw new TypeError('Unexpected business response');
    const wrapper=el(document,'section','');
    wrapper.className='bam-ai-drafts';
    wrapper.append(el(document,'h2','AI Content Drafts'));
    wrapper.append(el(document,'p','Drafts only. Publishing disabled.'));
    if(!model.drafts.length)
      wrapper.append(el(document,'p','No AI drafts yet.'));
    for(const draft of model.drafts){
      const item=el(document,'article','');
      item.append(el(document,'h3',draft.platform));
      item.append(el(document,'p',draft.postText));
      if(draft.imagePrompt!==null){
        item.append(el(document,'h4','Image prompt — copy to ChatGPT if desired'));
        item.append(el(document,'p',draft.imagePrompt));
        if(draft.needsMedia&&!draft.mediaAttached&&copyText&&openUrl){
          const mount=el(document,'div','');
          handoff.render({document,container:mount,
            imagePrompt:draft.imagePrompt,copyText,openUrl,needsMedia:true});
          item.append(mount);
        }
      }
      item.append(el(document,'p',draft.needsMedia&&!draft.mediaAttached
        ?'Media needed — this draft is on hold'
        :draft.mediaAttached
          ?'Media verified and attached — awaiting factual verification and approval'
          :'Awaiting factual verification and approval'));
      wrapper.append(item);
    }
    container.replaceChildren(wrapper);
    return model;
  }
  return Object.freeze({render});
});
