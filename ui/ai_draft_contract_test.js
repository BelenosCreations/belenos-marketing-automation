'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./ai_draft_contract.js');
const {read}=require('./dashboard_http_client.js');
const good={tenant_id:'shop',publishing_enabled:false,drafts:[{
  tenant_id:'shop',draft_id:'a'.repeat(32),platform:'facebook',
  post_text:'<img src=x onerror=alert(1)>',
  image_prompt:'Neutral product photo',needs_media:true,
  media_attached:false,status:'needs_media',revision:1,
  publishing_enabled:false
}]};
assert.equal(normalize(good).drafts[0].status,'needs_media');
assert.equal(normalize(good).drafts[0].postText,
  '<img src=x onerror=alert(1)>');
for(const change of [
  {tenant_id:'other'},{media_attached:true},{publishing_enabled:true},
  {status:'published'},{revision:0},{needs_media:false},
  {image_prompt:123}
]){
  const bad=JSON.parse(JSON.stringify(good));
  Object.assign(bad.drafts[0],change);
  assert.throws(()=>normalize(bad),TypeError);
}
async function main(){
  const response=await read({kind:'aiDrafts',token:'valid',
    expectedTenantId:'shop',origin:'https://bam.example',
    fetchImpl:async(url,options)=>{
      assert.equal(url,'https://bam.example/api/v1/ai-drafts');
      assert.equal(options.method,'GET');
      return {ok:true,json:async()=>good};
    }});
  assert.equal(response.drafts.length,1);
  await assert.rejects(()=>read({kind:'aiDrafts',token:'valid',
    expectedTenantId:'other',origin:'https://bam.example',
    fetchImpl:async()=>({ok:true,json:async()=>good})}),TypeError);
  console.log('BAM AI draft HTTP contract tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
