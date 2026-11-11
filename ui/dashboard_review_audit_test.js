'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){return {tag,children:[],className:'',textContent:'',
  listeners:{},disabled:false,value:'',
  append(...x){this.children.push(...x)},
  replaceChildren(...x){this.children=x},
  addEventListener(event,fn){this.listeners[event]=fn},
  setAttribute(name,value){this[name]=value}}}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),eid='b'.repeat(32),errors=[],calls=[];
let role='owner',failHistory=false;
const fetchImpl=async(url,options)=>{
 calls.push({url,options});
 if(url.endsWith('/dashboard'))
  return {ok:true,json:async()=>({
   schema_version:1,tenant_id:'shop',role,
   businesses:[{tenant_id:'shop',display_name:'Shop'}],
   cards:[
    {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
    {id:'approvals',label:'Approvals',value:1,availability:'available'},
    {id:'content',label:'Content',value:1,availability:'available'},
    {id:'connections',label:'Connections',value:0,availability:'available'}],
   drafts:[{request_id:rid,channel:'facebook',draft_text:'New tumbler',
     suggestion:'Check image rights',status:'ready_for_review',
     missing_items:[]}],
   analytics:{availability:'not_connected',series:null},
   schedule:{availability:'not_connected',posts:null},
   publishing_enabled:false})};
 if(url.endsWith('/review-readiness'))
  return {ok:true,status:200,json:async()=>({
   tenant_id:'shop',status:'review_preview_only',held_count:1,
   editorial_material_complete_count:1,approved_count:0,
   publishing_enabled:false,items:[{
    request_id:rid,revision:1,channel:'facebook',
    status:'ready_for_review',missing_items:[],unverified_items:[],
    editorial_material_complete:true,
    blockers:['truthguard_review_required',
      'owner_approval_not_implemented','social_publishing_disabled'],
    approved:false,publishing_enabled:false
   }]})};
 if(url.endsWith('/review-feedback'))
  return {ok:true,status:200,json:async()=>({
    tenant_id:'shop',status:'feedback_only',items:[],
    approval_granted:false,publishing_enabled:false})};
 if(url.endsWith('/review-feedback-history')){
  if(failHistory)return {ok:false,status:503};
  return {ok:true,status:200,json:async()=>({
   tenant_id:'shop',status:'feedback_history_only',
   truncated:false,approval_granted:false,publishing_enabled:false,
   events:[{event_id:eid,request_id:rid,action:'created',
    draft_revision:1,occurred_at:102}]})};
 }
 throw Error('Unexpected route '+url);
};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function activity(){
 return container.children[0].children.find(x=>x.className==='bam-review-activity');
}
function open(){
 container.children[0].children[1].children[1].listeners.click();
}
async function settle(){for(let n=0;n<5;n++)await tick();}
async function main(){
 const app=create({document,container,fetchImpl,
  origin:'https://bam.example',enableReviewReadiness:true,
  enableReviewFeedback:true,enableReviewAudit:true,
  onError:error=>errors.push(error)});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 await app.refresh();
 open();await settle();
 assert.ok(activity());
 assert.match(activity().children[0].textContent,/Recent reviewer note activity/);
 assert.match(activity().children[2].textContent,/Note created/);
 assert.match(activity().children[2].textContent,/Draft aaaaaaaa/);
 assert.ok(calls.some(x=>x.url.endsWith('/review-feedback-history')));
 assert.ok(calls.every(x=>x.options.method==='GET'));
 assert.ok(!activity().children.some(x=>
     /Review original photo/.test(x.textContent)));
 failHistory=true;
 const failed=await app.refreshReviewAudit();
 assert.equal(failed.error,true);
 assert.match(activity().children[2].textContent,/unavailable/);
 assert.match(errors.at(-1),/history unavailable/);
 const old=activity().children.find(x=>x.textContent==='Refresh reviewer activity');
 const checked=calls.filter(x=>x.url.endsWith('/review-feedback-history')).length;
 app.clear();
 role='viewer';failHistory=false;
 app.activate({token:'v'.repeat(43),tenantId:'shop'});
 await app.refresh();
 open();await settle();
 assert.equal(activity(),undefined);
 assert.equal(calls.filter(x=>x.url.endsWith('/review-feedback-history')).length,
   checked);
 old.listeners.click();
 assert.equal(calls.filter(x=>x.url.endsWith('/review-feedback-history')).length,
   checked);
 app.clear();
 assert.equal(container.children.length,0);
 console.log('BAM metadata-only reviewer history panel role and lifecycle tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
