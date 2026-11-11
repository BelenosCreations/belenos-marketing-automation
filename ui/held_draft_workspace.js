/* Explicit held-draft Content Studio: create and change hold state only.
 * No publication, approval, upload, media verification, analytics or auto retry.
 * All mutations are server-authorized; a tenant switch invalidates pending UI.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./dashboard_http_client.js'),
      require('./held_draft_write_client.js'),
      require('./pending_media_client.js'),
      require('./content_risk_client.js'),
      require('./held_draft_csv_import.js'));
  else root.BAMHeldDraftWorkspace=factory(
    root.BAMReadClient,root.BAMHeldDraftWriteClient,root.BAMPendingMediaClient,
    root.BAMContentRiskClient,root.BAMHeldDraftCSVImport);
})(typeof globalThis!=='undefined'?globalThis:this,function(readClient,writeClient,pendingClient,riskClient,csvImport){
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
    let canEdit=false,mediaEnabled=false,mediaStatusReady=false;
    let mediaStatuses=new Map(),riskReports=new Map(),riskPending=new Set();
    let plannedImport=null;
    function setMediaEnabled(allowed){
      if(typeof allowed!=='boolean')throw new TypeError('Trusted media capability required');
      mediaEnabled=allowed&&canEdit;
      mediaStatusReady=false;mediaStatuses=new Map();
      if(model&&active)render();
    }
    function setCanEdit(allowed){
      if(typeof allowed!=='boolean')throw new TypeError('Trusted draft edit permission required');
      canEdit=allowed;
      if(!allowed){
        mediaEnabled=false;mediaStatusReady=false;mediaStatuses=new Map();
      }
      if(model&&active)render();
    }
    function clear(){
      epoch++;requestVersion++;active=null;model=null;busy=false;canEdit=false;
      mediaEnabled=false;mediaStatusReady=false;mediaStatuses=new Map();
      riskReports=new Map();riskPending=new Set();plannedImport=null;
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
      const viewingSession=active,viewingEpoch=epoch;
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
        if(busy||viewingSession!==active||viewingEpoch!==epoch)return;
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
          if(Number.isSafeInteger(draft.revision)&&draft.revision>=1){
            const found=riskReports.get(draft.id);
            if(found&&found.revision===draft.revision){
              article.append(make(document,'p',
                found.signalCount
                  ?'Potential marketing claim flags: '+found.signalCount
                  :'No heuristic flags found. This is not factual verification.'));
              for(const signal of found.signals){
                article.append(make(document,'p',
                  signal.category.replaceAll('_',' ')+': '+signal.text));
              }
              if(found.truncated)
                article.append(make(document,'p',
                  'Additional risk flags omitted from this short preview.'));
              article.append(make(document,'p',
                'Heuristic screening is incomplete. Human factual and media review is still required.'));
            }
            const riskButton=make(document,'button',
              'Check marketing claim risks');
            riskButton.type='button';riskButton.className='secondary';
            riskButton.disabled=riskPending.has(draft.id);
            riskButton.addEventListener('click',()=>{
              if(active!==viewingSession||epoch!==viewingEpoch)return;
              void inspectRisk({requestId:draft.id,revision:draft.revision});
            });
            article.append(riskButton);
          }
          if(canEdit&&Number.isSafeInteger(draft.revision)&&draft.revision>=1){
            for(const [target,label,initial] of [
              ['draft_text','Save revised post copy',draft.text],
              ['suggestion','Save revised content guidance',draft.suggestion]
            ]){
              const editor=make(document,'textarea','');
              editor.value=initial;
              editor.maxLength=2000;editor.rows=3;
              article.append(editor);
              const save=make(document,'button',label);
              save.type='button';save.className='secondary';
              save.disabled=busy;
              save.addEventListener('click',async()=>{
                if(busy||viewingSession!==active||viewingEpoch!==epoch)
                  return;
                await reviseDraft({requestId:draft.id,target,
                  revisedText:editor.value.trim(),
                  expectedRevision:draft.revision});
              });
              article.append(save);
            }
            article.append(make(document,'p',
              'Text changes are version-checked and remain unpublished. No content is automatically approved.'));
          }
          if(canEdit&&mediaEnabled&&status==='needs_content'){
            const item=draft.missing.find(value=>
              /photo|image|picture|artwork|graphic/i.test(value));
            if(item){
              const state=mediaStatuses.get(draft.id+':'+item);
              if(!mediaStatusReady){
                article.append(make(document,'p',
                  'Private image status unavailable. Refresh before submitting another file.'));
              }else if(state==='pending_scan'){
                article.append(make(document,'p',
                  'Image received in private quarantine. Awaiting review; not verified, approved or publishable.'));
                const remove=make(document,'button','Discard pending image');
                remove.type='button';remove.className='secondary';
                remove.disabled=busy;
                remove.addEventListener('click',()=>{
                  if(busy||viewingSession!==active||
                     viewingEpoch!==epoch||!mediaEnabled)return;
                  remove.disabled=true;
                  const confirm=make(document,'button',
                    'Confirm discard of unverified image');
                  confirm.type='button';confirm.className='secondary';
                  confirm.addEventListener('click',async()=>{
                    if(busy||viewingSession!==active||viewingEpoch!==epoch)
                      return;
                    await discardImage({requestId:draft.id,item});
                  });
                  article.append(confirm);
                });
                article.append(remove);
              }else{
              const picker=make(document,'input','');
              picker.type='file';
              picker.accept='image/png,image/jpeg,image/webp';
              article.append(picker);
              const upload=make(document,'button',
                'Send image for private review');
              upload.type='button';upload.className='secondary';
              upload.disabled=busy;
              upload.addEventListener('click',async()=>{
                if(busy||!active||active!==viewingSession||
                   epoch!==viewingEpoch)return;
                const file=picker.files&&picker.files[0];
                if(!file){
                  if(onError)onError('Choose an image before submitting.');
                  return;
                }
                await stageImage({requestId:draft.id,item,file});
              });
              article.append(upload);
              article.append(make(document,'p',
                'This image stays private and pending. No safety, rights or approval review has occurred.'));
              }
            }
          }
          if(canEdit&&status!=='ready_for_review'){
            const actions=status==='needs_content'
              ?[['postponed','Postpone'],['unavailable','Mark unavailable']]
              :[['needs_content','Reopen as needing content']];
            for(const [target,label] of actions){
              const button=make(document,'button',label);
              button.type='button';button.className='secondary';
              button.disabled=busy;
              button.addEventListener('click',async()=>{
                if(busy||active!==viewingSession||epoch!==viewingEpoch)return;
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
      if(canEdit){
        const bulk=make(document,'section','');
        bulk.className='panel stack';
        bulk.append(make(document,'h3','Advanced: import held drafts from CSV'));
        bulk.append(make(document,'p',
          'Import 1–20 unpublished drafts. Columns: channel,draft_text,suggestion,required_items. Separate required items with |. Missing items default to image. No publishing or AI requests.'));
        const chooser=make(document,'input','');
        chooser.type='file';chooser.accept='.csv,text/csv';
        bulk.append(chooser);
        const previewButton=make(document,'button','Preview CSV draft import');
        previewButton.type='button';previewButton.className='secondary';
        previewButton.disabled=busy;
        previewButton.addEventListener('click',async()=>{
          if(busy||active!==viewingSession||epoch!==viewingEpoch)return;
          const file=chooser.files&&chooser.files[0];
          if(!file||!Number.isSafeInteger(file.size)||file.size>131072||
             file.size<1||typeof file.text!=='function'){
            if(onError)onError('Choose a CSV file of 128 KiB or smaller.');
            return;
          }
          try{
            const source=await file.text();
            if(active!==viewingSession||epoch!==viewingEpoch)return;
            const entries=csvImport.parse(source);
            const duplicates=new Set(model.drafts.map(x=>
              x.channel+'\u0000'+x.text.toLowerCase().replace(/\s+/g,' ').trim()));
            if(entries.some(x=>duplicates.has(
                x.channel+'\u0000'+x.draftText.toLowerCase().replace(/\s+/g,' ').trim())))
              throw new TypeError('Draft text already exists');
            plannedImport=entries;
            render();
          }catch(error){
            plannedImport=null;
            if(onError)onError('CSV draft preview failed. Check columns, row count, and duplicates.');
          }
        });
        bulk.append(previewButton);
        if(plannedImport){
          bulk.append(make(document,'p',
            plannedImport.length+' unpublished drafts validated. Review the source CSV, then confirm import. This may partially complete if the server becomes unavailable.'));
          for(const entry of plannedImport){
            const row=make(document,'p',entry.channel+': '+entry.draftText);
            bulk.append(row);
          }
          const confirm=make(document,'button',
            'Confirm import of '+plannedImport.length+' held drafts');
          confirm.type='button';confirm.className='primary';confirm.disabled=busy;
          confirm.addEventListener('click',async()=>{
            if(busy||active!==viewingSession||epoch!==viewingEpoch)return;
            await importCSV();
          });
          bulk.append(confirm);
          const cancel=make(document,'button','Cancel CSV import');
          cancel.type='button';cancel.className='secondary';
          cancel.addEventListener('click',()=>{
            if(!busy&&active===viewingSession&&epoch===viewingEpoch){
              plannedImport=null;render();
            }
          });
          bulk.append(cancel);
        }
        wrap.append(bulk);
      }
      container.replaceChildren(wrap);
    }
    async function importCSV(){
      if(!active||!canEdit||busy||!plannedImport)return {error:true};
      const mine=active,version=epoch,rows=plannedImport;
      plannedImport=null;busy=true;
      let created=0,error=false;
      try{
        for(const row of rows){
          if(version!==epoch||active!==mine)return {stale:true};
          await writeClient.createDraft({
            origin,fetchImpl,token:mine.token,
            expectedTenantId:mine.tenantId,
            channel:row.channel,draftText:row.draftText,
            suggestion:row.suggestion,requiredItems:[...row.requiredItems],
            priority:row.priority});
          created++;
        }
      }catch(failure){
        error=true;
      }finally{
        if(version===epoch&&active===mine){
          try{await refresh();}catch(unavailable){error=true;}
          if(onNotice&&created)
            onNotice(created+' held drafts saved as unpublished.');
          if(error&&onError)
            onError('CSV import stopped after '+created+
              ' confirmed drafts. Review existing drafts before trying again.');
          busy=false;render();
        }
      }
      if(version!==epoch||active!==mine)return {stale:true};
      return {stale:false,created,error};
    }
    async function inspectRisk({requestId,revision}){
      if(!active||riskPending.has(requestId))return {error:true};
      const mine=active,version=epoch;
      riskPending.add(requestId);
      render();
      try{
        const report=await riskClient.preview({
          origin,fetchImpl,token:mine.token,
          expectedTenantId:mine.tenantId,
          requestId,expectedRevision:revision});
        if(version!==epoch||active!==mine)return {stale:true};
        const current=model&&model.drafts.find(x=>x.id===requestId);
        if(!current||current.revision!==revision)return {stale:true};
        riskReports.set(requestId,report);render();
        return {stale:false,signalCount:report.signalCount};
      }catch(error){
        if(version!==epoch||active!==mine)return {stale:true};
        if(onError)onError(
          'Marketing claim preview unavailable. No draft has been approved.');
        return {error:true};
      }finally{
        riskPending.delete(requestId);
        if(version===epoch&&active===mine)render();
      }
    }
    async function refresh(){
      if(!active)throw new TypeError('BAM sign-in required');
      const mine=active,version=epoch,request=++requestVersion;
      try{
        const data=await readClient.read({kind:'drafts',token:mine.token,
          fetchImpl,origin,expectedTenantId:mine.tenantId});
        if(version!==epoch||active!==mine||request!==requestVersion)
          return {stale:true};
        if(mediaEnabled&&hashBytes&&data.drafts.length){
          try{
            const latest=await pendingClient.statuses({
              origin,fetchImpl,token:mine.token,
              expectedTenantId:mine.tenantId});
            if(version!==epoch||active!==mine||request!==requestVersion)
              return {stale:true};
            mediaStatuses=new Map(latest.items.map(x=>[
              x.requestId+':'+x.item,x.status]));
            mediaStatusReady=true;
          }catch(error){
            if(version!==epoch||active!==mine||request!==requestVersion)
              return {stale:true};
            mediaStatuses=new Map();mediaStatusReady=false;
            if(onError)onError('Private media status could not be checked. Image upload is temporarily disabled.');
          }
        }else{
          mediaStatuses=new Map();mediaStatusReady=false;
        }
        for(const [id,report] of riskReports){
          const draft=data.drafts.find(x=>x.id===id);
          if(!draft||draft.revision!==report.revision)
            riskReports.delete(id);
        }
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
          status:result.status,
          ...(result.revision===undefined?{}:{revision:result.revision}),
          publishingEnabled:false};
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
    async function stageImage({requestId,item,file}){
      if(!active||!canEdit||!mediaEnabled||busy||!hashBytes)
        return {error:true};
      const mine=active,version=epoch;
      busy=true;
      try{
        const received=await pendingClient.stage({
          origin,fetchImpl,token:mine.token,expectedTenantId:mine.tenantId,
          requestId,item,file,hashBytes,
          isCurrent:()=>version===epoch&&mine===active&&
            canEdit&&mediaEnabled});
        if(version!==epoch||mine!==active)return {stale:true};
        const updated=await refresh();
        if(updated.stale||updated.error)return updated;
        if(onNotice)onNotice(
          'Image received into private pending review. It is not verified, approved or ready to publish.');
        return received;
      }catch(error){
        if(version===epoch&&mine===active&&onError)
          onError('Image receipt unavailable. Check the selected file and private media configuration.');
        return {error:true};
      }finally{
        if(version===epoch&&mine===active){busy=false;render();}
      }
    }
    async function discardImage({requestId,item}){
      if(!active||!canEdit||!mediaEnabled||!mediaStatusReady||
         mediaStatuses.get(requestId+':'+item)!=='pending_scan'||busy)
        return {error:true};
      const mine=active,version=epoch;
      busy=true;
      try{
        const result=await pendingClient.discard({
          origin,fetchImpl,token:mine.token,
          expectedTenantId:mine.tenantId,requestId,item});
        if(version!==epoch||active!==mine)return {stale:true};
        const latest=await refresh();
        if(latest.error||latest.stale)return latest;
        if(onNotice)onNotice(
          'Unverified pending image discarded. You may submit a replacement.');
        return result;
      }catch(error){
        if(version===epoch&&active===mine&&onError)
          onError('Pending image could not be discarded; refresh to check its status.');
        return {error:true};
      }finally{
        if(version===epoch&&active===mine){busy=false;render();}
      }
    }
    function createDraft(args){return mutate(writeClient.createDraft,args);}
    function reviseDraft(args){return mutate(writeClient.reviseDraft,args);}
    function changeHold(args){return mutate(writeClient.changeHold,args);}
    return Object.freeze({activate,refresh,clear,inspectRisk,importCSV,
      createDraft,changeHold,
      reviseDraft,
      stageImage,discardImage,setCanEdit,setMediaEnabled});
  }
  return Object.freeze({create});
});
