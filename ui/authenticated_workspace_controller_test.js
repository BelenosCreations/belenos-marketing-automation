'use strict';
const assert=require('node:assert/strict');
const {create}=require('./authenticated_workspace_controller.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},
  append(...x){this.children.push(...x)},
  replaceChildren(...x){this.children=x},
  addEventListener(k,f){this.listeners[k]=f}}}
const document={createElement:node};
const dashboard=node('main'),drafts=node('main'),settings=node('main'),
  facts=node('main'),costs=node('main');
const data={
  dashboard:{schema_version:1,tenant_id:'shop',
    businesses:[{tenant_id:'shop',display_name:'Example Shop'}],
    cards:[
      {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
      {id:'approvals',label:'Approvals',value:0,availability:'available'},
      {id:'content',label:'Content',value:0,availability:'available'},
      {id:'connections',label:'Connections',value:0,availability:'available'}],
    drafts:[],analytics:{availability:'not_connected',series:null},
    schedule:{availability:'not_connected',posts:null},
    publishing_enabled:false},
  'ai-drafts':{tenant_id:'shop',drafts:[],publishing_enabled:false},
  'ai-settings':{tenant_id:'shop',provider:'openai',
    mode:'bam_sponsored',own_key_configured:false,
    memory:{},key_exposed:false,publishing_enabled:false},
  'ai-business-facts':{tenant_id:'shop',facts:{name:'Example Shop'},
    revision:1,provenance:'owner_confirmed',confirmed_at:100,
    publishing_enabled:false},
  'ai-cost-summary':{tenant_id:'shop',events:0,input_tokens:0,
    output_tokens:0,estimated_micro_usd:0,
    pricing_basis:'operator_configured',
    actual_billing_verified:false,publishing_enabled:false}
};
let blocked=null,failAI=false;
const fetchImpl=async(url)=>{
  const kind=url.split('/').pop();
  if(blocked&&kind==='dashboard')
    return {ok:true,json:async()=>blocked};
  return {ok:!(failAI&&kind==='ai-settings'),
    json:async()=>data[kind]};
};
const app=create({document,dashboardContainer:dashboard,
  aiDraftsContainer:drafts,aiSettingsContainer:settings,
  aiFactsContainer:facts,aiCostContainer:costs,
  fetchImpl,origin:'https://bam.example'});
async function main(){
  app.activate({token:'valid',tenantId:'shop'});
  assert.equal((await app.refresh()).stale,false);
  assert.equal(dashboard.children.length,1);
  assert.equal(facts.children.length,1);
  failAI=true;
  assert.equal((await app.refresh()).error,true);
  assert.equal(dashboard.children.length,0);
  assert.equal(settings.children.length,0);
  assert.equal(costs.children.length,0);
  failAI=false;
  app.activate({token:'valid',tenantId:'shop'});
  blocked=new Promise(resolve=>{blocked.resolve=resolve});
  // A pending server read must never resurrect a logged-out session.
  const pending=app.refresh();
  await Promise.resolve();
  app.clear();
  blocked.resolve(data.dashboard);
  assert.equal((await pending).stale,true);
  assert.equal(dashboard.children.length,0);
  console.log('BAM authenticated workspace lifecycle tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
