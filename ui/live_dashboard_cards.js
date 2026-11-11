/* Live-data BAM dashboard: large overview cards with safe drilldowns.
 * No sample analytics, fake scheduling, HTML injection, publishing, or token storage.
 * The signed-in shell supplies a session and handles business switching.
 */
(function(root,factory){
  'use strict';
  if(typeof module==='object'&&module.exports)
    module.exports=factory(require('./dashboard_http_client.js'));
  else root.BAMLiveDashboard=factory(root.BAMReadClient);
})(typeof globalThis!=='undefined'?globalThis:this,function(client){
  'use strict';
  const order=['scheduled','approvals','content','connections'];
  function element(doc,tag,text){
    const item=doc.createElement(tag);
    item.textContent=text;
    return item;
  }
  function create({document,container,fetchImpl,origin,onError,
                   onOpenContentStudio}){
    if(!document||!container||typeof container.replaceChildren!=='function'||
       typeof fetchImpl!=='function'||typeof origin!=='string')
      throw new TypeError('Dashboard dependencies required');
    if(onError!==undefined&&typeof onError!=='function')
      throw new TypeError('Error callback required');
    if(onOpenContentStudio!==undefined&&typeof onOpenContentStudio!=='function')
      throw new TypeError('Content Studio navigation callback required');
    let active=null,epoch=0,requestVersion=0,current=null,view='home';
    function clear(){
      epoch++;requestVersion++;active=null;current=null;view='home';
      container.replaceChildren();
    }
    function activate({token,tenantId}){
      if(typeof token!=='string'||!token.trim()||token.length>2048||
         typeof tenantId!=='string'||!tenantId.trim()||tenantId.length>128)
        throw new TypeError('Authenticated identity required');
      clear();active={token,tenantId};
    }
    function show(section){
      if(!current)return;
      if(section!=='home'&&!order.includes(section))
        throw new TypeError('Unknown dashboard section');
      view=section;
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
          button.addEventListener('click',()=>show(id));
          cards.append(button);
        }
        wrap.append(cards);
      }else{
        const back=element(document,'button','Back to overview');
        back.type='button';
        back.addEventListener('click',()=>show('home'));
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
            open.addEventListener('click',()=>onOpenContentStudio());
            wrap.append(open);
          }
        }else if(section==='scheduled'){
          wrap.append(element(document,'p',
            'Scheduling is not connected. No scheduled posts are verified.'));
        }else if(section==='approvals'){
          wrap.append(element(document,'p',
            'Approval count is shown above. Open Content Studio to review details.'));
        }else{
          wrap.append(element(document,'p',
            'Connected account count is shown above. Open Connections for details.'));
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
        current=data;show(view);
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
    return Object.freeze({activate,refresh,clear,show});
  }
  return Object.freeze({create});
});
