/* Optional manual ChatGPT image handoff for held BAM drafts.
 * No OpenAI API key, automated ChatGPT login, media generation or upload.
 * Opening ChatGPT and copying the prompt are separate user actions.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)module.exports=factory();
  else root.BAMManualImageHandoff=factory();
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';
  const CHATGPT_URL='https://chatgpt.com/';
  function element(doc,tag,label){
    const n=doc.createElement(tag);
    n.textContent=label;
    return n;
  }
  function render({document,container,imagePrompt,copyText,openUrl,
                   needsMedia=true}){
    if(!document||!container||typeof container.replaceChildren!=='function'||
       typeof copyText!=='function'||typeof openUrl!=='function'||
       typePrompt(imagePrompt)===false||needsMedia!==true)
      throw new TypeError('Verified manual image handoff required');
    const wrap=element(document,'section','');
    wrap.append(element(document,'h3','Create your image in ChatGPT'));
    wrap.append(element(document,'p',
      'This is optional and manual. Copy the image brief, open your own ChatGPT account, create and revise the image there, then return to BAM to upload it for verification.'));
    const prompt=element(document,'p',imagePrompt);
    wrap.append(prompt);
    const copy=element(document,'button','Copy image prompt');
    copy.type='button';
    copy.addEventListener('click',()=>copyText(imagePrompt));
    const open=element(document,'button','Open ChatGPT');
    open.type='button';
    open.addEventListener('click',()=>openUrl(CHATGPT_URL));
    wrap.append(copy,open);
    wrap.append(element(document,'p',
      'Media still required. BAM will not silently schedule or publish without the verified image.'));
    container.replaceChildren(wrap);
    return {mediaNeeded:true,publishingEnabled:false};
  }
  function typePrompt(value){
    return typeof value==='string'&&!!value.trim()&&value.length<=2000;
  }
  return Object.freeze({render,CHATGPT_URL});
});
