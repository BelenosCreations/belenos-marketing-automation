'use strict';
const assert=require('node:assert/strict');
const {create}=require('./ai_workspace.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items},
  addEventListener(name,fn){this.listeners[name]=fn}}}
const document={createElement:node};
const drafts=node('main'),settings=node('main'),facts=node('main'),
  costs=node('main'),editor=node('main');
const fetchImpl=async(url)=>({ok:true,json:async()=>{
  if(url.endsWith('/ai-drafts'))
    return {tenant_id:'shop',publishing_enabled:false,drafts:[]};
  if(url.endsWith('/ai-settings'))
    return {tenant_id:'shop',provider:'openai',mode:'bam_sponsored',
      own_key_configured:false,memory:{},key_exposed:false,
      publishing_enabled:false};
  if(url.endsWith('/ai-cost-summary'))
    return {tenant_id:'shop',events:1,input_tokens:1000,
      output_tokens:200,estimated_micro_usd:1800,
      pricing_basis:'operator_configured',
      actual_billing_verified:false,publishing_enabled:false};
  if(url.endsWith('/ai-business-facts'))
    return {tenant_id:'shop',facts:{product:'Custom tumblers'},
      revision:1,provenance:'owner_confirmed',confirmed_at:100,
      publishing_enabled:false};
  throw new Error('Unexpected route');
}});
async function main(){
  const saved=[];
  const workspace=create({document,draftsContainer:drafts,
    settingsContainer:settings,factsContainer:facts,costContainer:costs,
    factsEditorContainer:editor,canManageFacts:true,
    onSaveFacts:payload=>saved.push(payload),
    fetchImpl,origin:'https://bam.example'});
  workspace.activate({token:'valid',tenantId:'shop'});
  workspace.setCapabilities({manageFacts:true,createDrafts:true});
  assert.equal((await workspace.refresh()).draftCount,0);
  assert.match(facts.children[0].children[1].textContent,/Owner-confirmed/);
  assert.equal(facts.children[0].children[2].textContent,
               'product: Custom tumblers');
  assert.match(costs.children[0].children[4].textContent,/\$0\.0018/);
  editor.children[0].children[4].listeners.click();
  assert.equal(saved.length,1);
  assert.equal(saved[0].expectedTenantId,'shop');
  workspace.clear();
  assert.equal(editor.children.length,0);
  const broken=create({document,draftsContainer:drafts,
    settingsContainer:settings,factsContainer:facts,costContainer:costs,
    fetchImpl:async()=>({ok:false}),origin:'https://bam.example'});
  broken.activate({token:'valid',tenantId:'shop'});
  assert.equal((await broken.refresh()).error,true);
  assert.equal(facts.children.length,0);
  assert.equal(costs.children.length,0);
  assert.equal(editor.children.length,0);
  workspace.clear();
  assert.equal(facts.children.length,0);
  assert.equal(costs.children.length,0);
  // A later failed refresh must also erase the privileged editable form.
  let failNext=false;
  const flaky=create({document,draftsContainer:drafts,
    settingsContainer:settings,factsContainer:facts,costContainer:costs,
    factsEditorContainer:editor,canManageFacts:true,onSaveFacts:()=>{},
    fetchImpl:(...args)=>failNext?Promise.resolve({ok:false}):fetchImpl(...args),
    origin:'https://bam.example'});
  flaky.activate({token:'valid',tenantId:'shop'});
  flaky.setCapabilities({manageFacts:true,createDrafts:true});
  assert.equal((await flaky.refresh()).error,undefined);
  assert.equal(editor.children.length,1);
  failNext=true;
  assert.equal((await flaky.refresh()).error,true);
  assert.equal(editor.children.length,0);
  assert.equal(facts.children.length,0);
  flaky.clear();
  console.log('BAM AI workspace fact provenance tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
