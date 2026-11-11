/* Explicit business-private review queue priority update. Never publication. */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMHeldDraftPriorityClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const id=/^[a-f0-9]{32}$/;
  const bearer=/^[A-Za-z0-9_-]{32,2048}$/;
  function exact(data,keys){
    return data!==null&&typeof data==='object'&&
      !Array.isArray(data)&&Object.keys(data).length===keys.length&&
      keys.every(key=>Object.prototype.hasOwnProperty.call(data,key));
  }
  async function update(options){
    const {origin,fetchImpl,token,expectedTenantId,
      requestId,priority,expectedPriorityToken,expectedContentRevision}=
      options||{};
    if(typeof origin!=='string'||
       !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
       typeof fetchImpl!=='function'||typeof token!=='string'||
       !bearer.test(token)||typeof expectedTenantId!=='string'||
       !expectedTenantId.trim()||expectedTenantId.length>128||
       typeof requestId!=='string'||!id.test(requestId)||
       !Number.isSafeInteger(priority)||priority< -10||priority>10||
       typeof expectedPriorityToken!=='string'||
       !id.test(expectedPriorityToken)||
       !Number.isSafeInteger(expectedContentRevision)||
       expectedContentRevision<1)
      throw new TypeError('Trusted current held queue priority required');
    const response=await fetchImpl(origin+'/api/v1/content/priority',{
      method:'PUT',mode:'same-origin',credentials:'omit',cache:'no-store',
      redirect:'error',headers:{
        'Content-Type':'application/json',Accept:'application/json',
        Authorization:'Bearer '+token},
      body:JSON.stringify({request_id:requestId,priority,
                           expected_priority_token:expectedPriorityToken})
    });
    if(!response||!response.ok||response.status!==200)
      throw new Error('Draft queue priority changed or unavailable; refresh');
    const result=await response.json();
    if(!exact(result,['tenant_id','request_id','priority',
         'priority_token','revision','status','publishing_enabled'])||
       result.tenant_id!==expectedTenantId||
       result.request_id!==requestId||
       result.priority!==priority||
       result.revision!==expectedContentRevision||
       typeof result.priority_token!=='string'||
       !id.test(result.priority_token)||
       result.priority_token===expectedPriorityToken||
       result.status!=='held_priority_only'||
       result.publishing_enabled!==false)
      throw new TypeError('Unsafe queue priority response');
    return Object.freeze({
      tenantId:result.tenant_id,requestId,
      priority,priorityToken:result.priority_token,
      contentRevision:result.revision,
      status:'held_priority_only',publishingEnabled:false});
  }
  return Object.freeze({update});
});
