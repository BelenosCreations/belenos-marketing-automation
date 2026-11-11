'use strict';
const assert=require('node:assert/strict');
const {create}=require('./posting_preferences_workspace.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},value:'',
  append(...x){this.children.push(...x)},replaceChildren(...x){this.children=x},
  addEventListener(k,f){this.listeners[k]=f}}}
const document={createElement:node},container=node('main');
let current={tenant_id:'shop',mode:'smart',timezone:null,manual_times:[],
  configured:false,publishing_enabled:false};
let wait=null,release=null;
const calls=[];
const fetchImpl=async(url,opts)=>{
  calls.push(opts);
  if(opts.method==='PUT'){
    const payload=JSON.parse(opts.body);
    current={tenant_id:'shop',mode:payload.mode,
      timezone:payload.timezone,manual_times:payload.manual_times,
      configured:true,publishing_enabled:false};
    return {ok:true,json:async()=>current};
  }
  if(wait)await wait;
  if(url.endsWith('/posting-time-preview')){
    const manual=current.configured&&current.mode==='manual';
    return {ok:true,json:async()=>({
      tenant_id:'shop',mode:current.mode,
      timezone:current.timezone,
      status:!current.configured?'not_configured':
        manual?'manual_preview':'needs_audience_data',
      slots:manual?[{local_date:'2026-11-11',local_time:'10:00',
        utc_at:'2026-11-11T15:00:00+00:00'}]:[],
      skipped_dst:0,truncated:false,publishing_enabled:false})};
  }
  return {ok:true,json:async()=>current};
};
async function main(){
  const app=create({document,container,fetchImpl,origin:'https://bam.example'});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  app.setCanManage(true);
  assert.equal((await app.refresh()).stale,false);
  assert.equal(container.children.length,1);
  const saved=await app.save({mode:'manual',timezone:'America/New_York',
    manualTimes:['10:00','18:30']});
  assert.equal(saved.mode,'manual');
  assert.equal(saved.publishingEnabled,false);
  assert.equal(calls.filter(x=>x.method==='PUT').length,1);
  assert.equal(container.children[0].children[2].textContent,
    'Saved mode: manual · America/New_York');
  assert.equal(container.children[0].children.at(-1).children[1].textContent,
    'Possible next-seven-day local times only. These are not scheduled posts.');
  assert.match(container.children[0].children.at(-1).children[2].textContent,
    /2026-11-11 at 10:00/);
  await app.save({mode:'smart',timezone:'America/New_York',manualTimes:[]});
  assert.equal(current.mode,'smart');
  // Pending preferences may not resurrect after a tenant switch/signout.
  wait=new Promise(resolve=>{release=resolve});
  const pending=app.refresh();
  await Promise.resolve();
  app.clear();release();
  assert.equal((await pending).stale,true);
  assert.equal(container.children.length,0);
  console.log('BAM posting preferences workspace lifecycle tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
