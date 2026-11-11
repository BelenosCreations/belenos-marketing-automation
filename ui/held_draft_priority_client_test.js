'use strict';
const assert=require('node:assert/strict');
const {update}=require('./held_draft_priority_client.js');
const RID='a'.repeat(32),OLD='b'.repeat(32),NEW='c'.repeat(32);
const calls=[];
const base={origin:'https://bam.example',fetchImpl:async(url,opts)=>{
  calls.push({url,opts});
  return {ok:true,status:200,json:async()=>({
    tenant_id:'shop',request_id:RID,priority:2,
    priority_token:NEW,revision:3,status:'held_priority_only',
    publishing_enabled:false})};
},token:'t'.repeat(43),expectedTenantId:'shop',
 requestId:RID,priority:2,expectedPriorityToken:OLD,
 expectedContentRevision:3};
async function main(){
 const result=await update(base);
 assert.equal(result.priority,2);
 assert.equal(result.priorityToken,NEW);
 assert.equal(result.contentRevision,3);
 assert.equal(result.publishingEnabled,false);
 assert.equal(calls[0].url,'https://bam.example/api/v1/content/priority');
 assert.equal(calls[0].opts.method,'PUT');
 assert.equal(calls[0].opts.credentials,'omit');
 assert.deepEqual(JSON.parse(calls[0].opts.body),{
   request_id:RID,priority:2,expected_priority_token:OLD});
 assert.equal(calls[0].opts.headers.Authorization,'Bearer '+'t'.repeat(43));
 for(const invalid of [
   {origin:'http://bam.example'},{token:'bad'},
   {expectedTenantId:''},{requestId:'bad'},
   {priority:11},{priority:-11},{priority:true},
   {expectedPriorityToken:'bad'},{expectedPriorityToken:null},
   {expectedContentRevision:0}
 ])await assert.rejects(()=>update({...base,...invalid}),TypeError);
 assert.equal(calls.length,1);
 for(const bad of [
   {tenant_id:'another'},
   {status:'scheduled'},
   {publishing_enabled:true},
   {priority:1},{revision:4},
   {priority_token:OLD},
   {priority_token:'not-a-version'},
   {approved:true}
 ])await assert.rejects(()=>update({...base,fetchImpl:async()=>({
   ok:true,status:200,json:async()=>({
     tenant_id:'shop',request_id:RID,priority:2,
     priority_token:NEW,revision:3,status:'held_priority_only',
     publishing_enabled:false,...bad
   })})}),TypeError);
 await assert.rejects(()=>update({...base,fetchImpl:async()=>({
   ok:false,status:409
 })}),Error);
 console.log('BAM strict nonpublishing priority update browser tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
