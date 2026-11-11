'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){
  return {tag,textContent:'',children:[],listeners:{},disabled:false,
    append(...nodes){this.children.push(...nodes)},
    replaceChildren(...nodes){this.children=nodes},
    addEventListener(name,fn){this.listeners[name]=fn}};
}
const document={createElement:node};
function dashboard(tenant='shop',role='owner',availability='available'){
  return {schema_version:1,tenant_id:tenant,role,
    businesses:[{tenant_id:tenant,display_name:'Shop'}],
    cards:[
      {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
      {id:'approvals',label:'Approvals',value:0,availability:'available'},
      {id:'content',label:'Content',value:0,availability:'available'},
      {id:'connections',label:'Connections',
        value:availability==='available'?1:null,availability}],
    drafts:[],analytics:{availability:'not_connected',series:null},
    schedule:{availability:'not_connected',posts:null},
    publishing_enabled:false};
}
const connections={tenant_id:'shop',visibility:'authorized',
  connections:[{platform:'facebook',account_id:'shop-page',
    scope:'read_insights',status:'connected',
    updated_at:101,expires_at:900,publishing_enabled:false}],
  publishing_enabled:false};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function main(){
  const container=node('main'),requests=[],errors=[];
  let block=null,release=null,fail=false;
  const fetchImpl=async (url,opts)=>{
    requests.push({url,opts});
    if(url.endsWith('/dashboard'))
      return {ok:true,json:async()=>dashboard()};
    if(url.endsWith('/connections')){
      if(block)await block;
      if(fail)return {ok:false};
      return {ok:true,json:async()=>connections};
    }
    throw new Error('Unexpected URL');
  };
  const app=create({document,container,fetchImpl,
    origin:'https://bam.example',onError:text=>errors.push(text)});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  assert.equal((await app.refresh()).stale,false);
  const oldCard=container.children[0].children[1].children[3];
  oldCard.listeners.click();
  await tick();
  assert.equal(requests.filter(x=>x.url.endsWith('/connections')).length,1);
  assert.equal(requests.at(-1).opts.credentials,'omit');
  assert.equal(requests.at(-1).opts.headers.Authorization,'Bearer '+'a'.repeat(43));
  const section=container.children[0];
  assert.match(section.children[2].textContent,/Read-only provider status/);
  const entry=section.children.find(x=>x.tag==='article');
  assert.ok(entry);
  assert.equal(entry.children[0].textContent,'facebook · shop-page');
  assert.match(entry.children[1].textContent,/read-only insights/);
  assert.equal(entry.children[2].textContent,'Access scope: read_insights');
  assert.equal(section.children.some(x=>/schedule now/i.test(x.textContent)),false);
  fail=true;
  assert.equal((await app.refreshConnections()).error,true);
  assert.match(container.children[0].children[3].textContent,
    /could not be verified/);
  assert.equal(errors.length,1);
  // A detached old card cannot navigate after business-switch / logout.
  app.clear();
  oldCard.listeners.click();
  assert.equal(container.children.length,0);
  app.activate({token:'b'.repeat(43),tenantId:'shop'});
  fail=false;
  block=new Promise(resolve=>{release=resolve});
  await app.refresh();
  const pending=app.refreshConnections();
  await Promise.resolve();
  app.clear();
  release();
  assert.equal((await pending).stale,true);
  assert.equal(container.children.length,0);
  // Restricted connections never cause a detailed provider fetch.
  const restricted=node('main'),restrictedCalls=[];
  const restrictedApp=create({document,container:restricted,origin:'https://bam.example',
    fetchImpl:async(url)=>{
      restrictedCalls.push(url);
      if(url.endsWith('/dashboard'))
        return {ok:true,json:async()=>dashboard('shop','content_creator','restricted')};
      throw new Error('Unauthorized social connection request');
    }});
  restrictedApp.activate({token:'c'.repeat(43),tenantId:'shop'});
  await restrictedApp.refresh();
  restricted.children[0].children[1].children[3].listeners.click();
  await tick();
  assert.equal(restrictedCalls.length,1);
  assert.match(restricted.children[0].children[2].textContent,/restricted/);
  console.log('BAM read-only connected-account drilldown tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
