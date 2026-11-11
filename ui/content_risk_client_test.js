'use strict';
const assert=require('node:assert/strict');
const {preview}=require('./content_risk_client.js');
const id='b'.repeat(32),calls=[];
const base={origin:'https://bam.example',fetchImpl:async(url,opts)=>{
 calls.push({url,opts});
 return {ok:true,json:async()=>({tenant_id:'shop',request_id:id,
   revision:3,signals:[{category:'price_or_discount',
    start:0,end:3,text:'$18'}],signal_count:1,truncated:false,
   review_required:true,extraction_complete:false,
   status:'held',publishing_enabled:false})};
},token:'a'.repeat(43),expectedTenantId:'shop',
 requestId:id,expectedRevision:3};
async function main(){
 const result=await preview(base);
 assert.equal(result.signals[0].text,'$18');
 assert.equal(result.publishingEnabled,false);
 assert.equal(result.extractionComplete,false);
 assert.equal(calls[0].url,'https://bam.example/api/v1/content/risk-preview?request_id='+id);
 assert.equal(calls[0].opts.method,'GET');
 assert.equal(calls[0].opts.credentials,'omit');
 assert.equal(calls[0].opts.headers.Authorization,'Bearer '+'a'.repeat(43));
 for(const patch of [{origin:'http://bam.example'},
   {token:'bad'},{requestId:'bad'},{expectedRevision:1.5},
   {expectedRevision:true},{expectedTenantId:''}]){
   await assert.rejects(()=>preview({...base,...patch}),TypeError);
 }
 await assert.rejects(()=>preview({...base,expectedRevision:2}),TypeError);
 await assert.rejects(()=>preview({...base,fetchImpl:async()=>({
   ok:true,json:async()=>({tenant_id:'shop',request_id:id,revision:3,
      signals:[],signal_count:0,truncated:false,review_required:true,
      extraction_complete:false,status:'held',publishing_enabled:true})})}),TypeError);
 await assert.rejects(()=>preview({...base,fetchImpl:async()=>({
   ok:true,json:async()=>({tenant_id:'other',request_id:id,revision:3,
      signals:[],signal_count:0,truncated:false,review_required:true,
      extraction_complete:false,status:'held',publishing_enabled:false})})}),TypeError);
 await assert.rejects(()=>preview({...base,fetchImpl:async()=>({
   ok:true,json:async()=>({tenant_id:'shop',request_id:id,revision:3,
      signals:[{category:'proven_true',start:0,end:3,text:'$18'}],
      signal_count:1,truncated:false,review_required:true,
      extraction_complete:false,status:'held',publishing_enabled:false})})}),TypeError);
 console.log('BAM read-only content risk preview client tests passed');
}
main().catch(err=>{console.error(err);process.exitCode=1});
