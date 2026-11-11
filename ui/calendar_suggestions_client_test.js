'use strict';
const assert=require('node:assert/strict');
const {suggest}=require('./calendar_proposals_client.js');
const rid='a'.repeat(32);
const utc='2026-11-11T15:00:00+00:00';
const options={origin:'https://bam.example',token:'t'.repeat(43),
  expectedTenantId:'shop'};
const response={tenant_id:'shop',status:'suggestion_preview_only',
  preference_status:'manual_preview',unassigned_held_count:1,
  available_slot_count:2,posts_scheduled:0,publishing_enabled:false,
  items:[{request_id:rid,draft_revision:3,utc_at:utc,
    local_date:'2026-11-11',local_time:'10:00',
    timezone:'America/New_York',publishing_enabled:false}]};
const calls=[];
const transport=data=>async(url,opts)=>{
  calls.push({url,opts});
  return {ok:true,status:200,json:async()=>data};
};
async function main(){
 const result=await suggest({...options,fetchImpl:transport(response)});
 assert.equal(result.items[0].requestId,rid);
 assert.equal(result.items[0].draftRevision,3);
 assert.equal(result.postsScheduled,0);
 assert.ok(Object.isFrozen(result.items));
 assert.ok(calls[0].url.endsWith('/api/v1/calendar-suggestions'));
 assert.equal(calls[0].opts.method,'GET');
 assert.equal(calls[0].opts.credentials,'omit');
 assert.equal(calls[0].opts.body,undefined);
 const variants=[
   {...response,tenant_id:'other'},
   {...response,status:'scheduled'},
   {...response,posts_scheduled:1},
   {...response,items:[{...response.items[0],approved:true}]},
   {...response,items:[...response.items,...response.items]},
   {...response,preference_status:'needs_audience_data'},
   {...response,available_slot_count:0},
   {...response,unassigned_held_count:0},
   {...response,publishing_enabled:true}
 ];
 for(const body of variants)
   await assert.rejects(
     ()=>suggest({...options,fetchImpl:transport(body)}),TypeError);
 for(const altered of [{origin:'http://bam.example'},
                        {token:'bad'},{expectedTenantId:''}])
   await assert.rejects(
     ()=>suggest({...options,...altered,
                  fetchImpl:transport(response)}),TypeError);
 console.log('BAM strict read-only calendar suggestion client tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
