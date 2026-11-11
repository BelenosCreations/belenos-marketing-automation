'use strict';
const assert=require('node:assert/strict');
const {list,save,discard}=require('./review_feedback_client.js');
const rid='a'.repeat(32),version='b'.repeat(32),next='c'.repeat(32);
const base={origin:'https://bam.example',token:'t'.repeat(43),
 expectedTenantId:'shop',requestId:rid,expectedRevision:2,
 expectedFeedbackToken:version,note:'Please confirm permission for artwork'};
const calls=[];
const data={tenant_id:'shop',status:'feedback_only',
 approval_granted:false,publishing_enabled:false};
const fetchImpl=async(url,opts)=>{
 calls.push({url,opts});
 const body=opts.method==='GET'?{...data,items:[{
   request_id:rid,draft_revision:1,current_revision:2,stale:true,
   note:'Previous feedback',feedback_token:version,updated_at:105,
   approval_granted:false,publishing_enabled:false
 }]}:opts.method==='PUT'?{...data,request_id:rid,
   draft_revision:2,feedback_token:next}:{...data,request_id:rid,removed:1};
 return {ok:true,status:200,json:async()=>body};
};
async function main(){
 const options={...base,fetchImpl};
 const read=await list(options);
 assert.equal(read.items[0].stale,true);
 assert.equal(read.items[0].feedbackToken,version);
 assert.ok(Object.isFrozen(read.items));
 const saved=await save(options);
 assert.equal(saved.feedbackToken,next);
 assert.equal(saved.approvalGranted,false);
 const removed=await discard(options);
 assert.equal(removed.removed,1);
 assert.equal(calls.length,3);
 assert.ok(calls.every(({url})=>url.endsWith('/api/v1/review-feedback')));
 assert.deepEqual(calls.map(x=>x.opts.method),['GET','PUT','DELETE']);
 assert.equal(calls[0].opts.credentials,'omit');
 assert.equal(calls[0].opts.body,undefined);
 assert.deepEqual(JSON.parse(calls[1].opts.body),{
  request_id:rid,expected_revision:2,expected_feedback_token:version,
  note:base.note});
 assert.deepEqual(JSON.parse(calls[2].opts.body),{
  request_id:rid,expected_feedback_token:version});
 assert.equal(calls[2].opts.headers.Authorization,'Bearer '+'t'.repeat(43));
 for(const changes of [
    {origin:'http://bam.example'}, {token:'bad'},
    {requestId:'short'},{expectedFeedbackToken:'invalid'},
    {expectedFeedbackToken:undefined},{expectedRevision:0},
    {expectedRevision:true},{note:' padded '},{note:'x'.repeat(1001)}])
  await assert.rejects(()=>save({...options,...changes}),TypeError);
 for(const field of [
    {tenant_id:'other'},{approval_granted:true},
    {publishing_enabled:true},{status:'approved'}])
  await assert.rejects(()=>list({...options,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({...data,items:[],...field})})}),TypeError);
 await assert.rejects(()=>list({...options,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({...data,items:[{
     request_id:rid,draft_revision:1,current_revision:2,stale:false,
     note:'Modified',feedback_token:version,updated_at:105,
     approval_granted:false,publishing_enabled:false}]})})}),TypeError);
 await assert.rejects(()=>save({...options,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({...data,request_id:rid,
     draft_revision:2,feedback_token:'bad'})})}),TypeError);
 await assert.rejects(()=>discard({...options,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({...data,request_id:rid,
     removed:2})})}),TypeError);
 console.log('BAM conflict-safe private editorial feedback browser tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
