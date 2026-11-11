'use strict';
const assert=require('node:assert/strict');
const {create}=require('./authenticated_session_controller.js');

function environment({badDashboard=false,failedLogin=false}={}){
  const requests=[],events=[],errors=[];
  let refreshFailure=badDashboard;
  const workspace={
    activate:({token,tenantId})=>events.push(['activate',token,tenantId]),
    clear:()=>events.push(['clear']),
    refresh:async()=>refreshFailure
      ?{stale:false,error:true}
      :{stale:false,tenantId:'shop',draftCount:2}
  };
  const fetchImpl=async(url,opts)=>{
    requests.push({url,opts});
    if(url.endsWith('/password')||url.endsWith('/google'))
      return failedLogin?{ok:false}:{
        ok:true,json:async()=>({
          session_token:'a'.repeat(43),publishing_enabled:false})};
    if(url.endsWith('/google-challenge'))
      return {ok:true,json:async()=>({
        challenge_id:'b'.repeat(43),nonce:'c'.repeat(43),expires_at:400,
        publishing_enabled:false})};
    if(url.endsWith('/logout')||url.endsWith('/logout-everywhere'))
      return {ok:true,json:async()=>({
        signed_out:true,publishing_enabled:false,
        ...(url.endsWith('/logout-everywhere')?{sessions_revoked:3}:{})})};
    throw new Error('Unexpected route '+url);
  };
  const c=create({origin:'https://bam.example',fetchImpl,workspace,
    onError:message=>errors.push(message)});
  return {c,requests,events,errors,setRefreshFailure:x=>refreshFailure=x};
}
async function main(){
  const a=environment();
  assert.equal(a.c.activeTenant(),null);
  assert.equal(a.c.clear,undefined);
  const signed=await a.c.passwordSignIn({
    email:'owner@example.com',password:'correct horse battery staple',
    tenantId:'shop'});
  assert.deepEqual(signed,{status:'ready',tenantId:'shop',
    draftCount:2,publishingEnabled:false});
  assert.equal(a.c.activeTenant(),'shop');
  assert.equal(a.events.filter(x=>x[0]==='activate').length,1);
  assert.equal(a.events.filter(x=>x[0]==='activate')[0][1],'a'.repeat(43));
  await assert.rejects(()=>a.c.passwordSignIn({
    email:'owner@example.com',password:'correct horse battery staple',
    tenantId:'other'}),TypeError);
  assert.deepEqual(await a.c.refresh(),{
    stale:false,tenantId:'shop',draftCount:2});
  const before=a.events.length;
  const out=await a.c.signOut({everywhere:true});
  assert.deepEqual(out,{localCleared:true,serverRevoked:true,
    sessionsRevoked:3});
  assert.equal(a.c.activeTenant(),null);
  assert.equal(a.events[before][0],'clear');
  assert.equal(a.requests.at(-1).opts.headers.Authorization,
    'Bearer '+'a'.repeat(43));
  await assert.rejects(()=>a.c.refresh(),TypeError);

  const b=environment({failedLogin:true});
  const denied=await b.c.passwordSignIn({
    email:'owner@example.com',password:'bad password passphrase',
    tenantId:'shop'});
  assert.equal(denied.status,'error');
  assert.equal(b.c.activeTenant(),null);
  assert.equal(b.events.some(x=>x[0]==='activate'),false);
  assert.equal(b.errors.length,1);

  const g=environment();
  const challenge=await g.c.beginGoogle();
  assert.equal(challenge.nonce,'c'.repeat(43));
  const google=await g.c.googleSignIn({
    challengeId:challenge.challengeId,idToken:'server-verifies-this',
    tenantId:'shop'});
  assert.equal(google.status,'ready');
  await g.c.signOut();

  const broken=environment({badDashboard:true});
  const result=await broken.c.passwordSignIn({
    email:'owner@example.com',password:'correct horse battery staple',
    tenantId:'shop'});
  assert.equal(result.status,'error');
  assert.equal(broken.c.activeTenant(),null);
  assert.equal(broken.requests.at(-1).url.endsWith('/logout'),true);
  assert.equal(broken.errors.at(-1),'Sign-in could not complete');

  // A sign-out during a pending login must discard and revoke the late session.
  const events=[],requests=[];
  let releaseLogin;
  const pendingFetch=(url,opts)=>{
    requests.push({url,opts});
    if(url.endsWith('/password'))
      return new Promise(resolve=>{releaseLogin=resolve});
    if(url.endsWith('/logout'))
      return Promise.resolve({ok:true,json:async()=>({
        signed_out:true,publishing_enabled:false})});
    throw new Error('Unexpected request '+url);
  };
  const delayed=create({origin:'https://bam.example',
    fetchImpl:pendingFetch,workspace:{
      activate:()=>events.push('activated'),
      refresh:async()=>({tenantId:'shop'}),
      clear:()=>events.push('cleared')}});
  const pending=delayed.passwordSignIn({email:'owner@example.com',
    password:'correct horse battery staple',tenantId:'shop'});
  assert.equal(typeof releaseLogin,'function');
  assert.equal((await delayed.signOut()).localCleared,true);
  releaseLogin({ok:true,json:async()=>({
    session_token:'z'.repeat(43),publishing_enabled:false})});
  assert.deepEqual(await pending,{stale:true});
  assert.equal(delayed.activeTenant(),null);
  assert.equal(events.includes('activated'),false);
  assert.equal(requests.at(-1).url.endsWith('/logout'),true);

  console.log('BAM authenticated session workspace lifecycle tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
