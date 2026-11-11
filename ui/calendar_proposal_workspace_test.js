'use strict';
const assert=require('node:assert/strict');
const {create}=require('./held_draft_workspace.js');
function node(tag){return {tag,children:[],textContent:'',className:'',
  disabled:false,value:'',listeners:{},
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items},
  addEventListener(name,fn){this.listeners[name]=fn}}}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),utc='2026-11-11T15:00:00+00:00';
let proposal=null,tenant='shop';
const calls=[],notices=[],errors=[];
const fetchImpl=async(url,options)=>{
  calls.push({url,options});
  if(url.endsWith('/drafts')&&options.method==='GET')
    return {ok:true,json:async()=>({
      tenant_id:tenant,publishing_enabled:false,drafts:[{
        request_id:rid,channel:'facebook',
        draft_text:'Custom tumbler',suggestion:'Need image review',
        missing_items:['image'],priority:0,
        status:'needs_content',revision:1}]})};
  if(url.endsWith('/posting-time-preview'))
    return {ok:true,json:async()=>({
      tenant_id:tenant,mode:'manual',timezone:'America/New_York',
      status:'manual_preview',slots:[{
        local_date:'2026-11-11',local_time:'10:00',utc_at:utc}],
      skipped_dst:0,truncated:false,publishing_enabled:false})};
  if(url.endsWith('/calendar-proposals')){
    if(options.method==='GET')
      return {ok:true,status:200,json:async()=>({
        tenant_id:'shop',status:'proposal_only',posts_scheduled:0,
        publishing_enabled:false,items:proposal?[proposal]:[]})};
    if(options.method==='POST'){
      const request=JSON.parse(options.body);
      assert.deepEqual(request,{
        request_id:rid,expected_revision:1,utc_at:utc});
      proposal={request_id:rid,draft_revision:1,current_revision:1,
        utc_at:utc,local_date:'2026-11-11',local_time:'10:00',
        timezone:'America/New_York',content_changed:false,
        slot_current:true,publishing_enabled:false};
      return {ok:true,status:201,json:async()=>({
        tenant_id:'shop',request_id:rid,utc_at:utc,status:'proposal_only',
        posts_scheduled:0,publishing_enabled:false})};
    }
    if(options.method==='DELETE'){
      assert.deepEqual(JSON.parse(options.body),{request_id:rid});
      proposal=null;
      return {ok:true,status:200,json:async()=>({
        tenant_id:'shop',request_id:rid,removed:1,status:'proposal_only',
        posts_scheduled:0,publishing_enabled:false})};
    }
  }
  throw Error('Unexpected route '+url);
};
function details(){
  const article=container.children[0].children[3].children[1];
  return article.children.find(x=>x.className==='bam-calendar-proposal');
}
async function main(){
  const app=create({document,container,fetchImpl,origin:'https://bam.example',
    onError:text=>errors.push(text),onNotice:text=>notices.push(text),
    enableCalendarProposals:true});
  app.activate({token:'t'.repeat(43),tenantId:'shop'});
  app.setCanEdit(true);
  assert.equal((await app.refresh()).heldCount,1);
  let calendar=details();
  assert.ok(calendar);
  const save=calendar.children.find(x=>x.textContent===
    'Save draft date proposal (not schedule)');
  const select=calendar.children.find(x=>x.tag==='select');
  assert.ok(save);
  assert.equal(select.value,utc);
  await save.listeners.click();
  assert.ok(proposal);
  assert.match(notices.at(-1),/did not schedule or approve/);
  assert.equal(calls.filter(x=>x.options.method==='POST').length,1);
  calendar=details();
  assert.ok(calendar.children.some(x=>/Proposed: 2026-11-11/.test(x.textContent)));
  const remove=calendar.children.find(x=>x.textContent==='Remove proposed time');
  assert.ok(remove);
  await remove.listeners.click();
  assert.equal(proposal,null);
  assert.match(notices.at(-1),/Only the proposed date/);
  assert.equal(calls.filter(x=>x.options.method==='DELETE').length,1);
  assert.equal(errors.length,0);
  const old=details().children.find(x=>
    x.textContent==='Save draft date proposal (not schedule)');
  app.setCanEdit(false);
  await old.listeners.click();
  assert.equal(calls.filter(x=>x.options.method==='POST').length,1);
  app.clear();
  await old.listeners.click();
  assert.equal(container.children.length,0);
  // Browser never writes social provider scheduling or publishing routes.
  assert.equal(calls.some(x=>/publish|social\/schedule|\/ai-generate/.test(x.url)),
    false);
  console.log('BAM held-draft proposed calendar UI tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
