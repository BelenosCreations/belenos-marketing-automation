'use strict';
const assert=require('node:assert/strict');
const {activity}=require('./team_members_client.js');
const ctx={origin:'https://bam.example',token:'x'.repeat(43),
  expectedTenantId:'shop'};
const good={tenant_id:'shop',status:'private_team_activity',events:[
  {event_id:9,member_id:'m'.repeat(32),actor_id:'o'.repeat(32),
   previous_role:'content_creator',resulting_role:'viewer',
   action:'change_role',changed_at:105,revision_after:3},
  {event_id:8,member_id:'n'.repeat(32),actor_id:'o'.repeat(32),
   previous_role:'employee',resulting_role:'employee',
   action:'deactivate',changed_at:100,revision_after:2}
],publishing_enabled:false};
async function main(){
  const calls=[];
  const fetchImpl=async(url,opts)=>{
    calls.push({url,opts});
    return {ok:true,json:async()=>good};
  };
  const result=await activity({...ctx,fetchImpl});
  assert.equal(result.events.length,2);
  assert.equal(result.events[0].action,'change_role');
  assert.ok(Object.isFrozen(result.events[0]));
  assert.equal(calls[0].url,'https://bam.example/api/v1/team/activity');
  assert.equal(calls[0].opts.method,'GET');
  assert.equal(calls[0].opts.credentials,'omit');
  assert.equal(calls[0].opts.redirect,'error');
  for(const untrusted of [
    {...good,tenant_id:'other'},
    {...good,publishing_enabled:true},
    {...good,events:[...good.events].reverse()},
    {...good,events:[{...good.events[0],actor_id:'other id'}]},
    {...good,events:[{...good.events[0],changed_at:Infinity}]},
    {...good,events:[{...good.events[0],revision_after:true}]},
    {...good,events:[{...good.events[0],role:'owner'}]}
  ])await assert.rejects(()=>activity({...ctx,
    fetchImpl:async()=>({ok:true,json:async()=>untrusted})}),TypeError);
  await assert.rejects(()=>activity({...ctx,fetchImpl,
    origin:'http://bam.example'}),TypeError);
  console.log('BAM private owner-only team activity browser tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
