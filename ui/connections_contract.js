/* Only server-scoped, read-only connection metadata. Never provider secrets. */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMConnectionsData=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const states=new Set(['pending','connected','refresh_required','revoked','expired']);
  function exact(value,keys){
    return value&&typeof value==='object'&&!Array.isArray(value)&&
      Object.keys(value).length===keys.length&&
      keys.every(key=>Object.prototype.hasOwnProperty.call(value,key));
  }
  function cleanText(value,max){
    return typeof value==='string'&&value.trim().length>0&&
      value===value.trim()&&value.length<=max;
  }
  function normalize(body){
    if(!exact(body,['tenant_id','visibility','connections','publishing_enabled'])||
       !cleanText(body.tenant_id,128)||body.visibility!=='authorized'||
       !Array.isArray(body.connections)||body.connections.length>250||
       body.publishing_enabled!==false)
      throw new TypeError('Invalid authorized social connection details');
    const found=new Set();
    const connections=body.connections.map(row=>{
      if(!exact(row,['platform','account_id','scope','status','updated_at',
                     'expires_at','publishing_enabled'])||
         !cleanText(row.platform,128)||!cleanText(row.account_id,128)||
         !cleanText(row.scope,128)||/write|publish/i.test(row.scope)||
         !states.has(row.status)||
         !Number.isSafeInteger(row.updated_at)||row.updated_at<0||
         (row.expires_at!==null&&
          (!Number.isSafeInteger(row.expires_at)||row.expires_at<0))||
         row.publishing_enabled!==false)
        throw new TypeError('Invalid read-only provider account');
      const key=row.platform+'\u0000'+row.account_id;
      if(found.has(key))throw new TypeError('Duplicate provider account');
      found.add(key);
      return Object.freeze({platform:row.platform,accountId:row.account_id,
        scope:row.scope,status:row.status,updatedAt:row.updated_at,
        expiresAt:row.expires_at,publishingEnabled:false});
    });
    return Object.freeze({tenantId:body.tenant_id,visibility:'authorized',
      connections:Object.freeze(connections),publishingEnabled:false});
  }
  return Object.freeze({normalize});
});
