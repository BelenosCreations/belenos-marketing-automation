'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./dashboard_data_contract.js');
const payload={
  schema_version:1,tenant_id:'shop',role:'owner',
  businesses:[{tenant_id:'shop',display_name:'Example Shop',role:'owner'}],
  cards:[
    {id:'scheduled',label:'Scheduled posts',value:null,availability:'not_connected'},
    {id:'approvals',label:'Needs review',value:1,availability:'available'},
    {id:'content',label:'Content needed',value:1,availability:'available'},
    {id:'connections',label:'Social connections',value:null,availability:'restricted'}
  ],
  drafts:[
    {request_id:'a'.repeat(32),channel:'facebook',draft_text:'Example',
     suggestion:'Provide photo',status:'needs_content',missing_items:['photo'],priority:0},
    {request_id:'b'.repeat(32),channel:'instagram',draft_text:'Another example',
     suggestion:'Review',status:'ready_for_review',missing_items:[],priority:0}
  ],
  analytics:{availability:'not_connected',series:null},
  schedule:{availability:'not_connected',posts:null},
  publishing_enabled:false
};
const clone=()=>JSON.parse(JSON.stringify(payload));
const result=normalize(payload);
assert.equal(result.tenantId,'shop');
assert.equal(result.drafts.length,2);
assert.equal(result.cards.scheduled.value,null);
assert.equal(result.cards.connections.availability,'restricted');
assert.equal(result.publishingEnabled,false);
assert.equal(result.analyticsAvailable,false);
assert.equal(result.scheduleAvailable,false);
for(const mutation of [
  p=>{p.publishing_enabled=true},
  p=>{p.tenant_id='other'},
  p=>{p.cards[0].value=0},
  p=>{p.cards[1].value=-1},
  p=>{p.cards.pop()},
  p=>{p.drafts[0].status='published'},
  p=>{p.drafts[0].channel='unknown'},
  p=>{p.drafts.push({...p.drafts[0]})},
  p=>{p.analytics.series=[123]},
  p=>{p.businesses.push({...p.businesses[0]})}
]){
  const modified=clone();mutation(modified);
  assert.throws(()=>normalize(modified),TypeError);
}
assert.equal(payload.drafts[0].draft_text,'Example','Adapter does not mutate backend data');
console.log('BAM authenticated dashboard data contract tests passed');
