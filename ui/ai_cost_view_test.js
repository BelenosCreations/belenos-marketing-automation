'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./ai_cost_contract.js');
const {render}=require('./ai_cost_view.js');
const {read}=require('./dashboard_http_client.js');
function node(tag){return {tag,textContent:'',children:[],
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items}}}
const document={createElement:node},container=node('main');
const data={tenant_id:'shop',events:1,input_tokens:1000,
  output_tokens:200,estimated_micro_usd:1800,
  pricing_basis:'operator_configured',
  actual_billing_verified:false,publishing_enabled:false};
assert.equal(normalize(data).estimatedMicroUsd,1800);
render({document,container,payload:data,expectedTenantId:'shop'});
assert.match(container.children[0].children[4].textContent,/\$0.0018/);
assert.match(container.children[0].children[5].textContent,/Not an invoice/);
for(const patch of [
  {actual_billing_verified:true},{publishing_enabled:true},
  {estimated_micro_usd:-1},{estimated_micro_usd:1.1},
  {pricing_basis:'live_bill'}
])assert.throws(()=>normalize({...data,...patch}),TypeError);
const old=container.children[0];
assert.throws(()=>render({document,container,payload:data,
  expectedTenantId:'other'}),TypeError);
assert.equal(container.children[0],old);
async function main(){
  const result=await read({kind:'aiCosts',token:'valid',
    expectedTenantId:'shop',origin:'https://bam.example',
    fetchImpl:async(url)=>{assert.equal(url,
      'https://bam.example/api/v1/ai-cost-summary');
      return {ok:true,json:async()=>data}}});
  assert.equal(result.events,1);
  console.log('BAM AI estimated-cost UI tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
