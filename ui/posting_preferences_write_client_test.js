'use strict';
const assert=require('node:assert/strict');
const {save}=require('./posting_preferences_write_client.js');
const calls=[];
const base={origin:'https://bam.example',token:'a'.repeat(43),
  expectedTenantId:'shop',mode:'manual',timezone:'America/New_York',
  manualTimes:['10:00','18:30']};
const fetchImpl=async(url,opts)=>{
  calls.push({url,opts});
  const submitted=JSON.parse(opts.body);
  return {ok:true,json:async()=>({tenant_id:'shop',mode:submitted.mode,
    timezone:submitted.timezone,manual_times:submitted.manual_times,
    configured:true,publishing_enabled:false})};
};
async function main(){
  const result=await save({...base,fetchImpl});
  assert.equal(result.mode,'manual');
  assert.equal(result.publishingEnabled,false);
  assert.equal(calls[0].url,'https://bam.example/api/v1/posting-preferences');
  assert.equal(calls[0].opts.method,'PUT');
  assert.equal(calls[0].opts.credentials,'omit');
  assert.equal(calls[0].opts.mode,'same-origin');
  assert.equal(calls[0].opts.redirect,'error');
  assert.deepEqual(JSON.parse(calls[0].opts.body),{
    mode:'manual',timezone:'America/New_York',
    manual_times:['10:00','18:30']});
  assert.equal(calls[0].opts.headers.Authorization,'Bearer '+'a'.repeat(43));
  for(const overrides of [
    {origin:'http://bam.example'},{mode:'smart'},
    {mode:'manual',manualTimes:[]},
    {mode:'manual',manualTimes:['10:00','10:00']},
    {mode:'manual',manualTimes:['24:00']},
    {timezone:' '},{timezone:'America/New_York '},
    {mode:'manual',manualTimes:[10]}]){
    assert.throws(()=>save({...base,fetchImpl,...overrides}),TypeError);
  }
  assert.equal(calls.length,1);
  await assert.rejects(()=>save({...base,
    fetchImpl:async()=>({ok:true,json:async()=>({
      tenant_id:'other',mode:'manual',timezone:'America/New_York',
      manual_times:['10:00','18:30'],configured:true,
      publishing_enabled:false})})}),TypeError);
  await assert.rejects(()=>save({...base,
    fetchImpl:async()=>({ok:true,json:async()=>({
      tenant_id:'shop',mode:'manual',timezone:'America/New_York',
      manual_times:['10:00','18:30'],configured:true,
      publishing_enabled:true})})}),TypeError);
  console.log('BAM posting preferences write client tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
