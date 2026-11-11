/* Authenticated business switch. The server decides membership and role.
 * No cookies, storage, auto-retries, account provisioning or publishing.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMBusinessSwitchClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const sessionToken=/^[A-Za-z0-9_-]{32,2048}$/;
  function validTenant(value){
    return typeof value==='string'&&value.length<=128&&
      value.trim().length>0&&value===value.trim();
  }
  async function activate({origin,fetchImpl,sessionToken:oldToken,
                           targetTenantId}){
    if(typeof origin!=='string'||
       !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
       typeof fetchImpl!=='function'||
       typeof oldToken!=='string'||!sessionToken.test(oldToken)||
       !validTenant(targetTenantId))
      throw new TypeError('Trusted BAM business session required');
    const response=await fetchImpl(origin+'/api/v1/businesses/activate',{
      method:'POST',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{'Content-Type':'application/json','Accept':'application/json',
        Authorization:'Bearer '+oldToken},
      body:JSON.stringify({target_tenant_id:targetTenantId})
    });
    if(!response||!response.ok)
      throw new Error('Unable to change BAM business');
    const body=await response.json();
    if(!body||typeof body!=='object'||Array.isArray(body)||
       body.tenant_id!==targetTenantId||
       typeof body.session_token!=='string'||
       !sessionToken.test(body.session_token)||
       body.session_token===oldToken||
       body.publishing_enabled!==false||
       Object.keys(body).some(k=>![
         'tenant_id','session_token','publishing_enabled'].includes(k)))
      throw new TypeError('Invalid server business switch response');
    return Object.freeze({sessionToken:body.session_token,
      tenantId:body.tenant_id,publishingEnabled:false});
  }
  return Object.freeze({activate});
});
