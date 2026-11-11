'use strict';
const assert=require('node:assert/strict');
const {stage}=require('./pending_media_client.js');
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
 console.log('BAM pending manual image return client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
