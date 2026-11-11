/* Business fact provenance contract for authenticated read-only UI. */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMAIFactsData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function normalize(body){
    if(!body||typeof body!=='object'||Array.isArray(body)||
       typeof body.tenant_id!=='string'||!body.tenant_id||
       !['not_configured','owner_confirmed'].includes(body.provenance)||
       !Number.isSafeInteger(body.revision)||body.revision<0||
       body.publishing_enabled!==false||
       !body.facts||typeof body.facts!=='object'||Array.isArray(body.facts)||
       Object.keys(body.facts).length>40||
       Object.entries(body.facts).some(([k,v])=>
         !k.trim()||k.length>80||typeof v!=='string'||
         !v.trim()||v.length>500))
      throw new TypeError('Invalid AI fact snapshot');
    if(body.provenance==='not_configured'){
      if(body.revision!==0||Object.keys(body.facts).length||
         body.confirmed_at!==null)
        throw new TypeError('Unconfigured facts cannot be confirmed');
    }else if(body.revision<1||!Object.keys(body.facts).length||
             !Number.isSafeInteger(body.confirmed_at)||
             body.confirmed_at<0)
      throw new TypeError('Confirmed fact provenance required');
    return {tenantId:body.tenant_id,provenance:body.provenance,
      revision:body.revision,facts:{...body.facts},
      confirmedAt:body.confirmed_at,publishingEnabled:false};
  }
  return Object.freeze({normalize});
});
