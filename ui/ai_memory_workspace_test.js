'use strict';
const assert=require('node:assert/strict');
const {create}=require('./ai_workspace.js');
function node(tag){
 return {tag,textContent:'',className:'',value:'',disabled:false,
  listeners:{},children:[],
  append(...parts){this.children.push(...parts)},
  replaceChildren(...parts){this.children=parts},
  addEventListener(kind,fn){this.listeners[kind]=fn}};
}
const document={createElement:node},
  drafts=node('main'),settings=node('main');
const calls=[],errors=[];
let memory={tone:'Brief posts'};
const token='t'.repeat(43);
const fetchImpl=async(url,opts)=>{
 calls.push({url,opts});
 if(url.endsWith('/ai-drafts'))
   return {ok:true,json:async()=>({
     tenant_id:'shop',drafts:[],publishing_enabled:false})};
 if(url.endsWith('/ai-settings'))
   return {ok:true,json:async()=>({
     tenant_id:'shop',provider:'openai',mode:'bam_sponsored',
     own_key_configured:false,memory:{...memory},key_exposed:false,
     publishing_enabled:false})};
 if(url.endsWith('/ai-memory')&&opts.method==='PUT'){
   assert.equal(opts.credentials,'omit');
   assert.equal(opts.headers.Authorization,'Bearer '+token);
   const request=JSON.parse(opts.body);
   if(JSON.stringify(request.expected_memory)!==JSON.stringify(memory))
     return {ok:false,status:409};
   memory={...request.memory};
   return {ok:true,status:200,json:async()=>({
      tenant_id:'shop',memory:{...memory},publishing_enabled:false})};
 }
 throw new Error('Unexpected request '+url);
};
async function main(){
 const app=create({document,draftsContainer:drafts,settingsContainer:settings,
   origin:'https://bam.example',fetchImpl,onError:text=>errors.push(text)});
 app.activate({token,tenantId:'shop'});
 app.setCapabilities({manageFacts:false,createDrafts:true});
 assert.equal((await app.refresh()).draftCount,0);
 let editor=settings.children[0].children.at(-1);
 assert.equal(editor.className,'bam-ai-memory-editor');
 let row=editor.children.find(x=>x.className==='bam-ai-memory-row');
 assert.equal(row.children[0].value,'tone');
 assert.equal(row.children[1].value,'Brief posts');
 row.children[1].value='Short, factual Facebook copy';
 let save=editor.children.find(x=>
   x.textContent==='Save AI writing preferences');
 await save.listeners.click();
 assert.deepEqual(memory,{tone:'Short, factual Facebook copy'});
 assert.equal(errors.length,0);
 assert.equal(calls.filter(x=>x.url.endsWith('/ai-memory')).length,1);
 editor=settings.children[0].children.at(-1);
 row=editor.children.find(x=>x.className==='bam-ai-memory-row');
 assert.equal(row.children[1].value,'Short, factual Facebook copy');
 assert.match(settings.children[0].children[5].textContent,
   /Short, factual Facebook copy/);
 // Another device updated the same identity's memory: old edits fail.
 memory={tone:'More recent setting'};
 row.children[1].value='Stale override';
 save=editor.children.find(x=>
   x.textContent==='Save AI writing preferences');
 await save.listeners.click();
 assert.deepEqual(memory,{tone:'More recent setting'});
 assert.ok(errors.some(x=>/Refresh before editing again/.test(x)));
 const requestsBeforeRotation=calls.length;
 app.activate({token:'q'.repeat(43),tenantId:'other'});
 await save.listeners.click();
 assert.equal(calls.length,requestsBeforeRotation);
 app.clear();
 assert.equal(settings.children.length,0);
 // Viewers cannot edit preferences or fire mutable calls.
 const viewer=create({document,draftsContainer:drafts,
   settingsContainer:settings,origin:'https://bam.example',fetchImpl});
 viewer.activate({token,tenantId:'shop'});
 viewer.setCapabilities({manageFacts:false,createDrafts:false});
 await viewer.refresh();
 assert.equal(settings.children[0].children.some(x=>
   x.className==='bam-ai-memory-editor'),false);
 console.log('BAM per-user AI writing preference workspace tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
