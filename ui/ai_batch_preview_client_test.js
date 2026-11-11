'use strict';
const assert=require('node:assert/strict');
const {preview,validTopics}=require('./ai_batch_preview_client.js');
const base={origin:'https://bam.example',token:'t'.repeat(43),
 expectedTenantId:'shop',topics:['Product highlight','Gift idea'],
 platform:'facebook',includeImagePrompt:true};
const calls=[];
const result={tenant_id:'shop',mode:'bam_sponsored',
 fact_revision:2,fact_provenance:'owner_confirmed',
 items:[{topic:'Product highlight',platform:'facebook',
         image_prompt_planned:true},
        {topic:'Gift idea',platform:'facebook',
         image_prompt_planned:true}],
 planned_individual_requests:2,provider_requests_made:0,
 quota_reserved:false,actual_cost_known:false,
 drafts_created:0,status:'planning_only',publishing_enabled:false};
const fetchImpl=async(url,opts)=>{
 calls.push({url,opts});
 return {ok:true,status:200,json:async()=>result};
};
async function main(){
 const data=await preview({...base,fetchImpl});
 assert.equal(data.status,'planning_only');
 assert.equal(data.plannedIndividualRequests,2);
 assert.equal(data.providerRequestsMade,0);
 assert.equal(data.draftsCreated,0);
 assert.equal(data.publishingEnabled,false);
 assert.equal(calls[0].url,'https://bam.example/api/v1/ai/batch-preview');
 assert.equal(calls[0].opts.method,'POST');
 assert.equal(calls[0].opts.credentials,'omit');
 assert.deepEqual(JSON.parse(calls[0].opts.body),{
   topics:base.topics,platform:'facebook',include_image_prompt:true
 });
 assert.equal(Object.isFrozen(data.items),true);
 assert.equal(validTopics(['Gift idea','Other']),true);
 assert.equal(validTopics(['Gift idea','gift idea']),false);
 for(const patch of [
  {origin:'http://bam.example'},{token:'bad'}, {expectedTenantId:''},
  {topics:['Same','same']},{topics:[]},{topics:[' A ']},
  {topics:Array(15).fill('same')},{topics:['']},
  {includeImagePrompt:'yes'},{platform:'unknown'}
 ])await assert.rejects(()=>preview({...base,fetchImpl,...patch}),TypeError);
 assert.equal(calls.length,1);
 for(const invalid of [
   {...result,provider_requests_made:1},
   {...result,quota_reserved:true},
   {...result,publishing_enabled:true},
   {...result,actual_cost_known:true},
   {...result,drafts_created:2},
   {...result,tenant_id:'other'},
   {...result,mode:'unknown'},
   {...result,status:'scheduled'},
   {...result,items:[{...result.items[0],publish_now:true},result.items[1]]},
   {...result,items:[{...result.items[0],topic:'Wrong'},result.items[1]]},
   {...result,secret:'vault:secret'},
 ])await assert.rejects(()=>preview({...base,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>invalid})}),TypeError);
 await assert.rejects(()=>preview({...base,fetchImpl:async()=>({
    ok:false,status:503})}),Error);
 console.log('BAM zero-cost advance AI batch preview client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
