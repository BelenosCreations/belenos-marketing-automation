'use strict';
const assert=require('node:assert/strict');
const {create}=require('./local_product_draft_client.js');
const calls=[];
const base={origin:'https://bam.example',sessionToken:'a'.repeat(43),
  expectedTenantId:'shop',platform:'facebook',includeImagePrompt:true};
const fetchImpl=async(url,opts)=>{
  calls.push({url,opts});
  const data=JSON.parse(opts.body);
  return {ok:true,json:async()=>({
    tenant_id:'shop',draft_id:'b'.repeat(32),platform:data.platform,
    post_text:'Example Shop: Custom tumblers. Contact us for details.',
    image_prompt:data.include_image_prompt?'Generic conceptual graphic':null,
    needs_media:data.include_image_prompt,media_attached:false,
    status:data.include_image_prompt?'needs_media':'draft_pending_verification',
    revision:1,publishing_enabled:false,
    generation_method:'local_template',openai_requests:0})};
};
async function main(){
  const result=await create({...base,fetchImpl});
  assert.equal(result.openaiRequests,0);
  assert.equal(result.status,'needs_media');
  assert.equal(calls[0].url,'https://bam.example/api/v1/ai/local-product-draft');
  assert.equal(calls[0].opts.method,'POST');
  assert.equal(calls[0].opts.credentials,'omit');
  assert.equal(calls[0].opts.mode,'same-origin');
  assert.equal(calls[0].opts.cache,'no-store');
  assert.deepEqual(JSON.parse(calls[0].opts.body),{
    platform:'facebook',include_image_prompt:true});
  assert.equal(calls[0].opts.headers.Authorization,'Bearer '+'a'.repeat(43));
  await create({...base,fetchImpl,includeImagePrompt:false});
  assert.equal(calls.length,2);
  for(const patch of [
    {origin:'http://bam.example'},{sessionToken:'bad'},
    {expectedTenantId:''},{platform:'unknown'},
    {includeImagePrompt:'yes'}]){
    await assert.rejects(()=>create({...base,fetchImpl,...patch}),TypeError);
  }
  await assert.rejects(()=>create({...base,
    fetchImpl:async()=>({ok:true,json:async()=>({
      tenant_id:'other',draft_id:'b'.repeat(32),platform:'facebook',
      post_text:'Valid',image_prompt:'Generic',needs_media:true,
      media_attached:false,status:'needs_media',revision:1,
      publishing_enabled:false,generation_method:'local_template',
      openai_requests:0})})}),TypeError);
  await assert.rejects(()=>create({...base,
    fetchImpl:async()=>({ok:true,json:async()=>({
      tenant_id:'shop',draft_id:'b'.repeat(32),platform:'facebook',
      post_text:'Valid',image_prompt:'Generic',needs_media:true,
      media_attached:false,status:'needs_media',revision:1,
      publishing_enabled:false,generation_method:'local_template',
      openai_requests:1})})}),TypeError);
  assert.equal(calls.length,2);
  console.log('BAM zero-cost local product draft browser tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
