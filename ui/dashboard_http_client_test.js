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
  assert.equal(calls.length,1);
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
  console.log('BAM HTTPS read-only client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
