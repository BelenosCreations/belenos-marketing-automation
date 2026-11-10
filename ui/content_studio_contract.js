/* BAM read-only Content Studio contract.
 * Server owns tenant isolation and permissions. Browser validates structure,
 * never trusts client-supplied roles, and never enables publishing.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMContentStudioData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const statuses=new Set(['needs_content','ready_for_review','postponed','unavailable']);
  const channels=new Set(['facebook','instagram','linkedin','pinterest','tiktok','youtube']);
  const text=(x,max)=>typeof x==='string'&&x.trim().length>0&&x.length<=max;
  function normalize(body){
    if(!body||typeof body!=='object'||Array.isArray(body)||
       !text(body.tenant_id,128)||body.publishing_enabled!==false||
       !Array.isArray(body.drafts))throw new TypeError('Invalid content list');
    const seen=new Set();
    const drafts=body.drafts.map(d=>{
      if(!d||typeof d!=='object'||Array.isArray(d)||
         !/^[a-f0-9]{32}$/.test(d.request_id)||seen.has(d.request_id)||
         !channels.has(d.channel)||!statuses.has(d.status)||
         !text(d.draft_text,2000)||!text(d.suggestion,2000)||
         !Number.isSafeInteger(d.priority)||d.priority<-10||d.priority>10||
         !Array.isArray(d.missing_items)||
         d.missing_items.some(item=>!text(item,80))||
         new Set(d.missing_items).size!==d.missing_items.length)
        throw new TypeError('Invalid content request');
      seen.add(d.request_id);
      return {id:d.request_id,channel:d.channel,status:d.status,
        text:d.draft_text,suggestion:d.suggestion,
        priority:d.priority,missing:[...d.missing_items]};
    });
    return {tenantId:body.tenant_id,drafts,publishingEnabled:false};
  }
  return Object.freeze({normalize});
});
