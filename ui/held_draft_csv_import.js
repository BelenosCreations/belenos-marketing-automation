/* Strict browser-only bulk held-draft CSV parser.
 * CSV contents never leave the browser except through explicit individual
 * authorized, unpublished draft-create requests after user confirmation.
 */
(function(root,factory){
 'use strict';
 if(typeof module==='object'&&module.exports)module.exports=factory();
 else root.BAMHeldDraftCSVImport=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 'use strict';
 const channels=new Set(['facebook','instagram','linkedin',
   'pinterest','tiktok','youtube']);
 const HEADERS=['channel','draft_text','suggestion','required_items'];
 function table(raw){
   if(typeof raw!=='string'||!raw.trim()||raw.length>131072)
     throw new TypeError('CSV text required, maximum 128 KiB');
   const rows=[];
   let row=[],field='',quoted=false,after=false;
   const flush=()=>{row.push(field);field='';after=false;};
   const end=()=>{flush();rows.push(row);row=[];};
   for(let i=0;i<raw.length;i++){
     const ch=raw[i];
     if(quoted){
       if(ch==='"'){
         if(raw[i+1]==='"'){field+='"';i++;}
         else{quoted=false;after=true;}
       }else field+=ch;
     }else if(ch==='"'){
       if(after||field!=='')throw new TypeError('Unexpected CSV quote');
       quoted=true;
     }else if(after&&ch!==' '&&ch!=='\t'&&ch!==','&&ch!=='\r'&&ch!=='\n'){
       throw new TypeError('Unexpected text after quoted CSV field');
     }else if(ch===','){
       flush();
     }else if(ch==='\r'||ch==='\n'){
       end();
       if(ch==='\r'&&raw[i+1]==='\n')i++;
     }else if(!after){
       field+=ch;
     }
     if(rows.length>21||row.length>4||field.length>6000)
       throw new TypeError('CSV size or row limit exceeded');
   }
   if(quoted)throw new TypeError('Unclosed CSV quote');
   if(row.length||field||after)end();
   return rows;
 }
 function parse(raw){
   const rows=table(raw.replace(/^\uFEFF/,''));
   if(rows.length<2||rows.length>21||
      rows[0].length!==HEADERS.length||
      !HEADERS.every((name,i)=>rows[0][i]===name))
     throw new TypeError('CSV header and 1-20 draft rows required');
   const seen=new Set();
   const drafts=rows.slice(1).map((row,index)=>{
     if(row.length!==4)
       throw new TypeError('Invalid CSV column count at row '+(index+2));
     const [channel,post,tip,needs]=row.map(s=>s.trim());
     const required=needs?needs.split('|').map(s=>s.trim()):['image'];
     if(!channels.has(channel)||!post||post.length>2000||
        !tip||tip.length>2000||required.length>12||
        required.some(x=>!x||x.length>80)||
        new Set(required).size!==required.length)
       throw new TypeError('Invalid unpublished draft at row '+(index+2));
     const key=channel+'\u0000'+post.toLowerCase().replace(/\s+/g,' ');
     if(seen.has(key))
       throw new TypeError('Repeated draft copy in CSV import');
     seen.add(key);
     return Object.freeze({channel,draftText:post,suggestion:tip,
       requiredItems:Object.freeze(required),priority:0});
   });
   return Object.freeze(drafts);
 }
 return Object.freeze({parse});
});
