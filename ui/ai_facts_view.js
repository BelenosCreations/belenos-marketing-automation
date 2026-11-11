/* Read-only business fact provenance panel, for Settings / AI. */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./ai_facts_contract.js'));
  else root.BAMAIFactsView=factory(root.BAMAIFactsData);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract){
  'use strict';
  function el(doc,tag,text){
    const node=doc.createElement(tag);
    node.textContent=text;
    return node;
  }
  function render({document,container,payload,expectedTenantId}){
    if(!document||!container||typeof container.replaceChildren!=='function')
      throw new TypeError('Fact panel mount required');
    const model=contract.normalize(payload);
    if(expectedTenantId!==undefined&&expectedTenantId!==model.tenantId)
      throw new TypeError('Unexpected business response');
    const section=el(document,'section','');
    section.append(el(document,'h3','Business facts for AI'));
    if(model.provenance==='not_configured'){
      section.append(el(document,'p',
        'No owner-confirmed business facts yet. AI drafts should remain on hold.'));
    }else{
      section.append(el(document,'p',
        'Owner-confirmed facts, revision '+model.revision+
        '. These are not independently verified.'));
      for(const [key,value] of Object.entries(model.facts))
        section.append(el(document,'p',key+': '+value));
    }
    section.append(el(document,'p','No approval or publishing from this panel.'));
    container.replaceChildren(section);
    return model;
  }
  return Object.freeze({render});
});
