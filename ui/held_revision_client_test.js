'use strict';
const assert=require('node:assert/strict');
const {reviseDraft}=require('./held_draft_write_client.js');
const requestId='b'.repeat(32),token='a'.repeat(43),calls=[];
const base={origin:'https://bam.example',token,expectedTenantId:'shop',
  requestId,target:'draft_text',revisedText:'Corrected held copy',
  expectedRevision:2};
async function success(url,opts){
  calls.push({url,opts});
  return {ok:true,json:async()=>({
    tenant_id:'shop',request_id:requestId,status:'needs_content',
    revision:3,publishing_enabled:false})};
}
async function main(){
  const saved=await reviseDraft({...base,fetchImpl:success});
  assert.equal(saved.revision,3);
  assert.equal(saved.status,'needs_content');
  assert.equal(saved.publishingEnabled,false);
  assert.equal(calls[0].url,'https://bam.example/api/v1/content/drafts');
  assert.equal(calls[0].opts.method,'PUT');
  assert.equal(calls[0].opts.credentials,'omit');
  assert.equal(calls[0].opts.mode,'same-origin');
  assert.equal(calls[0].opts.cache,'no-store');
  assert.equal(calls[0].opts.headers.Authorization,'Bearer '+token);
  assert.deepEqual(JSON.parse(calls[0].opts.body),{
    request_id:requestId,target:'draft_text',
    revised_text:'Corrected held copy',expected_revision:2});
  for(const invalid of [
    {origin:'http://bam.example'},
    {expectedTenantId:' '},{token:'bad'},
    {requestId:'bad'},{target:'status'},
    {target:'required_items'},{revisedText:''},
    {revisedText:' Extra whitespace '},
    {revisedText:'a'.repeat(2001)},
    {expectedRevision:0},{expectedRevision:true},
    {expectedRevision:1.5}]){
    await assert.rejects(()=>reviseDraft({
      ...base,fetchImpl:success,...invalid}),TypeError);
  }
  assert.equal(calls.length,1);
  const malformed=[
    {tenant_id:'other',request_id:requestId,status:'needs_content',
     revision:3,publishing_enabled:false},
    {tenant_id:'shop',request_id:requestId,status:'approved',
     revision:3,publishing_enabled:false},
    {tenant_id:'shop',request_id:requestId,status:'needs_content',
     revision:2,publishing_enabled:false},
    {tenant_id:'shop',request_id:requestId,status:'needs_content',
     revision:3,publishing_enabled:true},
    {tenant_id:'shop',request_id:requestId,status:'needs_content',
     revision:3,publishing_enabled:false,auto_publish:true}
  ];
  for(const value of malformed){
    await assert.rejects(()=>reviseDraft({...base,fetchImpl:async()=>({
      ok:true,json:async()=>value})}),TypeError);
  }
  await assert.rejects(()=>reviseDraft({...base,fetchImpl:async()=>({
    ok:false})}),Error);
  console.log('BAM revision-guarded manual held-draft client tests passed');
}
main().catch(err=>{console.error(err);process.exitCode=1});
