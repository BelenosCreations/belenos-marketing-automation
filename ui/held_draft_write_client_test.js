'use strict';
const assert=require('node:assert/strict');
const {createDraft,changeHold}=require('./held_draft_write_client.js');
const token='a'.repeat(43),id='b'.repeat(32);
async function main(){
  const requests=[];
  const fetchImpl=async(url,opts)=>{
    requests.push({url,opts});
    const state=url.endsWith('/drafts')?'needs_content':
      JSON.parse(opts.body).status;
    return {ok:true,json:async()=>({tenant_id:'shop',request_id:id,
      status:state,publishing_enabled:false})};
  };
  const ctx={origin:'https://bam.example',fetchImpl,token,expectedTenantId:'shop'};
  const created=await createDraft({...ctx,channel:'facebook',
    draftText:'New tumbler',suggestion:'Need a verified photo',
    requiredItems:['image'],priority:1});
  assert.equal(created.id,id);
  assert.equal(created.publishingEnabled,false);
  assert.deepEqual(JSON.parse(requests[0].opts.body),{
    channel:'facebook',draft_text:'New tumbler',
    suggestion:'Need a verified photo',required_items:['image'],priority:1});
  assert.equal(requests[0].opts.credentials,'omit');
  assert.equal(requests[0].opts.mode,'same-origin');
  assert.equal(requests[0].opts.redirect,'error');
  assert.equal(requests[0].opts.cache,'no-store');
  assert.equal(requests[0].opts.headers.Authorization,'Bearer '+token);
  const changed=await changeHold({...ctx,requestId:id,status:'postponed',
    expectedRevision:1});
  assert.equal(changed.status,'postponed');
  assert.equal(requests[1].url,'https://bam.example/api/v1/content/hold');
  assert.deepEqual(JSON.parse(requests[1].opts.body),{
    request_id:id,status:'postponed',expected_revision:1});
  const count=requests.length;
  for(const item of [
    {channel:'facebook',draftText:'copy',suggestion:'guide',
      requiredItems:[],priority:0},
    {channel:'facebook',draftText:'copy',suggestion:'guide',
      requiredItems:['image','image']},
    {channel:'facebook',draftText:'copy',suggestion:'guide',
      requiredItems:['image'],priority:true},
    {channel:'facebook',draftText:'copy',suggestion:'guide',
      requiredItems:['image'],tenant_id:'other'},
    {channel:'facebook',draftText:'copy',suggestion:'guide',
      requiredItems:['image'],priority:12}
  ]){
    if(item.tenant_id)continue;
    await assert.rejects(()=>createDraft({...ctx,...item}),TypeError);
  }
  for(const status of ['published','approved','ready_for_review'])
    await assert.rejects(()=>changeHold({...ctx,requestId:id,status,
      expectedRevision:1}),TypeError);
  await assert.rejects(()=>changeHold({...ctx,requestId:id,
    status:'postponed'}),TypeError);
  await assert.rejects(()=>changeHold({...ctx,requestId:id,
    status:'postponed',expectedRevision:true}),TypeError);
  await assert.rejects(()=>changeHold({...ctx,requestId:'not-an-id',
    status:'postponed'}),TypeError);
  await assert.rejects(()=>createDraft({...ctx,origin:'http://bam.example',
    channel:'facebook',draftText:'copy',suggestion:'guide',
    requiredItems:['image']}),TypeError);
  await assert.rejects(()=>createDraft({...ctx,fetchImpl:async()=>({
    ok:true,json:async()=>({tenant_id:'other',request_id:id,
      status:'needs_content',publishing_enabled:false})}),
    channel:'facebook',draftText:'copy',suggestion:'guide',
    requiredItems:['image']}),TypeError);
  await assert.rejects(()=>changeHold({...ctx,fetchImpl:async()=>({
    ok:true,json:async()=>({tenant_id:'shop',request_id:id,
      status:'postponed',publishing_enabled:true})}),
    requestId:id,status:'postponed',expectedRevision:1}),TypeError);
  assert.equal(requests.length,count);
  console.log('BAM held draft write boundary tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
