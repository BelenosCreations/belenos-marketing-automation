/* BAM authenticated dashboard renderer. Inject trusted, validated server payload.
 * Does not fetch, authenticate, switch businesses or publish.
 * All user-controlled strings use textContent, never innerHTML.
 */
(function(root,factory){
  'use strict';
  const api=factory(root.BAMDashboardData);
  if(typeof module==='object'&&module.exports)module.exports=factory(require('./dashboard_data_contract.js'));
  else root.BAMLiveView=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(contract){
  'use strict';
  function make(doc,tag,className,text){
    const node=doc.createElement(tag);
    if(className)node.className=className;
    if(text!==undefined)node.textContent=String(text);
    return node;
  }
  function clear({container}){
    if(!container||typeof container.replaceChildren!=='function')
      throw new TypeError('Valid dashboard mount required');
    container.replaceChildren();
  }
  function render({document,container,payload,expectedTenantId}){
    if(!document||!container||typeof container.replaceChildren!=='function')
      throw new TypeError('Valid dashboard mount required');
    // Fail closed: validation completes before changing the DOM.
    const model=contract.normalize(payload);
    if(expectedTenantId!==undefined&&model.tenantId!==expectedTenantId)
      throw new TypeError('Unexpected business response');
    const wrapper=make(document,'section','bam-live-dashboard');
    const business=model.businesses.find(b=>b.tenant_id===model.tenantId);
    wrapper.append(make(document,'h2','bam-live-heading',business.name));
    const note=make(document,'p','bam-live-notice',
      'Authenticated read-only view. Scheduling and publishing are disabled.');
    wrapper.append(note);
    const cards=make(document,'div','bam-live-cards');
    for(const id of ['scheduled','approvals','content','connections']){
      const card=model.cards[id];
      const panel=make(document,'section','bam-live-card');
      panel.append(make(document,'h3','bam-live-card-title',card.label));
      const value=card.availability==='available'
        ?String(card.value)
        :card.availability==='restricted'?'Restricted':'Not connected';
      panel.append(make(document,'p','bam-live-card-value',value));
      cards.append(panel);
    }
    wrapper.append(cards);
    const studio=make(document,'section','bam-live-content');
    studio.append(make(document,'h3','','Content needing attention'));
    if(!model.drafts.length){
      studio.append(make(document,'p','','No content requests requiring attention.'));
    }
    for(const draft of model.drafts){
      const article=make(document,'article','bam-live-draft');
      article.append(make(document,'h4','',draft.channel+' — '+draft.status.replaceAll('_',' ')));
      article.append(make(document,'p','',draft.text));
      article.append(make(document,'p','',draft.suggestion));
      if(draft.missing.length)
        article.append(make(document,'p','','Needed: '+draft.missing.join(', ')));
      studio.append(article);
    }
    wrapper.append(studio);
    container.replaceChildren(wrapper);
    return model;
  }
  return Object.freeze({render,clear});
});
