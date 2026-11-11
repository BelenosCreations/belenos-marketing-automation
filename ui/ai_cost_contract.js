/* Strict read-only AI cost estimates; never present estimates as invoices. */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMAICostData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  function normalize(body){
    if(!body||typeof body!=='object'||Array.isArray(body)||
       typeof body.tenant_id!=='string'||!body.tenant_id||
       body.pricing_basis!=='operator_configured'||
       body.actual_billing_verified!==false||
       body.publishing_enabled!==false||
       ['events','input_tokens','output_tokens','estimated_micro_usd']
         .some(k=>!Number.isSafeInteger(body[k])||body[k]<0))
      throw new TypeError('Invalid estimated AI usage');
    return {tenantId:body.tenant_id,events:body.events,
      inputTokens:body.input_tokens,outputTokens:body.output_tokens,
      estimatedMicroUsd:body.estimated_micro_usd,
      pricingBasis:'operator_configured',actualBillingVerified:false,
      publishingEnabled:false};
  }
  return Object.freeze({normalize});
});
