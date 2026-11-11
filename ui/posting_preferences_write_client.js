/* Explicit, owner-authorized posting time preference update.
 * This client never schedules, publishes or accepts browser role claims.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./posting_preferences_contract.js'));
  else root.BAMPostingPreferencesWriteClient=factory(root.BAMPostingPreferencesData);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract){
  'use strict';
  const tokenPattern=/^[A-Za-z0-9_-]{32,2048}$/;
  const clock=/^(?:[01][0-9]|2[0-3]):[0-5][0-9]$/;
  function save({origin,fetchImpl,token,expectedTenantId,
                 mode,timezone,manualTimes}){
    if(typeof origin!=='string'||
       !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
       typeof fetchImpl!=='function'||!tokenPattern.test(token)||
       typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
       expectedTenantId.length>128)
      throw new TypeError('Trusted BAM session required');
    if(!['smart','manual'].includes(mode)||typeof timezone!=='string'||
       !timezone.trim()||timezone!==timezone.trim()||timezone.length>80||
       !Array.isArray(manualTimes)||manualTimes.length>24||
       manualTimes.some(v=>typeof v!=='string'||!clock.test(v))||
       new Set(manualTimes).size!==manualTimes.length||
       (mode==='manual'&&!manualTimes.length)||
       (mode==='smart'&&manualTimes.length))
      throw new TypeError('Invalid posting time preferences');
    return (async()=>{
      const response=await fetchImpl(origin+'/api/v1/posting-preferences',{
        method:'PUT',mode:'same-origin',credentials:'omit',
        cache:'no-store',redirect:'error',
        headers:{'Content-Type':'application/json',Accept:'application/json',
          Authorization:'Bearer '+token},
        body:JSON.stringify({mode,timezone,manual_times:[...manualTimes]})
      });
      if(!response||!response.ok)
        throw new Error('Posting preference save not confirmed');
      const body=await response.json();
      if(!body||typeof body!=='object'||Array.isArray(body)||
         body.tenant_id!==expectedTenantId||
         Object.keys(body).some(k=>!['tenant_id','mode','timezone',
             'manual_times','configured','publishing_enabled'].includes(k)))
        throw new TypeError('Unexpected business preference response');
      const result=contract.normalize(body);
      if(!result.configured||result.mode!==mode||
         result.timezone!==timezone||
         [...result.manualTimes].sort().join(',')!==
           [...manualTimes].sort().join(','))
        throw new TypeError('Preference response does not match request');
      return result;
    })();
  }
  return Object.freeze({save});
});
