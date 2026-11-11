'use strict';
const assert=require('node:assert/strict');
const {create}=require('./held_draft_workspace.js');
function node(tag){return {tag,children:[],textContent:'',listeners:{},
 value:'',disabled:false,files:null,
 append(...v){this.children.push(...v)},
 replaceChildren(...v){this.children=v},
 addEventListener(name,callback){this.listeners[name]=callback}}}
const document={createElement:node};
const header='channel,draft_text,suggestion,required_items\n';
const csv=header+'facebook,Product one,Need image,image\n'+
  'instagram,Product two,Need approval,permission|photo';
function setup({failureOn=0}={}){
 const container=node('main'),calls=[],notices=[],errors=[],drafts=[];
 let tries=0;
 const fetchImpl=async(url,opts)=>{
   calls.push({url,opts});
   if(opts.method==='GET')return {ok:true,json:async()=>({
     tenant_id:'shop',publishing_enabled:false,drafts})};
   if(url.endsWith('/content/drafts')&&opts.method==='POST'){
     tries++;
     if(failureOn===tries)return {ok:false};
     const item=JSON.parse(opts.body),id=tries.toString(16).padStart(32,'0');
     drafts.push({request_id:id,channel:item.channel,
       draft_text:item.draft_text,suggestion:item.suggestion,
       missing_items:item.required_items,priority:0,
       status:'needs_content',revision:1});
     return {ok:true,json:async()=>({
       tenant_id:'shop',request_id:id,status:'needs_content',
       publishing_enabled:false})};
   }
   throw Error('Unexpected request');
 };
 const app=create({document,container,fetchImpl,origin:'https://bam.example',
   onNotice:value=>notices.push(value),onError:value=>errors.push(value)});
 app.activate({token:'a'.repeat(43),tenantId:'shop'});
 app.setCanEdit(true);
 return {app,container,calls,notices,errors,drafts};
}
function controls(container){
 const wrap=container.children[0],advanced=wrap.children.at(-1);
 const picker=advanced.children.find(x=>x.tag==='input');
 const preview=advanced.children.find(
   x=>x.textContent==='Preview CSV draft import');
 const confirm=advanced.children.find(x=>
   x.textContent.startsWith('Confirm import of '));
 return {advanced,picker,preview,confirm};
}
async function prepare(instance){
 await instance.app.refresh();
 const first=controls(instance.container);
 first.picker.files=[{size:csv.length,text:async()=>csv}];
 await first.preview.listeners.click();
 const next=controls(instance.container);
 assert.ok(next.confirm);
 assert.equal(next.confirm.textContent,'Confirm import of 2 held drafts');
}
async function main(){
 const instance=setup();
 await prepare(instance);
 await controls(instance.container).confirm.listeners.click();
 assert.equal(instance.drafts.length,2);
 assert.equal(instance.calls.filter(x=>x.opts.method==='POST').length,2);
 assert.ok(instance.notices.some(x=>/2 held drafts saved/.test(x)));
 assert.equal(instance.errors.length,0);
 assert.equal(instance.drafts.every(x=>x.status==='needs_content'),true);
 assert.equal(instance.calls.every(x=>
   !x.opts.body||!JSON.parse(x.opts.body).publish_now),true);
 assert.equal(controls(instance.container).confirm,undefined);
 // Existing exact copied drafts must not be imported twice.
 const again=controls(instance.container);
 again.picker.files=[{size:csv.length,text:async()=>csv}];
 await again.preview.listeners.click();
 assert.equal(controls(instance.container).confirm,undefined);
 assert.ok(instance.errors.some(x=>/duplicates/.test(x)));
 const partial=setup({failureOn:2});
 await prepare(partial);
 await controls(partial.container).confirm.listeners.click();
 assert.equal(partial.drafts.length,1);
 assert.ok(partial.errors.some(x=>/stopped after 1/.test(x)));
 assert.ok(partial.notices.some(x=>/1 held drafts/.test(x)));
 assert.equal(partial.calls.filter(x=>x.opts.method==='POST').length,2);
 const old=controls(partial.container).preview;
 partial.app.clear();
 await old.listeners.click();
 assert.equal(partial.container.children.length,0);
 console.log('BAM explicit bulk held-draft CSV UI tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
