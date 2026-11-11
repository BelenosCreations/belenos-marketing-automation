'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./dashboard_data_contract.js');
const base={schema_version:1,tenant_id:'shop',
 businesses:[{tenant_id:'shop',display_name:'Shop'}],
 cards:['scheduled','approvals','content','connections'].map(id=>({
  id,label:id,value:id==='scheduled'?null:0,
  availability:id==='scheduled'?'not_connected':'available'
 })),
 drafts:[],analytics:{availability:'not_connected',series:null},
 schedule:{availability:'not_connected',posts:null},publishing_enabled:false
};
for(const role of ['owner','marketing_manager','content_creator','employee','viewer'])
 assert.equal(normalize({...base,role}).role,role);
assert.equal(normalize(base).role,'viewer');
for(const role of ['admin','superuser','',null,123,true])
 assert.throws(()=>normalize({...base,role}),TypeError);
assert.equal(normalize(base).pendingMediaAvailable,false);
assert.equal(normalize({...base,pending_media_available:true}).pendingMediaAvailable,true);
for(const invalid of ['true',1,null,[],{}])
 assert.throws(()=>normalize({...base,pending_media_available:invalid}),TypeError);
console.log('BAM dashboard capability role contract tests passed');
