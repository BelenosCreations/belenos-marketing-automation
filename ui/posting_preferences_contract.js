/* BAM posting preference response validator. Preference data never implies
 * a post was scheduled or that smart recommendations are available.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMPostingPreferencesData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const time=/^(?:[01][0-9]|2[0-3]):[0-5][0-9]$/;
  function normalize(body){
    if(!body||typeof body!=='object'||Array.isArray(body)||
       typeof body.tenant_id!=='string'||!body.tenant_id||
       !['smart','manual'].includes(body.mode)||
       typeof body.configured!=='boolean'||
       body.publishing_enabled!==false||
       !Array.isArray(body.manual_times)||
       body.manual_times.length>24||
       body.manual_times.some(t=>typeof t!=='string'||!time.test(t))||
       new Set(body.manual_times).size!==body.manual_times.length)
      throw new TypeError('Invalid posting preferences');
    if(!body.configured){
      if(body.mode!=='smart'||body.timezone!==null||
         body.manual_times.length!==0)
        throw new TypeError('Unconfigured preference must not imply timezone');
    }else{
      if(typeof body.timezone!=='string'||!body.timezone||
         body.timezone.length>80)
        throw new TypeError('Configured timezone required');
      if(body.mode==='manual'&&!body.manual_times.length)
        throw new TypeError('Manual mode needs times');
      if(body.mode==='smart'&&body.manual_times.length)
        throw new TypeError('Smart mode cannot have manual times');
    }
    return {tenantId:body.tenant_id,mode:body.mode,
      timezone:body.timezone,configured:body.configured,
      manualTimes:[...body.manual_times],publishingEnabled:false};
  }
  return Object.freeze({normalize});
});
