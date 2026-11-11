'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./posting_preferences_contract.js');
const unconfigured={tenant_id:'shop',mode:'smart',timezone:null,
  manual_times:[],configured:false,publishing_enabled:false};
assert.equal(normalize(unconfigured).timezone,null);
const manual={tenant_id:'shop',mode:'manual',timezone:'America/New_York',
  manual_times:['10:00','18:30'],configured:true,publishing_enabled:false};
assert.equal(normalize(manual).manualTimes.length,2);
for(const patch of [
  {publishing_enabled:true},{mode:'published'},
  {timezone:null},{manual_times:[]},{manual_times:['24:00']},
  {manual_times:['10:00','10:00']},{manual_times:['¹0:00']}
]){
  assert.throws(()=>normalize({...manual,...patch}),TypeError);
}
assert.throws(()=>normalize({...unconfigured,timezone:'America/New_York'}),TypeError);
assert.throws(()=>normalize({...manual,mode:'smart'}),TypeError);
console.log('BAM posting preference contract tests passed');
