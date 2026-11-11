'use strict';
const assert=require('node:assert/strict');
const {create}=require('./held_draft_workspace.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},
  value:'',className:'',disabled:false,
  append(...x){this.children.push(...x)},
  replaceChildren(...x){this.children=x},
  addEventListener(name,fn){this.listeners[name]=fn},
  setAttribute(name,value){this[name]=value}};}
const document={createElement:node},container=node('main');
const draft=(id,channel,status,copy,guidance)=>({
  request_id:id.repeat(32),channel,status,draft_text:copy,
  suggestion:guidance,priority:0,revision:1,missing_items:['image']});
let tenant='shop';
const drafts=[draft('a','facebook','needs_content',
  'Christmas tumblers','Product photography'),
  draft('b','instagram','ready_for_review',
  'Custom resin painting','Portrait proof'),
  draft('c','instagram','postponed','Spring calendar','Wait until April'),
  draft('d','facebook','unavailable','Old promotion','Offer withdrawn')];
const calls=[];
const fetchImpl=async(url,options)=>{
  calls.push({url,options});
  if(!url.endsWith('/drafts')||options.method!=='GET')
    throw Error('Filtering must not call a write endpoint');
  return {ok:true,json:async()=>({
    tenant_id:tenant,publishing_enabled:false,
    drafts:tenant==='shop'?drafts:[draft('e','facebook',
      'needs_content','Other tenant safety checklist','Separate account')]})};
};
function filters(){
 const root=container.children[0];
 const region=root.children.find(x=>x.className==='bam-content-studio-filters');
 assert.ok(region);
 const controls=region.children[1].children;
 return {status:controls[0],channel:controls[1],query:controls[2],
  apply:controls[3],clear:controls[4],summary:region.children[2]};
}
function visible(){
 const root=container.children[0];
 const statusSections=root.children.filter(x=>x.tag==='section'&&
   x.className!=='bam-content-studio-filters');
 return statusSections.flatMap(x=>x.children.filter(y=>y.tag==='article'))
  .map(article=>article.children[1].textContent);
}
async function main(){
 const app=create({document,container,fetchImpl,origin:'https://bam.example'});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 app.setCanEdit(true);
 await app.refresh();
 assert.equal(visible().length,4);
 assert.match(filters().summary.textContent,/4 of 4/);
 let f=filters();
 f.status.value='ready_for_review';f.channel.value='instagram';
 f.query.value='resin';
 f.apply.listeners.click();
 assert.deepEqual(visible(),['Custom resin painting']);
 assert.match(filters().summary.textContent,/1 of 4/);
 assert.equal(calls.length,1);
 await app.refresh();
 assert.deepEqual(visible(),['Custom resin painting']);
 f=filters();
 f.query.value='x'.repeat(121);
 assert.throws(()=>f.apply.listeners.click(),TypeError);
 assert.deepEqual(visible(),['Custom resin painting']);
 f=filters();
 f.clear.listeners.click();
 assert.equal(visible().length,4);
 assert.match(filters().summary.textContent,/4 of 4/);
 f=filters();
 f.query.value='image';
 f.apply.listeners.click();
 assert.equal(visible().length,0);
 assert.match(filters().summary.textContent,/0 of 4/);
 const oldButton=filters().clear;
 app.clear();
 tenant='other';
 app.activate({token:'u'.repeat(43),tenantId:'other'});
 app.setCanEdit(false);
 await app.refresh();
 assert.deepEqual(visible(),['Other tenant safety checklist']);
 assert.match(filters().summary.textContent,/1 of 1/);
 oldButton.listeners.click();
 assert.deepEqual(visible(),['Other tenant safety checklist']);
 assert.ok(calls.every(x=>x.options.method==='GET'));
 app.clear();
 assert.equal(container.children.length,0);
 console.log('BAM private Content Studio nonmutating search and filtering tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
