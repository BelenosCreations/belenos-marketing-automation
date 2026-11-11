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
    let connectionData=null,connectionPending=false,connectionError=false;
    let connectionRequest=0;
    function clear(){
      epoch++;requestVersion++;connectionRequest++;
      active=null;current=null;view='home';
      connectionData=null;connectionPending=false;connectionError=false;
      container.replaceChildren();
    }
    function activate({token,tenantId}){
      if(typeof token!=='string'||!token.trim()||token.length>2048||
         typeof tenantId!=='string'||!tenantId.trim()||tenantId.length>128)
        throw new TypeError('Authenticated identity required');
      clear();active={token,tenantId};
    }
    async function refreshConnections(){
      if(!active||!current||
         current.cards.connections.availability!=='available')
        return {restricted:true};
      if(connectionPending)return {pending:true};
      const mine=active,version=epoch,request=++connectionRequest;
      connectionPending=true;connectionError=false;
      if(view==='connections')show('connections');
      try{
        const data=await client.read({kind:'connections',token:mine.token,
          fetchImpl,origin,expectedTenantId:mine.tenantId});
        if(epoch!==version||active!==mine||request!==connectionRequest)
          return {stale:true};
        connectionData=data;
        return {stale:false,count:data.connections.length};
      }catch(error){
        if(epoch!==version||active!==mine||request!==connectionRequest)
          return {stale:true};
        connectionData=null;connectionError=true;
        if(onError)onError('Connection details could not be loaded');
        return {error:true};
      }finally{
        if(epoch===version&&active===mine&&request===connectionRequest){
          connectionPending=false;
          if(view==='connections')show('connections');
        }
      }
    }
    function show(section){
      if(!current)return;
      if(section!=='home'&&!order.includes(section))
        throw new TypeError('Unknown dashboard section');
      view=section;
      const scope=active,scopeEpoch=epoch;
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
          button.addEventListener('click',()=>{
            if(active!==scope||epoch!==scopeEpoch)return;
            show(id);
            if(id==='connections'&&
               current.cards.connections.availability==='available')
              void refreshConnections();
          });
          cards.append(button);
        }
        wrap.append(cards);
      }else{
        const back=element(document,'button','Back to overview');
        back.type='button';
        back.addEventListener('click',()=>{
          if(active===scope&&epoch===scopeEpoch)show('home');
        });
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
            open.addEventListener('click',()=>{
              if(active===scope&&epoch===scopeEpoch)onOpenContentStudio();
            });
            wrap.append(open);
          }
        }else if(section==='scheduled'){
          wrap.append(element(document,'p',
            'Scheduling is not connected. No scheduled posts are verified.'));
        }else if(section==='approvals'){
          wrap.append(element(document,'p',
            'Approval count is shown above. Open Content Studio to review details.'));
        }else if(section==='connections'){
          const state=current.cards.connections.availability;
          if(state!=='available'){
            wrap.append(element(document,'p',
              'Social connection details are restricted for this business role.'));
          }else{
            wrap.append(element(document,'p',
              'Read-only provider status. A connected analytics account does not enable social publishing.'));
            if(connectionPending){
              wrap.append(element(document,'p','Loading account connection status...'));
            }else if(connectionError){
              wrap.append(element(document,'p',
                'Connection status could not be verified. Please refresh.'));
            }else if(connectionData){
              if(!connectionData.connections.length)
                wrap.append(element(document,'p','No analytics account connections configured.'));
              for(const item of connectionData.connections){
                const article=element(document,'article','');
                article.append(element(document,'h3',item.platform+' · '+item.accountId));
                const statuses={
                  connected:'Connected for read-only insights',
                  pending:'Connection setup pending',
                  refresh_required:'Reconnect required',
                  revoked:'Connection revoked',
                  expired:'Connection expired'
                };
                article.append(element(document,'p',statuses[item.status]));
                article.append(element(document,'p','Access scope: '+item.scope));
                const at=new Date(item.updatedAt*1000);
                if(Number.isFinite(at.getTime()))
                  article.append(element(document,'p',
                    'Status checked by BAM registry: '+at.toISOString().slice(0,10)+' UTC'));
                wrap.append(article);
              }
            }else{
              wrap.append(element(document,'p',
                'Select Refresh account statuses to check this business.'));
            }
            const refresh=element(document,'button','Refresh account statuses');
            refresh.type='button';refresh.className='secondary';
            refresh.disabled=connectionPending;
            refresh.addEventListener('click',()=>{
              if(active!==scope||epoch!==scopeEpoch)return;
              void refreshConnections();
            });
            wrap.append(refresh);
          }
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
        connectionRequest++;
        connectionData=null;connectionPending=false;connectionError=false;
        current=data;show(view);
        if(view==='connections'&&
           data.cards.connections.availability==='available')
          void refreshConnections();
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
    return Object.freeze({activate,refresh,clear,show,refreshConnections});
  }
  return Object.freeze({create});
});
