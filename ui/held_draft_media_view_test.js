'use strict';
const assert=require('node:assert/strict');
const {create}=require('./held_draft_workspace.js');
function node(tag){
  return {tag,textContent:'',children:[],listeners:{},value:'',
    append(...xs){this.children.push(...xs)},
    replaceChildren(...xs){this.children=xs},
    addEventListener(k,fn){this.listeners[k]=fn}};
}
const document={createElement:node},container=node('main');
const draftId='a'.repeat(32),attachmentId='b'.repeat(32);
const data=Uint8Array.from([137,80,78,71,13,10,26,10,42]);
const file={type:'image/png',size:data.length,
  arrayBuffer:async()=>data.slice().buffer};
const calls=[],notices=[],errors=[];
let hasReceipt=false;
const fetchImpl=async(url,opts)=>{
  calls.push({url,opts});
  if(url.endsWith('/media-status'))return {ok:true,status:200,
    json:async()=>({tenant_id:'shop',items:hasReceipt?[{
      request_id:draftId,item:'image',status:'pending_scan'}]:[],
      media_verified:false,publishing_enabled:false})};
  if(opts.method==='GET')return {ok:true,json:async()=>({
    tenant_id:'shop',publishing_enabled:false,drafts:[{
      request_id:draftId,channel:'facebook',draft_text:'Draft',
      suggestion:'Provide approved image',status:'needs_content',
      missing_items:['image'],priority:0}]})};
  if(url.endsWith('/media-pending')){
    hasReceipt=false;
    return {ok:true,status:200,json:async()=>({tenant_id:'shop',
      request_id:draftId,item:'image',removed:1,
      media_verified:false,publishing_enabled:false})};
  }
  if(url.endsWith('/upload-preflight'))
    return {ok:true,status:202,json:async()=>({
      tenant_id:'shop',request_id:draftId,item:'image',
      attachment_id:attachmentId,status:'pending',
      max_bytes:20*1024*1024,upload_url:null,publishing_enabled:false})};
  hasReceipt=true;
  return {ok:true,status:202,json:async()=>({
    tenant_id:'shop',attachment_id:attachmentId,status:'pending_scan',
    bytes_received:data.length,media_verified:false,publishing_enabled:false})};
};
async function main(){
  const app=create({document,container,fetchImpl,origin:'https://bam.example',
    onNotice:msg=>notices.push(msg),onError:msg=>errors.push(msg),
    hashBytes:async()=> 'f'.repeat(64)});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  app.setCanEdit(true);app.setMediaEnabled(true);
  assert.equal((await app.refresh()).heldCount,1);
  const article=container.children[0].children[3].children[1];
  const picker=article.children.find(x=>x.tag==='input');
  const upload=article.children.find(x=>
    x.textContent==='Send image for private review');
  assert.ok(picker&&upload);
  picker.files=[file];
  await upload.listeners.click();
  assert.equal(calls.filter(x=>x.opts.method==='POST').length,1);
  assert.equal(calls.filter(x=>x.opts.method==='PUT').length,1);
  assert.equal(calls.filter(x=>x.url.endsWith('/media-status')).length,2,
    JSON.stringify({errors,notices,paths:calls.map(x=>x.url)}));
  const after=container.children[0].children[3].children[1];
  assert.ok(after.children.some(x=>/Awaiting review/.test(x.textContent)));
  assert.equal(after.children.some(x=>x.textContent==='Send image for private review'),false);
  const remove=after.children.find(x=>x.textContent==='Discard pending image');
  assert.ok(remove);
  await remove.listeners.click();
  const confirm=after.children.find(
    x=>x.textContent==='Confirm discard of unverified image');
  assert.ok(confirm);
  await confirm.listeners.click();
  assert.equal(calls.filter(x=>x.opts.method==='DELETE').length,1);
  assert.equal(hasReceipt,false);
  const restored=container.children[0].children[3].children[1];
  assert.ok(restored.children.some(
    x=>x.textContent==='Send image for private review'));
  assert.match(notices.at(-1),/discarded/);
  assert.ok(notices.some(x=>/pending review/.test(x)));
  assert.equal(errors.length,0);
  app.setMediaEnabled(false);
  assert.equal(container.children[0].children[3].children[1].children.some(
    x=>x.textContent==='Send image for private review'),false);
  app.clear();
  assert.equal(container.children.length,0);
  console.log('BAM private pending image picker DOM tests passed');
}
main().catch(err=>{console.error(err);process.exitCode=1});
