'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./ai_facts_contract.js');
const {read}=require('./dashboard_http_client.js');
const confirmed={tenant_id:'shop',facts:{business_name:'Example Shop'},
  revision:1,provenance:'owner_confirmed',confirmed_at:100,
  publishing_enabled:false};
assert.equal(normalize(confirmed).facts.business_name,'Example Shop');
const empty={tenant_id:'shop',facts:{},revision:0,
  provenance:'not_configured',confirmed_at:null,publishing_enabled:false};
assert.equal(normalize(empty).revision,0);
for(const change of [
  {provenance:'verified_by_google'},{publishing_enabled:true},
  {revision:0},{facts:{}},{confirmed_at:null},
  {facts:{business_name:3}}
])assert.throws(()=>normalize({...confirmed,...change}),TypeError);
async function main(){
  const result=await read({kind:'aiFacts',token:'valid',
    expectedTenantId:'shop',origin:'https://bam.example',
    fetchImpl:async(url,options)=>{
      assert.equal(url,'https://bam.example/api/v1/ai-business-facts');
      assert.equal(options.method,'GET');
      return {ok:true,json:async()=>confirmed};
    }});
  assert.equal(result.provenance,'owner_confirmed');
  await assert.rejects(()=>read({kind:'aiFacts',token:'valid',
    expectedTenantId:'other',origin:'https://bam.example',
    fetchImpl:async()=>({ok:true,json:async()=>confirmed})}),TypeError);
  console.log('BAM owner-confirmed AI facts HTTP tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
