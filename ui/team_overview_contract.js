/* Owner-only, aggregate BAM membership status. No personal identifiers. */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMTeamOverviewData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const roles=['owner','marketing_manager','content_creator','employee','viewer'];
 function exact(value,keys){
   return value&&typeof value==='object'&&!Array.isArray(value)&&
     Object.keys(value).length===keys.length&&
     keys.every(k=>Object.prototype.hasOwnProperty.call(value,k));
 }
 function normalize(body){
   if(!exact(body,['tenant_id','roles','active_members',
      'inactive_members','invitation_status','publishing_enabled'])||
      typeof body.tenant_id!=='string'||!body.tenant_id.trim()||
      body.tenant_id.length>128||
      !exact(body.roles,roles)||
      !Number.isSafeInteger(body.active_members)||body.active_members<1||
      !Number.isSafeInteger(body.inactive_members)||body.inactive_members<0||
      body.invitation_status!=='not_connected'||
      body.publishing_enabled!==false)
     throw new TypeError('Untrusted team overview');
   let count=0;
   for(const role of roles){
     const n=body.roles[role];
     if(!Number.isSafeInteger(n)||n<0||n>100000)
       throw new TypeError('Untrusted team role total');
     count+=n;
   }
   if(body.roles.owner<1||count!==body.active_members||
      count>100000||body.inactive_members>100000)
     throw new TypeError('Mismatched team totals');
   return Object.freeze({tenantId:body.tenant_id,
     roles:Object.freeze({...body.roles}),
     activeMembers:count,inactiveMembers:body.inactive_members,
     invitationStatus:'not_connected',publishingEnabled:false});
 }
 return Object.freeze({normalize});
});
