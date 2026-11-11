'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){return {tag,children:[],textContent:'',listeners:{},
  disabled:false,append(...x){this.children.push(...x)},
  replaceChildren(...x){this.children=x},
  addEventListener(name,fn){this.listeners[name]=fn}}}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),version='b'.repeat(32);
const utc='2026-11-12T15:00:00+00:00';
const calls=[],errors=[],notices=[];
let proposal=null,role='owner';
function overview(){return {
 schema_version:1,tenant_id:'shop',role,
 businesses:[{tenant_id:'shop',display_name:'Shop'}],
 cards:[
  {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
  {id:'approvals',label:'Approvals',value:0,availability:'available'},
  {id:'content',label:'Content',value:1,availability:'available'},
  {id:'connections',label:'Connections',value:0,availability:'available'}],
 drafts:[{request_id:rid,channel:'facebook',draft_text:'New private product draft',
   suggestion:'Obtain product photograph',status:'needs_content',
   missing_items:['image']}],
 analytics:{availability:'not_connected',series:null},
 schedule:{availability:'not_connected',posts:null},
 publishing_enabled:false
};}
const fetchImpl=async(url,opts)=>{
 calls.push({url,opts});
 if(url.endsWith('/dashboard'))
  return {ok:true,json:async()=>overview()};
 if(url.endsWith('/posting-time-preview'))
  return {ok:true,json:async()=>({
    tenant_id:'shop',mode:'manual',timezone:'America/New_York',
    status:'manual_preview',slots:[{
     utc_at:utc,local_date:'2026-11-12',local_time:'10:00'}],
    skipped_dst:0,truncated:false,publishing_enabled:false})};
 if(url.endsWith('/calendar-proposals')){
   if(opts.method==='GET')return {ok:true,status:200,json:async()=>({
    tenant_id:'shop',status:'proposal_only',posts_scheduled:0,
    publishing_enabled:false,items:proposal?[{
     request_id:rid,draft_revision:1,current_revision:1,utc_at:utc,
     local_date:'2026-11-12',local_time:'10:00',
     timezone:'America/New_York',proposal_token:version,
     content_changed:false,slot_current:true,
     publishing_enabled:false}]:[]})};
   if(opts.method==='POST'){
    assert.equal(role,'owner');
    assert.deepEqual(JSON.parse(opts.body),{
     request_id:rid,expected_revision:1,utc_at:utc,
     expected_proposal_token:null});
    proposal={saved:true};
    return {ok:true,status:201,json:async()=>({
     tenant_id:'shop',request_id:rid,utc_at:utc,
     proposal_token:version,status:'proposal_only',
     posts_scheduled:0,publishing_enabled:false})};
   }
 }
 if(url.endsWith('/calendar-suggestions'))
   return {ok:true,status:200,json:async()=>({
     tenant_id:'shop',status:'suggestion_preview_only',
     preference_status:'manual_preview',
     unassigned_held_count:proposal?0:1,
     available_slot_count:proposal?0:1,
     items:proposal?[]:[{
       request_id:rid,draft_revision:1,utc_at:utc,
       local_date:'2026-11-12',local_time:'10:00',
       timezone:'America/New_York',publishing_enabled:false}],
     posts_scheduled:0,publishing_enabled:false})};
 throw Error('Unexpected route '+url);
};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function find(root,match){
 if(match(root))return root;
 for(const child of root.children||[]){
   const found=find(child,match);
   if(found)return found;
 }
 return null;
}
function byLabel(label){
 return find(container,x=>x.tag==='button'&&x.textContent===label);
}
async function open(app){
 await app.refresh();
 const scheduled=container.children[0].children[1].children[0];
 scheduled.listeners.click();
 for(let i=0;i<3;i++)await tick();
}
async function main(){
 const app=create({document,container,fetchImpl,
  origin:'https://bam.example',onError:e=>errors.push(e),
  onNotice:e=>notices.push(e),
  enableCalendarProposals:true,enableCalendarSuggestions:true});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 await open(app);
 const choose=byLabel('Choose draft-only date (not schedule)');
 assert.ok(choose);
 assert.equal(calls.filter(x=>x.opts.method==='POST').length,0);
 choose.listeners.click();
 const confirm=byLabel('Confirm this proposed draft date');
 assert.ok(confirm);
 assert.equal(calls.filter(x=>x.opts.method==='POST').length,0);
 await confirm.listeners.click();
 assert.ok(proposal);
 assert.equal(calls.filter(x=>x.opts.method==='POST').length,1);
 assert.match(notices.at(-1),/No post was scheduled or approved/);
 assert.equal(byLabel('Choose draft-only date (not schedule)'),null);
 assert.equal(errors.length,0);
 assert.ok(calls.every(x=>!x.url.includes('/publish')&&
                          !x.url.includes('/ai-generate')));
 app.clear();
 role='viewer';proposal=null;
 app.activate({token:'v'.repeat(43),tenantId:'shop'});
 await open(app);
 assert.equal(byLabel('Choose draft-only date (not schedule)'),null);
 const count=calls.filter(x=>x.opts.method==='POST').length;
 app.clear();
 assert.equal(container.children.length,0);
 choose.listeners.click();
 assert.equal(calls.filter(x=>x.opts.method==='POST').length,count);
 console.log('BAM explicit two-stage unpublished calendar suggestion selection passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
