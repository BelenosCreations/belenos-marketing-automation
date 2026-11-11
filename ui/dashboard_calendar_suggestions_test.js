'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){
 return {tag,children:[],textContent:'',listeners:{},
   disabled:false,append(...values){this.children.push(...values)},
   replaceChildren(...values){this.children=values},
   addEventListener(event,handler){this.listeners[event]=handler}};
}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),utc='2026-11-11T15:00:00+00:00';
const calls=[],errors=[];
let hold=null,release=null;
const fetchImpl=async(url,options)=>{
 calls.push({url,options});
 if(url.endsWith('/dashboard'))
  return {ok:true,json:async()=>({
    schema_version:1,tenant_id:'shop',role:'owner',
    businesses:[{tenant_id:'shop',display_name:'Shop'}],
    cards:[
      {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
      {id:'approvals',label:'Approvals',value:0,availability:'available'},
      {id:'content',label:'Content',value:1,availability:'available'},
      {id:'connections',label:'Connections',value:0,availability:'available'}],
    drafts:[{request_id:rid,channel:'facebook',draft_text:'Custom shirt idea',
      suggestion:'Need product image',status:'needs_content',
      missing_items:['image']}],
    analytics:{availability:'not_connected',series:null},
    schedule:{availability:'not_connected',posts:null},
    publishing_enabled:false})};
 if(url.endsWith('/posting-time-preview'))
  return {ok:true,json:async()=>({
    tenant_id:'shop',mode:'manual',timezone:'America/New_York',
    status:'manual_preview',
    slots:[{local_date:'2026-11-11',local_time:'10:00',utc_at:utc}],
    skipped_dst:0,truncated:false,publishing_enabled:false})};
 if(url.endsWith('/calendar-suggestions')){
  if(hold)await hold;
  return {ok:true,status:200,json:async()=>({
    tenant_id:'shop',status:'suggestion_preview_only',
    preference_status:'manual_preview',
    unassigned_held_count:1,available_slot_count:1,
    posts_scheduled:0,publishing_enabled:false,
    items:[{request_id:rid,draft_revision:1,utc_at:utc,
      local_date:'2026-11-11',local_time:'10:00',
      timezone:'America/New_York',publishing_enabled:false}]})};
 }
 throw Error('Unexpected URL '+url);
};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function main(){
 const app=create({document,container,fetchImpl,
   origin:'https://bam.example',enableCalendarSuggestions:true,
   onError:error=>errors.push(error)});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 await app.refresh();
 const button=container.children[0].children[1].children[0];
 button.listeners.click();
 await tick();
 const sections=container.children[0].children.filter(x=>x.tag==='section');
 assert.equal(sections.length,2);
 assert.match(sections[1].children[0].textContent,/suggestions only/);
 assert.match(sections[1].children[2].children[0].textContent,/2026-11-11/);
 assert.match(sections[1].children[2].children[1].textContent,/Custom shirt idea/);
 assert.match(container.children[0].children[2].textContent,/No social scheduler/);
 assert.equal(errors.length,0);
 assert.ok(calls.some(x=>x.url.endsWith('/calendar-suggestions')));
 assert.ok(calls.every(x=>x.options.method==='GET'));
 hold=new Promise(resolve=>{release=resolve});
 const pending=app.refreshPostingPreview();
 await Promise.resolve();
 app.clear();
 release();
 assert.equal((await pending).stale,true);
 assert.equal(container.children.length,0);
 button.listeners.click();
 assert.equal(container.children.length,0);
 console.log('BAM unpublished suggested calendar dashboard test passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
