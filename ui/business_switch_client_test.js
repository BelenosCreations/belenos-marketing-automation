'use strict';
const assert=require('node:assert/strict');
const {activate}=require('./business_switch_client.js');

const old='a'.repeat(43),fresh='s'.repeat(43);
let requests=[];
const provider=async(url,opts)=>{
  requests.push({url,opts});
  return {ok:true,json:async()=>({
    tenant_id:'other',session_token:fresh,publishing_enabled:false})};
};
async function main(){
  const switched=await activate({origin:'https://bam.example',
    fetchImpl:provider,sessionToken:old,targetTenantId:'other'});
  assert.deepEqual(switched,{sessionToken:fresh,
    tenantId:'other',publishingEnabled:false});
  assert.equal(requests[0].url,'https://bam.example/api/v1/businesses/activate');
  assert.equal(requests[0].opts.method,'POST');
  assert.equal(requests[0].opts.credentials,'omit');
  assert.equal(requests[0].opts.cache,'no-store');
  assert.equal(requests[0].opts.redirect,'error');
  assert.equal(requests[0].opts.headers.Authorization,'Bearer '+old);
  assert.deepEqual(JSON.parse(requests[0].opts.body),
    {target_tenant_id:'other'});
  for(const origin of ['http://bam.example',
      'https://evil.example@bam.example','https://bam.example/path',
      'https://bam.example#fragment']){
    await assert.rejects(()=>activate({origin,fetchImpl:provider,
      sessionToken:old,targetTenantId:'other'}),TypeError);
  }
  await assert.rejects(()=>activate({origin:'https://bam.example',
    fetchImpl:provider,sessionToken:'bad',targetTenantId:'other'}),TypeError);
  await assert.rejects(()=>activate({origin:'https://bam.example',
    fetchImpl:provider,sessionToken:old,targetTenantId:' other '}),TypeError);
  for(const bad of [
    {tenant_id:'wrong',session_token:fresh,publishing_enabled:false},
    {tenant_id:'other',session_token:old,publishing_enabled:false},
    {tenant_id:'other',session_token:123,publishing_enabled:false},
    {tenant_id:'other',session_token:fresh,publishing_enabled:true},
    {tenant_id:'other',session_token:fresh,publishing_enabled:false,
      role:'owner'}
  ]){
    await assert.rejects(()=>activate({origin:'https://bam.example',
      fetchImpl:async()=>({ok:true,json:async()=>bad}),
      sessionToken:old,targetTenantId:'other'}),TypeError);
  }
  await assert.rejects(()=>activate({origin:'https://bam.example',
    fetchImpl:async()=>({ok:false}),sessionToken:old,
    targetTenantId:'other'}),/Unable to change/);
  assert.equal(requests.length,1);
  console.log('BAM business switch session client tests passed');
}
main().catch(err=>{console.error(err);process.exitCode=1});
