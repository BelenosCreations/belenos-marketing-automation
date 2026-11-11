/* Live-data BAM dashboard: large overview cards with safe drilldowns.
 * No sample analytics, fake scheduling, HTML injection, publishing, or token storage.
 * The signed-in shell supplies a session and handles business switching.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./dashboard_http_client.js'),
      require('./calendar_proposals_client.js'));
  else root.BAMLiveDashboard=factory(root.BAMReadClient,
    root.BAMCalendarProposalsClient);
})(typeof globalThis!=='undefined'?globalThis:this,function(client,calendarClient){
  'use strict';
  const order=['scheduled','approvals','content','connections'];
  function element(doc,tag,text){
    const item=doc.createElement(tag);
    item.textContent=text;
    return item;
  }
  function create({document,container,fetchImpl,origin,onError,
                   onOpenContentStudio,onOpenPostingSettings,
                   enableCalendarProposals=false,
                   enableCalendarSuggestions=false}){
    if(!document||!container||typeof container.replaceChildren!=='function'||
       typeof fetchImpl!=='function'||typeof origin!=='string')
      throw new TypeError('Dashboard dependencies required');
    if(onError!==undefined&&typeof onError!=='function')
      throw new TypeError('Error callback required');
    if(onOpenContentStudio!==undefined&&typeof onOpenContentStudio!=='function')
      throw new TypeError('Content Studio navigation callback required');
    if(onOpenPostingSettings!==undefined&&typeof onOpenPostingSettings!=='function')
      throw new TypeError('Posting settings navigation callback required');
    if(typeof enableCalendarProposals!=='boolean'||
       typeof enableCalendarSuggestions!=='boolean')
      throw new TypeError('Explicit calendar preview feature switch required');
    let active=null,epoch=0,requestVersion=0,current=null,view='home';
    let connectionData=null,connectionPending=false,connectionError=false;
    let connectionRequest=0;
    let postingPreview=null,previewPending=false,previewError=false;
    let previewRequest=0,calendarData=null,calendarError=false;
    let suggestionsData=null,suggestionsError=false;
    function clear(){
      epoch++;requestVersion++;connectionRequest++;previewRequest++;
      active=null;current=null;view='home';
      connectionData=null;connectionPending=false;connectionError=false;
      postingPreview=null;previewPending=false;previewError=false;
      calendarData=null;calendarError=false;
      suggestionsData=null;suggestionsError=false;
      container.replaceChildren();
    }
    function activate({token,tenantId}){
      if(typeof token!=='string'||!token.trim()||token.length>2048||
         typeof tenantId!=='string'||!tenantId.trim()||tenantId.length>128)
        throw new TypeError('Authenticated identity required');
      clear();active={token,tenantId};
    }
    async function refreshConnections(){
      if(!active||!current||
         current.cards.connections.availability!=='available')
        return {restricted:true};
      if(connectionPending)return {pending:true};
      const mine=active,version=epoch,request=++connectionRequest;
      connectionPending=true;connectionError=false;
      if(view==='connections')show('connections');
      try{
        const data=await client.read({kind:'connections',token:mine.token,
          fetchImpl,origin,expectedTenantId:mine.tenantId});
        if(epoch!==version||active!==mine||request!==connectionRequest)
          return {stale:true};
        connectionData=data;
        return {stale:false,count:data.connections.length};
      }catch(error){
        if(epoch!==version||active!==mine||request!==connectionRequest)
          return {stale:true};
        connectionData=null;connectionError=true;
        if(onError)onError('Connection details could not be loaded');
        return {error:true};
      }finally{
        if(epoch===version&&active===mine&&request===connectionRequest){
          connectionPending=false;
          if(view==='connections')show('connections');
        }
      }
    }
    async function refreshPostingPreview(){
      if(!active||!current)return {stale:true};
      if(previewPending)return {pending:true};
      const mine=active,version=epoch,request=++previewRequest;
      previewPending=true;previewError=false;
      if(view==='scheduled')show('scheduled');
      try{
        const [data,proposals,suggestions]=await Promise.allSettled([
          client.read({kind:'postingPreview',token:mine.token,
            fetchImpl,origin,expectedTenantId:mine.tenantId}),
          enableCalendarProposals?calendarClient.list({
            origin,fetchImpl,token:mine.token,
            expectedTenantId:mine.tenantId}):Promise.resolve(null),
          enableCalendarSuggestions?calendarClient.suggest({
            origin,fetchImpl,token:mine.token,
            expectedTenantId:mine.tenantId}):Promise.resolve(null)
        ]);
        if(epoch!==version||active!==mine||request!==previewRequest)
          return {stale:true};
        if(data.status==='fulfilled'){
          postingPreview=data.value;previewError=false;
        }else{
          postingPreview=null;previewError=true;
          if(onError)onError('Posting-time preview could not be loaded');
        }
        if(enableCalendarProposals){
          if(proposals.status==='fulfilled'){
            calendarData=proposals.value;calendarError=false;
          }else{
            calendarData=null;calendarError=true;
            if(onError)onError('Private draft calendar could not be loaded');
          }
        }
        if(enableCalendarSuggestions){
          if(suggestions.status==='fulfilled'){
            suggestionsData=suggestions.value;suggestionsError=false;
          }else{
            suggestionsData=null;suggestionsError=true;
            if(onError)onError('Draft-only time suggestions could not be loaded');
          }
        }
        return data.status==='fulfilled'
          ?{stale:false,status:data.value.status}
          :{error:true};
      }catch(error){
        if(epoch!==version||active!==mine||request!==previewRequest)
          return {stale:true};
        postingPreview=null;previewError=true;
        if(onError)onError('Posting-time preview could not be loaded');
        return {error:true};
      }finally{
        if(epoch===version&&active===mine&&request===previewRequest){
          previewPending=false;
          if(view==='scheduled')show('scheduled');
        }
      }
    }
    function show(section){
      if(!current)return;
      if(section!=='home'&&!order.includes(section))
        throw new TypeError('Unknown dashboard section');
      view=section;
      const scope=active,scopeEpoch=epoch;
      const wrap=element(document,'section','');
      if(section==='home'){
        wrap.append(element(document,'h2','Your marketing overview'));
        const cards=element(document,'div','');
        cards.className='bam-live-cards';
        for(const id of order){
          const card=current.cards[id];
          const button=element(document,'button','');
          button.type='button';
          button.className='bam-live-card';
          const label=element(document,'strong',card.label);
          const value=element(document,'span',
            card.availability==='available'
              ?String(card.value):'Not available');
          button.append(label,value);
          button.addEventListener('click',()=>{
            if(active!==scope||epoch!==scopeEpoch)return;
            show(id);
            if(id==='connections'&&
               current.cards.connections.availability==='available')
              void refreshConnections();
            if(id==='scheduled')void refreshPostingPreview();
          });
          cards.append(button);
        }
        wrap.append(cards);
      }else{
        const back=element(document,'button','Back to overview');
        back.type='button';
        back.addEventListener('click',()=>{
          if(active===scope&&epoch===scopeEpoch)show('home');
        });
        wrap.append(back);
        wrap.append(element(document,'h2',current.cards[section].label));
        if(section==='content'){
          if(!current.drafts.length)
            wrap.append(element(document,'p','No held content requests.'));
          for(const draft of current.drafts){
            const article=element(document,'article','');
            article.append(element(document,'strong',draft.channel));
            article.append(element(document,'p',draft.text));
            article.append(element(document,'p',draft.suggestion));
            if(draft.missing.length)
              article.append(element(document,'p',
                'Still needed: '+draft.missing.join(', ')));
            wrap.append(article);
          }
          if(onOpenContentStudio){
            const open=element(document,'button','Open Content Studio');
            open.type='button';open.className='secondary';
            open.addEventListener('click',()=>{
              if(active===scope&&epoch===scopeEpoch)onOpenContentStudio();
            });
            wrap.append(open);
          }
        }else if(section==='scheduled'){
          wrap.append(element(document,'p',
            'No social scheduler is connected. No posts are scheduled or verified.'));
          const preview=element(document,'section','');
          preview.append(element(document,'h3','Possible local posting times'));
          if(previewPending){
            preview.append(element(document,'p',
              'Checking saved posting-time preferences...'));
          }else if(previewError){
            preview.append(element(document,'p',
              'Posting-time preview unavailable. No posts have been scheduled.'));
          }else if(!postingPreview){
            preview.append(element(document,'p',
              'Select Refresh time preview to see possible posting times.'));
          }else if(postingPreview.status==='not_configured'){
            preview.append(element(document,'p',
              'Posting-time preferences are not configured for this business.'));
          }else if(postingPreview.status==='needs_audience_data'){
            preview.append(element(document,'p',
              'Smart mode needs verified audience data. No optimal posting time is available yet.'));
          }else{
            preview.append(element(document,'p',
              'Manual mode: suggested clock times only, not scheduled posts.'));
            for(const slot of postingPreview.slots.slice(0,10)){
              preview.append(element(document,'p',
                slot.localDate+' at '+slot.localTime+' ('+
                postingPreview.timezone+')'));
            }
            if(postingPreview.slots.length>10||postingPreview.truncated)
              preview.append(element(document,'p',
                'Additional proposed times omitted from this dashboard preview.'));
            if(postingPreview.skippedDst)
              preview.append(element(document,'p',
                postingPreview.skippedDst+' ambiguous or nonexistent daylight-saving times omitted.'));
          }
          const update=element(document,'button','Refresh time preview');
          update.type='button';update.className='secondary';
          update.disabled=previewPending;
          update.addEventListener('click',()=>{
            if(active===scope&&epoch===scopeEpoch)
              void refreshPostingPreview();
          });
          preview.append(update);
          if(onOpenPostingSettings){
            const settings=element(document,'button','Open posting-time settings');
            settings.type='button';settings.className='secondary';
            settings.addEventListener('click',()=>{
              if(active===scope&&epoch===scopeEpoch)onOpenPostingSettings();
            });
            preview.append(settings);
          }
          wrap.append(preview);
          if(enableCalendarProposals){
            const calendar=element(document,'section','');
            calendar.append(element(document,'h3',
              'Proposed draft calendar — not scheduled posts'));
            if(previewPending){
              calendar.append(element(document,'p','Checking private content proposals...'));
            }else if(calendarError||!calendarData){
              calendar.append(element(document,'p',
                'Proposed times unavailable. This does not mean there are no drafts.'));
            }else if(!calendarData.items.length){
              calendar.append(element(document,'p',
                'No proposed draft dates saved for this business.'));
            }else{
              for(const entry of calendarData.items){
                const item=element(document,'article','');
                item.append(element(document,'p',
                  entry.localDate+' at '+entry.localTime+' ('+entry.timezone+')'));
                if(entry.contentChanged)
                  item.append(element(document,'p',
                    'Draft changed since this proposal; choose a new time or refresh it.'));
                if(!entry.slotCurrent)
                  item.append(element(document,'p',
                    'This time no longer matches current posting preferences.'));
                item.append(element(document,'p',
                  'Draft proposal only — no approval, scheduled job or social publication.'));
                calendar.append(item);
              }
            }
            if(onOpenContentStudio){
              const edit=element(document,'button','Manage proposed draft times');
              edit.type='button';edit.className='secondary';
              edit.addEventListener('click',()=>{
                if(active===scope&&epoch===scopeEpoch)onOpenContentStudio();
              });
              calendar.append(edit);
            }
            wrap.append(calendar);
          }
          if(enableCalendarSuggestions){
            const planner=element(document,'section','');
            planner.append(element(document,'h3',
              'Possible dates for unassigned drafts — suggestions only'));
            if(previewPending)
              planner.append(element(document,'p','Checking held draft options...'));
            else if(suggestionsError||!suggestionsData)
              planner.append(element(document,'p',
                'Draft suggestions unavailable; no dates were assigned.'));
            else if(suggestionsData.preferenceStatus!=='manual_preview')
              planner.append(element(document,'p',
                'Owner-configured Manual times are needed. Smart recommendations require verified audience data.'));
            else if(!suggestionsData.items.length)
              planner.append(element(document,'p',
                'No unassigned drafts can be paired with an open Manual slot right now.'));
            else{
              planner.append(element(document,'p',
                'Preview only. Save any chosen date in Content Studio; nothing is scheduled or approved.'));
              for(const suggestion of suggestionsData.items){
                const item=element(document,'article','');
                const draft=current.drafts.find(x=>x.id===suggestion.requestId);
                item.append(element(document,'p',
                  suggestion.localDate+' at '+suggestion.localTime+
                  ' ('+suggestion.timezone+')'));
                item.append(element(document,'p',
                  draft?'Held draft: '+draft.text:
                  'Held draft reference: '+suggestion.requestId.slice(0,8)));
                planner.append(item);
              }
              if(suggestionsData.unassignedHeldCount>suggestionsData.items.length)
                planner.append(element(document,'p',
                  'Additional held drafts do not currently have suggested slots.'));
            }
            if(onOpenContentStudio){
              const manage=element(document,'button','Choose a proposed date in Content Studio');
              manage.type='button';manage.className='secondary';
              manage.addEventListener('click',()=>{
                if(active===scope&&epoch===scopeEpoch)onOpenContentStudio();
              });
              planner.append(manage);
            }
            wrap.append(planner);
          }
        }else if(section==='approvals'){
          wrap.append(element(document,'p',
            'Ready-for-review requests are not approved or scheduled posts.'));
          const review=current.drafts.filter(x=>x.status==='ready_for_review');
          if(!review.length)
            wrap.append(element(document,'p','No content marked ready for review.'));
          for(const draft of review){
            const article=element(document,'article','');
            article.append(element(document,'h3',draft.channel));
            article.append(element(document,'p',draft.text));
            article.append(element(document,'p',draft.suggestion));
            wrap.append(article);
          }
          if(onOpenContentStudio){
            const open=element(document,'button','Open Content Studio');
            open.type='button';open.className='secondary';
            open.addEventListener('click',()=>{
              if(active===scope&&epoch===scopeEpoch)onOpenContentStudio();
            });
            wrap.append(open);
          }
        }else if(section==='connections'){
          const state=current.cards.connections.availability;
          if(state!=='available'){
            wrap.append(element(document,'p',
              'Social connection details are restricted for this business role.'));
          }else{
            wrap.append(element(document,'p',
              'Read-only provider status. A connected analytics account does not enable social publishing.'));
            if(connectionPending){
              wrap.append(element(document,'p','Loading account connection status...'));
            }else if(connectionError){
              wrap.append(element(document,'p',
                'Connection status could not be verified. Please refresh.'));
            }else if(connectionData){
              if(!connectionData.connections.length)
                wrap.append(element(document,'p','No analytics account connections configured.'));
              for(const item of connectionData.connections){
                const article=element(document,'article','');
                article.append(element(document,'h3',item.platform+' · '+item.accountId));
                const statuses={
                  connected:'Connected for read-only insights',
                  pending:'Connection setup pending',
                  refresh_required:'Reconnect required',
                  revoked:'Connection revoked',
                  expired:'Connection expired'
                };
                article.append(element(document,'p',statuses[item.status]));
                article.append(element(document,'p','Access scope: '+item.scope));
                const at=new Date(item.updatedAt*1000);
                if(Number.isFinite(at.getTime()))
                  article.append(element(document,'p',
                    'Status checked by BAM registry: '+at.toISOString().slice(0,10)+' UTC'));
                wrap.append(article);
              }
            }else{
              wrap.append(element(document,'p',
                'Select Refresh account statuses to check this business.'));
            }
            const refresh=element(document,'button','Refresh account statuses');
            refresh.type='button';refresh.className='secondary';
            refresh.disabled=connectionPending;
            refresh.addEventListener('click',()=>{
              if(active!==scope||epoch!==scopeEpoch)return;
              void refreshConnections();
            });
            wrap.append(refresh);
          }
        }
      }
      container.replaceChildren(wrap);
    }
    async function refresh(){
      if(!active)throw new TypeError('Sign-in required');
      const mine=active,version=epoch,request=++requestVersion;
      try{
        const data=await client.read({kind:'dashboard',token:mine.token,
          fetchImpl,origin,expectedTenantId:mine.tenantId});
        if(version!==epoch||request!==requestVersion||mine!==active)
          return {stale:true};
        connectionRequest++;previewRequest++;
        connectionData=null;connectionPending=false;connectionError=false;
        postingPreview=null;previewPending=false;previewError=false;
        calendarData=null;calendarError=false;
        suggestionsData=null;suggestionsError=false;
        current=data;show(view);
        if(view==='connections'&&
           data.cards.connections.availability==='available')
          void refreshConnections();
        if(view==='scheduled')void refreshPostingPreview();
        return {stale:false,tenantId:data.tenantId,role:data.role,
          pendingMediaAvailable:data.pendingMediaAvailable,
          businesses:data.businesses.map(b=>({tenantId:b.tenant_id,name:b.name}))};
      }catch(error){
        if(version!==epoch||request!==requestVersion||mine!==active)
          return {stale:true};
        current=null;container.replaceChildren();
        if(onError)onError('Unable to load dashboard');
        return {stale:false,error:true};
      }
    }
    return Object.freeze({activate,refresh,clear,show,refreshConnections,
      refreshPostingPreview});
  }
  return Object.freeze({create});
});
