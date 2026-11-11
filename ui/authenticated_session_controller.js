/* BAM authenticated shell coordinator for a future real sign-in screen.
 * A trusted HTTPS service supplies BAM sessions. All tokens stay in memory.
 * Workspace data is cleared before sign-out, failed login, or tenant change.
 * No Google button/OAuth popup, device storage, auto-posting or analytics polling.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./auth_login_client.js'),
      require('./business_switch_client.js'));
  else root.BAMSessionController=factory(root.BAMAuthClient,
    root.BAMBusinessSwitchClient);
})(typeof globalThis!=='undefined'?globalThis:this,function(client,switchClient){
  'use strict';
  function create({origin,fetchImpl,workspace,onError}){
    if(typeof origin!=='string'||typeof fetchImpl!=='function'||
       !workspace||typeof workspace.activate!=='function'||
       typeof workspace.refresh!=='function'||
       typeof workspace.clear!=='function'||
       (onError!==undefined&&typeof onError!=='function'))
      throw new TypeError('Authenticated workspace required');
    let active=null,epoch=0,signingIn=false,pendingSwitch=null;
    function clear(){
      epoch++;
      const prior=active||pendingSwitch;
      active=null;pendingSwitch=null;
      workspace.clear();
      return prior;
    }
    async function revokeDetached(session,everywhere=false){
      if(!session)return {signedOut:true};
      try{
        return await client.logout({origin,fetchImpl,
          sessionToken:session.sessionToken,everywhere});
      }catch(error){
        if(onError)onError('Server session could not be revoked; it may remain valid until expiry');
        return {signedOut:false};
      }
    }
    async function complete(login){
      if(active||signingIn||pendingSwitch)
        throw new TypeError('Sign out before signing in again');
      signingIn=true;
      const version=++epoch;
      let session=null;
      try{
        session=await login();
        if(version!==epoch){
          await revokeDetached(session);
          return {stale:true};
        }
        active=session;
        workspace.activate({token:session.sessionToken,tenantId:session.tenantId});
        const loaded=await workspace.refresh();
        if(version!==epoch||active!==session)return {stale:true};
        if(!loaded||loaded.error||loaded.stale||
           loaded.tenantId!==session.tenantId)
          throw new Error('Authenticated workspace unavailable');
        return Object.freeze({status:'ready',tenantId:session.tenantId,
          draftCount:loaded.draftCount,
          businesses:Array.isArray(loaded.businesses)?loaded.businesses:[],
          publishingEnabled:false});
      }catch(error){
        if(version!==epoch)return {stale:true};
        clear();
        await revokeDetached(session);
        if(onError)onError('Sign-in could not complete');
        return {status:'error',publishingEnabled:false};
      }finally{
        if(version===epoch||!active)signingIn=false;
      }
    }
    function passwordSignIn({email,password,tenantId}){
      return complete(()=>client.passwordLogin({
        origin,fetchImpl,email,password,tenantId}));
    }
    function googleSignIn({challengeId,idToken,tenantId}){
      return complete(()=>client.googleLogin({
        origin,fetchImpl,challengeId,idToken,tenantId}));
    }
    function beginGoogle(){
      if(active||signingIn||pendingSwitch)
        throw new TypeError('Sign out before Google sign-in');
      return client.beginGoogle({origin,fetchImpl});
    }
    async function signOut({everywhere=false}={}){
      if(typeof everywhere!=='boolean')
        throw new TypeError('Explicit sign-out scope required');
      const previous=clear();
      const result=await revokeDetached(previous,everywhere);
      return Object.freeze({localCleared:true,
        serverRevoked:result.signedOut===true,
        ...(Number.isSafeInteger(result.sessionsRevoked)
          ?{sessionsRevoked:result.sessionsRevoked}:{})});
    }
    async function refresh(){
      if(!active)throw new TypeError('BAM sign-in required');
      const mine=active,version=epoch;
      try{
        const result=await workspace.refresh();
        if(version!==epoch||active!==mine)return {stale:true};
        if(!result||result.error||result.stale||
           result.tenantId!==mine.tenantId)
          throw new Error('Workspace refresh failed');
        return {stale:false,tenantId:mine.tenantId,
          draftCount:result.draftCount,businesses:result.businesses};
      }catch(error){
        if(version!==epoch||active!==mine)return {stale:true};
        clear();
        await revokeDetached(mine);
        if(onError)onError('Authenticated workspace could not be refreshed');
        return {stale:false,error:true};
      }
    }
    async function switchBusiness({tenantId}){
      if(!active||signingIn||pendingSwitch)
        throw new TypeError('Active BAM session required');
      if(typeof tenantId!=='string'||!tenantId.trim()||
         tenantId===active.tenantId||tenantId.length>128)
        throw new TypeError('Different BAM business required');
      const previous=active,version=++epoch;
      active=null;pendingSwitch=previous;
      workspace.clear();
      let replacement=null;
      try{
        replacement=await switchClient.activate({origin,fetchImpl,
          sessionToken:previous.sessionToken,targetTenantId:tenantId});
        if(version!==epoch){
          await revokeDetached(replacement);
          return {stale:true};
        }
        pendingSwitch=null;active=replacement;
        workspace.activate({
          token:replacement.sessionToken,tenantId:replacement.tenantId});
        const loaded=await workspace.refresh();
        if(version!==epoch||active!==replacement)return {stale:true};
        if(!loaded||loaded.error||loaded.stale||
           loaded.tenantId!==tenantId)
          throw new Error('Switched BAM workspace unavailable');
        return Object.freeze({status:'ready',tenantId,
          draftCount:loaded.draftCount,
          businesses:Array.isArray(loaded.businesses)?loaded.businesses:[],
          publishingEnabled:false});
      }catch(error){
        if(version!==epoch)return {stale:true};
        clear();
        await revokeDetached(replacement||previous);
        if(onError)onError('Business switch unavailable; sign in again');
        return {status:'error',publishingEnabled:false};
      }
    }
    function activeTenant(){return active?active.tenantId:null;}
    return Object.freeze({passwordSignIn,beginGoogle,googleSignIn,
      signOut,refresh,switchBusiness,activeTenant});
  }
  return Object.freeze({create});
});
