/* BAM signed-in workspace coordinator, independent of authentication provider.
 * The login service supplies a session token and active business.
 * No token persistence, demo data, background polling or publishing.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./live_dashboard_cards.js'),
      require('./ai_workspace.js'),require('./held_draft_workspace.js'),
      require('./posting_preferences_workspace.js'),
      require('./ai_write_client.js'),require('./team_overview_workspace.js'));
  else root.BAMAuthenticatedWorkspace=factory(
    root.BAMLiveDashboard,root.BAMAIWorkspace,root.BAMHeldDraftWorkspace,
    root.BAMPostingPreferencesWorkspace,root.BAMAIWriteClient,
    root.BAMTeamOverviewWorkspace);
})(typeof globalThis!=='undefined'?globalThis:this,
function(dashboardModule,aiModule,heldModule,prefsModule,aiWriter,teamModule){
  'use strict';
  function create({document,dashboardContainer,aiDraftsContainer,
                   aiSettingsContainer,aiFactsContainer,aiCostContainer,
                   fetchImpl,origin,onError,copyText,openUrl,
                   aiFactsEditorContainer,canManageFacts=false,onSaveFacts,
                   contentStudioContainer,onOpenContentStudio,onOpenPostingSettings,
                   postingPreferencesContainer,teamOverviewContainer,
                   enableLocalTemplates=false,enableBatchPreviews=false,
                   enableCalendarProposals=false,
                   hashMediaBytes,onNotice}){
    let activeSession=null,epoch=0,active=false;
    const dashboard=dashboardModule.create({
      document,container:dashboardContainer,fetchImpl,origin,onError,
      onOpenContentStudio,onOpenPostingSettings,
      enableCalendarProposals});
    async function saveConfirmedFacts({facts,expectedRevision,expectedTenantId}){
      const mine=activeSession,version=epoch;
      if(!mine||expectedTenantId!==mine.tenantId){
        if(onError)onError('Sign in to the correct business to save facts');
        return {error:true};
      }
      try{
        const saved=await aiWriter.confirmFacts({
          origin,fetchImpl,token:mine.token,
          expectedTenantId:mine.tenantId,facts,expectedRevision});
        if(version!==epoch||activeSession!==mine)return {stale:true};
        const latest=await ai.refresh();
        if(version!==epoch||activeSession!==mine)return {stale:true};
        if(latest.error){clear();return {error:true};}
        return saved;
      }catch(error){
        if(version===epoch&&activeSession===mine&&onError)
          onError('Business facts could not be saved. Owner access, current revision and confirmed details are required.');
        return {error:true};
      }
    }
    const ai=aiModule.create({document,draftsContainer:aiDraftsContainer,
      settingsContainer:aiSettingsContainer,factsContainer:aiFactsContainer,
      costContainer:aiCostContainer,fetchImpl,origin,onError,
      copyText,openUrl,factsEditorContainer:aiFactsEditorContainer,
      canManageFacts:false,
      onSaveFacts:onSaveFacts||saveConfirmedFacts,
      enableLocalTemplates,enableBatchPreviews});
    const held=contentStudioContainer?heldModule.create({document,
      container:contentStudioContainer,fetchImpl,origin,onError,
      hashBytes:hashMediaBytes,onNotice,
      enableCalendarProposals}):null;
    const prefs=postingPreferencesContainer?prefsModule.create({document,
      container:postingPreferencesContainer,fetchImpl,origin,onError}):null;
    const team=teamOverviewContainer?teamModule.create({document,
      container:teamOverviewContainer,fetchImpl,origin,onError}):null;
    function clear(){
      epoch++;active=false;activeSession=null;
      dashboard.clear();ai.clear();if(held)held.clear();if(prefs)prefs.clear();
      if(team)team.clear();
    }
    function activate({token,tenantId}){
      clear();
      activeSession={token,tenantId};
      dashboard.activate({token,tenantId});
      ai.activate({token,tenantId});
      if(held)held.activate({token,tenantId});
      if(prefs)prefs.activate({token,tenantId});
      if(team)team.activate({token,tenantId});
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
      const canEdit=['owner','marketing_manager','content_creator']
        .includes(overview.role);
      ai.setCapabilities({manageFacts:overview.role==='owner',
        createDrafts:canEdit});
      if(held){
        held.setCanEdit(canEdit);
        held.setMediaEnabled(canEdit&&overview.pendingMediaAvailable);
      }
      if(prefs)prefs.setCanManage(overview.role==='owner');
      if(team)team.setOwner(overview.role==='owner');
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
      if(prefs){
        const preference=await prefs.refresh();
        if(version!==epoch)return {stale:true};
        if(preference.error){clear();return {stale:false,error:true};}
        if(preference.stale)return {stale:true};
      }
      if(team){
        const membership=await team.refresh();
        if(version!==epoch)return {stale:true};
        if(membership.stale)return {stale:true};
        // Team count reporting is optional and must not revoke an otherwise
        // valid BAM session when the owner-only read is unavailable.
      }
      return {stale:false,tenantId:overview.tenantId,
        draftCount:details.draftCount,businesses:overview.businesses};
    }
    return Object.freeze({activate,refresh,clear,
      showDashboardSection:dashboard.show});
  }
  return Object.freeze({create});
});
