/* BAM owner-editable smart/manual posting time preferences.
 * A saved preference is NOT a scheduled post or an optimization claim.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./dashboard_http_client.js'),
      require('./posting_preferences_write_client.js'));
  else root.BAMPostingPreferencesWorkspace=factory(
    root.BAMReadClient,root.BAMPostingPreferencesWriteClient);
})(typeof globalThis!=='undefined'?globalThis:this,function(reader,writer){
  'use strict';
  function make(doc,tag,content){
    const node=doc.createElement(tag);node.textContent=content;return node;
  }
  function labeled(doc,form,title,control){
    const wrap=make(doc,'div','');wrap.className='field';
    wrap.append(make(doc,'label',title),control);form.append(wrap);
    return control;
  }
  function create({document,container,fetchImpl,origin,onError}){
    if(!document||!container||typeof container.replaceChildren!=='function'||
       typeof fetchImpl!=='function'||typeof origin!=='string'||
       (onError!==undefined&&typeof onError!=='function'))
      throw new TypeError('Posting preference workspace required');
    let active=null,epoch=0,requestVersion=0,busy=false,data=null,preview=null;
    let canManage=false;
    function setCanManage(allowed){
      if(typeof allowed!=='boolean')throw new TypeError('Trusted owner role required');
      canManage=allowed;
      if(active&&data)render();
    }
    function clear(){
      epoch++;requestVersion++;active=null;data=null;preview=null;
      busy=false;canManage=false;
      container.replaceChildren();
    }
    function activate({token,tenantId}){
      if(typeof token!=='string'||!token.trim()||token.length>2048||
         typeof tenantId!=='string'||!tenantId.trim()||tenantId.length>128)
        throw new TypeError('Signed-in business required');
      clear();active={token,tenantId};
    }
    function renderPreview(pane){
      const section=make(document,'section','');
      section.append(make(document,'h3','Upcoming local time preview'));
      if(!preview){
        section.append(make(document,'p',
          'Read-only posting-time preview temporarily unavailable. No posts scheduled.'));
      }else if(preview.status==='not_configured'){
        section.append(make(document,'p',
          'Configure posting times to see a preview. No posts scheduled.'));
      }else if(preview.status==='needs_audience_data'){
        section.append(make(document,'p',
          'Smart mode needs verified audience data; no optimal times can be claimed yet.'));
      }else{
        section.append(make(document,'p',
          'Possible next-seven-day local times only. These are not scheduled posts.'));
        for(const slot of preview.slots){
          section.append(make(document,'p',
            slot.localDate+' at '+slot.localTime+' ('+preview.timezone+')'));
        }
        if(preview.skippedDst)
          section.append(make(document,'p',
            preview.skippedDst+' ambiguous or nonexistent DST times omitted.'));
        if(preview.truncated)
          section.append(make(document,'p',
            'Preview truncated; no posts were queued.'));
      }
      pane.append(section);
    }
    function render(){
      if(!active||!data)return;
      const pane=make(document,'section','');
      pane.append(make(document,'h2','Posting times'));
      pane.append(make(document,'p',
        'Choose smart timing or set specific local posting times. Preferences only: no posts are scheduled or published.'));
      pane.append(make(document,'p',data.configured
        ?'Saved mode: '+data.mode+' · '+data.timezone
        :'Not configured. An owner must select an IANA timezone and save.'));
      if(!canManage){
        pane.append(make(document,'p','Only the business owner can change posting times.'));
        renderPreview(pane);
        container.replaceChildren(pane);
        return;
      }
      const form=make(document,'form','');form.className='stack';
      const mode=make(document,'select','');
      for(const [value,label] of [['smart','Smart (recommendations when available)'],
                                  ['manual','Manual (specific times)']]){
        const option=make(document,'option',label);
        option.value=value;mode.append(option);
      }
      mode.value=data.mode;
      labeled(document,form,'Posting time mode',mode);
      const timezone=labeled(document,form,'IANA timezone',
        make(document,'input',''));
      timezone.value=data.timezone||'';timezone.maxLength=80;
      timezone.required=true;timezone.placeholder='America/New_York';
      const times=labeled(document,form,'Local times, comma separated (24-hour HH:MM)',
        make(document,'textarea',''));
      times.rows=2;times.value=data.manualTimes.join(', ');
      times.placeholder='10:00, 18:30';
      function toggleTimes(){times.disabled=mode.value!=='manual';}
      mode.addEventListener('change',toggleTimes);toggleTimes();
      const submit=make(document,'button','Save posting preferences');
      submit.className='primary';submit.type='submit';submit.disabled=busy;
      form.append(submit);
      form.addEventListener('submit',async event=>{
        event.preventDefault();
        if(busy)return;
        const manualTimes=mode.value==='manual'
          ?times.value.split(',').map(v=>v.trim())
          :[];
        await save({mode:mode.value,timezone:timezone.value.trim(),manualTimes});
      });
      pane.append(form);
      pane.append(make(document,'p',
        'Only business owners can save. Smart mode does not mean verified optimal times are available.'));
      renderPreview(pane);
      container.replaceChildren(pane);
    }
    async function refresh(){
      if(!active)throw new TypeError('Sign-in required');
      const mine=active,version=epoch,request=++requestVersion;
      try{
        const result=await reader.read({kind:'preferences',
          token:mine.token,fetchImpl,origin,
          expectedTenantId:mine.tenantId});
        if(version!==epoch||request!==requestVersion||mine!==active)
          return {stale:true};
        let proposed=null;
        try{
          proposed=await reader.read({kind:'postingPreview',
            token:mine.token,fetchImpl,origin,
            expectedTenantId:mine.tenantId});
        }catch(error){
          // This is read-only guidance; failure must never imply a booking,
          // publishing authorization, or session revocation.
          if(onError&&version===epoch&&mine===active)
            onError('Posting-time preview unavailable. No posts are scheduled.');
        }
        if(version!==epoch||request!==requestVersion||mine!==active)
          return {stale:true};
        data=result;preview=proposed;render();
        return {stale:false,tenantId:mine.tenantId};
      }catch(error){
        if(version!==epoch||request!==requestVersion||mine!==active)
          return {stale:true};
        clear();
        if(onError)onError('Unable to load posting time preferences');
        return {stale:false,error:true};
      }
    }
    async function save({mode,timezone,manualTimes}){
      if(!active||busy||!canManage)
        throw new TypeError('Posting preferences are owner-only');
      const mine=active,version=epoch;busy=true;
      try{
        const result=await writer.save({origin,fetchImpl,
          token:mine.token,expectedTenantId:mine.tenantId,
          mode,timezone,manualTimes});
        if(version!==epoch||mine!==active)return {stale:true};
        const read=await refresh();
        if(read.error||read.stale)return read;
        return {stale:false,tenantId:result.tenantId,mode:result.mode,
          publishingEnabled:false};
      }catch(error){
        if(version!==epoch||mine!==active)return {stale:true};
        if(onError)onError('Posting preferences could not be saved; check owner access and values.');
        render();
        return {error:true};
      }finally{
        if(version===epoch&&mine===active){
          busy=false;render();
        }
      }
    }
    return Object.freeze({activate,refresh,clear,save,setCanManage});
  }
  return Object.freeze({create});
});
