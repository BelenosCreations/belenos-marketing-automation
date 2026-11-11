'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./posting_time_preview_contract.js');
const first={local_date:'2026-11-11',local_time:'10:00',
  utc_at:'2026-11-11T15:00:00+00:00'};
const second={local_date:'2026-11-11',local_time:'18:30',
  utc_at:'2026-11-11T23:30:00+00:00'};
const body={tenant_id:'shop',mode:'manual',timezone:'America/New_York',
  status:'manual_preview',slots:[first,second],skipped_dst:0,
  truncated:false,publishing_enabled:false};
const verified=normalize(body);
assert.equal(verified.slots[0].localTime,'10:00');
assert.equal(verified.publishingEnabled,false);
assert.equal(Object.isFrozen(verified.slots),true);
const smart={...body,mode:'smart',status:'needs_audience_data',slots:[]};
assert.equal(normalize(smart).slots.length,0);
assert.equal(normalize({...smart,timezone:null,status:'not_configured'}).status,
  'not_configured');
for(const bad of [
  {...body,tenant_id:'another',publishing_enabled:true},
  {...body,status:'scheduled'},
  {...body,mode:'smart'},
  {...body,slots:[second,first]},
  {...body,slots:[first,first]},
  {...body,slots:[{...first,local_time:'25:00'}]},
  {...body,slots:[{...first,utc_at:'2026-11-11T15:00:00Z'}]},
  {...body,slots:[{...first,verified:true}]},
  {...body,skipped_dst:-1},
  {...body,skipped_dst:true},
  {...body,truncated:'false'},
  {...body,scheduled_job_created:true},
  {...smart,slots:[first]},
  {...smart,status:'not_configured',timezone:'America/New_York'}
])assert.throws(()=>normalize(bad),TypeError);
console.log('BAM read-only posting-time preview contract tests passed');
