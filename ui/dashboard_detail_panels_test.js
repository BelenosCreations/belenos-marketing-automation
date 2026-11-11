'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){
  return {tag,textContent:'',children:[],listeners:{},disabled:false,
    append(...parts){this.children.push(...parts)},
    replaceChildren(...parts){this.children=parts},
    addEventListener(kind,fn){this.listeners[kind]=fn}};
}
const document={createElement:node};
function dashboard(tenant='shop'){
  return {schema_version:1,tenant_id:tenant,role:'owner',
    businesses:[{tenant_id:tenant,display_name:'Example Shop'}],
    cards:[
      {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
      {id:'approvals',label:'Approvals',value:1,availability:'available'},
      {id:'content',label:'Content',value:1,availability:'available'},
      {id:'connections',label:'Connections',value:0,availability:'available'}],
    drafts:[{request_id:'a'.repeat(32),channel:'facebook',
      draft_text:'Ready product copy',suggestion:'Final review required',
      status:'ready_for_review',missing_items:[]}],
    analytics:{availability:'not_connected',series:null},
    schedule:{availability:'not_connected',posts:null},publishing_enabled:false};
}
function proposal(tenant='shop'){
  return {tenant_id:tenant,mode:'manual',timezone:'America/New_York',
    status:'manual_preview',slots:[
      {local_date:'2026-11-11',local_time:'10:00',
       utc_at:'2026-11-11T15:00:00+00:00'},
      {local_date:'2026-11-11',local_time:'18:30',
       utc_at:'2026-11-11T23:30:00+00:00'}],
    skipped_dst:1,truncated:false,publishing_enabled:false};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function main(){
  const container=node('main'),requests=[],errors=[],opened={studio:0,settings:0};
  let fail=false,delay=null,release=null;
  const fetchImpl=async(url,opts)=>{
    requests.push({url,opts});
    if(url.endsWith('/dashboard'))
      return {ok:true,json:async()=>dashboard()};
    if(url.endsWith('/posting-time-preview')){
      if(delay)await delay;
      return fail?{ok:false}:{ok:true,json:async()=>proposal()};
    }
    throw new Error('Unexpected request');
  };
  const app=create({document,container,origin:'https://bam.example',
    fetchImpl,onError:e=>errors.push(e),
    onOpenContentStudio:()=>opened.studio++,
    onOpenPostingSettings:()=>opened.settings++});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  assert.equal((await app.refresh()).stale,false);
  const home=container.children[0].children[1].children;
  home[1].listeners.click();
  const ready=container.children[0].children.find(x=>x.tag==='article');
  assert.ok(ready);
  assert.equal(ready.children[1].textContent,'Ready product copy');
  assert.match(container.children[0].children[2].textContent,
    /not approved or scheduled/);
  const studio=container.children[0].children.find(
    x=>x.textContent==='Open Content Studio');
  studio.listeners.click();
  assert.equal(opened.studio,1);
  app.show('home');
  container.children[0].children[1].children[0].listeners.click();
  await tick();
  const panel=container.children[0].children.find(x=>x.tag==='section');
  assert.ok(panel);
  assert.match(panel.children[1].textContent,/Manual mode/);
  assert.match(panel.children[2].textContent,/2026-11-11 at 10:00/);
  assert.match(panel.children.at(-3).textContent,/daylight-saving/);
  const openSettings=panel.children.find(
    x=>x.textContent==='Open posting-time settings');
  openSettings.listeners.click();
  assert.equal(opened.settings,1);
  assert.equal(requests.filter(x=>x.url.endsWith('/posting-time-preview')).length,1);
  assert.equal(requests.at(-1).opts.credentials,'omit');
  fail=true;
  assert.equal((await app.refreshPostingPreview()).error,true);
  const errorPanel=container.children[0].children.find(x=>x.tag==='section');
  assert.match(errorPanel.children[1].textContent,/unavailable/);
  assert.equal(errors.length,1);
  // A stale result cannot restore private time data after logout or switch.
  fail=false;
  delay=new Promise(resolve=>{release=resolve});
  const inFlight=app.refreshPostingPreview();
  await Promise.resolve();
  app.clear();
  release();
  assert.equal((await inFlight).stale,true);
  assert.equal(container.children.length,0);
  home[0].listeners.click();
  assert.equal(container.children.length,0);
  console.log('BAM scheduled and review-card drilldown tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
