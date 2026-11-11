/* Browser login transport for BAM-owned identity (not social sign-in).
 * The authenticated shell owns the returned token in memory only.
 * No cookies, localStorage, retries, social access or publish operations.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMAuthClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const tokenPattern=/^[A-Za-z0-9_-]{32,2048}$/;
  function originOf(origin){
    if(typeof origin!=='string'||!/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin))
      throw new TypeError('HTTPS BAM origin required');
    const url=new URL(origin);
    if(url.protocol!=='https:'||url.username||url.password||
       url.pathname!=='/'||url.search||url.hash)
      throw new TypeError('Invalid BAM origin');
    return url.origin;
  }
  async function request({origin,fetchImpl,path,body,sessionToken}){
    const url=originOf(origin);
    if(typeof fetchImpl!=='function')throw new TypeError('Fetch required');
    const headers={'Content-Type':'application/json','Accept':'application/json'};
    if(sessionToken!==undefined){
      if(typeof sessionToken!=='string'||!tokenPattern.test(sessionToken))
        throw new TypeError('Verified BAM session required');
      headers.Authorization='Bearer '+sessionToken;
    }
    const response=await fetchImpl(url+path,{
      method:'POST',mode:'same-origin',credentials:'omit',redirect:'error',
      cache:'no-store',headers,body:JSON.stringify(body)
    });
    if(!response||!response.ok)
      throw new Error('BAM sign-in unavailable');
    const result=await response.json();
    if(!result||typeof result!=='object'||Array.isArray(result)||
       result.publishing_enabled!==false)
      throw new TypeError('Invalid authentication response');
    return result;
  }
  function session(result,tenantId){
    if(!tokenPattern.test(result.session_token||'')||
       Object.keys(result).some(key=>
         !['session_token','publishing_enabled'].includes(key)))
      throw new TypeError('Invalid BAM session response');
    return Object.freeze({sessionToken:result.session_token,tenantId,
      publishingEnabled:false});
  }
  function validText(value,max){
    return typeof value==='string'&&!!value.trim()&&value.length<=max;
  }
  async function passwordLogin({origin,fetchImpl,email,password,tenantId}){
    if(!validText(email,254)||!validText(password,1024)||
       !validText(tenantId,128))
      throw new TypeError('Account credentials and business required');
    return session(await request({origin,fetchImpl,
      path:'/api/v1/auth/password',body:{email,password,tenant_id:tenantId}}),
      tenantId);
  }
  async function beginGoogle({origin,fetchImpl}){
    const result=await request({origin,fetchImpl,
      path:'/api/v1/auth/google-challenge',body:{}});
    if(!validText(result.challenge_id,256)||!validText(result.nonce,256)||
       !Number.isSafeInteger(result.expires_at)||result.expires_at<=0||
       Object.keys(result).some(key=>![
         'challenge_id','nonce','expires_at','publishing_enabled'].includes(key)))
      throw new TypeError('Invalid Google challenge response');
    return Object.freeze({challengeId:result.challenge_id,
      nonce:result.nonce,expiresAt:result.expires_at});
  }
  async function googleLogin({origin,fetchImpl,challengeId,idToken,tenantId}){
    if(!validText(challengeId,256)||!validText(idToken,4096)||
       !validText(tenantId,128))
      throw new TypeError('Verified Google challenge and business required');
    return session(await request({origin,fetchImpl,
      path:'/api/v1/auth/google',
      body:{challenge_id:challengeId,id_token:idToken,
        tenant_id:tenantId}}),tenantId);
  }
  async function logout({origin,fetchImpl,sessionToken,everywhere=false}){
    if(typeof everywhere!=='boolean')throw new TypeError('Explicit sign-out scope required');
    const result=await request({origin,fetchImpl,sessionToken,
      path:everywhere?'/api/v1/auth/logout-everywhere':'/api/v1/auth/logout',
      body:{}});
    const allowed=everywhere?['signed_out','sessions_revoked','publishing_enabled']:
      ['signed_out','publishing_enabled'];
    if(result.signed_out!==true||Object.keys(result).some(k=>!allowed.includes(k))||
       (everywhere&&(!Number.isSafeInteger(result.sessions_revoked)||
         result.sessions_revoked<0)))
      throw new TypeError('Invalid BAM sign-out response');
    return Object.freeze({signedOut:true,
      ...(everywhere?{sessionsRevoked:result.sessions_revoked}:{})});
  }
  return Object.freeze({passwordLogin,beginGoogle,googleLogin,logout});
});
