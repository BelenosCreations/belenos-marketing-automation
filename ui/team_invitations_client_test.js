'use strict';
const assert=require('node:assert/strict');
const {list,cancel}=require('./team_invitations_client.js');
const ctx={origin:'https://bam.example',token:'x'.repeat(43),
  expectedTenantId:'shop'};
const record={invitation_id:'a'.repeat(32),
  email:'invitee@example.com',role:'viewer',expires_at:700000};
async function main(){
  const calls=[];
  const fetchImpl=async(url,opts)=>{
    calls.push({url,opts});
    return {ok:true,json:async()=>url.endsWith('/cancel')
      ?{tenant_id:'shop',invitation_id:record.invitation_id,
        status:'cancelled',publishing_enabled:false}
      :{tenant_id:'shop',status:'private_pending_invitations',
        items:[record],publishing_enabled:false}};
  };
  const listed=await list({...ctx,fetchImpl});
  assert.equal(listed.items[0].email,'invitee@example.com');
  assert.ok(Object.isFrozen(listed.items));
  assert.equal(calls[0].opts.method,'GET');
  assert.equal(calls[0].opts.credentials,'omit');
  const cancelled=await cancel({...ctx,fetchImpl,
    invitationId:record.invitation_id});
  assert.equal(cancelled.cancelled,true);
  assert.equal(calls[1].opts.method,'POST');
  assert.deepEqual(JSON.parse(calls[1].opts.body),
    {invitation_id:record.invitation_id});
  const count=calls.length;
  await assert.rejects(()=>cancel({...ctx,fetchImpl,
    invitationId:'bad'}),TypeError);
  await assert.rejects(()=>list({...ctx,fetchImpl,
    origin:'http://bam.example'}),TypeError);
  for(const unsafe of [
    {tenant_id:'other',status:'private_pending_invitations',items:[record],
     publishing_enabled:false},
    {tenant_id:'shop',status:'private_pending_invitations',items:[record],
     publishing_enabled:true},
    {tenant_id:'shop',status:'private_pending_invitations',
     items:[{...record,token_hash:'hidden'}],publishing_enabled:false},
    {tenant_id:'shop',status:'private_pending_invitations',
     items:[{...record,role:'owner'}],publishing_enabled:false}
  ])await assert.rejects(()=>list({...ctx,
    fetchImpl:async()=>({ok:true,json:async()=>unsafe})}),TypeError);
  assert.equal(calls.length,count);
  console.log('BAM disabled-by-default pending invitation browser client tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
