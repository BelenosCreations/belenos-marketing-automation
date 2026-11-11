'use strict';
const assert=require('node:assert/strict');
const {generate,confirmFacts}=require('./ai_write_client.js');
const key='a'.repeat(32);
async function main(){
  const calls=[];
  const fetchImpl=async(url,options)=>{
    calls.push({url,options});
    return {ok:true,json:async()=>url.endsWith('/ai-generate')
      ?{created:true,tenant_id:'shop',draft_id:'b'.repeat(32),
        status:'needs_media',publishing_enabled:false}
      :{tenant_id:'shop',facts:{name:'Example Shop'},revision:1,
        provenance:'owner_confirmed',confirmed_at:100,
        publishing_enabled:false}};
  };
  const base={origin:'https://bam.example',token:'valid',
    fetchImpl};
  const result=await generate({...base,requestKey:key,topic:'Tumblers',
    platform:'facebook',needsMedia:true,includeImagePrompt:true});
  assert.equal(result.created,true);
  assert.equal(calls[0].options.method,'POST');
  assert.equal(calls[0].options.credentials,'omit');
  assert.equal(calls[0].options.headers['Idempotency-Key'],key);
  assert.deepEqual(JSON.parse(calls[0].options.body),{
    topic:'Tumblers',platform:'facebook',
    needs_media:true,include_image_prompt:true});
  await confirmFacts({...base,facts:{name:'Example Shop'},
    expectedRevision:0});
  assert.equal(calls[1].options.method,'PUT');
  assert.deepEqual(JSON.parse(calls[1].options.body),{
    facts:{name:'Example Shop'},expected_revision:0});
  await assert.rejects(()=>generate({...base,requestKey:'bad',
    topic:'Tumblers',platform:'facebook',needsMedia:true,
    includeImagePrompt:true}),TypeError);
  await assert.rejects(()=>confirmFacts({...base,
    facts:{tenant_id:'other',name:3},expectedRevision:0}),TypeError);
  await assert.rejects(()=>generate({...base,origin:'http://bam.example',
    requestKey:key,topic:'Tumblers',platform:'facebook',needsMedia:true,
    includeImagePrompt:true}),TypeError);
  assert.equal(calls.length,2);
  console.log('BAM AI explicit write client tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
