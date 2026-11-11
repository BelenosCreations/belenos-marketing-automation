'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){
  return {tag,children:[],textContent:'',disabled:false,listeners:{},
    append(...items){this.children.push(...items)},
    replaceChildren(...items){this.children=items},
    addEventListener(event,handler){this.listeners[event]=handler}};
}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),utc='2026-11-11T15:00:00+00:00';
function overview(){
 return {schema_version:1,tenant_id:'shop',role:'owner',
   businesses:[{tenant_id:'shop',display_name:'Shop'}],
   cards:[
     {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
     {id:'approvals',label:'Approvals',value:0,availability:'available'},
     {id:'content',label:'Content',value:1,availability:'available'},
     {id:'connections',label:'Connections',value:0,availability:'available'}],
   drafts:[],analytics:{availability:'not_connected',series:null},
   schedule:{availability:'not_connected',posts:null},
   publishing_enabled:false};
}
const errors=[],calls=[];
let failCalendar=false,hold=null,release=null;
const fetchImpl=async(url,opts)=>{
 calls.push({url,opts});
 if(url.endsWith('/dashboard'))
   return {ok:true,json:async()=>overview()};
 if(url.endsWith('/posting-time-preview'))
   return {ok:true,json:async()=>({
     tenant_id:'shop',mode:'manual',timezone:'America/New_York',
     status:'manual_preview',slots:[{
       local_date:'2026-11-11',local_time:'10:00',utc_at:utc}],
     skipped_dst:0,truncated:false,publishing_enabled:false})};
 if(url.endsWith('/calendar-proposals')){
   if(hold)await hold;
   if(failCalendar)return {ok:false,status:503};
   return {ok:true,status:200,json:async()=>({
     tenant_id:'shop',status:'proposal_only',posts_scheduled:0,
     publishing_enabled:false,items:[{
       request_id:rid,draft_revision:1,current_revision:2,
       utc_at:utc,local_date:'2026-11-11',local_time:'10:00',
       timezone:'America/New_York',content_changed:true,
       slot_current:false,publishing_enabled:false
     }]})};
 }
 throw Error('Unexpected request');
};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function main(){
 const app=create({document,container,fetchImpl,
   origin:'https://bam.example',enableCalendarProposals:true,
   onError:e=>errors.push(e)});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 await app.refresh();
 const schedule=container.children[0].children[1].children[0];
 schedule.listeners.click();
 await tick();
 const sections=container.children[0].children.filter(x=>x.tag==='section');
 assert.equal(sections.length,2);
 assert.equal(sections[0].children[0].textContent,
   'Possible local posting times');
 assert.match(sections[1].children[0].textContent,/not scheduled posts/);
 assert.match(sections[1].children[1].children[0].textContent,/2026-11-11/);
 assert.match(sections[1].children[1].children[1].textContent,
   /Draft changed/);
 assert.match(sections[1].children[1].children[2].textContent,
   /no longer matches/);
 assert.match(container.children[0].children[2].textContent,/No social scheduler/);
 assert.equal(calls.filter(x=>x.url.endsWith('/calendar-proposals')).length,1);
 assert.equal(calls.at(-1).opts.credentials,'omit');
 assert.equal(calls.at(-1).opts.method,'GET');
 failCalendar=true;
 const failed=await app.refreshPostingPreview();
 assert.equal(failed.stale,false);
 const fallback=container.children[0].children.filter(x=>x.tag==='section')[1];
 assert.match(fallback.children[1].textContent,/unavailable/);
 assert.equal(errors.at(-1),'Private draft calendar could not be loaded');
 failCalendar=false;
 hold=new Promise(resolve=>{release=resolve});
 const pending=app.refreshPostingPreview();
 await Promise.resolve();
 app.clear();
 release();
 assert.equal((await pending).stale,true);
 assert.equal(container.children.length,0);
 schedule.listeners.click();
 assert.equal(container.children.length,0);
 console.log('BAM unpublished dashboard calendar proposal drilldown tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
