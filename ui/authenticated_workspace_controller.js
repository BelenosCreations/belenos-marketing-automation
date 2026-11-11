/* BAM signed-in workspace coordinator, independent of authentication provider.
 * The login service supplies a session token and active business.
 * No token persistence, demo data, background polling or publishing.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./live_dashboard_cards.js'),
      require('./ai_workspace.js'),require('./held_draft_workspace.js'));
  else root.BAMAuthenticatedWorkspace=factory(
    root.BAMLiveDashboard,root.BAMAIWorkspace,root.BAMHeldDraftWorkspace);
})(typeof globalThis!=='undefined'?globalThis:this,
function(dashboardModule,aiModule,heldModule){
  'use strict';
  function create({document,dashboardContainer,aiDraftsContainer,
                   aiSettingsContainer,aiFactsContainer,aiCostContainer,
                   fetchImpl,origin,onError,copyText,openUrl,
                   aiFactsEditorContainer,canManageFacts=false,onSaveFacts,
                   contentStudioContainer}){
    const dashboard=dashboardModule.create({
      document,container:dashboardContainer,fetchImpl,origin,onError});
    const ai=aiModule.create({document,draftsContainer:aiDraftsContainer,
      settingsContainer:aiSettingsContainer,factsContainer:aiFactsContainer,
      costContainer:aiCostContainer,fetchImpl,origin,onError,
      copyText,openUrl,factsEditorContainer:aiFactsEditorContainer,
      canManageFacts,onSaveFacts});
    const held=contentStudioContainer?heldModule.create({document,
      container:contentStudioContainer,fetchImpl,origin,onError}):null;
    let active=false,epoch=0;
    function clear(){
      epoch++;active=false;dashboard.clear();ai.clear();if(held)held.clear();
    }
    function activate({token,tenantId}){
      clear();
      dashboard.activate({token,tenantId});
      ai.activate({token,tenantId});
      if(held)held.activate({token,tenantId});
      active=true;
    }
    async function refresh(){
      if(!active)throw new TypeError('Sign-in required');
      const version=epoch;
      // Sequential loading avoids showing AI content under a stale dashboard.
      const overview=await dashboard.refresh();
      if(version!==epoch)return {stale:true};
      if(overview.error){
        clear();
        return {stale:false,error:true};
      }
      if(overview.stale)return {stale:true};
      const details=await ai.refresh();
      if(version!==epoch)return {stale:true};
      if(details.error){
        clear();
        return {stale:false,error:true};
      }
      if(details.stale)return {stale:true};
      if(held){
        const content=await held.refresh();
        if(version!==epoch)return {stale:true};
        if(content.error){clear();return {stale:false,error:true};}
        if(content.stale)return {stale:true};
      }
      return {stale:false,tenantId:overview.tenantId,
        draftCount:details.draftCount,businesses:overview.businesses};
    }
    return Object.freeze({activate,refresh,clear,
      showDashboardSection:dashboard.show});
  }
  return Object.freeze({create});
});
