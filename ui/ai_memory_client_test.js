'use strict';
const assert=require('node:assert/strict');
const {save,validMap}=require('./ai_memory_client.js');
const proposed={tone:'Short Facebook posts',audience:'Local customers'};
const prior={tone:'Long'};
const calls=[];
const base={origin:'https://bam.example',sessionToken:'t'.repeat(43),
  expectedTenantId:'shop',memory:proposed,expectedMemory:prior};
async function fetchImpl(url,opts){
  calls.push({url,opts});
  return {ok:true,status:200,json:async()=>({
    tenant_id:'shop',memory:proposed,publishing_enabled:false})};
}
async function main(){
  const saved=await save({...base,fetchImpl});
  assert.equal(saved.memory.tone,'Short Facebook posts');
  assert.equal(saved.publishingEnabled,false);
  assert.equal(calls[0].url,'https://bam.example/api/v1/ai-memory');
  assert.equal(calls[0].opts.method,'PUT');
  assert.equal(calls[0].opts.credentials,'omit');
  assert.equal(calls[0].opts.headers.Authorization,'Bearer '+'t'.repeat(43));
  assert.deepEqual(JSON.parse(calls[0].opts.body),{
    memory:proposed,expected_memory:prior});
  for(const invalid of [
    {origin:'http://bam.example'},{sessionToken:'bad'},
    {expectedTenantId:' '},{memory:{tone:' '}},
    {memory:{token:'secret'}},{memory:{'api_key':'sk-test'}},
    {memory:{tone:'sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ12345'}},
    {memory:{tone:1}},{memory:{'':'x'}},
    {expectedMemory:{tone:' '}},
    {memory:Object.fromEntries(Array.from({length:41},(_,i)=>['k'+i,'v']))}
  ])await assert.rejects(()=>save({...base,fetchImpl,...invalid}),TypeError);
  assert.equal(calls.length,1);
  assert.equal(validMap({}),true);
  assert.equal(validMap({'style':'Brief.'}),true);
  assert.equal(validMap({'password':'never'}),false);
  await assert.rejects(()=>save({...base,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({
      tenant_id:'other',memory:proposed,publishing_enabled:false})})}),TypeError);
  await assert.rejects(()=>save({...base,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({
      tenant_id:'shop',memory:proposed,
      publishing_enabled:true})})}),TypeError);
  await assert.rejects(()=>save({...base,fetchImpl:async()=>({
    ok:true,status:200,json:async()=>({
      tenant_id:'shop',memory:{tone:'Different'},
      publishing_enabled:false})})}),TypeError);
  await assert.rejects(()=>save({...base,fetchImpl:async()=>({
    ok:false,status:409})}),Error);
  console.log('BAM tenant-scoped per-user AI preference client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
