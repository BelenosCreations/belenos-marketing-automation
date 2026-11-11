'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){return {tag,children:[],textContent:'',listeners:{},disabled:false,
 append(...x){this.children.push(...x)},
 replaceChildren(...x){this.children=x},
 addEventListener(name,fn){this.listeners[name]=fn}}}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),errors=[],calls=[];
let failed=false,hold=null,release=null;
const fetchImpl=async(url,options)=>{
 calls.push({url,options});
 if(url.endsWith('/dashboard')){
  return {ok:true,json:async()=>({
   schema_version:1,tenant_id:'shop',role:'owner',
   businesses:[{tenant_id:'shop',display_name:'Shop'}],
   cards:[
    {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
    {id:'approvals',label:'Approvals',value:1,availability:'available'},
    {id:'content',label:'Content',value:1,availability:'available'},
    {id:'connections',label:'Connections',value:0,availability:'available'}],
   drafts:[{request_id:rid,channel:'facebook',draft_text:'Example tumbler',
     suggestion:'Find real product image',status:'ready_for_review',
     missing_items:[]}],
   analytics:{availability:'not_connected',series:null},
   schedule:{availability:'not_connected',posts:null},
   publishing_enabled:false})};
 }
 if(url.endsWith('/review-readiness')){
  if(hold)await hold;
  if(failed)return {ok:false,status:503};
  return {ok:true,status:200,json:async()=>({
   tenant_id:'shop',status:'review_preview_only',held_count:1,
   editorial_material_complete_count:1,approved_count:0,
   publishing_enabled:false,items:[{
    request_id:rid,revision:2,channel:'facebook',
    status:'ready_for_review',missing_items:[],unverified_items:[],
    editorial_material_complete:true,
    blockers:['truthguard_review_required',
      'owner_approval_not_implemented','social_publishing_disabled'],
    approved:false,publishing_enabled:false
   }]})};
 }
 throw Error('Unexpected endpoint '+url);
};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function main(){
 const app=create({document,container,fetchImpl,
  origin:'https://bam.example',enableReviewReadiness:true,
  onError:message=>errors.push(message)});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 await app.refresh();
 const approvals=container.children[0].children[1].children[1];
 approvals.listeners.click();
 await tick();
 let section=container.children[0].children.find(x=>x.tag==='section');
 assert.ok(section);
 assert.match(section.children[0].textContent,/Editorial preparation/);
 assert.match(section.children[2].textContent,/1 of 1 held drafts/);
 assert.match(section.children[3].children[0].textContent,/Example tumbler/);
 assert.match(section.children[3].children[1].textContent,/still pending/);
 assert.ok(calls.some(x=>x.url.endsWith('/review-readiness')));
 assert.ok(calls.every(x=>x.options.method==='GET'));
 assert.equal(calls.at(-1).options.credentials,'omit');
 assert.equal(errors.length,0);
 failed=true;
 const result=await app.refreshReviewReadiness();
 assert.equal(result.error,true);
 section=container.children[0].children.find(x=>x.tag==='section');
 assert.match(section.children[2].textContent,/unavailable/);
 assert.match(errors.at(-1),/unavailable/);
 failed=false;
 hold=new Promise(resolve=>{release=resolve});
 const pending=app.refreshReviewReadiness();
 await Promise.resolve();
 app.clear();
 release();
 assert.equal((await pending).stale,true);
 assert.equal(container.children.length,0);
 approvals.listeners.click();
 assert.equal(container.children.length,0);
 console.log('BAM editorial-readiness Approvals dashboard tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
