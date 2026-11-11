/* Live-data BAM dashboard: large overview cards with safe drilldowns.
 * No sample analytics, fake scheduling, HTML injection, publishing, or token storage.
 * The signed-in shell supplies a session and handles business switching.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./dashboard_http_client.js'),
      require('./calendar_proposals_client.js'),
       require('./review_readiness_client.js'),
       require('./review_feedback_client.js'));
  else root.BAMLiveDashboard=factory(root.BAMReadClient,
    root.BAMCalendarProposalsClient,root.BAMReviewReadinessClient,
     root.BAMReviewFeedbackClient);
})(typeof globalThis!=='undefined'?globalThis:this,function(client,calendarClient,reviewClient,feedbackClient){
  'use strict';
  const order=['scheduled','approvals','content','connections'];
  function element(doc,tag,text){
    const item=doc.createElement(tag);
    item.textContent=text;
    return item;
  }
  function create({document,container,fetchImpl,origin,onError,onNotice,
                   onOpenContentStudio,onOpenPostingSettings,
                   enableCalendarProposals=false,
                   enableCalendarSuggestions=false,
                   enableReviewReadiness=false,
                   enableReviewFeedback=false}){
    if(!document||!container||typeof container.replaceChildren!=='function'||
       typeof fetchImpl!=='function'||typeof origin!=='string')
      throw new TypeError('Dashboard dependencies required');
    if(onNotice!==undefined&&typeof onNotice!=='function')
      throw new TypeError('Notice callback required');
    if(onError!==undefined&&typeof onError!=='function')
      throw new TypeError('Error callback required');
    if(onOpenContentStudio!==undefined&&typeof onOpenContentStudio!=='function')
      throw new TypeError('Content Studio navigation callback required');
    if(onOpenPostingSettings!==undefined&&typeof onOpenPostingSettings!=='function')
      throw new TypeError('Posting settings navigation callback required');
    if(typeof enableCalendarProposals!=='boolean'||
       typeof enableCalendarSuggestions!=='boolean'||
       typeof enableReviewReadiness!=='boolean'||
       typeof enableReviewFeedback!=='boolean')
      throw new TypeError('Explicit calendar preview feature switch required');
    let active=null,epoch=0,requestVersion=0,current=null,view='home';
    let connectionData=null,connectionPending=false,connectionError=false;
    let connectionRequest=0;
    let postingPreview=null,previewPending=false,previewError=false;
    let previewRequest=0,calendarData=null,calendarError=false;
    let suggestionsData=null,suggestionsError=false;
    let quickProposalPending=false;
    let reviewData=null,reviewPending=false,reviewError=false,reviewRequest=0;
    let feedbackData=null,feedbackPending=false,feedbackError=false;
    let feedbackRequest=0,feedbackWriting=false;
    function clear(){
      epoch++;requestVersion++;connectionRequest++;previewRequest++;reviewRequest++;feedbackRequest++;
      active=null;current=null;view='home';
      connectionData=null;connectionPending=false;connectionError=false;
      postingPreview=null;previewPending=false;previewError=false;
      calendarData=null;calendarError=false;
      suggestionsData=null;suggestionsError=false;
      quickProposalPending=false;
      reviewData=null;reviewPending=false;reviewError=false;
      feedbackData=null;feedbackPending=false;feedbackError=false;
      feedbackWriting=false;
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
    async function saveSuggestedDate(suggestion,snapshot){
      if(!enableCalendarProposals||!enableCalendarSuggestions||
         !active||!current||!calendarData||!suggestionsData||
         suggestionsData!==snapshot||!snapshot.items.includes(suggestion)||
         !['owner','marketing_manager','content_creator']
            .includes(current.role)||
         quickProposalPending||previewPending||
         calendarData.items.some(row=>row.requestId===suggestion.requestId))
        return {restricted:true};
      const mine=active,version=epoch;
      quickProposalPending=true;
      if(view==='scheduled')show('scheduled');
      try{
        const result=await calendarClient.propose({
          origin,fetchImpl,token:mine.token,
          expectedTenantId:mine.tenantId,
          requestId:suggestion.requestId,
          expectedRevision:suggestion.draftRevision,
          utcAt:suggestion.utcAt,expectedProposalToken:null
        });
        if(version!==epoch||active!==mine)return {stale:true};
        const latest=await refreshPostingPreview();
        if(version!==epoch||active!==mine)return {stale:true};
        if(latest.error||latest.stale||latest.pending)
          return {error:true};
        if(onNotice)onNotice(
          'Draft-only date proposal saved. No post was scheduled or approved.');
        return result;
      }catch(error){
        if(version!==epoch||active!==mine)return {stale:true};
        if(onError)onError(
          'Draft date was not saved; another editor may have used this slot. Refresh and choose again.');
        void refreshPostingPreview();
        return {error:true};
      }finally{
        if(version===epoch&&active===mine){
          quickProposalPending=false;
          if(view==='scheduled')show('scheduled');
        }
      }
    }
    async function refreshReviewReadiness(){
      if(!enableReviewReadiness||!active||!current)return {restricted:true};
      if(reviewPending)return {pending:true};
      const mine=active,version=epoch,request=++reviewRequest;
      reviewPending=true;reviewError=false;
      if(view==='approvals')show('approvals');
      try{
        const data=await reviewClient.read({
          origin,fetchImpl,token:mine.token,
          expectedTenantId:mine.tenantId});
        if(epoch!==version||active!==mine||request!==reviewRequest)
          return {stale:true};
        reviewData=data;
        if(enableReviewFeedback)void refreshReviewFeedback();
        return {stale:false,heldCount:data.heldCount};
      }catch(error){
        if(epoch!==version||active!==mine||request!==reviewRequest)
          return {stale:true};
        reviewData=null;reviewError=true;
        if(onError)onError('Private editorial preparation is unavailable');
        return {error:true};
      }finally{
        if(epoch===version&&active===mine&&request===reviewRequest){
          reviewPending=false;
          if(view==='approvals')show('approvals');
        }
      }
    }

    async function refreshReviewFeedback(){
      if(!enableReviewFeedback||!active||!current||!reviewData)
        return {restricted:true};
      if(feedbackPending)return {pending:true};
      const mine=active,version=epoch,request=++feedbackRequest;
      feedbackPending=true;feedbackError=false;
      if(view==='approvals')show('approvals');
      try{
        const data=await feedbackClient.list({
          origin,fetchImpl,token:mine.token,
          expectedTenantId:mine.tenantId});
        if(epoch!==version||active!==mine||request!==feedbackRequest)
          return {stale:true};
        feedbackData=data;
        return {stale:false,count:data.items.length};
      }catch(error){
        if(epoch!==version||active!==mine||request!==feedbackRequest)
          return {stale:true};
        feedbackData=null;feedbackError=true;
        if(onError)onError('Private editorial feedback is unavailable');
        return {error:true};
      }finally{
        if(epoch===version&&active===mine&&request===feedbackRequest){
          feedbackPending=false;
          if(view==='approvals')show('approvals');
        }
      }
    }
    async function changeReviewFeedback(method,parameters){
      if(!enableReviewFeedback||!active||!current||!reviewData||
         !feedbackData||feedbackPending||feedbackError||feedbackWriting||
         !['owner','marketing_manager'].includes(current.role))
        return {restricted:true};
      const check=reviewData.items.find(row=>
        row.requestId===parameters.requestId);
      const old=feedbackData.items.find(row=>
        row.requestId===parameters.requestId);
      if(!check||((old&&old.feedbackToken)||null)!==
          parameters.expectedFeedbackToken||
         (method==='save'&&check.revision!==parameters.expectedRevision))
        return {stale:true};
      const mine=active,version=epoch;
      feedbackWriting=true;
      if(view==='approvals')show('approvals');
      try{
        const options={origin,fetchImpl,token:mine.token,
          expectedTenantId:mine.tenantId,...parameters};
        const saved=method==='save'
          ?await feedbackClient.save(options)
          :await feedbackClient.discard(options);
        if(epoch!==version||active!==mine)return {stale:true};
        const updated=await refreshReviewFeedback();
        if(epoch!==version||active!==mine)return {stale:true};
        if(updated.error||updated.stale)return updated;
        if(onNotice)onNotice(method==='save'
          ?'Private editorial note saved; nothing was approved or scheduled.'
          :'Editorial note removed; draft remains unpublished.');
        return saved;
      }catch(error){
        if(epoch!==version||active!==mine)return {stale:true};
        if(onError)onError('Review feedback was not changed. Refresh to resolve a stale note or draft.');
        void refreshReviewFeedback();
        return {error:true};
      }finally{
        if(epoch===version&&active===mine){
          feedbackWriting=false;
          if(view==='approvals')show('approvals');
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
            if(id==='approvals'&&enableReviewReadiness)
              void refreshReviewReadiness();
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
                if(enableCalendarProposals&&calendarData&&!calendarError&&
                   ['owner','marketing_manager','content_creator']
                       .includes(current.role)&&!quickProposalPending){
                  const snapshot=suggestionsData;
                  const choose=element(document,'button',
                    'Choose draft-only date (not schedule)');
                  choose.type='button';choose.className='secondary';
                  choose.addEventListener('click',()=>{
                    if(active!==scope||epoch!==scopeEpoch||
                       suggestionsData!==snapshot||previewPending)return;
                    choose.disabled=true;
                    const confirm=element(document,'button',
                      'Confirm this proposed draft date');
                    confirm.type='button';confirm.className='secondary';
                    confirm.addEventListener('click',async()=>{
                      if(active!==scope||epoch!==scopeEpoch||
                         suggestionsData!==snapshot)return;
                      await saveSuggestedDate(suggestion,snapshot);
                    });
                    const cancel=element(document,'button','Cancel date proposal');
                    cancel.type='button';cancel.className='secondary';
                    cancel.addEventListener('click',()=>{
                      if(active===scope&&epoch===scopeEpoch)
                        show('scheduled');
                    });
                    item.append(confirm,cancel);
                  });
                  item.append(choose);
                }
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
          if(enableReviewReadiness){
            const reviewSection=element(document,'section','');
            reviewSection.append(element(document,'h3',
              'Editorial preparation checklist'));
            reviewSection.append(element(document,'p',
              'This is a private content/materials preview. It does not approve, schedule or publish any post.'));
            if(reviewPending){
              reviewSection.append(element(document,'p',
                'Checking draft material and attachment states...'));
            }else if(reviewError||!reviewData){
              reviewSection.append(element(document,'p',
                'Editorial checklist unavailable. Refresh before relying on any review status.'));
            }else{
              reviewSection.append(element(document,'p',
                reviewData.editorialMaterialCompleteCount+' of '+
                reviewData.heldCount+
                ' held drafts have verified required materials for editorial review. None are approved.'));
              for(const check of reviewData.items){
                const item=element(document,'article','');
                const draft=current.drafts.find(x=>x.id===check.requestId);
                item.append(element(document,'strong',
                  draft?draft.channel+' · '+draft.text:
                    check.channel+' · Draft '+check.requestId.slice(0,8)));
                item.append(element(document,'p',
                  check.editorialMaterialComplete?
                    'Required materials verified; editorial and owner review still pending.':
                    'Not yet prepared for editorial review: '+check.status));
                if(check.missingItems.length)
                  item.append(element(document,'p',
                    'Missing: '+check.missingItems.join(', ')));
                if(check.unverifiedItems.length)
                  item.append(element(document,'p',
                    'Not independently verified: '+check.unverifiedItems.join(', ')));
                item.append(element(document,'p',
                  'Still blocked: '+check.blockers.join(', ').replaceAll('_',' ')));
                if(enableReviewFeedback){
                  if(feedbackPending){
                    item.append(element(document,'p','Loading private review notes...'));
                  }else if(feedbackError||!feedbackData){
                    item.append(element(document,'p',
                      'Feedback unavailable. Refresh before editing notes.'));
                  }else{
                    const stored=feedbackData.items.find(entry=>
                      entry.requestId===check.requestId);
                    if(stored){
                      item.append(element(document,'p',
                        'Editorial feedback: '+stored.note));
                      if(stored.stale||stored.draftRevision!==check.revision)
                        item.append(element(document,'p',
                          'This note refers to older draft copy and must be reconsidered.'));
                    }else{
                      item.append(element(document,'p',
                        'No editorial feedback recorded for this draft.'));
                    }
                    if(['owner','marketing_manager'].includes(current.role)){
                      const input=element(document,'textarea','');
                      input.value=stored?stored.note:'';
                      input.maxLength=1000;input.rows=3;
                      input.disabled=feedbackWriting;
                      input.setAttribute&&input.setAttribute(
                        'aria-label','Private editorial note');
                      item.append(input);
                      const save=element(document,'button',
                        stored?'Update private review note':'Add private review note');
                      save.type='button';save.className='secondary';
                      save.disabled=feedbackWriting;
                      save.addEventListener('click',async()=>{
                        if(active!==scope||epoch!==scopeEpoch)return;
                        await changeReviewFeedback('save',{
                          requestId:check.requestId,
                          expectedRevision:check.revision,
                          expectedFeedbackToken:stored?stored.feedbackToken:null,
                          note:input.value});
                      });
                      item.append(save);
                      if(stored){
                        const remove=element(document,'button',
                          'Remove private review note');
                        remove.type='button';remove.className='secondary';
                        remove.disabled=feedbackWriting;
                        remove.addEventListener('click',()=>{
                          if(active!==scope||epoch!==scopeEpoch)return;
                          remove.disabled=true;
                          const confirm=element(document,'button',
                            'Confirm removal of private note');
                          confirm.type='button';confirm.className='secondary';
                          confirm.addEventListener('click',async()=>{
                            if(active!==scope||epoch!==scopeEpoch)return;
                            await changeReviewFeedback('discard',{
                              requestId:check.requestId,
                              expectedFeedbackToken:stored.feedbackToken});
                          });
                          const cancel=element(document,'button',
                            'Cancel removal');
                          cancel.type='button';cancel.className='secondary';
                          cancel.addEventListener('click',()=>{
                            if(active===scope&&epoch===scopeEpoch)show('approvals');
                          });
                          item.append(confirm,cancel);
                        });
                        item.append(remove);
                      }
                    }
                  }
                }
                reviewSection.append(item);
              }
            }
            const refresh=element(document,'button','Refresh editorial checklist');
            refresh.type='button';refresh.className='secondary';
            refresh.disabled=reviewPending;
            refresh.addEventListener('click',()=>{
              if(active===scope&&epoch===scopeEpoch)
                void refreshReviewReadiness();
            });
            reviewSection.append(refresh);
            wrap.append(reviewSection);
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
        connectionRequest++;previewRequest++;reviewRequest++;feedbackRequest++;
        connectionData=null;connectionPending=false;connectionError=false;
        postingPreview=null;previewPending=false;previewError=false;
        calendarData=null;calendarError=false;
        suggestionsData=null;suggestionsError=false;
        quickProposalPending=false;
        reviewData=null;reviewPending=false;reviewError=false;
        feedbackData=null;feedbackPending=false;feedbackError=false;
        feedbackWriting=false;
        current=data;show(view);
        if(view==='connections'&&
           data.cards.connections.availability==='available')
          void refreshConnections();
        if(view==='scheduled')void refreshPostingPreview();
        if(view==='approvals'&&enableReviewReadiness)
          void refreshReviewReadiness();
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
      refreshPostingPreview,refreshReviewReadiness,
       refreshReviewFeedback});
  }
  return Object.freeze({create});
});
