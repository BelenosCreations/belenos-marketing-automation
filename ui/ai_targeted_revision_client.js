/* Strict explicit-action AI component regeneration client.
 * Does not store keys, trigger itself, retry provider attempts or publish.
 * The UI feature stays disabled unless operator explicitly enables it.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMAITargetedRevisionClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const hex=/^[a-f0-9]{32}$/;
  const bearer=/^[A-Za-z0-9_-]{32,2048}$/;
  const allowedHold=new Set(['already_completed','already_failed',
    'already_in_progress','limit_reached','not_entitled']);
  const allowedStatus=new Set(['needs_media','draft_pending_verification']);
  function exact(value,keys){
    return value!==null&&typeof value==='object'&&!Array.isArray(value)&&
      Object.keys(value).length===keys.length&&keys.every(k=>
        Object.prototype.hasOwnProperty.call(value,k));
  }
  function newRequestKey(secureRandom){
    if(!secureRandom||typeof secureRandom.getRandomValues!=='function')
      throw new TypeError('Cryptographic random source required');
    const bytes=new Uint8Array(16);
    if(secureRandom.getRandomValues(bytes)!==bytes||
       bytes.every(value=>value===0))
      throw new TypeError('Secure random request identifier unavailable');
    return [...bytes].map(value=>value.toString(16).padStart(2,'0')).join('');
  }
  async function revise({origin,fetchImpl,token,expectedTenantId,
     draftId,expectedRevision,target,instruction,topic,requestKey}){
    if(typeof origin!=='string'||
       !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
       typeof fetchImpl!=='function'||!bearer.test(token)||
       typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
       expectedTenantId.length>128||
       !hex.test(draftId)||!hex.test(requestKey)||
       !Number.isSafeInteger(expectedRevision)||expectedRevision<1||
       !['post_text','image_prompt'].includes(target)||
       typeof instruction!=='string'||!instruction.trim()||
       instruction.length>500||
       typeof topic!=='string'||!topic.trim()||topic.length>300)
      throw new TypeError('Invalid explicit targeted AI revision');
    const result=await fetchImpl(origin+'/api/v1/ai/targeted-revision',{
      method:'POST',mode:'same-origin',credentials:'omit',cache:'no-store',
      redirect:'error',headers:{'Content-Type':'application/json',
        Accept:'application/json',Authorization:'Bearer '+token,
        'Idempotency-Key':requestKey},
      body:JSON.stringify({draft_id:draftId,expected_revision:expectedRevision,
        target,instruction,topic})
    });
    if(!result||!result.ok||![200,201].includes(result.status))
      throw new Error('AI revision not confirmed; refresh before retrying');
    const body=await result.json();
    if(!body||typeof body!=='object'||Array.isArray(body)||
       body.tenant_id!==expectedTenantId||body.publishing_enabled!==false||
       typeof body.revised!=='boolean')
      throw new TypeError('Untrusted AI revision response');
    if(body.revised){
      if(result.status!==201||!exact(body,['revised','tenant_id',
          'draft_id','revision','status','publishing_enabled'])||
         body.draft_id!==draftId||
         body.revision!==expectedRevision+1||
         !allowedStatus.has(body.status))
        throw new TypeError('Untrusted revised draft');
      return Object.freeze({revised:true,tenantId:body.tenant_id,
        draftId,revision:body.revision,status:body.status,
        publishingEnabled:false});
    }
    if(result.status!==200||
       !exact(body,['revised','tenant_id','reason','publishing_enabled'])||
       !allowedHold.has(body.reason))
      throw new TypeError('Untrusted AI revision hold reason');
    return Object.freeze({revised:false,tenantId:body.tenant_id,
      reason:body.reason,publishingEnabled:false});
  }
  return Object.freeze({revise,newRequestKey});
});
