'use strict';
const assert=require('node:assert/strict');
const client=require('./auth_login_client.js');

const calls=[];
const success=async(url,options)=>{
  calls.push({url,options});
  let body;
  if(url.endsWith('/google-challenge'))
    body={challenge_id:'b'.repeat(43),nonce:'c'.repeat(43),
      expires_at:400,publishing_enabled:false};
  else if(url.endsWith('/logout-everywhere'))
    body={signed_out:true,sessions_revoked:2,publishing_enabled:false};
  else if(url.endsWith('/logout'))
    body={signed_out:true,publishing_enabled:false};
  else body={session_token:'a'.repeat(43),publishing_enabled:false};
  return {ok:true,json:async()=>body};
};
async function main(){
  const session=await client.passwordLogin({origin:'https://bam.example',
    fetchImpl:success,email:'owner@example.com',
    password:'correct horse battery staple',tenantId:'shop'});
  assert.deepEqual(session,{sessionToken:'a'.repeat(43),
    tenantId:'shop',publishingEnabled:false});
  const call=calls[0];
  assert.equal(call.url,'https://bam.example/api/v1/auth/password');
  assert.equal(call.options.method,'POST');
  assert.equal(call.options.mode,'same-origin');
  assert.equal(call.options.credentials,'omit');
  assert.equal(call.options.cache,'no-store');
  assert.equal(call.options.redirect,'error');
  assert.deepEqual(JSON.parse(call.options.body),{
    email:'owner@example.com',password:'correct horse battery staple',
    tenant_id:'shop'});
  assert.equal(call.options.headers.Authorization,undefined);
  const challenge=await client.beginGoogle({origin:'https://bam.example',
    fetchImpl:success});
  assert.equal(challenge.nonce,'c'.repeat(43));
  assert.equal(challenge.challengeId,'b'.repeat(43));
  assert.equal(calls[1].options.body,'{}');
  const google=await client.googleLogin({origin:'https://bam.example',
    fetchImpl:success,challengeId:challenge.challengeId,idToken:'verified-jwt',
    tenantId:'shop'});
  assert.equal(google.sessionToken,'a'.repeat(43));
  assert.equal(JSON.parse(calls[2].options.body).tenant_id,'shop');
  const signedOut=await client.logout({origin:'https://bam.example',
    fetchImpl:success,sessionToken:'a'.repeat(43)});
  assert.deepEqual(signedOut,{signedOut:true});
  assert.equal(calls[3].options.headers.Authorization,'Bearer '+'a'.repeat(43));
  assert.equal(calls[3].options.body,'{}');
  const globally=await client.logout({origin:'https://bam.example',
    fetchImpl:success,sessionToken:'a'.repeat(43),everywhere:true});
  assert.deepEqual(globally,{signedOut:true,sessionsRevoked:2});
  assert.equal(calls[4].url,'https://bam.example/api/v1/auth/logout-everywhere');
  await assert.rejects(()=>client.logout({origin:'https://bam.example',
    fetchImpl:success,sessionToken:'invalid'}),TypeError);
  await assert.rejects(()=>client.logout({origin:'https://bam.example',
    fetchImpl:async()=>({ok:true,json:async()=>({signed_out:true,
      publishing_enabled:false,session_token:'leaked'})}),
    sessionToken:'a'.repeat(43)}),TypeError);
  await assert.rejects(()=>client.passwordLogin({
    origin:'http://bam.example',fetchImpl:success,email:'x@a.com',
    password:'correct horse battery staple',tenantId:'shop'}),TypeError);
  await assert.rejects(()=>client.passwordLogin({
    origin:'https://bam.example.evil/path',fetchImpl:success,
    email:'x@a.com',password:'correct horse battery staple',
    tenantId:'shop'}),TypeError);
  await assert.rejects(()=>client.passwordLogin({
    origin:'https://bam.example',fetchImpl:success,
    email:'x@a.com',password:'',tenantId:'shop'}),TypeError);
  await assert.rejects(()=>client.googleLogin({
    origin:'https://bam.example',fetchImpl:success,
    challengeId:'',idToken:'verified-jwt',tenantId:'shop'}),TypeError);
  await assert.rejects(()=>client.beginGoogle({
    origin:'https://bam.example',
    fetchImpl:async()=>({ok:true,json:async()=>({
      challenge_id:'x',nonce:'y',expires_at:0,
      publishing_enabled:true})})}),TypeError);
  await assert.rejects(()=>client.passwordLogin({
    origin:'https://bam.example',fetchImpl:async()=>({
      ok:true,json:async()=>({session_token:'a'.repeat(43),
        publishing_enabled:false,role:'owner'})}),
    email:'owner@example.com',password:'correct horse battery staple',
    tenantId:'shop'}),TypeError);
  await assert.rejects(()=>client.passwordLogin({
    origin:'https://bam.example',fetchImpl:async()=>({ok:false}),
    email:'owner@example.com',password:'correct horse battery staple',
    tenantId:'shop'}),/unavailable/);
  assert.equal(calls.length,5);
  console.log('BAM authenticated sign-in client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
