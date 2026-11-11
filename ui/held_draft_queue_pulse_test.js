'use strict';
const assert=require('node:assert/strict');
const {create}=require('./held_draft_workspace.js');
function node(tag){
 return {tag,textContent:'',children:[],listeners:{},value:'',
 className:'',disabled:false,
 append(...items){this.children.push(...items)},
 replaceChildren(...items){this.children=items},
 addEventListener(event,fn){this.listeners[event]=fn},
 setAttribute(name,value){this[name]=value}};
}
const document={createElement:node},container=node('main');
const sample=(id,status,priority,missing)=>({
 request_id:id.repeat(32),channel:'facebook',status,
 priority,revision:1,draft_text:'Product '+id,
 suggestion:'Get confirmed artwork '+id,missing_items:missing});
const shop=[
 sample('a','needs_content',3,['image','permission']),
 sample('b','needs_content',0,['photo']),
 sample('c','ready_for_review',1,[]),
 sample('d','postponed',-1,[]),
 sample('e','unavailable',2,['image'])
];
let tenant='shop';const calls=[];
const fetchImpl=async(url,opts)=>{
 calls.push({url,opts});
 if(!url.endsWith('/drafts')||opts.method!=='GET')
  throw Error('Unexpected write or unrelated endpoint');
 return {ok:true,json:async()=>({
  tenant_id:tenant,publishing_enabled:false,
  drafts:tenant==='shop'?shop:[sample('f','needs_content',-2,['image'])]})};
};
function ui(){
 const root=container.children[0];
 const section=root.children.find(x=>x.className==='bam-content-studio-filters');
 assert.ok(section);
 const controls=section.children[1].children;
 const pulse=section.children.find(x=>x.className==='bam-content-queue-pulse');
 assert.ok(pulse);
 return {section,controls,pulse};
}
function countVisible(){
 const root=container.children[0];
 return root.children.filter(x=>x.tag==='section'&&
  x.className!=='bam-content-studio-filters')
  .reduce((sum,section)=>sum+
   section.children.filter(x=>x.tag==='article').length,0);
}
async function main(){
 const app=create({document,container,fetchImpl,origin:'https://bam.example'});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 app.setCanEdit(false);
 await app.refresh();
 let {pulse,controls}=ui();
 assert.match(pulse.children[1].textContent,/2 need content/);
 assert.match(pulse.children[1].textContent,/1 ready for human review/);
 assert.match(pulse.children[1].textContent,/2 postponed\/unavailable/);
 assert.match(pulse.children[2].textContent,/1 high-priority drafts/);
 assert.match(pulse.children[2].textContent,/3 total outstanding checklist items/);
 assert.equal(countVisible(),5);
 assert.equal(controls[5].value,'all');
 controls[5].value='urgent';
 controls[3].listeners.click();
 assert.equal(countVisible(),2);
 assert.match(ui().section.children[2].textContent,/2 of 5/);
 ui().pulse.children[3].children[0].listeners.click();
 assert.equal(countVisible(),1);
 assert.match(ui().section.children[2].textContent,/1 of 5/);
 assert.equal(ui().controls[5].value,'high');
 ui().pulse.children[3].children[1].listeners.click();
 assert.equal(countVisible(),1);
 assert.equal(ui().controls[0].value,'ready_for_review');
 ui().pulse.children[3].children[2].listeners.click();
 assert.equal(countVisible(),5);
 controls=ui().controls;
 controls[5].value='invalid';
 assert.throws(()=>controls[3].listeners.click(),TypeError);
 assert.equal(countVisible(),5);
 const oldShortcut=ui().pulse.children[3].children[0];
 app.clear();
 tenant='other';
 app.activate({token:'v'.repeat(43),tenantId:'other'});
 await app.refresh();
 assert.equal(countVisible(),1);
 assert.match(ui().pulse.children[1].textContent,/1 need content/);
 oldShortcut.listeners.click();
 assert.equal(countVisible(),1);
 assert.equal(ui().controls[5].value,'all');
 assert.ok(calls.every(x=>x.opts.method==='GET'));
 app.clear();
 assert.equal(container.children.length,0);
 console.log('BAM held queue priority pulse, quick filters and tenant reset passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
