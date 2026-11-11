/* Authenticated AI workspace controller for BAM.
 * Explicitly read-only; never persists bearer tokens in browser storage.
 * Every async response is invalidated on account/business switch or logout.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./dashboard_http_client.js'),
      require('./ai_draft_view.js'),require('./ai_settings_view.js'));
  else root.BAMAIWorkspace=factory(root.BAMReadClient,
    root.BAMAIDraftView,root.BAMAISettingsView);
})(typeof globalThis!=='undefined'?globalThis:this,
function(client,draftView,settingsView){
  'use strict';
  function create({document,draftsContainer,settingsContainer,
                   fetchImpl,origin,onError}){
    if(!document||!draftsContainer||!settingsContainer||
       typeof fetchImpl!=='function'||typeof origin!=='string')
      throw new TypeError('Workspace dependencies required');
    if(onError!==undefined&&typeof onError!=='function')
      throw new TypeError('Invalid error callback');
    let active=null,epoch=0,requestVersion=0;
    function clear(){
      epoch+=1;
      requestVersion+=1;
      active=null;
      draftsContainer.replaceChildren();
      settingsContainer.replaceChildren();
    }
    function activate({token,tenantId}){
      if(typeof token!=='string'||!token.trim()||token.length>2048||
         typeof tenantId!=='string'||!tenantId.trim()||tenantId.length>128)
        throw new TypeError('Authenticated identity required');
      clear();
      active={token,tenantId};
    }
    async function refresh(){
      if(!active)throw new TypeError('Sign-in required');
      const mine=active,version=epoch,request=++requestVersion;
      try{
        // Fetch both before rendering either to avoid partial stale UI.
        const [drafts,settings]=await Promise.all([
          client.read({kind:'aiDrafts',token:mine.token,fetchImpl,origin,
                       expectedTenantId:mine.tenantId}),
          client.read({kind:'aiSettings',token:mine.token,fetchImpl,origin,
                       expectedTenantId:mine.tenantId})
        ]);
        if(version!==epoch||request!==requestVersion||active!==mine)return {stale:true};
        // Renderers validate all data before replacing the current mount.
        draftView.render({document,container:draftsContainer,
          payload:{tenant_id:drafts.tenantId,publishing_enabled:false,
            drafts:drafts.drafts.map(d=>({
              tenant_id:drafts.tenantId,draft_id:d.id,platform:d.platform,
              post_text:d.postText,image_prompt:d.imagePrompt,
              needs_media:d.needsMedia,media_attached:d.mediaAttached,
              status:d.status,revision:d.revision,publishing_enabled:false
            }))},expectedTenantId:mine.tenantId});
        settingsView.render({document,container:settingsContainer,
          payload:{tenant_id:settings.tenantId,provider:'openai',
            mode:settings.mode,own_key_configured:settings.ownKeyConfigured,
            memory:settings.memory,key_exposed:false,
            publishing_enabled:false},expectedTenantId:mine.tenantId});
        return {stale:false,tenantId:mine.tenantId,
                draftCount:drafts.drafts.length};
      }catch(error){
        if(version!==epoch||active!==mine)return {stale:true};
        // Fail closed: never leave stale private content visible on errors.
        draftsContainer.replaceChildren();
        settingsContainer.replaceChildren();
        // Do not expose private server error details to the user.
        if(onError)onError('Unable to load AI workspace');
        return {stale:false,error:true};
      }
    }
    return Object.freeze({activate,refresh,clear});
  }
  return Object.freeze({create});
});
