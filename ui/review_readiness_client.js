/* Read-only, tenant-private editorial preparation preview. Never approval. */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMReviewReadinessClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const id=/^[a-f0-9]{32}$/;
 const auth=/^[A-Za-z0-9_-]{32,2048}$/;
 const channels=new Set(['facebook','instagram','linkedin',
   'pinterest','tiktok','youtube']);
 const statuses=new Set(['needs_content','ready_for_review',
   'postponed','unavailable']);
 const blockers=new Set(['draft_held','missing_required_content',
   'unverified_or_unexpected_content','not_ready_for_editorial_review',
   'truthguard_review_required','owner_approval_not_implemented',
   'social_publishing_disabled']);
 const always=['truthguard_review_required',
               'owner_approval_not_implemented','social_publishing_disabled'];
 function exact(x,keys){
  return x!==null&&typeof x==='object'&&!Array.isArray(x)&&
    Object.keys(x).length===keys.length&&
    keys.every(key=>Object.prototype.hasOwnProperty.call(x,key));
 }
 function strings(items,limit){
  return Array.isArray(items)&&items.length<=limit&&
    items.every(x=>typeof x==='string'&&x.trim()&&x.length<=80)&&
    new Set(items).size===items.length;
 }
 async function read({origin,fetchImpl,token,expectedTenantId}){
  if(typeof origin!=='string'||
     !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
     typeof fetchImpl!=='function'||typeof token!=='string'||
     !auth.test(token)||typeof expectedTenantId!=='string'||
     !expectedTenantId.trim()||expectedTenantId.length>128)
    throw new TypeError('Active trusted business review session required');
  const response=await fetchImpl(origin+'/api/v1/review-readiness',{
    method:'GET',mode:'same-origin',credentials:'omit',
    redirect:'error',cache:'no-store',
    headers:{Authorization:'Bearer '+token,Accept:'application/json'}
  });
  if(!response||!response.ok||response.status!==200)
   throw new Error('Private review preparation unavailable');
  const value=await response.json();
  if(!exact(value,['tenant_id','status','held_count',
     'editorial_material_complete_count','items','approved_count',
     'publishing_enabled'])||
     value.tenant_id!==expectedTenantId||
     value.status!=='review_preview_only'||
     !Number.isSafeInteger(value.held_count)||
     value.held_count<0||value.held_count>200||
     !Number.isSafeInteger(value.editorial_material_complete_count)||
     value.editorial_material_complete_count<0||
     value.editorial_material_complete_count>value.held_count||
     !Array.isArray(value.items)||value.items.length!==value.held_count||
     value.approved_count!==0||value.publishing_enabled!==false)
    throw new TypeError('Untrusted business review preview');
  const seen=new Set();let complete=0;
  const items=value.items.map(row=>{
    if(!exact(row,['request_id','revision','channel','status',
        'missing_items','unverified_items','editorial_material_complete',
        'blockers','approved','publishing_enabled'])||
       typeof row.request_id!=='string'||!id.test(row.request_id)||
       seen.has(row.request_id)||
       !Number.isSafeInteger(row.revision)||row.revision<1||
       !channels.has(row.channel)||!statuses.has(row.status)||
       !strings(row.missing_items,20)||!strings(row.unverified_items,20)||
       row.missing_items.some(x=>row.unverified_items.includes(x))||
       !strings(row.blockers,7)||
       row.blockers.length<3||row.blockers.some(x=>!blockers.has(x))||
       !always.every(x=>row.blockers.includes(x))||
       typeof row.editorial_material_complete!=='boolean'||
       (row.editorial_material_complete&&
        (row.status!=='ready_for_review'||row.missing_items.length||
         row.unverified_items.length||row.blockers.length!==3))||
       row.approved!==false||row.publishing_enabled!==false)
      throw new TypeError('Untrusted held review item');
    seen.add(row.request_id);
    complete+=Number(row.editorial_material_complete);
    return Object.freeze({
      requestId:row.request_id,revision:row.revision,
      channel:row.channel,status:row.status,
      missingItems:Object.freeze([...row.missing_items]),
      unverifiedItems:Object.freeze([...row.unverified_items]),
      editorialMaterialComplete:row.editorial_material_complete,
      blockers:Object.freeze([...row.blockers]),
      approved:false,publishingEnabled:false
    });
  });
  if(complete!==value.editorial_material_complete_count)
    throw new TypeError('Untrusted editorial review total');
  return Object.freeze({
    tenantId:value.tenant_id,status:'review_preview_only',
    heldCount:value.held_count,editorialMaterialCompleteCount:complete,
    items:Object.freeze(items),approvedCount:0,publishingEnabled:false
  });
 }
 return Object.freeze({read});
});
