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
    'business-switch','business-switch-label',
    'overview-panel','drafts-panel','content-panel','settings-panel',
    'email','password','business','appearance',
    'bam-posting-preferences','bam-content-studio','bam-dashboard','bam-ai-drafts','bam-ai-settings','bam-ai-facts','bam-ai-cost'];
  const elements=Object.fromEntries(ids.map(id=>[id,node()]));
  const nav=['overview','drafts','content','settings'].map(panel=>{
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
    businesses:[{tenant_id:'shop',display_name:'Example Shop'},
      {tenant_id:'other',display_name:'Second Service'}],
    cards:[
      {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
      {id:'approvals',label:'Approvals',value:0,availability:'available'},
      {id:'content',label:'Content',value:0,availability:'available'},
      {id:'connections',label:'Connections',value:0,availability:'available'}],
    drafts:[],analytics:{availability:'not_connected',series:null},
    schedule:{availability:'not_connected',posts:null},
    publishing_enabled:false},
  drafts:{tenant_id:'shop',publishing_enabled:false,drafts:[]},
  'posting-preferences':{tenant_id:'shop',mode:'smart',timezone:null,
    manual_times:[],configured:false,publishing_enabled:false},
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
  assert.match(html,/id="business-switch"/);
  assert.match(html,/data-bam-panel="settings"/);
  assert.match(html,/src="\.\.\/branding\/source\/app_icon\.svg"/);
  assert.doesNotMatch(html,/class="mark"[^>]*>B<\/span>/);
  for(const script of ['dashboard_http_client.js',
      'authenticated_workspace_controller.js','authenticated_session_controller.js',
      'business_switch_client.js',
      'bam_signed_in_shell.js'])
    assert.ok(html.includes('src="'+script+'"'),script);
  assert.ok(!html.includes('localStorage'));
  const f=fixture(),e=f.elements;
  const opened=[],clipboard=[],requests=[];
  let currentTenant='shop';
  const holds={shop:[],other:[]};
  const window={navigator:{clipboard:{
    writeText:async text=>clipboard.push(text)}},
    open:(...args)=>opened.push(args)};
  const fetchImpl=async(url,opts)=>{
    requests.push({url,opts});
    const kind=url.split('/').pop();
    if(kind==='password')return {ok:true,json:async()=>({
      session_token:'a'.repeat(43),publishing_enabled:false})};
    if(kind==='activate'){
      currentTenant=JSON.parse(opts.body).target_tenant_id;
      return {ok:true,json:async()=>({tenant_id:currentTenant,
        session_token:'s'.repeat(43),publishing_enabled:false})};
    }
    if(url.endsWith('/content/drafts')&&opts.method==='POST'){
      const item=JSON.parse(opts.body);
      holds[currentTenant].push({request_id:'b'.repeat(32),
        channel:item.channel,draft_text:item.draft_text,
        suggestion:item.suggestion,missing_items:item.required_items,
        status:'needs_content',priority:0});
      return {ok:true,json:async()=>({tenant_id:currentTenant,
        request_id:'b'.repeat(32),status:'needs_content',
        publishing_enabled:false})};
    }
    if(url.endsWith('/content/hold')&&opts.method==='POST'){
      const change=JSON.parse(opts.body);
      const item=holds[currentTenant].find(x=>x.request_id===change.request_id);
      if(!item)throw new Error('Unrecognized held draft');
      item.status=change.status;
      return {ok:true,json:async()=>({tenant_id:currentTenant,
        request_id:item.request_id,status:item.status,
        publishing_enabled:false})};
    }
    if(kind==='posting-preferences'&&opts.method==='PUT'){
      const payload=JSON.parse(opts.body);
      data['posting-preferences']={tenant_id:currentTenant,
        mode:payload.mode,timezone:payload.timezone,
        manual_times:payload.manual_times,configured:true,
        publishing_enabled:false};
      return {ok:true,json:async()=>data['posting-preferences']};
    }
    if(kind==='logout')return {ok:true,json:async()=>({
      signed_out:true,publishing_enabled:false})};
    if(Object.prototype.hasOwnProperty.call(data,kind))
      return {ok:true,json:async()=>({
        ...data[kind],tenant_id:currentTenant,
        ...(kind==='drafts'?{drafts:holds[currentTenant]}:{})})};
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
  assert.equal(e['bam-content-studio'].children.length,1);
  assert.equal(e['bam-posting-preferences'].children.length,1);
  assert.equal(e['bam-dashboard'].children[0].children[1].children.length,4);
  assert.equal(e['active-business'].textContent,'Business: shop');
  // The Content Studio is an explicit, unpublished, tenant-scoped write UI.
  const heldForm=e['bam-content-studio'].children[0].children[2];
  heldForm.children[2].children[1].value='New product preview';
  heldForm.children[3].children[1].value='Use a confirmed product photograph';
  await heldForm.listeners.submit({preventDefault(){}});
  assert.equal(holds.shop.length,1);
  assert.equal(holds.shop[0].status,'needs_content');
  assert.equal(holds.shop[0].draft_text,'New product preview');
  const heldArticle=e['bam-content-studio'].children[0].children[3].children[1];
  const holdButton=heldArticle.children.find(x=>x.textContent==='Postpone');
  assert.ok(holdButton);
  await holdButton.listeners.click();
  assert.equal(holds.shop[0].status,'postponed');
  assert.equal(e['business-switch'].children.length,2);
  assert.equal(e['business-switch'].hidden,false);
  assert.equal(requests[0].opts.credentials,'omit');
  f.nav[3].listeners.click();
  assert.equal(e['settings-panel'].hidden,false);
  const prefForm=e['bam-posting-preferences'].children[0].children[3];
  prefForm.children[0].children[1].value='manual';
  prefForm.children[1].children[1].value='America/New_York';
  prefForm.children[2].children[1].value='10:00, 18:30';
  await prefForm.listeners.submit({preventDefault(){}});
  assert.equal(data['posting-preferences'].mode,'manual');
  assert.deepEqual(data['posting-preferences'].manual_times,['10:00','18:30']);
  assert.equal(e['overview-panel'].hidden,true);
  e.appearance.listeners.change({target:{value:'light'}});
  assert.equal(f.document.documentElement.dataset.theme,'light');
  await e.refresh.listeners.click();
  assert.match(e.notice.textContent,/refreshed/);
  e['business-switch'].value='other';
  await e['business-switch'].listeners.change();
  assert.equal(e['active-business'].textContent,'Business: other');
  assert.equal(holds.other.length,0);
  assert.equal(e['bam-content-studio'].children[0].children[3].children.length,1);
  assert.equal(e['bam-dashboard'].children.length,1);
  const switching=requests.find(r=>r.url.endsWith('/businesses/activate'));
  assert.ok(switching);
  assert.equal(switching.opts.headers.Authorization,'Bearer '+'a'.repeat(43));
  assert.deepEqual(JSON.parse(switching.opts.body),{target_tenant_id:'other'});
  await e.logout.listeners.click();
  assert.equal(e['workspace-view'].hidden,true);
  assert.equal(e['sign-in-view'].hidden,false);
  assert.equal(e['bam-dashboard'].children.length,0);
  assert.equal(e['bam-ai-facts'].children.length,0);
  assert.equal(requests.at(-1).opts.headers.Authorization,
    'Bearer '+'s'.repeat(43));
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
