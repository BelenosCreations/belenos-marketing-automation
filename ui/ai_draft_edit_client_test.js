'use strict';
const assert=require('node:assert/strict');
const {revise}=require('./ai_draft_edit_client.js');
const calls=[],tenant='shop',draftId='b'.repeat(32);
const base={origin:'https://bam.example',sessionToken:'a'.repeat(43),
  expectedTenantId:tenant,draftId,target:'post_text',
  revisedText:'Corrected copy',expectedRevision:1};
const fetchImpl=async(url,opts)=>{
  calls.push({url,opts});
  const body=JSON.parse(opts.body);
  return {ok:true,json:async()=>({
    tenant_id:tenant,draft_id:draftId,platform:'facebook',
    post_text:body.target==='post_text'?body.revised_text:'Original',
    image_prompt:body.target==='image_prompt'?body.revised_text:'Conceptual image',
    needs_media:true,media_attached:false,status:'needs_media',
    revision:body.expected_revision+1,publishing_enabled:false})};
};
async function main(){
  const result=await revise({...base,fetchImpl});
  assert.equal(result.revision,2);
  assert.equal(result.publishingEnabled,false);
  assert.equal(calls[0].url,'https://bam.example/api/v1/ai-drafts');
  assert.equal(calls[0].opts.method,'PUT');
  assert.equal(calls[0].opts.credentials,'omit');
  assert.equal(calls[0].opts.mode,'same-origin');
  assert.equal(calls[0].opts.redirect,'error');
  assert.deepEqual(JSON.parse(calls[0].opts.body),{
    draft_id:draftId,target:'post_text',revised_text:'Corrected copy',
    expected_revision:1});
  await revise({...base,fetchImpl,target:'image_prompt',
    revisedText:'Revised generic concept'});
  assert.equal(calls.length,2);
  for(const override of [
    {origin:'http://bam.example'},{sessionToken:'bad'},
    {expectedTenantId:' '},{draftId:'wrong'},
    {target:'publish'},{expectedRevision:0},{expectedRevision:true},
    {revisedText:''},{revisedText:'X'.repeat(4001)},
    {target:'image_prompt',revisedText:'X'.repeat(2001)}]){
    await assert.rejects(()=>revise({...base,fetchImpl,...override}),TypeError);
  }
  await assert.rejects(()=>revise({...base,
    fetchImpl:async()=>({ok:true,json:async()=>({
      tenant_id:'other',draft_id:draftId,platform:'facebook',
      post_text:'Corrected copy',image_prompt:'Conceptual image',
      needs_media:true,media_attached:false,status:'needs_media',
      revision:2,publishing_enabled:false})})}),TypeError);
  await assert.rejects(()=>revise({...base,
    fetchImpl:async()=>({ok:true,json:async()=>({
      tenant_id:'shop',draft_id:draftId,platform:'facebook',
      post_text:'Corrected copy',image_prompt:'Conceptual image',
      needs_media:true,media_attached:false,status:'needs_media',
      revision:2,publishing_enabled:true})})}),TypeError);
  assert.equal(calls.length,2);
  console.log('BAM manual AI draft revision client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
