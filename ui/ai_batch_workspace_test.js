'use strict';
const assert=require('node:assert/strict');
const {create}=require('./ai_workspace.js');
function node(tag){
  return {tag,children:[],textContent:'',className:'',value:'',
    checked:false,disabled:false,listeners:{},
    append(...children){this.children.push(...children)},
    replaceChildren(...children){this.children=children},
    addEventListener(event,callback){this.listeners[event]=callback}};
}
const document={createElement:node};
const drafts=node('main'),settings=node('main');
let tenant='shop',delay=null,release=null;
const requests=[],errors=[];
const fetchImpl=async(url,opts)=>{
  requests.push({url,opts});
  if(url.endsWith('/ai-drafts'))
    return {ok:true,json:async()=>({
      tenant_id:tenant,drafts:[],publishing_enabled:false})};
  if(url.endsWith('/ai-settings'))
    return {ok:true,json:async()=>({
      tenant_id:tenant,provider:'openai',mode:'bam_sponsored',
      own_key_configured:false,memory:{},key_exposed:false,
      publishing_enabled:false})};
  if(url.endsWith('/ai/batch-preview')){
    if(delay)await delay;
    const request=JSON.parse(opts.body);
    return {ok:true,status:200,json:async()=>({
      tenant_id:'shop',mode:'bam_sponsored',
      fact_revision:1,fact_provenance:'owner_confirmed',
      items:request.topics.map(topic=>({
        topic,platform:request.platform,
        image_prompt_planned:request.include_image_prompt})),
      planned_individual_requests:request.topics.length,
      provider_requests_made:0,quota_reserved:false,
      actual_cost_known:false,drafts_created:0,
      status:'planning_only',publishing_enabled:false})};
  }
  throw new Error('Unexpected request: '+url);
};
function controls(){
  const section=drafts.children[1];
  return {section,
    topic:section?.children?.find(x=>x.tag==='textarea'),
    platform:section?.children?.find(x=>x.tag==='select'),
    image:section?.children?.find(x=>x.tag==='label')?.children[0],
    details:section?.children?.find(x=>x.tag==='section'),
    button:section?.children?.find(x=>
      x.textContent==='Preview advance topic plan')};
}
async function main(){
  const app=create({document,draftsContainer:drafts,
    settingsContainer:settings,fetchImpl,
    origin:'https://bam.example',
    enableBatchPreviews:true,onError:text=>errors.push(text)});
  app.activate({token:'t'.repeat(43),tenantId:'shop'});
  app.setCapabilities({manageFacts:false,createDrafts:true});
  await app.refresh();
  const prepared=controls();
  assert.equal(prepared.section.className,'panel stack');
  assert.ok(prepared.button);
  prepared.topic.value='Tumbler spotlight\nHoliday gift idea';
  prepared.platform.value='facebook';
  prepared.image.checked=false;
  await prepared.button.listeners.click();
  assert.equal(requests.filter(x=>x.url.endsWith('/ai/batch-preview')).length,1);
  const call=requests.at(-1);
  assert.equal(call.opts.method,'POST');
  assert.equal(call.opts.credentials,'omit');
  assert.deepEqual(JSON.parse(call.opts.body),{
    topics:['Tumbler spotlight','Holiday gift idea'],
    platform:'facebook',include_image_prompt:false});
  assert.match(prepared.details.children[0].textContent,
    /Actual API requests: 0/);
  assert.match(prepared.details.children[0].textContent,
    /Drafts created: 0/);
  assert.equal(prepared.details.children.length,3);
  assert.equal(errors.length,0);
  // Duplicate topics do not make a server request.
  prepared.topic.value='Gift\ngift';
  await prepared.button.listeners.click();
  assert.equal(requests.filter(x=>x.url.endsWith('/ai/batch-preview')).length,1);
  assert.equal(errors.length,1);
  // Switch while a request is in flight: the previous result may not render.
  prepared.topic.value='Third idea';
  delay=new Promise(resolve=>{release=resolve});
  const pending=prepared.button.listeners.click();
  await Promise.resolve();
  app.activate({token:'u'.repeat(43),tenantId:'other'});
  release();
  await pending;
  assert.equal(drafts.children.length,0);
  await prepared.button.listeners.click();
  assert.equal(requests.filter(x=>x.url.endsWith('/ai/batch-preview')).length,2);
  // Restricted role never shows the planner.
  tenant='shop';delay=null;
  app.activate({token:'t'.repeat(43),tenantId:'shop'});
  app.setCapabilities({manageFacts:false,createDrafts:false});
  await app.refresh();
  assert.equal(drafts.children.length,1);
  app.clear();
  assert.equal(drafts.children.length,0);
  const ordinary=create({document,draftsContainer:drafts,
    settingsContainer:settings,fetchImpl,origin:'https://bam.example'});
  ordinary.activate({token:'t'.repeat(43),tenantId:'shop'});
  ordinary.setCapabilities({manageFacts:false,createDrafts:true});
  await ordinary.refresh();
  assert.equal(drafts.children.length,1);
  console.log('BAM zero-cost advance marketing batch workspace tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
