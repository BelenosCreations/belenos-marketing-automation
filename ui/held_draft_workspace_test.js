'use strict';
const assert=require('node:assert/strict');
const {create}=require('./held_draft_workspace.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},value:'',
  append(...x){this.children.push(...x)},replaceChildren(...x){this.children=x},
  addEventListener(k,f){this.listeners[k]=f}}}
const document={createElement:node},container=node('main');
const base={tenant_id:'shop',publishing_enabled:false,drafts:[]};
let draftCount=0,readWait=null,releaseRead=null;
const calls=[];
const fetchImpl=async(url,opts)=>{
  calls.push({url,opts});
  if(opts.method==='POST'){
    if(url.endsWith('/drafts')){draftCount++;return {ok:true,json:async()=>({
      tenant_id:'shop',request_id:'b'.repeat(32),status:'needs_content',
      publishing_enabled:false})};}
    return {ok:true,json:async()=>({tenant_id:'shop',
      request_id:'b'.repeat(32),status:JSON.parse(opts.body).status,
      publishing_enabled:false})};
  }
  if(readWait)await readWait;
  return {ok:true,json:async()=>({...base,drafts:draftCount?[{
    request_id:'b'.repeat(32),channel:'facebook',status:'needs_content',
    draft_text:'New launch',suggestion:'Wait for photo',priority:0,
    missing_items:['image']}]:[]})};
};
async function main(){
  const app=create({document,container,fetchImpl,origin:'https://bam.example'});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  app.setCanEdit(true);
  assert.equal((await app.refresh()).heldCount,0);
  const created=await app.createDraft({channel:'facebook',
    draftText:'New launch',suggestion:'Wait for photo',
    requiredItems:['image']});
  assert.equal(created.status,'needs_content');
  assert.equal(draftCount,1);
  assert.equal(container.children.length,1);
  const changed=await app.changeHold({
    requestId:'b'.repeat(32),status:'postponed'});
  assert.equal(changed.status,'postponed');
  assert.equal(calls.filter(x=>x.opts.method==='POST').length,2);
  // Failed server response cannot be displayed as success.
  const blocked=create({document,container:node('main'),origin:'https://bam.example',
    fetchImpl:async(url,opts)=>opts.method==='GET'
      ?{ok:true,json:async()=>base}
      :{ok:true,json:async()=>({tenant_id:'another',
        request_id:'b'.repeat(32),status:'needs_content',
        publishing_enabled:false})}});
  blocked.activate({token:'a'.repeat(43),tenantId:'shop'});
  blocked.setCanEdit(true);
  await blocked.refresh();
  assert.equal((await blocked.createDraft({channel:'facebook',
    draftText:'copy',suggestion:'guide',requiredItems:['image']})).error,true);
  // A stale business read cannot restore private content after logout/switch.
  readWait=new Promise(resolve=>{releaseRead=resolve});
  const pending=app.refresh();
  await Promise.resolve();
  app.clear();releaseRead();
  assert.equal((await pending).stale,true);
  assert.equal(container.children.length,0);
  console.log('BAM held draft workspace lifecycle tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
