/* Private read-only team summary; no invite links, member IDs or role writes. */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)
   module.exports=factory(require('./dashboard_http_client.js'),
     require('./team_members_client.js'),
     require('./team_invitations_client.js'));
 else root.BAMTeamOverviewWorkspace=factory(root.BAMReadClient,
     root.BAMTeamMembersClient,root.BAMTeamInvitationsClient);
})(typeof globalThis!=='undefined'?globalThis:this,function(reader,membersClient,invitesClient){
 'use strict';
 const labels=[['owner','Owners'],['marketing_manager','Marketing managers'],
   ['content_creator','Content creators'],['employee','Employees'],
   ['viewer','Viewers']];
 function element(doc,tag,text){
   const item=doc.createElement(tag);item.textContent=text;return item;
 }
 function create({document,container,fetchImpl,origin,onError,onNotice,
                  enableMemberManagement=false,
                  enableInvitationPreview=false}){
   if(!document||!container||typeof container.replaceChildren!=='function'||
      typeof fetchImpl!=='function'||typeof origin!=='string')
      throw new TypeError('Team workspace requires DOM and authenticated transport');
   if(typeof enableMemberManagement!=='boolean'||
      typeof enableInvitationPreview!=='boolean')
     throw new TypeError('Explicit team preview switches required');
   if(enableInvitationPreview&&!enableMemberManagement)
     throw new TypeError('Pending invitations require owner team controls');
   let active=null,epoch=0,requestVersion=0,owner=false,summary=null,failed=false;
   let memberData=null,memberError=false,memberPending=false,confirming=null;
   let auditData=null,auditError=false;
   let inviteData=null,inviteError=false,invitePending=false,confirmingInvite=null;
   let inviteHistory=null,inviteHistoryError=false;
   function clear(){
     epoch++;requestVersion++;active=null;owner=false;summary=null;failed=false;
     memberData=null;memberError=false;memberPending=false;confirming=null;
     auditData=null;auditError=false;
     inviteData=null;inviteError=false;invitePending=false;confirmingInvite=null;
     inviteHistory=null;inviteHistoryError=false;
     container.replaceChildren();
   }
   function activate({token,tenantId}){
     if(typeof token!=='string'||!token.trim()||token.length>2048||
        typeof tenantId!=='string'||!tenantId.trim()||tenantId.length>128)
       throw new TypeError('Current BAM business session required');
     clear();active={token,tenantId};
   }
   function setOwner(allowed){
     if(typeof allowed!=='boolean')throw new TypeError('Trusted role required');
     owner=allowed;
     if(!owner){
       requestVersion++;summary=null;failed=false;
       memberData=null;memberError=false;memberPending=false;confirming=null;
       auditData=null;auditError=false;
       inviteData=null;inviteError=false;invitePending=false;confirmingInvite=null;
     inviteHistory=null;inviteHistoryError=false;
     }
     render();
   }
   function render(){
     if(!active)return;
     const section=element(document,'section','');
     section.className='panel stack';
     section.append(element(document,'h2','Team access'));
     if(!owner){
       section.append(element(document,'p',
         'Only the current business owner can view team access counts.'));
     }else if(summary){
       section.append(element(document,'p',
         'Active team members: '+summary.activeMembers));
       section.append(element(document,'p',
         'Inactive memberships: '+summary.inactiveMembers));
       for(const [key,label] of labels)
         section.append(element(document,'p',
           label+': '+summary.roles[key]));
       section.append(element(document,'p',enableInvitationPreview
         ?'Pending invitations can be reviewed and cancelled when a trusted delivery callback is configured. This page cannot send invitations.'
         :'Team invitation previews are not enabled in this development workspace.'));
       section.append(element(document,'p',
         'These counts do not enable invitations, permission changes or publication.')); 
       if(enableMemberManagement){
         const heading=element(document,'h3','Existing business members');
         section.append(heading);
         if(memberError)
           section.append(element(document,'p',
             'Member details unavailable. Refresh before managing access.'));
         else if(!memberData)
           section.append(element(document,'p',
             'The current business roster has not loaded.'));
         else{
           section.append(element(document,'p',
             'Only the business owner can manage existing memberships. Changes sign affected members out of this business; new invitations are not connected.'));
           const mine=active,version=epoch,roster=memberData;
           section.append(element(document,'h3','Recent member changes'));
           if(auditError){
             section.append(element(document,'p',
               'Private team activity could not be checked. Refresh to try again.'));
           }else if(auditData&&auditData.events.length){
             for(const event of auditData.events){
               const who=roster.members.find(x=>x.id===event.memberId);
               const display=who?(who.email||'Member '+who.id.slice(0,8))
                 :'Member '+event.memberId.slice(0,8);
               const description=event.action==='deactivate'
                 ?'Access removed'
                 :'Role changed from '+event.fromRole.replace(/_/g,' ')+
                  ' to '+event.toRole.replace(/_/g,' ');
               const at=new Date(event.changedAt*1000);
               const when=Number.isNaN(at.getTime())
                 ?'Time unavailable':at.toLocaleString();
               section.append(element(document,'p',
                 display+': '+description+' · '+when));
             }
           }else if(auditData){
             section.append(element(document,'p',
               'No recorded team access changes.'));
           }
           if(enableInvitationPreview){
             section.append(element(document,'h3','Pending business invitations'));
             if(inviteError){
               section.append(element(document,'p',
                 'Invitation preview is not configured or is unavailable. No invitation was sent from this page.'));
             }else if(!inviteData){
               section.append(element(document,'p',
                 'Pending invitation details have not loaded.'));
             }else if(!inviteData.items.length){
               section.append(element(document,'p',
                 'No active delivered-callback invitations recorded.'));
             }else{
               const shown=inviteData;
               for(const pending of shown.items){
                 const article=element(document,'article','');
                 article.append(element(document,'strong',pending.email));
                 article.append(element(document,'p',
                   'Requested role: '+pending.role.replace(/_/g,' ')));
                 article.append(element(document,'p',
                   'Expires: '+new Date(pending.expiresAt*1000).toLocaleString()));
                 const cancel=element(document,'button','Cancel invitation');
                 cancel.type='button';cancel.className='secondary';
                 cancel.disabled=invitePending;
                 cancel.addEventListener('click',()=>{
                   if(!owner||active!==mine||epoch!==version||invitePending||
                      inviteData!==shown)return;
                   confirmingInvite=pending;
                   render();
                 });
                 article.append(cancel);
                 if(confirmingInvite===pending){
                   article.append(element(document,'p',
                     'Confirm cancellation. The existing invitation link will no longer be accepted. No email is sent.'));
                   const yes=element(document,'button','Confirm invitation cancellation');
                   yes.type='button';yes.className='primary';
                   yes.disabled=invitePending;
                   yes.addEventListener('click',()=>{
                     if(owner&&active===mine&&epoch===version&&
                        confirmingInvite===pending&&inviteData===shown&&!invitePending)
                       void cancelInvite(pending);
                   });
                   const no=element(document,'button','Keep invitation');
                   no.type='button';no.className='secondary';
                   no.addEventListener('click',()=>{
                     if(owner&&active===mine&&epoch===version&&
                        confirmingInvite===pending){confirmingInvite=null;render();}
                   });
                   article.append(yes,no);
                 }
                 section.append(article);
               }
             }
           }
           if(enableInvitationPreview){
             section.append(element(document,'h3','Recent invitation activity'));
             if(inviteHistoryError){
               section.append(element(document,'p',
                 'Private invitation history unavailable. Refresh to try again.'));
             }else if(!inviteHistory){
               section.append(element(document,'p',
                 'Invitation history has not yet loaded.'));
             }else if(!inviteHistory.events.length){
               section.append(element(document,'p',
                 'No invitation activity has been recorded.'));
             }else{
               const names={
                 delivered:'Invitation handed to trusted delivery',
                 delivery_failed:'Trusted invitation delivery failed',
                 cancelled:'Invitation cancelled',
                 accepted:'Invitation accepted'
               };
               for(const event of inviteHistory.events){
                 const at=new Date(event.occurredAt*1000);
                 const when=Number.isNaN(at.getTime())
                   ?'Time unavailable':at.toLocaleString();
                 section.append(element(document,'p',
                   names[event.action]+' · Invitation '+
                   event.invitationId.slice(0,8)+' · '+when));
               }
             }
           }
           for(const record of roster.members){
             const article=element(document,'article','');
             article.className='content-stack';
             article.append(element(document,'strong',
               record.email||'Member '+record.id.slice(0,8)));
             article.append(element(document,'p',
               'Role: '+record.role.replace(/_/g,' ')+
               ' · '+(record.active?'Active':'Inactive')+
               (record.isSelf?' (your account)':'')));
             if(record.active&&!record.isSelf&&record.role!=='owner'){
               const options=['marketing_manager','content_creator','employee','viewer'];
               const select=element(document,'select','');
               select.setAttribute('aria-label','Role for '+(record.email||record.id));
               for(const value of options){
                 const option=element(document,'option',value.replace(/_/g,' '));
                 option.value=value;select.append(option);
               }
               select.value=record.role;
               const change=element(document,'button','Change role');
               change.type='button';change.className='secondary';
               change.disabled=memberPending;
               change.addEventListener('click',()=>{
                 if(active!==mine||epoch!==version||!owner||memberPending||
                    memberData!==roster)return;
                 if(!options.includes(select.value)||select.value===record.role)return;
                 confirming={memberId:record.id,action:'change_role',
                   role:select.value,expectedRevision:record.revision};
                 render();
               });
               const remove=element(document,'button','Remove access');
               remove.type='button';remove.className='secondary';
               remove.disabled=memberPending;
               remove.addEventListener('click',()=>{
                 if(active!==mine||epoch!==version||!owner||memberPending||
                    memberData!==roster)return;
                 confirming={memberId:record.id,action:'deactivate',
                   expectedRevision:record.revision};
                 render();
               });
               article.append(select,change,remove);
               if(confirming&&confirming.memberId===record.id&&
                  confirming.expectedRevision===record.revision){
                 const planned=confirming;
                 article.append(element(document,'p',
                   planned.action==='deactivate'
                     ?'Confirm removing this member from this business. Existing sessions for this business will be revoked.'
                     :'Confirm changing the role to '+planned.role.replace(/_/g,' ')+
                      '. Existing sessions for this business will be revoked.'));
                 const approve=element(document,'button','Confirm team change');
                 approve.type='button';approve.className='primary';
                 approve.disabled=memberPending;
                 approve.addEventListener('click',()=>{
                   if(active===mine&&epoch===version&&owner&&
                      memberData===roster&&confirming===planned&&!memberPending)
                     void applyChange(planned);
                 });
                 const cancel=element(document,'button','Cancel team change');
                 cancel.type='button';cancel.className='secondary';
                 cancel.addEventListener('click',()=>{
                   if(active===mine&&epoch===version&&confirming===planned){
                     confirming=null;render();
                   }
                 });
                 article.append(approve,cancel);
               }
             }
             section.append(article);
           }
         }
       }
     }else if(failed){
       section.append(element(document,'p',
         'Team access counts unavailable. No member information displayed.'));
     }else{
       section.append(element(document,'p',
         'Team access counts have not yet been loaded.'));
     }
     container.replaceChildren(section);
   }
   async function refresh(){
     if(!active)throw new TypeError('Sign-in required');
     const mine=active,version=epoch,request=++requestVersion;
     if(!owner){summary=null;failed=false;render();return {restricted:true};}
     try{
       const result=await reader.read({kind:'teamOverview',
         token:mine.token,origin,fetchImpl,
         expectedTenantId:mine.tenantId});
       if(epoch!==version||active!==mine||request!==requestVersion||!owner)
         return {stale:true};
       summary=result;failed=false;
       if(enableMemberManagement){
         try{
           const roster=await membersClient.list({
             token:mine.token,origin,fetchImpl,
             expectedTenantId:mine.tenantId});
           if(epoch!==version||active!==mine||request!==requestVersion||!owner)
             return {stale:true};
           memberData=roster;memberError=false;
           if(enableInvitationPreview){
             try{
               const pending=await invitesClient.list({
                 token:mine.token,origin,fetchImpl,
                 expectedTenantId:mine.tenantId});
               if(epoch!==version||active!==mine||request!==requestVersion||!owner)
                 return {stale:true};
               inviteData=pending;inviteError=false;
               try{
                 const audit=await invitesClient.history({
                   token:mine.token,origin,fetchImpl,
                   expectedTenantId:mine.tenantId});
                 if(epoch!==version||active!==mine||
                    request!==requestVersion||!owner)
                   return {stale:true};
                 inviteHistory=audit;inviteHistoryError=false;
               }catch(error){
                 if(epoch!==version||active!==mine||
                    request!==requestVersion||!owner)
                   return {stale:true};
                 inviteHistory=null;inviteHistoryError=true;
                 if(onError)onError('Private invitation activity unavailable');
               }
             }catch(error){
               if(epoch!==version||active!==mine||request!==requestVersion||!owner)
                 return {stale:true};
               inviteData=null;inviteError=true;confirmingInvite=null;
               inviteHistory=null;inviteHistoryError=true;
               if(onError)onError('Private invitation preview unavailable');
             }
           }
           try{
             const activity=await membersClient.activity({
               token:mine.token,origin,fetchImpl,
               expectedTenantId:mine.tenantId});
             if(epoch!==version||active!==mine||request!==requestVersion||!owner)
               return {stale:true};
             auditData=activity;auditError=false;
           }catch(error){
             if(epoch!==version||active!==mine||request!==requestVersion||!owner)
               return {stale:true};
             auditData=null;auditError=true;
             if(onError)onError('Private team access history unavailable');
           }
         }catch(error){
           if(epoch!==version||active!==mine||request!==requestVersion||!owner)
             return {stale:true};
           memberData=null;memberError=true;confirming=null;
           auditData=null;auditError=false;
           inviteData=null;inviteError=false;confirmingInvite=null;
           inviteHistory=null;inviteHistoryError=false;
           if(onError)onError('Private team member details unavailable');
         }
       }
       render();
       return {stale:false,tenantId:result.tenantId,
         activeMembers:result.activeMembers};
     }catch(error){
       if(epoch!==version||active!==mine||request!==requestVersion||!owner)
         return {stale:true};
       summary=null;failed=true;memberData=null;memberError=false;
       confirming=null;auditData=null;auditError=false;
       inviteData=null;inviteError=false;confirmingInvite=null;
       inviteHistory=null;inviteHistoryError=false;render();
       if(onError)onError('Private team access counts unavailable');
       return {error:true};
     }
   }
   async function applyChange(planned){
     if(!active||!owner||!memberData||memberError||memberPending||
        confirming!==planned)return {restricted:true};
     const record=memberData.members.find(x=>x.id===planned.memberId);
     if(!record||!record.active||record.isSelf||
        record.revision!==planned.expectedRevision)
       return {stale:true};
     const mine=active,version=epoch;
     memberPending=true;confirming=null;render();
     try{
       const result=await membersClient.change({
         origin,fetchImpl,token:mine.token,expectedTenantId:mine.tenantId,
         memberId:planned.memberId,action:planned.action,
         expectedRevision:planned.expectedRevision,
         ...(planned.action==='change_role'?{role:planned.role}:{})});
       if(active!==mine||epoch!==version)return {stale:true};
       const current=await refresh();
       if(active!==mine||epoch!==version)return {stale:true};
       if(current.error||current.stale||memberError)return {error:true};
       if(onNotice)onNotice(planned.action==='deactivate'
         ?'Business member access removed. The affected business sessions were revoked.'
         :'Business member role updated. The affected business sessions were revoked.');
       return result;
     }catch(error){
       if(active!==mine||epoch!==version)return {stale:true};
       try{await refresh();}catch(readError){memberData=null;memberError=true;}
       if(active!==mine||epoch!==version)return {stale:true};
       if(onError)onError('Team change was not confirmed. Current membership was reloaded.');
       return {error:true};
     }finally{
       if(active===mine&&epoch===version){memberPending=false;render();}
     }
   }
   async function cancelInvite(pending){
     if(!owner||!active||!inviteData||inviteError||invitePending||
        confirmingInvite!==pending||!inviteData.items.includes(pending))
       return {restricted:true};
     const mine=active,version=epoch;
     invitePending=true;confirmingInvite=null;render();
     try{
       const cancelled=await invitesClient.cancel({
         origin,fetchImpl,token:mine.token,
         expectedTenantId:mine.tenantId,invitationId:pending.id});
       if(active!==mine||epoch!==version)return {stale:true};
       const latest=await refresh();
       if(active!==mine||epoch!==version)return {stale:true};
       if(latest.error||latest.stale||inviteError)return {error:true};
       if(onNotice)onNotice('Pending invitation cancelled; no email was sent.');
       return cancelled;
     }catch(error){
       if(active!==mine||epoch!==version)return {stale:true};
       try{await refresh();}catch(readError){inviteData=null;inviteError=true;}
       if(active!==mine||epoch!==version)return {stale:true};
       if(onError)onError('Cancellation not confirmed. Invitations were reloaded.');
       return {error:true};
     }finally{
       if(active===mine&&epoch===version){invitePending=false;render();}
     }
   }
   return Object.freeze({activate,setOwner,clear,refresh});
 }
 return Object.freeze({create});
});
