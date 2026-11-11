/* Owner-confirmed business facts editor for nested AI Settings.
 * Explicit Save only; never guesses business facts or writes automatically.
 * Backend must independently authorize the owner and enforce revision checks.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./ai_facts_contract.js'));
  else root.BAMAIFactsEditor=factory(root.BAMAIFactsData);
})(typeof globalThis!=='undefined'?globalThis:this,function(contract){
  'use strict';
  function el(doc,tag,label){
    const node=doc.createElement(tag);
    node.textContent=label;
    return node;
  }
  function render({document,container,payload,expectedTenantId,
                   canManage,onSave}){
    if(!document||!container||typeof container.replaceChildren!=='function'||
       typeof canManage!=='boolean'||
       (canManage&&typeof onSave!=='function'))
      throw new TypeError('Authorized facts editor dependencies required');
    const data=contract.normalize(payload);
    if(data.tenantId!==expectedTenantId)
      throw new TypeError('Unexpected business response');
    const wrapper=el(document,'section','');
    wrapper.append(el(document,'h3','Business facts for AI drafts'));
    wrapper.append(el(document,'p',
      'Only confirm facts you know are accurate. AI drafts remain subject to review.'));
    if(!canManage){
      wrapper.append(el(document,'p',
        'Only a business owner can confirm these facts.'));
      container.replaceChildren(wrapper);
      return {editable:false,publishingEnabled:false};
    }
    const rows=el(document,'div','');
    function addRow(key='',value=''){
      const row=el(document,'div','');
      const k=el(document,'input','');
      k.value=key;k.placeholder='Fact name';
      const v=el(document,'input','');
      v.value=value;v.placeholder='Confirmed fact';
      row.append(k,v);
      rows.append(row);
    }
    for(const [key,value] of Object.entries(data.facts))
      addRow(key,value);
    if(!Object.keys(data.facts).length)addRow();
    const add=el(document,'button','Add fact');
    add.type='button';
    add.addEventListener('click',()=>{
      if(rows.children.length<40)addRow();
    });
    const save=el(document,'button','Confirm and save facts');
    save.type='button';
    save.addEventListener('click',()=>{
      const facts={};
      for(const row of rows.children){
        const key=row.children[0].value.trim();
        const value=row.children[1].value.trim();
        if(!key||!value||key.length>80||value.length>500||
           Object.prototype.hasOwnProperty.call(facts,key))
          throw new TypeError('Complete unique fact names and values required');
        facts[key]=value;
      }
      if(!Object.keys(facts).length||Object.keys(facts).length>40)
        throw new TypeError('At least one confirmed fact required');
      return onSave({facts,expectedRevision:data.revision,
        expectedTenantId:data.tenantId});
    });
    wrapper.append(rows,add,save);
    wrapper.append(el(document,'p',
      'Saving records owner confirmation, not independent verification or permission to publish.'));
    container.replaceChildren(wrapper);
    return {editable:true,publishingEnabled:false};
  }
  return Object.freeze({render});
});
