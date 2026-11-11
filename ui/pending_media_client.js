/* Explicit manual image return: upload bytes only into private PENDING review.
 * No media verification, scheduling, approval or publishing.
 */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMPendingMediaClient=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const token=/^[A-Za-z0-9_-]{32,2048}$/;
 const id=/^[a-f0-9]{32}$/, sha=/^[a-f0-9]{64}$/;
 const mime=new Set(['image/png','image/jpeg','image/webp']);
 function record(x){return x&&typeof x==='object'&&!Array.isArray(x)}
 async function stage({origin,fetchImpl,token:bearer,expectedTenantId,
                       requestId,item,file,hashBytes}){
   if(typeof origin!=='string'||
      !/^https:\/\/[A-Za-z0-9.-]+(?::[0-9]{1,5})?$/.test(origin)||
      typeof fetchImpl!=='function'||!token.test(bearer)||
      typeof expectedTenantId!=='string'||!expectedTenantId.trim()||
      expectedTenantId.length>128||!id.test(requestId)||
      typeof item!=='string'||!item.trim()||item.length>80||
      !file||!mime.has(file.type)||!Number.isSafeInteger(file.size)||
      file.size<1||file.size>20*1024*1024||
      typeof file.arrayBuffer!=='function'||typeof hashBytes!=='function')
     throw new TypeError('Authenticated pending image required');
   const content=await file.arrayBuffer();
   if(!(content instanceof ArrayBuffer)||content.byteLength!==file.size)
     throw new TypeError('Invalid selected file bytes');
   const digest=await hashBytes(content);
   if(typeof digest!=='string'||!sha.test(digest))
     throw new TypeError('Invalid image digest');
   const authorization={'Authorization':'Bearer '+bearer};
   const first=await fetchImpl(origin+'/api/v1/content/upload-preflight',{
     method:'POST',mode:'same-origin',credentials:'omit',cache:'no-store',
     redirect:'error',
     headers:{...authorization,'Content-Type':'application/json',Accept:'application/json'},
     body:JSON.stringify({request_id:requestId,item,media_type:file.type,
       sha256:digest,byte_count:file.size})
   });
   if(!first||!first.ok||first.status!==202)
     throw new Error('Private image preflight unavailable');
   const intent=await first.json();
   if(!record(intent)||
      Object.keys(intent).some(k=>!['tenant_id','request_id','item',
        'attachment_id','status','max_bytes','upload_url',
        'publishing_enabled'].includes(k))||
      intent.tenant_id!==expectedTenantId||intent.request_id!==requestId||
      intent.item!==item||!id.test(intent.attachment_id)||
      intent.status!=='pending'||intent.upload_url!==null||
      intent.publishing_enabled!==false||
      !Number.isSafeInteger(intent.max_bytes)||
      intent.max_bytes<file.size||intent.max_bytes>250*1024*1024)
     throw new TypeError('Untrusted pending upload intent');
   const second=await fetchImpl(origin+'/api/v1/content/media-bytes',{
     method:'PUT',mode:'same-origin',credentials:'omit',cache:'no-store',
     redirect:'error',
     headers:{...authorization,'Content-Type':file.type,
       'X-BAM-Attachment-ID':intent.attachment_id,Accept:'application/json'},
     body:new Uint8Array(content)
   });
   if(!second||!second.ok||second.status!==202)
     throw new Error('Private image receipt unavailable');
   const result=await second.json();
   if(!record(result)||
      Object.keys(result).some(k=>!['tenant_id','attachment_id','status',
        'bytes_received','media_verified','publishing_enabled'].includes(k))||
      result.tenant_id!==expectedTenantId||
      result.attachment_id!==intent.attachment_id||
      result.status!=='pending_scan'||result.bytes_received!==file.size||
      result.media_verified!==false||result.publishing_enabled!==false)
     throw new TypeError('Untrusted image receipt');
   return Object.freeze({tenantId:result.tenant_id,
     attachmentId:result.attachment_id,status:'pending_scan',
     mediaVerified:false,publishingEnabled:false});
 }
 return Object.freeze({stage});
});
