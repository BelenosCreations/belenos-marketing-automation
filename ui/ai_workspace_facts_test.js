'use strict';
const assert=require('node:assert/strict');
const {create}=require('./ai_workspace.js');
function node(tag){return {tag,textContent:'',children:[],
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items}}}
const document={createElement:node};
const drafts=node('main'),settings=node('main'),facts=node('main'),
  costs=node('main');
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
  const workspace=create({document,draftsContainer:drafts,
    settingsContainer:settings,factsContainer:facts,costContainer:costs,
    fetchImpl,origin:'https://bam.example'});
  workspace.activate({token:'valid',tenantId:'shop'});
  assert.equal((await workspace.refresh()).draftCount,0);
  assert.match(facts.children[0].children[1].textContent,/Owner-confirmed/);
  assert.equal(facts.children[0].children[2].textContent,
               'product: Custom tumblers');
  assert.match(costs.children[0].children[4].textContent,/\\$0.0018/);
  const broken=create({document,draftsContainer:drafts,
    settingsContainer:settings,factsContainer:facts,
    fetchImpl:async()=>({ok:false}),origin:'https://bam.example'});
  broken.activate({token:'valid',tenantId:'shop'});
  assert.equal((await broken.refresh()).error,true);
  assert.equal(facts.children.length,0);
  assert.equal(costs.children.length,0);
  workspace.clear();
  assert.equal(facts.children.length,0);
  assert.equal(costs.children.length,0);
  console.log('BAM AI workspace fact provenance tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
