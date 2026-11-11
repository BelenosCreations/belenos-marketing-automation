'use strict';
const assert=require('node:assert/strict');
const {read}=require('./dashboard_http_client.js');
const body={
  schema_version:1,tenant_id:'shop',role:'owner',
  businesses:[{tenant_id:'shop',display_name:'Shop'}],
  cards:[
    {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
    {id:'approvals',label:'Review',value:0,availability:'available'},
    {id:'content',label:'Content',value:0,availability:'available'},
    {id:'connections',label:'Connections',value:0,availability:'available'}
  ],drafts:[],analytics:{availability:'not_connected',series:null},
  schedule:{availability:'not_connected',posts:null},publishing_enabled:false
};
async function main(){
  const calls=[];
  const fetchImpl=async(url,options)=>{
    calls.push({url,options});
    return {ok:true,json:async()=>body};
  };
  const options={kind:'dashboard',token:'secret-in-memory',
    origin:'https://bam.example',fetchImpl};
  const result=await read(options);
  assert.equal(result.tenantId,'shop');
  await assert.rejects(()=>read({...options,expectedTenantId:'other'}),TypeError);
  assert.equal((await read({...options,expectedTenantId:'shop'})).tenantId,'shop');
  assert.equal(calls.length,3);
  assert.equal(calls[0].url,'https://bam.example/api/v1/dashboard');
  assert.equal(calls[0].options.method,'GET');
  assert.equal(calls[0].options.credentials,'omit');
  assert.equal(calls[0].options.cache,'no-store');
  assert.equal(calls[0].options.redirect,'error');
  assert.equal(calls[0].options.headers.Authorization,'Bearer secret-in-memory');
  for(const origin of ['http://bam.example','https://user:pass@bam.example',
                       'https://bam.example/path','https://bam.example?token=foo']){
    await assert.rejects(()=>read({...options,origin}),TypeError);
  }
  await assert.rejects(()=>read({...options,kind:'publish'}),TypeError);
  await assert.rejects(()=>read({...options,token:''}),TypeError);
  await assert.rejects(()=>read({...options,fetchImpl:async()=>({ok:false})}),Error);
  await assert.rejects(()=>read({...options,fetchImpl:async()=>({
    ok:true,json:async()=>({...body,publishing_enabled:true})
  })}),TypeError);
  const drafts={tenant_id:'shop',publishing_enabled:false,
    drafts:[{request_id:'a'.repeat(32),channel:'facebook',
      draft_text:'Example',suggestion:'Photo',status:'postponed',
      missing_items:['photo'],priority:0}]};
  const draftResult=await read({...options,kind:'drafts',
    fetchImpl:async()=>({ok:true,json:async()=>drafts})});
  assert.equal(draftResult.drafts[0].status,'postponed');
  await assert.rejects(()=>read({...options,kind:'drafts',
    fetchImpl:async()=>({ok:true,json:async()=>({
      ...drafts,drafts:[{...drafts.drafts[0],status:'published'}]})})}),TypeError);
  const prefs={tenant_id:'shop',mode:'smart',timezone:null,
    manual_times:[],configured:false,publishing_enabled:false};
  const prefResult=await read({...options,kind:'preferences',
    fetchImpl:async()=>({ok:true,json:async()=>prefs})});
  assert.equal(prefResult.mode,'smart');
  assert.equal(prefResult.timezone,null);
  await assert.rejects(()=>read({...options,kind:'preferences',
    fetchImpl:async()=>({ok:true,json:async()=>({...prefs,
      timezone:'America/New_York'})})}),TypeError);
  const proposal={tenant_id:'shop',mode:'smart',
    timezone:'America/New_York',status:'needs_audience_data',
    slots:[],skipped_dst:0,truncated:false,publishing_enabled:false};
  const preview=await read({...options,kind:'postingPreview',
    expectedTenantId:'shop',fetchImpl:async(url)=>{
      assert.equal(url,'https://bam.example/api/v1/posting-time-preview');
      return {ok:true,json:async()=>proposal};
    }});
  assert.equal(preview.status,'needs_audience_data');
  assert.equal(preview.slots.length,0);
  await assert.rejects(()=>read({...options,kind:'postingPreview',
    fetchImpl:async()=>({ok:true,json:async()=>({
      ...proposal,slots:[{local_date:'2026-11-11',local_time:'10:00',
        utc_at:'2026-11-11T15:00:00+00:00'}]
    })})}),TypeError);
  const social={tenant_id:'shop',visibility:'authorized',connections:[
    {platform:'facebook',account_id:'page',scope:'read_insights',
     status:'connected',updated_at:100,expires_at:null,
     publishing_enabled:false}],publishing_enabled:false};
  const details=await read({...options,kind:'connections',
    expectedTenantId:'shop',fetchImpl:async(url,opts)=>{
      assert.equal(url,'https://bam.example/api/v1/connections');
      assert.equal(opts.method,'GET');
      return {ok:true,json:async()=>social};
    }});
  assert.equal(details.connections[0].accountId,'page');
  assert.equal(details.connections[0].publishingEnabled,false);
  await assert.rejects(()=>read({...options,kind:'connections',
    expectedTenantId:'shop',fetchImpl:async()=>({ok:true,
      json:async()=>({...social,connections:[{...social.connections[0],
        vault_reference:'secret'}]})})}),TypeError);
  const team={tenant_id:'shop',roles:{owner:1,marketing_manager:0,
    content_creator:1,employee:0,viewer:0},active_members:2,
    inactive_members:0,invitation_status:'not_connected',
    publishing_enabled:false};
  const membership=await read({...options,kind:'teamOverview',
    expectedTenantId:'shop',fetchImpl:async(url,opts)=>{
      assert.equal(url,'https://bam.example/api/v1/team-overview');
      assert.equal(opts.method,'GET');
      return {ok:true,json:async()=>team};
    }});
  assert.equal(membership.activeMembers,2);
  await assert.rejects(()=>read({...options,kind:'teamOverview',
    expectedTenantId:'shop',fetchImpl:async()=>({
      ok:true,json:async()=>({...team,subject_id:'secret'})})}),TypeError);
  console.log('BAM HTTPS read-only client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
