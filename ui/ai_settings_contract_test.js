'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./ai_settings_contract.js');
const {read}=require('./dashboard_http_client.js');
const good={tenant_id:'shop',provider:'openai',mode:'bam_sponsored',
  own_key_configured:false,memory:{tone:'friendly'},key_exposed:false,
  publishing_enabled:false};
assert.equal(normalize(good).memory.tone,'friendly');
for(const change of [
  {provider:'another-ai'},{mode:'unknown'},{key_exposed:true},
  {publishing_enabled:true},{api_key:'sk-secret'},
  {vault_reference:'vault:secret'},
  {memory:{tone:3}},{memory:null},
  {mode:'own_openai_key'}
])assert.throws(()=>normalize({...good,...change}),TypeError);
async function main(){
  const response=await read({kind:'aiSettings',token:'valid',
    origin:'https://bam.example',expectedTenantId:'shop',
    fetchImpl:async(url,opts)=>{
      assert.equal(url,'https://bam.example/api/v1/ai-settings');
      assert.equal(opts.method,'GET');
      return {ok:true,json:async()=>good};
    }});
  assert.equal(response.mode,'bam_sponsored');
  await assert.rejects(()=>read({kind:'aiSettings',token:'valid',
    origin:'https://bam.example',expectedTenantId:'other',
    fetchImpl:async()=>({ok:true,json:async()=>good})}),TypeError);
  console.log('BAM OpenAI settings HTTP contract tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
