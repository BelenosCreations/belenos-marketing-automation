/* Authenticated AI workspace controller for BAM.
 * Explicitly read-only; never persists bearer tokens in browser storage.
 * Every async response is invalidated on account/business switch or logout.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./dashboard_http_client.js'),
      require('./ai_draft_view.js'),require('./ai_settings_view.js'),
      require('./ai_facts_view.js'),require('./ai_cost_view.js'));
  else root.BAMAIWorkspace=factory(root.BAMReadClient,
    root.BAMAIDraftView,root.BAMAISettingsView,root.BAMAIFactsView,
    root.BAMAICostView);
})(typeof globalThis!=='undefined'?globalThis:this,
function(client,draftView,settingsView,factsView,costView){
  'use strict';
  function create({document,draftsContainer,settingsContainer,
                   factsContainer,costContainer,fetchImpl,origin,onError,
                   copyText,openUrl}){
    if(!document||!draftsContainer||!settingsContainer||
       typeof fetchImpl!=='function'||typeof origin!=='string')
      throw new TypeError('Workspace dependencies required');
    if(factsContainer!==undefined&&
       (!factsContainer||typeof factsContainer.replaceChildren!=='function'))
      throw new TypeError('Invalid facts mount');
    if(costContainer!==undefined&&
       (!costContainer||typeof costContainer.replaceChildren!=='function'))
      throw new TypeError('Invalid AI cost mount');
    if((copyText!==undefined||openUrl!==undefined)&&
       (typeof copyText!=='function'||typeof openUrl!=='function'))
      throw new TypeError('Manual image handoff requires both callbacks');
    if(onError!==undefined&&typeof onError!=='function')
      throw new TypeError('Invalid error callback');
    let active=null,epoch=0,requestVersion=0;
    function clear(){
      epoch+=1;
      requestVersion+=1;
      active=null;
      draftsContainer.replaceChildren();
      settingsContainer.replaceChildren();
      if(factsContainer)factsContainer.replaceChildren();
      if(costContainer)costContainer.replaceChildren();
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
        const [drafts,settings,facts,costs]=await Promise.all([
          client.read({kind:'aiDrafts',token:mine.token,fetchImpl,origin,
                       expectedTenantId:mine.tenantId}),
          client.read({kind:'aiSettings',token:mine.token,fetchImpl,origin,
                       expectedTenantId:mine.tenantId}),
          factsContainer?client.read({kind:'aiFacts',token:mine.token,
            fetchImpl,origin,expectedTenantId:mine.tenantId}):Promise.resolve(null),
          costContainer?client.read({kind:'aiCosts',token:mine.token,
            fetchImpl,origin,expectedTenantId:mine.tenantId}):Promise.resolve(null)
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
            }))},expectedTenantId:mine.tenantId,copyText,openUrl});
        settingsView.render({document,container:settingsContainer,
          payload:{tenant_id:settings.tenantId,provider:'openai',
            mode:settings.mode,own_key_configured:settings.ownKeyConfigured,
            memory:settings.memory,key_exposed:false,
            publishing_enabled:false},expectedTenantId:mine.tenantId});
        if(factsContainer)factsView.render({document,container:factsContainer,
          payload:{tenant_id:facts.tenantId,facts:facts.facts,
            revision:facts.revision,provenance:facts.provenance,
            confirmed_at:facts.confirmedAt,publishing_enabled:false},
          expectedTenantId:mine.tenantId});
        if(costContainer)costView.render({document,container:costContainer,
          payload:{tenant_id:costs.tenantId,events:costs.events,
            input_tokens:costs.inputTokens,output_tokens:costs.outputTokens,
            estimated_micro_usd:costs.estimatedMicroUsd,
            pricing_basis:'operator_configured',
            actual_billing_verified:false,publishing_enabled:false},
          expectedTenantId:mine.tenantId});
        return {stale:false,tenantId:mine.tenantId,
                draftCount:drafts.drafts.length};
      }catch(error){
        if(version!==epoch||request!==requestVersion||active!==mine)
          return {stale:true};
        // Fail closed: never leave stale private content visible on errors.
        draftsContainer.replaceChildren();
        settingsContainer.replaceChildren();
        if(factsContainer)factsContainer.replaceChildren();
        if(costContainer)costContainer.replaceChildren();
        // Do not expose private server error details to the user.
        if(onError)onError('Unable to load AI workspace');
        return {stale:false,error:true};
      }
    }
    return Object.freeze({activate,refresh,clear});
  }
  return Object.freeze({create});
});
