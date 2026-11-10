/* BAM read-only dashboard data contract (browser and Node).
 * Input MUST come from an authenticated, trusted backend response.
 * This adapter never fetches data, stores credentials, or publishes.
 */
(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.BAMDashboardData=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const statuses=new Set(['needs_content','ready_for_review']);
  const cards=new Set(['scheduled','approvals','content','connections']);
  const channels=new Set(['facebook','instagram','linkedin','pinterest','tiktok','youtube']);
  function object(x){return x!==null&&typeof x==='object'&&!Array.isArray(x)}
  function nonempty(x,max=2000){return typeof x==='string'&&x.trim().length>0&&x.length<=max}
  function normalize(payload){
    if(!object(payload)||payload.schema_version!==1||
       !nonempty(payload.tenant_id,128)||!Array.isArray(payload.businesses)||
       !Array.isArray(payload.cards)||!Array.isArray(payload.drafts)||
       payload.publishing_enabled!==false){
      throw new TypeError('Invalid authorized dashboard payload');
    }
    if(!payload.businesses.some(b=>object(b)&&b.tenant_id===payload.tenant_id))
      throw new TypeError('Active business missing from directory');
    const businesses=payload.businesses.map(b=>{
      if(!object(b)||!nonempty(b.tenant_id,128)||!nonempty(b.display_name,200))
        throw new TypeError('Invalid business');
      return {tenant_id:b.tenant_id,name:b.display_name};
    });
    if(new Set(businesses.map(b=>b.tenant_id)).size!==businesses.length)
      throw new TypeError('Duplicate businesses');
    const normalizedCards={};
    for(const card of payload.cards){
      if(!object(card)||!cards.has(card.id)||normalizedCards[card.id]||
         !['available','not_connected','restricted'].includes(card.availability))
        throw new TypeError('Invalid card');
      const available=card.availability==='available';
      if(available&&(!Number.isSafeInteger(card.value)||card.value<0))
        throw new TypeError('Invalid card count');
      if(!available&&card.value!==null)
        throw new TypeError('Unavailable count must be null');
      normalizedCards[card.id]={
        label:typeof card.label==='string'?card.label:card.id,
        value:card.value,availability:card.availability
      };
    }
    for(const id of cards)if(!normalizedCards[id])throw new TypeError('Missing card '+id);
    const drafts=payload.drafts.map(d=>{
      if(!object(d)||!nonempty(d.request_id,64)||
         !channels.has(d.channel)||!statuses.has(d.status)||
         !nonempty(d.draft_text)||!nonempty(d.suggestion)||
         !Array.isArray(d.missing_items)||
         d.missing_items.some(x=>!nonempty(x,80)))
        throw new TypeError('Invalid draft');
      return {
        id:d.request_id,channel:d.channel,text:d.draft_text,
        suggestion:d.suggestion,status:d.status,missing:[...d.missing_items]
      };
    });
    if(new Set(drafts.map(d=>d.id)).size!==drafts.length)
      throw new TypeError('Duplicate drafts');
    if(!object(payload.analytics)||!object(payload.schedule))
      throw new TypeError('Missing integration availability');
    if(payload.analytics.availability!=='not_connected'||
       payload.analytics.series!==null||
       payload.schedule.availability!=='not_connected'||
       payload.schedule.posts!==null)
      throw new TypeError('Unexpected unverified metrics');
    return {
      tenantId:payload.tenant_id,businesses,
      cards:normalizedCards,drafts,
      analyticsAvailable:false,scheduleAvailable:false,
      publishingEnabled:false
    };
  }
  return Object.freeze({normalize});
});
