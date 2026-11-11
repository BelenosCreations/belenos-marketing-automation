'use strict';
const assert=require('node:assert/strict');
const {create}=require('./held_draft_workspace.js');
function node(tag){return {tag,textContent:'',className:'',
  children:[],listeners:{},value:'',disabled:false,
  append(...x){this.children.push(...x)},
  replaceChildren(...x){this.children=x},
  addEventListener(event,fn){this.listeners[event]=fn},
  setAttribute(name,value){this[name]=value}};}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),errors=[],calls=[],drafts=[];
const fetchImpl=async(url,options)=>{
 calls.push({url,options});
 if(options.method==='GET'&&url.endsWith('/drafts'))
   return {ok:true,json:async()=>({
    tenant_id:'shop',publishing_enabled:false,drafts})};
 if(options.method==='POST'&&url.endsWith('/content/drafts')){
   const item=JSON.parse(options.body);
   assert.equal(item.priority,2);
   assert.equal(item.channel,'facebook');
   assert.equal(item.draft_text,'Priority custom print');
   assert.deepEqual(item.required_items,['image']);
   drafts.push({request_id:rid,channel:'facebook',priority:item.priority,
     draft_text:item.draft_text,suggestion:item.suggestion,
     missing_items:['image'],status:'needs_content',revision:1});
   return {ok:true,status:201,json:async()=>({
     tenant_id:'shop',request_id:rid,status:'needs_content',
     publishing_enabled:false})};
 }
 throw Error('Unexpected route or unsupported write');
};
function form(){
 return container.children[0].children.find(x=>x.tag==='form');
}
function fieldByLabel(label){
 const field=form().children.find(x=>x.tag==='div'&&
    x.children[0]?.textContent===label);
 assert.ok(field,label);
 return field.children[1];
}
async function main(){
 const app=create({document,container,fetchImpl,
   origin:'https://bam.example',onError:e=>errors.push(e)});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 app.setCanEdit(true);
 await app.refresh();
 assert.ok(form());
 const priority=fieldByLabel('Draft queue priority (higher reviewed first)');
 assert.equal(priority.value,'0');
 assert.equal(priority.children.length,5);
 fieldByLabel('Draft copy').value='Priority custom print';
 fieldByLabel('Content guidance').value='Request approved image';
 fieldByLabel('Required items, separated by commas').value='image';
 priority.value='2';
 await form().listeners.submit({preventDefault(){}});
 assert.equal(drafts.length,1);
 assert.equal(calls.filter(x=>x.options.method==='POST').length,1);
 const root=container.children[0];
 const queue=root.children.find(x=>x.tag==='section'&&
   x.children[0]?.textContent?.startsWith('needs content'));
 assert.ok(queue);
 assert.ok(queue.children[1].children.some(x=>
   /Draft priority: 2/.test(x.textContent)));
 const next=form();
 const priorityAgain=fieldByLabel('Draft queue priority (higher reviewed first)');
 priorityAgain.value='99';
 fieldByLabel('Draft copy').value='Another draft';
 fieldByLabel('Content guidance').value='More work';
 await next.listeners.submit({preventDefault(){}});
 assert.equal(calls.filter(x=>x.options.method==='POST').length,1);
 assert.ok(errors.length>0);
 assert.ok(calls.every(x=>!x.url.includes('/publish')));
 app.setCanEdit(false);
 assert.equal(form(),undefined);
 app.clear();
 assert.equal(container.children.length,0);
 console.log('BAM explicit unpublished draft priority selection and input validation passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
