/* Read-only OpenAI Settings panel. No raw key fields or mode-changing controls.
 * Place inside Settings, not the primary dashboard.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./ai_settings_contract.js'));
  else root.BAMAISettingsView=factory(root.BAMAISettingsData);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract){
  'use strict';
  function el(doc,tag,value){
    const node=doc.createElement(tag);
    node.textContent=value;
    return node;
  }
  function render({document,container,payload,expectedTenantId,
                   canEdit=false,onSave}){
    if(!document||!container||typeof container.replaceChildren!=='function')
      throw new TypeError('Valid settings mount required');
    if(typeof canEdit!=='boolean'||(canEdit&&typeof onSave!=='function'))
      throw new TypeError('AI preference editing requires explicit permission');
    const model=contract.normalize(payload);
    if(expectedTenantId!==undefined&&model.tenantId!==expectedTenantId)
      throw new TypeError('Unexpected business response');
    const section=el(document,'section','');
    section.className='bam-settings-ai';
    section.append(el(document,'h2','Settings — AI'));
    section.append(el(document,'p','AI provider: OpenAI'));
    section.append(el(document,'p',model.mode==='bam_sponsored'
      ?'AI usage mode: BAM-sponsored'
      :'AI usage mode: Your OpenAI API key'));
    section.append(el(document,'p',model.ownKeyConfigured
      ?'Personal key: configured (hidden)'
      :'Personal key: not configured'));
    section.append(el(document,'h3','Your content preferences'));
    const entries=Object.entries(model.memory);
    if(!entries.length)section.append(el(document,'p','No saved preferences.'));
    for(const [key,value] of entries)
      section.append(el(document,'p',key+': '+value));
    section.append(el(document,'p',canEdit
      ?'Account mode and personal API key remain read-only. Saving writing preferences never publishes content.'
      :'Read-only preview. No publishing enabled.'));
    if(canEdit){
      const panel=el(document,'section','');
      panel.className='bam-ai-memory-editor';
      panel.append(el(document,'h3','Edit your AI writing preferences'));
      panel.append(el(document,'p',
        'Each preference has a label and an instruction. For example: tone = brief and friendly. Empty both fields to remove a preference. Do not enter passwords, API keys or customer details.'));
      const rows=[];
      function addRow(key='',value=''){
        if(rows.length>=40)return;
        const row=el(document,'div','');
        row.className='bam-ai-memory-row';
        const name=el(document,'input','');
        name.type='text';name.value=key;name.maxLength=80;
        const detail=el(document,'input','');
        detail.type='text';detail.value=value;detail.maxLength=2000;
        row.append(name,detail);
        rows.push({name,detail});
        panel.append(row);
      }
      for(const [key,value] of Object.entries(model.memory))
        addRow(key,value);
      if(rows.length===0)addRow();
      const add=el(document,'button','Add writing preference');
      add.type='button';
      add.addEventListener('click',()=>addRow());
      panel.append(add);
      const feedback=el(document,'p','');
      panel.append(feedback);
      const save=el(document,'button','Save AI writing preferences');
      save.type='button';
      save.addEventListener('click',async()=>{
        if(save.disabled)return;
        const updated={};
        for(const {name,detail} of rows){
          const key=name.value.trim(),value=detail.value.trim();
          if(!key&&!value)continue;
          if(!key||!value||key.length>80||value.length>2000||
             Object.prototype.hasOwnProperty.call(updated,key)){
            feedback.textContent='Provide unique, nonempty labels and preference text.';
            return;
          }
          updated[key]=value;
        }
        feedback.textContent='';
        save.disabled=true;
        try{
          await onSave({memory:updated,expectedMemory:{...model.memory}});
        }finally{
          save.disabled=false;
        }
      });
      panel.append(save);
      section.append(panel);
    }
    container.replaceChildren(section);
    return model;
  }
  return Object.freeze({render});
});
