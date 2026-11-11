'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {mount}=require('./bam_signed_in_shell.js');

function node(tag='div'){
  return {tag,textContent:'',children:[],listeners:{},dataset:{},
    hidden:false,disabled:false,value:'',
    attributes:{},
    append(...items){this.children.push(...items)},
    replaceChildren(...items){this.children=items},
    addEventListener(name,fn){this.listeners[name]=fn},
    setAttribute(name,value){this.attributes[name]=value},
    removeAttribute(name){delete this.attributes[name]}};
}
function fixture(){
  const ids=['sign-in-view','workspace-view','notice','login-form',
    'sign-in-button','logout','refresh','active-business',
    'overview-panel','drafts-panel','settings-panel',
    'email','password','business','appearance',
    'bam-dashboard','bam-ai-drafts','bam-ai-settings','bam-ai-facts','bam-ai-cost'];
  const elements=Object.fromEntries(ids.map(id=>[id,node()]));
  const nav=['overview','drafts','settings'].map(panel=>{
    const button=node('button');button.dataset.bamPanel=panel;return button});
  const document={
    documentElement:{dataset:{}},createElement:node,
    getElementById:id=>elements[id]||null,
    querySelectorAll:selector=>
      selector==='[data-bam-panel]'?nav:[]
  };
  return {elements,nav,document};
}
const data={
  dashboard:{schema_version:1,tenant_id:'shop',
    businesses:[{tenant_id:'shop',display_name:'Example Shop'}],
    cards:[
      {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
      {id:'approvals',label:'Approvals',value:0,availability:'available'},
      {id:'content',label:'Content',value:0,availability:'available'},
      {id:'connections',label:'Connections',value:0,availability:'available'}],
    drafts:[],analytics:{availability:'not_connected',series:null},
    schedule:{availability:'not_connected',posts:null},
    publishing_enabled:false},
  'ai-drafts':{tenant_id:'shop',drafts:[],publishing_enabled:false},
  'ai-settings':{tenant_id:'shop',provider:'openai',mode:'bam_sponsored',
    own_key_configured:false,memory:{},key_exposed:false,
    publishing_enabled:false},
  'ai-business-facts':{tenant_id:'shop',facts:{name:'Example Shop'},
    revision:1,provenance:'owner_confirmed',confirmed_at:100,
    publishing_enabled:false},
  'ai-cost-summary':{tenant_id:'shop',events:0,input_tokens:0,
    output_tokens:0,estimated_micro_usd:0,
    pricing_basis:'operator_configured',
    actual_billing_verified:false,publishing_enabled:false}
};
async function main(){
  const html=fs.readFileSync(path.join(__dirname,'bam_signed_in_shell.html'),'utf8');
  assert.match(html,/id="login-form"/);
  assert.match(html,/id="bam-dashboard"/);
  assert.match(html,/data-bam-panel="settings"/);
  assert.match(html,/src="\.\.\/branding\/source\/app_icon\.svg"/);
  assert.doesNotMatch(html,/class="mark"[^>]*>B<\/span>/);
  for(const script of ['dashboard_http_client.js',
      'authenticated_workspace_controller.js','authenticated_session_controller.js',
      'bam_signed_in_shell.js'])
    assert.ok(html.includes('src="'+script+'"'),script);
  assert.ok(!html.includes('localStorage'));
  const f=fixture(),e=f.elements;
  const opened=[],clipboard=[],requests=[];
  const window={navigator:{clipboard:{
    writeText:async text=>clipboard.push(text)}},
    open:(...args)=>opened.push(args)};
  const fetchImpl=async(url,opts)=>{
    requests.push({url,opts});
    const kind=url.split('/').pop();
    if(kind==='password')return {ok:true,json:async()=>({
      session_token:'a'.repeat(43),publishing_enabled:false})};
    if(kind==='logout')return {ok:true,json:async()=>({
      signed_out:true,publishing_enabled:false})};
    if(Object.prototype.hasOwnProperty.call(data,kind))
      return {ok:true,json:async()=>data[kind]};
    throw new Error('Unexpected request '+url);
  };
  const shell=mount({document:f.document,window,
    origin:'https://bam.example',fetchImpl});
  assert.equal(shell.ready,true);
  assert.equal(e['workspace-view'].hidden,true);
  e.email.value='owner@example.com';
  e.password.value='correct horse battery staple';
  e.business.value='shop';
  await e['login-form'].listeners.submit({preventDefault(){}});
  assert.equal(e.password.value,'');
  assert.equal(e['sign-in-view'].hidden,true);
  assert.equal(e['workspace-view'].hidden,false);
  assert.equal(e['bam-dashboard'].children.length,1);
  assert.equal(e['bam-dashboard'].children[0].children[1].children.length,4);
  assert.equal(e['active-business'].textContent,'Business: shop');
  assert.equal(requests[0].opts.credentials,'omit');
  f.nav[2].listeners.click();
  assert.equal(e['settings-panel'].hidden,false);
  assert.equal(e['overview-panel'].hidden,true);
  e.appearance.listeners.change({target:{value:'light'}});
  assert.equal(f.document.documentElement.dataset.theme,'light');
  await e.refresh.listeners.click();
  assert.match(e.notice.textContent,/refreshed/);
  await e.logout.listeners.click();
  assert.equal(e['workspace-view'].hidden,true);
  assert.equal(e['sign-in-view'].hidden,false);
  assert.equal(e['bam-dashboard'].children.length,0);
  assert.equal(e['bam-ai-facts'].children.length,0);
  assert.equal(requests.at(-1).opts.headers.Authorization,
    'Bearer '+'a'.repeat(43));
  const insecure=fixture();
  const result=mount({document:insecure.document,window,
    origin:'file:///',fetchImpl});
  assert.equal(result.ready,false);
  assert.equal(insecure.elements['sign-in-button'].disabled,true);
  assert.match(insecure.elements.notice.textContent,/HTTPS/);
  assert.equal(opened.length,0);
  assert.equal(clipboard.length,0);
  console.log('BAM signed-in HTML shell integration smoke tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
