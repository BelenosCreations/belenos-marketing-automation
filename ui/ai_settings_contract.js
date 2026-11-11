/* BAM OpenAI-only account settings validator.
 * A safe settings response never contains an API key or vault reference.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMAISettingsData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function normalize(body){
    if(!body||typeof body!=='object'||Array.isArray(body)||
       typeof body.tenant_id!=='string'||!body.tenant_id||
       body.provider!=='openai'||
       !['bam_sponsored','own_openai_key'].includes(body.mode)||
       typeof body.own_key_configured!=='boolean'||
       body.key_exposed!==false||body.publishing_enabled!==false||
       !body.memory||typeof body.memory!=='object'||
       Array.isArray(body.memory)||
       Object.keys(body).some(k=>/secret|credential|token|vault|api_key/i.test(k))||
       Object.entries(body.memory).some(([k,v])=>
         k.length>80||typeof v!=='string'||v.length>2000)||
       (body.mode==='own_openai_key'&&!body.own_key_configured))
      throw new TypeError('Invalid AI settings');
    return {tenantId:body.tenant_id,provider:'openai',mode:body.mode,
      ownKeyConfigured:body.own_key_configured,
      memory:{...body.memory},publishingEnabled:false};
  }
  return Object.freeze({normalize});
});
