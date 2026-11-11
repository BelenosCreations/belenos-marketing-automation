/* BAM integration-stage signed-in page.
 * Mounts the approved large-card dashboard after a verified BAM session.
 * Not a production deployment or Google OAuth redirect implementation.
 */
(function(root,factory){
  'use strict';
  const api=(typeof module==='object'&&module.exports)
    ?factory(require('./authenticated_workspace_controller.js'),
      require('./authenticated_session_controller.js'))
    :factory(root.BAMAuthenticatedWorkspace,root.BAMSessionController);
  if(typeof module==='object'&&module.exports)module.exports=api;
  else{
    root.BAMSignedInShell=api;
    if(root.document)api.mount({
      document:root.document,window:root,origin:root.location.origin,
      fetchImpl:root.fetch.bind(root)});
  }
})(typeof globalThis!=='undefined'?globalThis:this,function(workspaceModule,sessionModule){
  'use strict';
  function mount({document,window,origin,fetchImpl}){
    if(!document||typeof document.getElementById!=='function'||
       !window||typeof fetchImpl!=='function')
      throw new TypeError('BAM browser shell required');
    const byId=id=>{
      const element=document.getElementById(id);
      if(!element)throw new Error('Missing BAM shell mount');
      return element;
    };
    const signInView=byId('sign-in-view');
    const workspaceView=byId('workspace-view');
    const notice=byId('notice'),form=byId('login-form');
    const loginButton=byId('sign-in-button');
    const logoutButton=byId('logout'),refreshButton=byId('refresh');
    const businessLabel=byId('active-business');
    const businessSelect=byId('business-switch');
    const switchLabel=byId('business-switch-label');
    const nav=[...document.querySelectorAll('[data-bam-panel]')];
    const panels={
      overview:byId('overview-panel'),
      drafts:byId('drafts-panel'),
      settings:byId('settings-panel')
    };
    function message(text){notice.textContent=text;}
    function signedOutView(){
      workspaceView.hidden=true;
      signInView.hidden=false;
      logoutButton.hidden=true;
      businessLabel.hidden=true;
      businessLabel.textContent='';
      businessSelect.hidden=true;switchLabel.hidden=true;
      businessSelect.replaceChildren();
    }
    function signedInView(tenantId,businesses=[]){
      signInView.hidden=true;
      workspaceView.hidden=false;
      logoutButton.hidden=false;
      businessLabel.hidden=false;
      businessLabel.textContent='Business: '+tenantId;
      const choices=[];
      for(const business of businesses){
        if(!business||typeof business.tenantId!=='string'||
           !business.tenantId||typeof business.name!=='string')
          throw new TypeError('Trusted business list required');
        const option=document.createElement('option');
        option.value=business.tenantId;
        option.textContent=business.name;
        choices.push(option);
      }
      businessSelect.replaceChildren(...choices);
      businessSelect.value=tenantId;
      businessSelect.disabled=choices.length<=1;
      businessSelect.hidden=choices.length<=1;
      switchLabel.hidden=choices.length<=1;
      showPanel('overview');
    }
    function showPanel(name){
      if(!Object.prototype.hasOwnProperty.call(panels,name))
        throw new TypeError('Unknown BAM panel');
      for(const [key,panel] of Object.entries(panels))
        panel.hidden=key!==name;
      for(const button of nav){
        if(button.dataset.bamPanel===name)
          button.setAttribute('aria-current','page');
        else button.removeAttribute('aria-current');
      }
    }
    signedOutView();
    if(typeof origin!=='string'||!origin.startsWith('https://')){
      message('Sign-in requires BAM to be hosted on a trusted HTTPS server. This local file is a UI preview only.');
      loginButton.disabled=true;
      return Object.freeze({ready:false,publishingEnabled:false});
    }
    const workspace=workspaceModule.create({
      document,dashboardContainer:byId('bam-dashboard'),
      aiDraftsContainer:byId('bam-ai-drafts'),
      aiSettingsContainer:byId('bam-ai-settings'),
      aiFactsContainer:byId('bam-ai-facts'),
      aiCostContainer:byId('bam-ai-cost'),
      fetchImpl,origin,onError:message,
      copyText:text=>{
        if(!window.navigator||!window.navigator.clipboard)
          return message('Clipboard unavailable; select and copy the image prompt manually.');
        return window.navigator.clipboard.writeText(text).then(
          ()=>message('Image prompt copied.'),
          ()=>message('Clipboard unavailable; select and copy the image prompt manually.'));
      },
      openUrl:url=>{
        if(url!=='https://chatgpt.com/')
          throw new TypeError('Unapproved image handoff destination');
        window.open(url,'_blank','noopener,noreferrer');
      }
    });
    const controller=sessionModule.create({
      origin,fetchImpl,workspace,onError:message
    });
    let pending=false;
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      if(pending)return;
      pending=true;loginButton.disabled=true;
      message('Verifying BAM account...');
      const email=byId('email').value;
      const password=byId('password').value;
      const tenantId=byId('business').value;
      byId('password').value='';
      try{
        const outcome=await controller.passwordSignIn({email,password,tenantId});
        if(outcome.status==='ready'){
          signedInView(outcome.tenantId,outcome.businesses);
          message('Signed in. Drafts and publishing controls remain restricted.');
        }else{
          signedOutView();
          message('Sign-in unavailable. Check your BAM credentials and business membership.');
        }
      }catch(error){
        signedOutView();
        message('Sign-in unavailable. Please sign out before changing accounts.');
      }finally{
        pending=false;loginButton.disabled=false;
      }
    });
    businessSelect.addEventListener('change',async()=>{
      const target=businessSelect.value;
      if(target===controller.activeTenant())return;
      businessSelect.disabled=true;
      message('Verifying access to the selected business...');
      try{
        const result=await controller.switchBusiness({tenantId:target});
        if(result.status==='ready'){
          signedInView(result.tenantId,result.businesses);
          message('Switched to '+businessLabel.textContent+'.');
        }else if(result.stale){
          signedOutView();
          message('Session changed; sign in to continue.');
        }else{
          signedOutView();
          message('Business switch unavailable; sign in again.');
        }
      }catch(error){
        const tenant=controller.activeTenant();
        if(tenant)businessSelect.value=tenant;
        else signedOutView();
        message('Could not change BAM business.');
      }finally{businessSelect.disabled=businessSelect.hidden;}
    });
    logoutButton.addEventListener('click',async()=>{
      // Remove all private DOM before the network request.
      signedOutView();
      message('Signing out...');
      const outcome=await controller.signOut();
      message(outcome.serverRevoked
        ?'Signed out of BAM.'
        :'This page has cleared your session. Server sign-out could not be confirmed.');
    });
    refreshButton.addEventListener('click',async()=>{
      message('Refreshing authorized BAM data...');
      const result=await controller.refresh();
      if(result.error){
        signedOutView();
        message('Session unavailable; please sign in again.');
      }else if(!result.stale){
        signedInView(result.tenantId,result.businesses);
        message('BAM data refreshed for the active business.');
      }
    });
    for(const button of nav)
      button.addEventListener('click',()=>showPanel(button.dataset.bamPanel));
    byId('appearance').addEventListener('change',event=>{
      const value=event.target.value;
      if(!['auto','light','dark'].includes(value))
        throw new TypeError('Invalid BAM appearance');
      document.documentElement.dataset.theme=value;
    });
    return Object.freeze({ready:true,publishingEnabled:false});
  }
  return Object.freeze({mount});
});
