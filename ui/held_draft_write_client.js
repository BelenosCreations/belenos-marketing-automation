/* BAM held-content write boundary. Never approve, schedule, upload or publish.
 * All credentials remain in caller memory; tenant identity comes from session.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMHeldDraftWriteClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const tokenPattern=/^[A-Za-z0-9_-]{32,2048}$/;
  const requestPattern=/^[a-f0-9]{32}$/;
  const channels=new Set(['facebook','instagram','linkedin','pinterest','tiktok','youtube']);
  const holds=new Set(['needs_content','postponed','unavailable']);
  function validText(value,max){
    return typeof value==='string'&&value.trim().length>0&&
      value===value.trim()&&value.length<=max;
  }
  function context({origin,fetchImpl,token,expectedTenantId}){
    if(typeof origin!=='string'||
       !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
       typeof fetchImpl!=='function'||!tokenPattern.test(token)||
       !validText(expectedTenantId,128))
      throw new TypeError('Trusted BAM content session required');
  }
  async function post({origin,fetchImpl,token,expectedTenantId},path,payload,expectedStatus){
    const response=await fetchImpl(origin+path,{
      method:'POST',mode:'same-origin',credentials:'omit',
      cache:'no-store',redirect:'error',
      headers:{'Content-Type':'application/json',Accept:'application/json',
        Authorization:'Bearer '+token},
      body:JSON.stringify(payload)
    });
    if(!response||!response.ok)throw new Error('Held content update unavailable');
    const body=await response.json();
    if(!body||typeof body!=='object'||Array.isArray(body)||
       body.tenant_id!==expectedTenantId||
       !requestPattern.test(body.request_id)||
       body.status!==expectedStatus||body.publishing_enabled!==false||
       Object.keys(body).some(k=>!['tenant_id','request_id','status',
           'publishing_enabled'].includes(k)))
      throw new TypeError('Invalid held-content response');
    return Object.freeze({tenantId:body.tenant_id,id:body.request_id,
      status:body.status,publishingEnabled:false});
  }
  async function createDraft(options){
    context(options);
    const {channel,draftText,suggestion,requiredItems,priority=0}=options;
    if(!channels.has(channel)||!validText(draftText,2000)||
       !validText(suggestion,2000)||
       !Array.isArray(requiredItems)||requiredItems.length<1||
       requiredItems.length>12||
       requiredItems.some(item=>!validText(item,80))||
       new Set(requiredItems).size!==requiredItems.length||
       !Number.isSafeInteger(priority)||priority< -10||priority>10)
      throw new TypeError('Invalid held-draft details');
    return post(options,'/api/v1/content/drafts',{
      channel,draft_text:draftText,suggestion,
      required_items:[...requiredItems],priority},'needs_content');
  }
  async function changeHold(options){
    context(options);
    if(!requestPattern.test(options.requestId)||!holds.has(options.status))
      throw new TypeError('Invalid draft hold request');
    return post(options,'/api/v1/content/hold',{
      request_id:options.requestId,status:options.status},options.status);
  }
  return Object.freeze({createDraft,changeHold});
});
