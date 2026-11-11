/* BAM browser read-only HTTPS client.
 * Token is supplied by trusted sign-in flow and kept in caller memory only.
 * No localStorage, cookies, cross-origin calls, writes or auto-retries.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory(require('./dashboard_data_contract.js'),require('./content_studio_contract.js'),require('./posting_preferences_contract.js'),require('./ai_draft_contract.js'),require('./ai_settings_contract.js'));
  else root.BAMReadClient=factory(root.BAMDashboardData,root.BAMContentStudioData,root.BAMPostingPreferencesData,root.BAMAIDraftData,root.BAMAISettingsData);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract,studioContract,postingContract,aiDraftContract,aiSettingsContract){
  'use strict';
  const routes=Object.freeze({
    dashboard:'/api/v1/dashboard',
    drafts:'/api/v1/drafts',
    preferences:'/api/v1/posting-preferences',
    aiDrafts:'/api/v1/ai-drafts',
    aiSettings:'/api/v1/ai-settings'
  });
  async function read({kind,token,fetchImpl,origin,expectedTenantId}){
    if(!Object.prototype.hasOwnProperty.call(routes,kind))
      throw new TypeError('Unknown read route');
    if(typeof token!=='string'||!token.trim()||token.length>2048)
      throw new TypeError('Valid session required');
    if(typeof fetchImpl!=='function')throw new TypeError('Fetch implementation required');
    if(typeof origin!=='string'||!origin.startsWith('https://'))
      throw new TypeError('HTTPS origin required');
    const parsed=new URL(origin);
    if(parsed.protocol!=='https:'||parsed.username||parsed.password||
       parsed.pathname!=='/'||parsed.search||parsed.hash)
      throw new TypeError('HTTPS origin must not contain credentials or path');
    const response=await fetchImpl(parsed.origin+routes[kind],{
      method:'GET',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{Authorization:'Bearer '+token,Accept:'application/json'}
    });
    if(!response||!response.ok)throw new Error('BAM read request failed');
    const body=await response.json();
    if(expectedTenantId!==undefined){
      if(typeof expectedTenantId!=='string'||!expectedTenantId||
         !body||body.tenant_id!==expectedTenantId)
        throw new TypeError('Unexpected business response');
    }
    if(kind==='dashboard')return contract.normalize(body);
    if(kind==='drafts')return studioContract.normalize(body);
    if(kind==='preferences')return postingContract.normalize(body);
    if(kind==='aiDrafts')return aiDraftContract.normalize(body);
    if(kind==='aiSettings')return aiSettingsContract.normalize(body);
    if(!body||typeof body!=='object'||body.publishing_enabled!==false)
      throw new TypeError('Invalid read-only response');
    return body;
  }
  return Object.freeze({read});
});
