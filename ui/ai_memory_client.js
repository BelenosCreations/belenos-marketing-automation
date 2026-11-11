/* Explicit own-business, per-user AI writing preferences update.
 * Never accepts API keys, provider tokens, plan selection or publishing.
 */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMAIMemoryClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const token=/^[A-Za-z0-9_-]{32,2048}$/;
 const forbidden=/api.?key|token|secret|password|credential|vault/i;
 function validMap(value){
   if(!value||typeof value!=='object'||Array.isArray(value)||
      Object.keys(value).length>40)return false;
   for(const [key,text] of Object.entries(value)){
     if(!key.trim()||key!==key.trim()||key.length>80||
        forbidden.test(key)||typeof text!=='string'||
        !text.trim()||text!==text.trim()||text.length>2000||
        /^sk-[A-Za-z0-9_-]{12,}/.test(text))return false;
   }
   return new TextEncoder().encode(JSON.stringify(value)).length<=16384;
 }
 function same(a,b){
   const aKeys=Object.keys(a).sort(),bKeys=Object.keys(b).sort();
   return aKeys.length===bKeys.length&&
     aKeys.every((key,i)=>key===bKeys[i]&&a[key]===b[key]);
 }
 async function save({origin,fetchImpl,sessionToken,expectedTenantId,
                      memory,expectedMemory}){
   if(typeof origin!=='string'||
      !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
      typeof fetchImpl!=='function'||!token.test(sessionToken)||
      typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
      expectedTenantId.length>128||!validMap(memory)||
      !validMap(expectedMemory))
     throw new TypeError('Trusted AI preference edit required');
   const result=await fetchImpl(origin+'/api/v1/ai-memory',{
     method:'PUT',mode:'same-origin',credentials:'omit',
     cache:'no-store',redirect:'error',
     headers:{Authorization:'Bearer '+sessionToken,
       'Content-Type':'application/json',Accept:'application/json'},
     body:JSON.stringify({memory,expected_memory:expectedMemory})
   });
   if(!result||!result.ok||result.status!==200)
     throw new Error('AI preferences not confirmed; refresh before retrying');
   const body=await result.json();
   if(!body||typeof body!=='object'||Array.isArray(body)||
      Object.keys(body).sort().join(',')!==
         'memory,publishing_enabled,tenant_id'||
      body.tenant_id!==expectedTenantId||
      body.publishing_enabled!==false||
      !validMap(body.memory)||!same(body.memory,memory))
     throw new TypeError('Untrusted AI preference response');
   return Object.freeze({tenantId:body.tenant_id,
     memory:Object.freeze({...body.memory}),publishingEnabled:false});
 }
 return Object.freeze({save,validMap});
});
