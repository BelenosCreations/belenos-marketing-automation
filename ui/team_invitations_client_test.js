'use strict';
const assert=require('node:assert/strict');
const {list,cancel,history,issue}=require('./team_invitations_client.js');
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
      :url.endsWith('/create')
      ?{tenant_id:'shop',invitation_created:true,
        invitation_id:'b'.repeat(32),expires_at:604901,
        publishing_enabled:false}
      :url.endsWith('/activity')
      ?{tenant_id:'shop',status:'private_invitation_activity',
        events:[{invitation_id:record.invitation_id,
                 action:'cancelled',occurred_at:101}],
        publishing_enabled:false}
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
  const audit=await history({...ctx,fetchImpl});
  assert.equal(audit.events[0].action,'cancelled');
  assert.equal(audit.events[0].invitationId,record.invitation_id);
  assert.ok(Object.isFrozen(audit.events));
  assert.equal(calls[2].opts.method,'GET');
  assert.equal(calls[2].opts.credentials,'omit');
  const event={invitation_id:record.invitation_id,
    action:'delivered',occurred_at:99};
  for(const unsafe of [
    {tenant_id:'shop',status:'private_invitation_activity',
      events:[{...event,email:'guest@example.com'}],publishing_enabled:false},
    {tenant_id:'shop',status:'private_invitation_activity',
      events:[event,{...event}],publishing_enabled:false},
    {tenant_id:'other',status:'private_invitation_activity',
      events:[event],publishing_enabled:false},
    {tenant_id:'shop',status:'private_invitation_activity',
      events:[{...event,action:'published'}],publishing_enabled:false}
  ])await assert.rejects(()=>history({...ctx,
    fetchImpl:async()=>({ok:true,json:async()=>unsafe})}),TypeError);
  const issued=await issue({...ctx,fetchImpl,
    email:'friend@example.com',role:'content_creator'});
  assert.equal(issued.issued,true);
  assert.equal(issued.invitationId,'b'.repeat(32));
  assert.deepEqual(JSON.parse(calls[3].opts.body),
    {email:'friend@example.com',role:'content_creator'});
  assert.equal(calls[3].opts.credentials,'omit');
  for(const bad of [
    {email:'not-an-email',role:'viewer'},
    {email:'friend@example.com',role:'owner'},
    {email:'friend@example.com',role:true},
    {email:' friend@example.com',role:'viewer'}
  ])await assert.rejects(()=>issue({...ctx,fetchImpl,...bad}),TypeError);
  for(const unsafe of [
    {tenant_id:'other',invitation_created:true,
      invitation_id:'b'.repeat(32),expires_at:604901,
      publishing_enabled:false},
    {tenant_id:'shop',invitation_created:true,
      invitation_id:'b'.repeat(32),expires_at:604901,
      publishing_enabled:false,token:'secret'},
    {tenant_id:'shop',invitation_created:true,
      invitation_id:'b'.repeat(32),expires_at:604901,
      publishing_enabled:true}
  ])await assert.rejects(()=>issue({...ctx,
    email:'friend@example.com',role:'viewer',
    fetchImpl:async()=>({ok:true,json:async()=>unsafe})}),TypeError);
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
