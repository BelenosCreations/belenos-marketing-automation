'use strict';
const assert=require('node:assert/strict');
const {revise,newRequestKey}=require('./ai_targeted_revision_client.js');
const draftId='a'.repeat(32),requestKey='b'.repeat(32);
const requests=[];
const base={origin:'https://bam.example',token:'t'.repeat(43),
  expectedTenantId:'shop',draftId,expectedRevision:1,
  target:'post_text',instruction:'Shorten the wording',
  topic:'Custom tumblers',requestKey};
async function fetchImpl(url,opts){
  requests.push({url,opts});
  return {ok:true,status:201,json:async()=>({
    revised:true,tenant_id:'shop',draft_id:draftId,revision:2,
    status:'needs_media',publishing_enabled:false})};
}
async function main(){
  const one=await revise({...base,fetchImpl});
  assert.equal(one.revised,true);
  assert.equal(one.revision,2);
  assert.equal(one.publishingEnabled,false);
  assert.equal(requests[0].url,
    'https://bam.example/api/v1/ai/targeted-revision');
  assert.equal(requests[0].opts.method,'POST');
  assert.equal(requests[0].opts.credentials,'omit');
  assert.equal(requests[0].opts.headers.Authorization,
    'Bearer '+'t'.repeat(43));
  assert.equal(requests[0].opts.headers['Idempotency-Key'],requestKey);
  assert.deepEqual(JSON.parse(requests[0].opts.body),{
    draft_id:draftId,expected_revision:1,target:'post_text',
    instruction:'Shorten the wording',topic:'Custom tumblers'});
  const hold=await revise({...base,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({revised:false,tenant_id:'shop',
      reason:'already_in_progress',publishing_enabled:false})})});
  assert.equal(hold.revised,false);
  assert.equal(hold.reason,'already_in_progress');
  for(const patch of [
    {origin:'http://bam.example'},{token:'invalid'},
    {expectedTenantId:' '},{draftId:'invalid'},
    {requestKey:'not-a-key'},{expectedRevision:0},
    {expectedRevision:true},{target:'publish'},
    {instruction:''},{instruction:'a'.repeat(501)},
    {topic:''},{topic:'t'.repeat(301)}
  ])await assert.rejects(()=>revise({...base,fetchImpl,...patch}),TypeError);
  assert.equal(requests.length,1);
  for(const payload of [
    {revised:true,tenant_id:'another',draft_id:draftId,revision:2,
     status:'needs_media',publishing_enabled:false},
    {revised:true,tenant_id:'shop',draft_id:draftId,revision:3,
     status:'needs_media',publishing_enabled:false},
    {revised:true,tenant_id:'shop',draft_id:draftId,revision:2,
     status:'published',publishing_enabled:false},
    {revised:true,tenant_id:'shop',draft_id:draftId,revision:2,
     status:'needs_media',publishing_enabled:true},
    {revised:true,tenant_id:'shop',draft_id:draftId,revision:2,
     status:'needs_media',publishing_enabled:false,secret:'vault-key'}
  ])await assert.rejects(()=>revise({...base,fetchImpl:async()=>({
    ok:true,status:201,json:async()=>payload})}),TypeError);
  await assert.rejects(()=>revise({...base,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({revised:false,
      tenant_id:'shop',reason:'published',
      publishing_enabled:false})})}),TypeError);
  await assert.rejects(()=>revise({...base,fetchImpl:async()=>({
    ok:false,status:503})}),Error);
  const random={getRandomValues(bytes){
    bytes[0]=10;bytes[15]=255;return bytes;
  }};
  assert.equal(newRequestKey(random),'0a'+'00'.repeat(14)+'ff');
  assert.throws(()=>newRequestKey(null),TypeError);
  assert.throws(()=>newRequestKey({getRandomValues:bytes=>bytes}),TypeError);
  console.log('BAM explicit targeted AI revision browser client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
