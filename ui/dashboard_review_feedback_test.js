'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){return {tag,children:[],textContent:'',listeners:{},
  disabled:false,value:'',append(...x){this.children.push(...x)},
  replaceChildren(...x){this.children=x},
  addEventListener(name,fn){this.listeners[name]=fn},
  setAttribute(name,value){this[name]=value}};}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),first='b'.repeat(32),second='c'.repeat(32);
const notices=[],errors=[],calls=[];
let note=null,version=first,role='owner',blockUpdate=false;
function response(path,method,body){
 if(path.endsWith('/dashboard'))return {
  schema_version:1,tenant_id:'shop',role,
  businesses:[{tenant_id:'shop',display_name:'Shop'}],
  cards:[
   {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
   {id:'approvals',label:'Approvals',value:1,availability:'available'},
   {id:'content',label:'Content',value:1,availability:'available'},
   {id:'connections',label:'Connections',value:0,availability:'available'}],
  drafts:[{request_id:rid,channel:'facebook',draft_text:'Product preview',
   suggestion:'Check photo rights',status:'needs_content',
   missing_items:['image']}],
  analytics:{availability:'not_connected',series:null},
  schedule:{availability:'not_connected',posts:null},
  publishing_enabled:false
 };
 if(path.endsWith('/review-readiness'))return {
  tenant_id:'shop',status:'review_preview_only',
  held_count:1,editorial_material_complete_count:0,
  approved_count:0,publishing_enabled:false,
  items:[{request_id:rid,revision:2,channel:'facebook',
   status:'needs_content',missing_items:['image'],unverified_items:[],
   editorial_material_complete:false,
   blockers:['missing_required_content','truthguard_review_required',
     'owner_approval_not_implemented','social_publishing_disabled'],
   approved:false,publishing_enabled:false}]
 };
 if(path.endsWith('/review-feedback')){
  const common={tenant_id:'shop',status:'feedback_only',
    approval_granted:false,publishing_enabled:false};
  if(method==='GET')return {...common,items:note?[{
    request_id:rid,draft_revision:2,current_revision:2,stale:false,
    note,feedback_token:version,updated_at:103,
    approval_granted:false,publishing_enabled:false}]:[]};
  if(method==='PUT'){
   assert.equal(body.request_id,rid);
   assert.equal(body.expected_revision,2);
   if(blockUpdate||body.expected_feedback_token!==(note?version:null))
    return null;
   note=body.note;
   version=note==='Initial feedback'?first:second;
   return {...common,request_id:rid,draft_revision:2,
    feedback_token:version};
  }
  if(method==='DELETE'){
   if(body.expected_feedback_token!==version)return null;
   note=null;
   return {...common,request_id:rid,removed:1};
  }
 }
 throw Error('Unexpected endpoint '+path);
}
const fetchImpl=async(url,opts)=>{
 const payload=opts.body?JSON.parse(opts.body):null;
 calls.push({url,opts,payload});
 const value=response(url,opts.method,payload);
 return value===null?{ok:false,status:409}:
   {ok:true,status:200,json:async()=>value};
};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function section(){
 return container.children[0].children.find(x=>x.tag==='section');
}
function record(){
 const s=section();assert.ok(s);
 return s.children.find(x=>x.tag==='article');
}
function control(label){
 return record().children.find(x=>x.textContent===label);
}
async function main(){
 const app=create({document,container,fetchImpl,origin:'https://bam.example',
   onError:error=>errors.push(error),
   onNotice:message=>notices.push(message),
   enableReviewReadiness:true,enableReviewFeedback:true});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 await app.refresh();
 const approvals=container.children[0].children[1].children[1];
 approvals.listeners.click();
 for(let i=0;i<3;i++)await tick();
 assert.match(record().children[0].textContent,/Product preview/);
 assert.ok(record().children.some(x=>x.textContent.includes('Missing: image')));
 const input=record().children.find(x=>x.tag==='textarea');
 assert.ok(input);
 assert.equal(input.value,'');
 input.value='Initial feedback';
 await control('Add private review note').listeners.click();
 assert.equal(note,'Initial feedback');
 assert.match(notices.at(-1),/nothing was approved or scheduled/);
 assert.match(record().children.find(x=>x.textContent.startsWith('Editorial feedback:')).textContent,
   /Initial feedback/);
 assert.ok(calls.some(c=>c.opts.method==='PUT'));
 assert.ok(calls.every(c=>c.opts.method==='GET'||
   c.url.endsWith('/review-feedback')));
 blockUpdate=true;
 const old=record().children.find(x=>x.tag==='textarea');
 old.value='Old screen request';
 await control('Update private review note').listeners.click();
 assert.equal(note,'Initial feedback');
 assert.match(errors.at(-1),/Refresh to resolve/);
 blockUpdate=false;
 for(let i=0;i<3;i++)await tick();
 await app.refreshReviewFeedback();
 for(let i=0;i<2;i++)await tick();
 const remove=control('Remove private review note');
 assert.ok(remove,'Expected current version-checked removal control');
 remove.listeners.click();
 const confirm=control('Confirm removal of private note');
 assert.ok(confirm);
 await confirm.listeners.click();
 assert.equal(note,null);
 assert.match(notices.at(-1),/draft remains unpublished/);
 assert.ok(calls.some(x=>x.opts.method==='DELETE'));
 app.clear();
 role='viewer';note='Owner-only instruction';version=first;
 app.activate({token:'x'.repeat(43),tenantId:'shop'});
 await app.refresh();
 container.children[0].children[1].children[1].listeners.click();
 for(let i=0;i<3;i++)await tick();
 assert.match(record().children.find(x=>
   x.textContent.startsWith('Editorial feedback:')).textContent,
   /Owner-only instruction/);
 assert.equal(record().children.some(x=>x.tag==='textarea'),false);
 const previous=calls.length;
 app.clear();
 approvals.listeners.click();
 assert.equal(container.children.length,0);
 assert.equal(calls.length,previous);
 console.log('BAM tenant-private editorial notes lifecycle and owner controls passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
