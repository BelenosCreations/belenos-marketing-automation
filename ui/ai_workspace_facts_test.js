'use strict';
const assert=require('node:assert/strict');
const {create}=require('./ai_workspace.js');
function node(tag){return {tag,textContent:'',children:[],
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items}}}
const document={createElement:node};
const drafts=node('main'),settings=node('main'),facts=node('main');
const fetchImpl=async(url)=>({ok:true,json:async()=>{
  if(url.endsWith('/ai-drafts'))
    return {tenant_id:'shop',publishing_enabled:false,drafts:[]};
  if(url.endsWith('/ai-settings'))
    return {tenant_id:'shop',provider:'openai',mode:'bam_sponsored',
      own_key_configured:false,memory:{},key_exposed:false,
      publishing_enabled:false};
  if(url.endsWith('/ai-business-facts'))
    return {tenant_id:'shop',facts:{product:'Custom tumblers'},
      revision:1,provenance:'owner_confirmed',confirmed_at:100,
      publishing_enabled:false};
  throw new Error('Unexpected route');
}});
async function main(){
  const workspace=create({document,draftsContainer:drafts,
    settingsContainer:settings,factsContainer:facts,
    fetchImpl,origin:'https://bam.example'});
  workspace.activate({token:'valid',tenantId:'shop'});
  assert.equal((await workspace.refresh()).draftCount,0);
  assert.match(facts.children[0].children[1].textContent,/Owner-confirmed/);
  assert.equal(facts.children[0].children[2].textContent,
               'product: Custom tumblers');
  workspace.clear();
  assert.equal(facts.children.length,0);
  console.log('BAM AI workspace fact provenance tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
