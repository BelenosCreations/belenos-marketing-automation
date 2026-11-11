/* Read-only OpenAI Settings panel. No raw key fields or mode-changing controls.
 * Place inside Settings, not the primary dashboard.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./ai_settings_contract.js'));
  else root.BAMAISettingsView=factory(root.BAMAISettingsData);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract){
  'use strict';
  function el(doc,tag,value){
    const node=doc.createElement(tag);
    node.textContent=value;
    return node;
  }
  function render({document,container,payload,expectedTenantId}){
    if(!document||!container||typeof container.replaceChildren!=='function')
      throw new TypeError('Valid settings mount required');
    const model=contract.normalize(payload);
    if(expectedTenantId!==undefined&&model.tenantId!==expectedTenantId)
      throw new TypeError('Unexpected business response');
    const section=el(document,'section','');
    section.className='bam-settings-ai';
    section.append(el(document,'h2','Settings — AI'));
    section.append(el(document,'p','AI provider: OpenAI'));
    section.append(el(document,'p',model.mode==='bam_sponsored'
      ?'AI usage mode: BAM-sponsored'
      :'AI usage mode: Your OpenAI API key'));
    section.append(el(document,'p',model.ownKeyConfigured
      ?'Personal key: configured (hidden)'
      :'Personal key: not configured'));
    section.append(el(document,'h3','Your content preferences'));
    const entries=Object.entries(model.memory);
    if(!entries.length)section.append(el(document,'p','No saved preferences.'));
    for(const [key,value] of entries)
      section.append(el(document,'p',key+': '+value));
    section.append(el(document,'p','Read-only preview. No publishing enabled.'));
    container.replaceChildren(section);
    return model;
  }
  return Object.freeze({render});
});
