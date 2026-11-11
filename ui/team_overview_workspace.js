/* Private read-only team summary; no invite links, member IDs or role writes. */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)
   module.exports=factory(require('./dashboard_http_client.js'));
 else root.BAMTeamOverviewWorkspace=factory(root.BAMReadClient);
})(typeof globalThis!=='undefined'?globalThis:this,function(reader){
 'use strict';
 const labels=[['owner','Owners'],['marketing_manager','Marketing managers'],
   ['content_creator','Content creators'],['employee','Employees'],
   ['viewer','Viewers']];
 function element(doc,tag,text){
   const item=doc.createElement(tag);item.textContent=text;return item;
 }
 function create({document,container,fetchImpl,origin,onError}){
   if(!document||!container||typeof container.replaceChildren!=='function'||
      typeof fetchImpl!=='function'||typeof origin!=='string')
      throw new TypeError('Team workspace requires DOM and authenticated transport');
   let active=null,epoch=0,requestVersion=0,owner=false,summary=null,failed=false;
   function clear(){
     epoch++;requestVersion++;active=null;owner=false;summary=null;failed=false;
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
     if(!owner){requestVersion++;summary=null;failed=false;}
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
       section.append(element(document,'p',
         'Team invitations are not connected in this development preview.'));
       section.append(element(document,'p',
         'These counts do not enable invitations, permission changes or publication.'));
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
       summary=result;failed=false;render();
       return {stale:false,tenantId:result.tenantId,
         activeMembers:result.activeMembers};
     }catch(error){
       if(epoch!==version||active!==mine||request!==requestVersion||!owner)
         return {stale:true};
       summary=null;failed=true;render();
       if(onError)onError('Private team access counts unavailable');
       return {error:true};
     }
   }
   return Object.freeze({activate,setOwner,clear,refresh});
 }
 return Object.freeze({create});
});
