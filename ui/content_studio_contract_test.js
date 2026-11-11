'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./content_studio_contract.js');
const good={
  tenant_id:'shop',publishing_enabled:false,
  drafts:[{request_id:'a'.repeat(32),channel:'facebook',
    draft_text:'Post example',suggestion:'Provide photo',
    status:'postponed',missing_items:['photo'],priority:0,revision:2}]
};
const clone=()=>JSON.parse(JSON.stringify(good));
const result=normalize(good);
assert.equal(result.tenantId,'shop');
assert.equal(result.drafts[0].status,'postponed');
assert.equal(result.drafts[0].revision,2);
assert.equal(result.drafts[0].missing[0],'photo');
assert.equal(result.publishingEnabled,false);
for(const mutate of [
  p=>{p.tenant_id=''},
  p=>{p.publishing_enabled=true},
  p=>{p.drafts[0].status='published'},
  p=>{p.drafts[0].priority=100},
  p=>{p.drafts[0].revision=0},
  p=>{p.drafts[0].revision=true},
  p=>{p.drafts[0].request_id='bad'},
  p=>{p.drafts[0].channel='other'},
  p=>{p.drafts[0].missing_items.push('photo')},
  p=>{p.drafts.push({...p.drafts[0]})}
]){
  const value=clone();mutate(value);
  assert.throws(()=>normalize(value),TypeError);
}
console.log('BAM Content Studio contract tests passed');
