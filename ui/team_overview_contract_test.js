'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./team_overview_contract.js');
const good={tenant_id:'shop',roles:{owner:1,marketing_manager:1,
  content_creator:2,employee:0,viewer:1},active_members:5,
  inactive_members:2,invitation_status:'not_connected',
  publishing_enabled:false};
assert.equal(normalize(good).activeMembers,5);
assert.equal(normalize(good).roles.content_creator,2);
assert.ok(Object.isFrozen(normalize(good).roles));
for(const bad of [
 {...good,tenant_id:' '},{...good,active_members:4},
 {...good,active_members:Infinity},{...good,active_members:5.5},
 {...good,inactive_members:-1},{...good,publishing_enabled:true},
 {...good,invitation_status:'enabled'},
 {...good,roles:{...good.roles,owner:0}},
 {...good,roles:{...good.roles,viewer:-1}},
 {...good,roles:{...good.roles,employee:true}},
 {...good,roles:{...good.roles,superuser:1}},
 {...good,token:'a'.repeat(32)}
])assert.throws(()=>normalize(bad),TypeError);
console.log('BAM owner-only aggregate team contract tests passed');
