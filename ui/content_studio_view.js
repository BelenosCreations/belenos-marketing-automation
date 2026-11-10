/* Read-only Content Studio renderer for all held draft statuses.
 * No approve, publish or media-upload buttons are exposed.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./content_studio_contract.js'));
  else root.BAMContentStudioView=factory(root.BAMContentStudioData);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract){
  'use strict';
  function make(doc,tag,content){
    const element=doc.createElement(tag);
    element.textContent=content;
    return element;
  }
  function render({document,container,payload,expectedTenantId}){
    if(!document||!container||typeof container.replaceChildren!=='function')
      throw new TypeError('Valid content mount required');
    const model=contract.normalize(payload);
    if(expectedTenantId!==undefined&&expectedTenantId!==model.tenantId)
      throw new TypeError('Unexpected business response');
    const wrapper=make(document,'section','');
    wrapper.className='bam-content-studio';
    wrapper.append(make(document,'h2','Content Studio'));
    wrapper.append(make(document,'p','Held drafts only — publishing disabled.'));
    for(const status of ['needs_content','ready_for_review','postponed','unavailable']){
      const drafts=model.drafts.filter(d=>d.status===status);
      const section=make(document,'section','');
      section.append(make(document,'h3',status.replaceAll('_',' ')+' ('+drafts.length+')'));
      for(const draft of drafts){
        const item=make(document,'article','');
        item.append(make(document,'h4',draft.channel));
        item.append(make(document,'p',draft.text));
        item.append(make(document,'p',draft.suggestion));
        if(draft.missing.length)
          item.append(make(document,'p','Needed: '+draft.missing.join(', ')));
        section.append(item);
      }
      wrapper.append(section);
    }
    container.replaceChildren(wrapper);
    return model;
  }
  return Object.freeze({render});
});
