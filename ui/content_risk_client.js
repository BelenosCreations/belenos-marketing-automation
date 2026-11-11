/* Private, read-only heuristic marketing claim hints for one current draft.
 * Never fact verification, approval, scheduling, or publication.
 */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMContentRiskClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const id=/^[a-f0-9]{32}$/;
 const token=/^[A-Za-z0-9_-]{32,2048}$/;
 const categories=new Set(['price_or_discount','guarantee',
   'urgency_or_availability','business_hours','testimonial']);
 function exact(record,keys){
   return record&&typeof record==='object'&&!Array.isArray(record)&&
     Object.keys(record).length===keys.length&&
     keys.every(k=>Object.prototype.hasOwnProperty.call(record,k));
 }
 async function preview({origin,fetchImpl,token:bearer,expectedTenantId,
                         requestId,expectedRevision}){
   if(typeof origin!=='string'||
      !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
      typeof fetchImpl!=='function'||!token.test(bearer)||
      typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
      expectedTenantId.length>128||!id.test(requestId)||
      !Number.isSafeInteger(expectedRevision)||expectedRevision<1)
     throw new TypeError('Current BAM draft session and revision required');
   const response=await fetchImpl(origin+
     '/api/v1/content/risk-preview?request_id='+requestId,{
       method:'GET',mode:'same-origin',credentials:'omit',cache:'no-store',
       redirect:'error',headers:{Authorization:'Bearer '+bearer,
         Accept:'application/json'}
     });
   if(!response||!response.ok)throw new Error('Marketing risk preview unavailable');
   const body=await response.json();
   if(!exact(body,['tenant_id','request_id','revision','signals',
      'signal_count','truncated','review_required','extraction_complete',
      'status','publishing_enabled'])||
      body.tenant_id!==expectedTenantId||body.request_id!==requestId||
      body.revision!==expectedRevision||!Array.isArray(body.signals)||
      body.signals.length>50||
      !Number.isSafeInteger(body.signal_count)||
      body.signal_count<body.signals.length||
      body.truncated!==(body.signal_count>body.signals.length)||
      body.review_required!==true||body.extraction_complete!==false||
      body.status!=='held'||body.publishing_enabled!==false)
     throw new TypeError('Untrusted review preview');
   const signals=body.signals.map(row=>{
     if(!exact(row,['category','start','end','text'])||
        !categories.has(row.category)||
        !Number.isSafeInteger(row.start)||
        !Number.isSafeInteger(row.end)||
        !(0<=row.start&&row.start<row.end&&row.end<=2000)||
        typeof row.text!=='string'||!row.text||
        row.text.length!==row.end-row.start)
       throw new TypeError('Invalid marketing claim risk signal');
     return Object.freeze({category:row.category,
       start:row.start,end:row.end,text:row.text});
   });
   return Object.freeze({tenantId:body.tenant_id,
     requestId:body.request_id,revision:body.revision,
     signals:Object.freeze(signals),signalCount:body.signal_count,
     truncated:body.truncated,reviewRequired:true,
     extractionComplete:false,publishingEnabled:false});
 }
 return Object.freeze({preview});
});
