'use strict';
const assert=require('node:assert/strict');
const {list,change}=require('./team_members_client.js');
const token='t'.repeat(43),id='m'.repeat(32);
const ctx={origin:'https://bam.example',token,expectedTenantId:'shop'};
const roster={tenant_id:'shop',status:'private_team_preview',
  members:[
    {member_id:'o'.repeat(32),role:'owner',active:true,revision:1,
     email:'owner@example.com',is_self:true},
    {member_id:id,role:'content_creator',active:true,revision:1,
     email:'worker@example.com',is_self:false}
  ],publishing_enabled:false};
async function main(){
  const calls=[];
  const fetchImpl=async(url,opts)=>{
    calls.push({url,opts});
    if(opts.method==='GET')return {ok:true,json:async()=>roster};
    const submitted=JSON.parse(opts.body);
    return {ok:true,json:async()=>({
      tenant_id:'shop',member_id:submitted.member_id,
      status:submitted.action==='deactivate'?'deactivated':'updated',
      revision:submitted.expected_revision+1,
      sessions_revoked:2,publishing_enabled:false})};
  };
  const data=await list({...ctx,fetchImpl});
  assert.equal(data.members.length,2);
  assert.equal(data.members[1].email,'worker@example.com');
  assert.ok(Object.isFrozen(data.members[0]));
  assert.equal(calls[0].opts.credentials,'omit');
  assert.equal(calls[0].opts.mode,'same-origin');
  assert.equal(calls[0].opts.cache,'no-store');
  const result=await change({...ctx,fetchImpl,memberId:id,
    action:'change_role',role:'viewer',expectedRevision:1});
  assert.equal(result.revision,2);
  assert.deepEqual(JSON.parse(calls[1].opts.body),{
    member_id:id,action:'change_role',expected_revision:1,role:'viewer'});
  assert.equal(result.publishingEnabled,false);
  await change({...ctx,fetchImpl,memberId:id,
    action:'deactivate',expectedRevision:2});
  assert.deepEqual(JSON.parse(calls[2].opts.body),{
    member_id:id,action:'deactivate',expected_revision:2});
  const count=calls.length;
  for(const bad of [
    {memberId:id,action:'change_role',role:'owner',expectedRevision:1},
    {memberId:id,action:'deactivate',role:'viewer',expectedRevision:1},
    {memberId:id,action:'deactivate',expectedRevision:true},
    {memberId:'invalid id',action:'deactivate',expectedRevision:1},
    {memberId:id,action:'publish',expectedRevision:1}
  ])await assert.rejects(()=>change({...ctx,fetchImpl,...bad}),TypeError);
  await assert.rejects(()=>list({...ctx,fetchImpl,
    origin:'http://bam.example'}),TypeError);
  await assert.rejects(()=>list({...ctx,fetchImpl:async()=>({
    ok:true,json:async()=>({...roster,tenant_id:'other'}})}),TypeError);
  await assert.rejects(()=>list({...ctx,fetchImpl:async()=>({
    ok:true,json:async()=>({...roster,publishing_enabled:true}})}),TypeError);
  await assert.rejects(()=>change({...ctx,fetchImpl:async()=>({
    ok:true,json:async()=>({tenant_id:'shop',member_id:id,
      status:'updated',revision:2,sessions_revoked:1,
      publishing_enabled:true})}),memberId:id,action:'change_role',
      role:'viewer',expectedRevision:1}),TypeError);
  assert.equal(calls.length,count);
  console.log('BAM private team membership client tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
