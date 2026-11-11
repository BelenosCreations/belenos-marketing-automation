'use strict';
const assert=require('node:assert/strict');
const {create}=require('./ai_workspace.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},value:'',
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items},
  addEventListener(event,fn){this.listeners[event]=fn}}}
const document={createElement:node},drafts=node('main'),
  settings=node('main'),facts=node('main');
const requestId='b'.repeat(32);
const calls=[];
let generated=false;
const fetchImpl=async(url,opts)=>{
  calls.push({url,opts});
  const kind=url.split('/').pop();
  if(kind==='local-service-draft'&&opts.method==='POST'){
    generated=true;
    return {ok:true,json:async()=>({
      tenant_id:'service-co',draft_id:requestId,platform:'facebook',
      post_text:'Example Service: Commercial cleaning. Contact us for details.',
      image_prompt:'Generic service illustration',needs_media:true,
      media_attached:false,status:'needs_media',revision:1,
      publishing_enabled:false,generation_method:'local_template',
      openai_requests:0})};
  }
  if(kind==='ai-drafts')return {ok:true,json:async()=>({
    tenant_id:'service-co',publishing_enabled:false,
    drafts:generated?[{tenant_id:'service-co',draft_id:requestId,
      platform:'facebook',post_text:'Example Service: Commercial cleaning. Contact us for details.',
      image_prompt:'Generic service illustration',needs_media:true,
      media_attached:false,status:'needs_media',revision:1,
      publishing_enabled:false}]:[]})};
  if(kind==='ai-settings')return {ok:true,json:async()=>({
    tenant_id:'service-co',provider:'openai',mode:'bam_sponsored',
    own_key_configured:false,memory:{},key_exposed:false,
    publishing_enabled:false})};
  if(kind==='ai-business-facts')return {ok:true,json:async()=>({
    tenant_id:'service-co',revision:1,provenance:'owner_confirmed',
    confirmed_at:101,facts:{business_name:'Example Service',
      service:'Commercial cleaning'},publishing_enabled:false})};
  throw new Error('Unexpected URL '+url);
};
async function main(){
  const app=create({document,draftsContainer:drafts,
    settingsContainer:settings,factsContainer:facts,
    origin:'https://bam.example',fetchImpl,enableLocalTemplates:true});
  app.activate({token:'a'.repeat(43),tenantId:'service-co'});
  app.setCapabilities({manageFacts:false,createDrafts:true});
  assert.equal((await app.refresh()).draftCount,0);
  const action=drafts.children[1];
  const template=action.children.find(x=>x.tag==='select');
  assert.ok(template);
  assert.equal(template.value,'service');
  assert.equal(template.children[0].textContent,'Service spotlight');
  const trigger=action.children.find(x=>
    x.textContent==='Create cost-free marketing draft');
  assert.ok(trigger);
  await trigger.listeners.click();
  assert.equal(generated,true);
  assert.equal(drafts.children[0].children.length,3);
  const write=calls.find(x=>x.url.endsWith('/local-service-draft'));
  assert.ok(write);
  assert.deepEqual(JSON.parse(write.opts.body),{
    platform:'facebook',include_image_prompt:true});
  assert.equal(write.opts.credentials,'omit');
  app.clear();
  assert.equal(drafts.children.length,0);
  console.log('BAM service business zero-cost draft UI tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
