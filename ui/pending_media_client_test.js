'use strict';
const assert=require('node:assert/strict');
const {stage,statuses,discard}=require('./pending_media_client.js');
const requestId='a'.repeat(32),attachmentId='b'.repeat(32);
const png=Uint8Array.from([137,80,78,71,13,10,26,10,45]);
const file={type:'image/png',size:png.length,
  arrayBuffer:async()=>png.slice().buffer};
const base={origin:'https://bam.example',token:'t'.repeat(43),
  expectedTenantId:'shop',requestId,item:'image',file,
  hashBytes:async()=> 'f'.repeat(64)};
function fakeFetch(record,override={}){
 return async(url,opts)=>{
   record.push({url,opts});
   if(url.endsWith('/upload-preflight'))return {ok:true,status:202,
     json:async()=>({...{tenant_id:'shop',request_id:requestId,item:'image',
       attachment_id:attachmentId,status:'pending',max_bytes:20*1024*1024,
       upload_url:null,publishing_enabled:false},...override.intent})};
   return {ok:true,status:202,json:async()=>({...{
     tenant_id:'shop',attachment_id:attachmentId,status:'pending_scan',
     bytes_received:png.length,media_verified:false,publishing_enabled:false
   },...override.receipt})};
 };
}
async function main(){
 const calls=[];
 const result=await stage({...base,fetchImpl:fakeFetch(calls)});
 assert.equal(result.status,'pending_scan');
 assert.equal(result.mediaVerified,false);
 assert.equal(result.publishingEnabled,false);
 assert.equal(calls.length,2);
 assert.equal(calls[0].opts.credentials,'omit');
 assert.equal(calls[0].opts.redirect,'error');
 assert.equal(JSON.parse(calls[0].opts.body).request_id,requestId);
 assert.equal(JSON.parse(calls[0].opts.body).sha256,'f'.repeat(64));
 assert.equal(calls[1].opts.method,'PUT');
 assert.equal(calls[1].opts.headers['X-BAM-Attachment-ID'],attachmentId);
 assert.deepEqual([...calls[1].opts.body],[...png]);
 for(const patch of [
  {origin:'http://bam.example'},{token:'invalid'},
  {requestId:'wrong'},{file:null},
  {file:{...file,size:21*1024*1024}},
  {file:{...file,type:'video/mp4'}},
  {hashBytes:async()=> 'invalid'}]){
   const seen=[];
   await assert.rejects(()=>stage({...base,fetchImpl:fakeFetch(seen),...patch}),TypeError);
   assert.equal(seen.length,0);
 }
 await assert.rejects(()=>stage({...base,fetchImpl:fakeFetch([],
   {intent:{tenant_id:'other'}})}),TypeError);
 await assert.rejects(()=>stage({...base,fetchImpl:fakeFetch([],
   {receipt:{media_verified:true}})}),TypeError);
 const states=await statuses({...base,fetchImpl:async(url,opts)=>{
   assert.equal(url,'https://bam.example/api/v1/content/media-status');
   assert.equal(opts.method,'GET');
   assert.equal(opts.credentials,'omit');
   assert.equal(opts.headers.Authorization,'Bearer '+'t'.repeat(43));
   return {ok:true,status:200,json:async()=>({
     tenant_id:'shop',items:[{request_id:requestId,item:'image',
       status:'pending_scan'}],media_verified:false,publishing_enabled:false})};
 }});
 assert.equal(states.items[0].status,'pending_scan');
 assert.equal(states.mediaVerified,false);
 await assert.rejects(()=>statuses({...base,fetchImpl:async()=>({
   ok:true,status:200,json:async()=>({tenant_id:'other',items:[],
     media_verified:false,publishing_enabled:false})})}),TypeError);
 await assert.rejects(()=>statuses({...base,fetchImpl:async()=>({
   ok:true,status:200,json:async()=>({tenant_id:'shop',items:[{
     request_id:requestId,item:'image',status:'verified'}],
     media_verified:false,publishing_enabled:false})})}),TypeError);
 const cancelled=[];
 await assert.rejects(()=>stage({...base,fetchImpl:fakeFetch(cancelled),
   isCurrent:()=>false}),/Session changed/);
 assert.equal(cancelled.length,0);
 let current=true;
 const switched=[];
 await assert.rejects(()=>stage({...base,
   fetchImpl:async(url,opts)=>{
     switched.push({url,opts});
     if(url.endsWith('/upload-preflight'))current=false;
     return fakeFetch([])(url,opts);
   },isCurrent:()=>current}),/Session changed/);
 assert.equal(switched.length,1);
 assert.ok(switched[0].url.endsWith('/upload-preflight'));
 const discarded=await discard({...base,fetchImpl:async(url,opts)=>{
   assert.equal(url,'https://bam.example/api/v1/content/media-pending');
   assert.equal(opts.method,'DELETE');
   assert.equal(opts.credentials,'omit');
   assert.deepEqual(JSON.parse(opts.body),{request_id:requestId,item:'image'});
   return {ok:true,status:200,json:async()=>({
     tenant_id:'shop',request_id:requestId,item:'image',removed:1,
     media_verified:false,publishing_enabled:false})};
 }});
 assert.equal(discarded.removed,1);
 assert.equal(discarded.publishingEnabled,false);
 await assert.rejects(()=>discard({...base,requestId:'bad',fetchImpl:fakeFetch([])}),TypeError);
 await assert.rejects(()=>discard({...base,fetchImpl:async()=>({
   ok:true,status:200,json:async()=>({
     tenant_id:'another',request_id:requestId,item:'image',removed:1,
     media_verified:false,publishing_enabled:false})})}),TypeError);
 console.log('BAM pending manual image return client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
