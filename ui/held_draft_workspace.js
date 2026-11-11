/* Explicit held-draft Content Studio: create and change hold state only.
 * No publication, approval, upload, media verification, analytics or auto retry.
 * All mutations are server-authorized; a tenant switch invalidates pending UI.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./dashboard_http_client.js'),
      require('./held_draft_write_client.js'),
      require('./pending_media_client.js'));
  else root.BAMHeldDraftWorkspace=factory(
    root.BAMReadClient,root.BAMHeldDraftWriteClient,root.BAMPendingMediaClient);
})(typeof globalThis!=='undefined'?globalThis:this,function(readClient,writeClient,pendingClient){
  'use strict';
  const channelNames=['facebook','instagram','linkedin','pinterest','tiktok','youtube'];
  const holdNames=['needs_content','ready_for_review','postponed','unavailable'];
  function make(document,tag,label){
    const element=document.createElement(tag);
    element.textContent=label;
    return element;
  }
  function field(document,form,label,control){
    const wrap=make(document,'div','');wrap.className='field';
    const caption=make(document,'label',label);
    wrap.append(caption,control);form.append(wrap);
    return control;
  }
  function create({document,container,fetchImpl,origin,onError,onNotice,hashBytes}){
    if(!document||!container||typeof container.replaceChildren!=='function'||
       typeof fetchImpl!=='function'||typeof origin!=='string'||
       (onError!==undefined&&typeof onError!=='function')||
       (onNotice!==undefined&&typeof onNotice!=='function')||
       (hashBytes!==undefined&&typeof hashBytes!=='function'))
      throw new TypeError('Content Studio dependencies required');
    let active=null,epoch=0,requestVersion=0,busy=false,model=null;
    let canEdit=false,mediaEnabled=false;
    function setMediaEnabled(allowed){
      if(typeof allowed!=='boolean')throw new TypeError('Trusted media capability required');
      mediaEnabled=allowed&&canEdit;
    }
    function setCanEdit(allowed){
      if(typeof allowed!=='boolean')throw new TypeError('Trusted draft edit permission required');
      canEdit=allowed;
      if(!allowed)mediaEnabled=false;
      if(model&&active)render();
    }
    function clear(){
      epoch++;requestVersion++;active=null;model=null;busy=false;canEdit=false;
      mediaEnabled=false;
      container.replaceChildren();
    }
    function activate({token,tenantId}){
      if(typeof token!=='string'||!token.trim()||token.length>2048||
         typeof tenantId!=='string'||!tenantId.trim()||tenantId.length>128)
        throw new TypeError('Authenticated content session required');
      clear();active={token,tenantId};
    }
    function render(){
      if(!model||!active)return;
      const wrap=make(document,'section','');
      wrap.className='bam-held-draft-workspace';
      wrap.append(make(document,'h2','Content Studio'));
      wrap.append(make(document,'p',
        'Create and organize unpublished content requests. Upload, approval, scheduling and publishing remain unavailable.'));
      if(!canEdit){
        wrap.append(make(document,'p','You can view held content but cannot create or edit it.'));
      }
      if(canEdit){
      const form=make(document,'form','');form.className='panel stack';
      form.append(make(document,'h3','New held draft'));
      const channel=make(document,'select','');
      for(const name of channelNames){
        const option=make(document,'option',name[0].toUpperCase()+name.slice(1));
        option.value=name;channel.append(option);
      }
      channel.value='facebook';
      field(document,form,'Social platform',channel);
      const draftText=field(document,form,'Draft copy',make(document,'textarea',''));
      draftText.maxLength=2000;draftText.required=true;draftText.rows=4;
      const suggestion=field(document,form,'Content guidance',make(document,'textarea',''));
      suggestion.maxLength=2000;suggestion.required=true;suggestion.rows=2;
      const items=field(document,form,'Required items, separated by commas',
        make(document,'input',''));
      items.value='image';items.maxLength=950;items.required=true;
      const submit=make(document,'button','Save as held draft');
      submit.type='submit';submit.className='primary';submit.disabled=busy;
      form.append(submit);
      form.addEventListener('submit',async event=>{
        event.preventDefault();
        if(busy)return;
        const requiredItems=items.value.split(',').map(x=>x.trim());
        const result=await createDraft({
          channel:channel.value,draftText:draftText.value.trim(),
          suggestion:suggestion.value.trim(),requiredItems});
        if(result.error&&onError)onError('Unable to save held draft');
      });
      wrap.append(form);
      }
      for(const status of holdNames){
        const list=model.drafts.filter(x=>x.status===status);
        const section=make(document,'section','');
        section.append(make(document,'h3',
          status.replaceAll('_',' ')+' ('+list.length+')'));
        for(const draft of list){
          const article=make(document,'article','');
          article.append(make(document,'h4',draft.channel));
          article.append(make(document,'p',draft.text));
          article.append(make(document,'p',draft.suggestion));
          if(draft.missing.length)
            article.append(make(document,'p',
              'Still needed: '+draft.missing.join(', ')));
          if(canEdit&&status!=='ready_for_review'){
            const actions=status==='needs_content'
              ?[['postponed','Postpone'],['unavailable','Mark unavailable']]
              :[['needs_content','Reopen as needing content']];
            for(const [target,label] of actions){
              const button=make(document,'button',label);
              button.type='button';button.className='secondary';
              button.disabled=busy;
              button.addEventListener('click',async()=>{
                if(busy)return;
                const result=await changeHold({requestId:draft.id,status:target});
                if(result.error&&onError)onError('Unable to change draft status');
              });
              article.append(button);
            }
          }
          section.append(article);
        }
        wrap.append(section);
      }
      container.replaceChildren(wrap);
    }
    async function refresh(){
      if(!active)throw new TypeError('BAM sign-in required');
      const mine=active,version=epoch,request=++requestVersion;
      try{
        const data=await readClient.read({kind:'drafts',token:mine.token,
          fetchImpl,origin,expectedTenantId:mine.tenantId});
        if(version!==epoch||active!==mine||request!==requestVersion)
          return {stale:true};
        model=data;render();
        return {stale:false,tenantId:mine.tenantId,
          heldCount:data.drafts.length};
      }catch(error){
        if(version!==epoch||active!==mine||request!==requestVersion)
          return {stale:true};
        clear();
        if(onError)onError('Unable to load Content Studio');
        return {stale:false,error:true};
      }
    }
    async function mutate(op,args){
      if(!active||busy||!canEdit)throw new TypeError('Content Studio not editable');
      const mine=active,version=epoch;busy=true;
      try{
        const result=await op({
          origin,fetchImpl,token:mine.token,
          expectedTenantId:mine.tenantId,...args});
        if(version!==epoch||active!==mine)return {stale:true};
        const latest=await refresh();
        if(latest.error||latest.stale)return latest;
        return {stale:false,tenantId:result.tenantId,id:result.id,
          status:result.status,publishingEnabled:false};
      }catch(error){
        if(version!==epoch||active!==mine)return {stale:true};
        // Retain authenticated read-only data but report failed mutation.
        if(onError)onError('Content mutation was not confirmed');
        render();
        return {error:true};
      }finally{
        if(version===epoch&&active===mine){
          busy=false;render();
        }
      }
    }
    function createDraft(args){return mutate(writeClient.createDraft,args);}
    function changeHold(args){return mutate(writeClient.changeHold,args);}
    return Object.freeze({activate,refresh,clear,createDraft,changeHold,
      setCanEdit,setMediaEnabled});
  }
  return Object.freeze({create});
});
