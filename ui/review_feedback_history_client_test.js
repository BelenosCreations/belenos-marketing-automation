'use strict';
const assert=require('node:assert/strict');
const {read}=require('./review_feedback_history_client.js');
const base={origin:'https://bam.example',token:'t'.repeat(43),
 expectedTenantId:'shop'};
const sample={tenant_id:'shop',status:'feedback_history_only',
 approval_granted:false,publishing_enabled:false,
 truncated:false,events:[{
   event_id:'a'.repeat(32),request_id:'b'.repeat(32),
   action:'created',draft_revision:1,occurred_at:200},{
   event_id:'c'.repeat(32),request_id:'b'.repeat(32),
   action:'updated',draft_revision:2,occurred_at:199}]};
const calls=[];
const impl=body=>async(url,opts)=>{
 calls.push({url,opts});
 return {ok:true,status:200,json:async()=>body};
};
async function main(){
 const result=await read({...base,fetchImpl:impl(sample)});
 assert.equal(result.events.length,2);
 assert.equal(result.events[0].action,'created');
 assert.ok(Object.isFrozen(result.events));
 assert.equal(calls[0].opts.method,'GET');
 assert.equal(calls[0].opts.credentials,'omit');
 assert.equal(calls[0].opts.body,undefined);
 assert.ok(calls[0].url.endsWith('/review-feedback-history'));
 for(const variant of [
   {...sample,tenant_id:'another'},
   {...sample,status:'approved'},
   {...sample,approval_granted:true},
   {...sample,publishing_enabled:true},
   {...sample,truncated:true},
   {...sample,events:[...sample.events,...sample.events]},
   {...sample,events:[{...sample.events[0],note:'Secret'}]},
   {...sample,events:[{...sample.events[0],action:'approved'}]},
   {...sample,events:[sample.events[1],sample.events[0]]},
   {...sample,events:[{...sample.events[0],occurred_at:true}]}
 ])await assert.rejects(()=>read({...base,fetchImpl:impl(variant)}),TypeError);
 for(const changes of [
  {origin:'http://bam.example'},{token:'bad'},
  {expectedTenantId:''}
 ])await assert.rejects(()=>read({...base,...changes,
    fetchImpl:impl(sample)}),TypeError);
 console.log('BAM owner-private redacted reviewer event history tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
