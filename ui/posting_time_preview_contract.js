/* Verified, strictly informational BAM posting-time preview.
 * Never presents proposed wall-clock times as queued or published posts.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMPostingTimePreviewData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const date=/^\d{4}-\d{2}-\d{2}$/;
  const clock=/^(?:[01]\d|2[0-3]):[0-5]\d$/;
  const instant=/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d\+00:00$/;
  const allowed=['tenant_id','mode','timezone','status','slots',
    'skipped_dst','truncated','publishing_enabled'];
  function normalize(body){
    if(!body||typeof body!=='object'||Array.isArray(body)||
       Object.keys(body).some(k=>!allowed.includes(k))||
       typeof body.tenant_id!=='string'||!body.tenant_id.trim()||
       body.tenant_id.length>128||!['manual','smart'].includes(body.mode)||
       !['manual_preview','needs_audience_data','not_configured'].includes(body.status)||
       body.publishing_enabled!==false||!Array.isArray(body.slots)||
       body.slots.length>30||!Number.isSafeInteger(body.skipped_dst)||
       body.skipped_dst<0||body.skipped_dst>336||
       typeof body.truncated!=='boolean')
      throw new TypeError('Invalid posting time preview response');
    if(body.status==='not_configured'){
      if(body.mode!=='smart'||body.timezone!==null||body.slots.length||
         body.skipped_dst!==0||body.truncated)
        throw new TypeError('Unconfigured posting time preview must be empty');
    }else{
      if(typeof body.timezone!=='string'||!body.timezone.trim()||
         body.timezone.length>80)
        throw new TypeError('Posting preview timezone required');
      if((body.mode==='manual')!==(body.status==='manual_preview'))
        throw new TypeError('Posting preview mode mismatch');
      if(body.mode==='smart'&&(body.slots.length||body.skipped_dst||body.truncated))
        throw new TypeError('No invented smart posting recommendations');
    }
    const seen=new Set();
    let last='';
    const slots=body.slots.map(slot=>{
      if(!slot||typeof slot!=='object'||Array.isArray(slot)||
         Object.keys(slot).sort().join(',')!=='local_date,local_time,utc_at'||
         typeof slot.local_date!=='string'||!date.test(slot.local_date)||
         typeof slot.local_time!=='string'||!clock.test(slot.local_time)||
         typeof slot.utc_at!=='string'||!instant.test(slot.utc_at)||
         !Number.isFinite(Date.parse(slot.utc_at))||
         (last&&last>=slot.utc_at))
        throw new TypeError('Invalid or unordered local time preview');
      last=slot.utc_at;
      const key=slot.local_date+slot.local_time;
      if(seen.has(key))throw new TypeError('Duplicate local time proposal');
      seen.add(key);
      return Object.freeze({localDate:slot.local_date,localTime:slot.local_time,
        utcAt:slot.utc_at});
    });
    return Object.freeze({tenantId:body.tenant_id,mode:body.mode,
      timezone:body.timezone,status:body.status,
      slots:Object.freeze(slots),skippedDst:body.skipped_dst,
      truncated:body.truncated,publishingEnabled:false});
  }
  return Object.freeze({normalize});
});
