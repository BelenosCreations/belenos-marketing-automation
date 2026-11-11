/* Read-only AI usage estimates for Settings, never the primary dashboard. */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./ai_cost_contract.js'));
  else root.BAMAICostView=factory(root.BAMAICostData);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract){
  'use strict';
  function el(doc,tag,text){
    const n=doc.createElement(tag);
    n.textContent=text;
    return n;
  }
  function render({document,container,payload,expectedTenantId}){
    if(!document||!container||typeof container.replaceChildren!=='function')
      throw new TypeError('AI usage mount required');
    const data=contract.normalize(payload);
    if(expectedTenantId!==undefined&&expectedTenantId!==data.tenantId)
      throw new TypeError('Unexpected business response');
    const section=el(document,'section','');
    section.append(el(document,'h3','AI usage estimates'));
    section.append(el(document,'p','Recorded requests: '+data.events));
    section.append(el(document,'p','Input tokens: '+data.inputTokens));
    section.append(el(document,'p','Output tokens: '+data.outputTokens));
    section.append(el(document,'p',
      'Estimated cost: $'+(data.estimatedMicroUsd/1000000).toFixed(4)));
    section.append(el(document,'p',
      'Operator-configured rates only. Not an invoice or verified charge.'));
    container.replaceChildren(section);
    return data;
  }
  return Object.freeze({render});
});
