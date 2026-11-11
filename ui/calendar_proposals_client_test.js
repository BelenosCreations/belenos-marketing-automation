'use strict';
const assert=require('node:assert/strict');
const {list,propose,discard}=require('./calendar_proposals_client.js');
const rid='a'.repeat(32);
const utc='2026-11-11T15:00:00+00:00';
const calls=[];
const base={origin:'https://bam.example',token:'t'.repeat(43),
 expectedTenantId:'shop',requestId:rid,expectedRevision:1,utcAt:utc};
function fetchImpl(url,opts){
 calls.push({url,opts});
 const common={tenant_id:'shop',status:'proposal_only',
   posts_scheduled:0,publishing_enabled:false};
 const data=opts.method==='GET'?{...common,items:[{
   request_id:rid,draft_revision:1,current_revision:1,utc_at:utc,
   local_date:'2026-11-11',local_time:'10:00',timezone:'America/New_York',
   content_changed:false,slot_current:true,publishing_enabled:false
 }]}:opts.method==='POST'?{...common,request_id:rid,utc_at:utc}
   :{...common,request_id:rid,removed:1};
 return Promise.resolve({ok:true,status:opts.method==='POST'?201:200,
    json:async()=>data});
}
async function main(){
 const options={...base,fetchImpl};
 const listed=await list(options);
 assert.equal(listed.items[0].localTime,'10:00');
 assert.equal(listed.items[0].slotCurrent,true);
 assert.equal(listed.postsScheduled,0);
 assert.equal((await propose(options)).status,'proposal_only');
 assert.equal((await discard(options)).removed,1);
 assert.equal(calls.length,3);
 assert.equal(calls[0].opts.method,'GET');
 assert.equal(calls[0].opts.credentials,'omit');
 assert.equal(calls[1].opts.method,'POST');
 assert.deepEqual(JSON.parse(calls[1].opts.body),{
    request_id:rid,expected_revision:1,utc_at:utc});
 assert.equal(calls[2].opts.method,'DELETE');
 assert.deepEqual(JSON.parse(calls[2].opts.body),{request_id:rid});
 assert.equal(calls[2].opts.headers.Authorization,'Bearer '+'t'.repeat(43));
 for(const change of [
   {origin:'http://bam.example'},{token:'short'},{requestId:'bad'},
   {utcAt:'2026-11-11T15:00:00Z'},{expectedRevision:0},
   {expectedRevision:true}])
  await assert.rejects(()=>propose({...options,...change}),TypeError);
 assert.equal(calls.length,3);
 await assert.rejects(()=>list({...options,fetchImpl:async()=>({
   ok:true,status:200,json:async()=>({
    tenant_id:'shop',status:'proposal_only',posts_scheduled:1,
    items:[],publishing_enabled:false})})}),TypeError);
 await assert.rejects(()=>list({...options,fetchImpl:async()=>({
   ok:true,status:200,json:async()=>({
    tenant_id:'other',status:'proposal_only',posts_scheduled:0,
    items:[],publishing_enabled:false})})}),TypeError);
 await assert.rejects(()=>list({...options,fetchImpl:async()=>({
   ok:true,status:200,json:async()=>({
    tenant_id:'shop',status:'proposal_only',posts_scheduled:0,
    items:[{request_id:rid,draft_revision:1,current_revision:1,
      utc_at:utc,local_date:'2026-11-11',local_time:'10:00',
      timezone:'America/New_York',content_changed:false,
      slot_current:true,publishing_enabled:false,approved:true}],
    publishing_enabled:false})})}),TypeError);
 await assert.rejects(()=>propose({...options,fetchImpl:async()=>({
   ok:true,status:201,json:async()=>({
    tenant_id:'shop',request_id:rid,utc_at:utc,
    posts_scheduled:0,status:'scheduled',publishing_enabled:false})})}),TypeError);
 await assert.rejects(()=>discard({...options,fetchImpl:async()=>({
   ok:true,status:200,json:async()=>({
    tenant_id:'shop',request_id:rid,removed:2,
    posts_scheduled:0,status:'proposal_only',publishing_enabled:false})})}),TypeError);
 console.log('BAM strict unpublished calendar proposal browser tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
