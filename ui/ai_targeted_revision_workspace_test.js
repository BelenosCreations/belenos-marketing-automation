'use strict';
const assert=require('node:assert/strict');
const {create}=require('./ai_workspace.js');
function element(tag){
  return {tag,textContent:'',className:'',value:'',disabled:false,children:[],
    listeners:{},append(...items){this.children.push(...items)},
    replaceChildren(...items){this.children=items},
    addEventListener(event,fn){this.listeners[event]=fn}};
}
const document={createElement:element};
const draftId='a'.repeat(32);
const drafts=element('main'),settings=element('main');
let copy='Initial product copy',revision=1,randomCounter=0;
const calls=[],errors=[];
const secureRandom={getRandomValues(bytes){
  bytes[0]=++randomCounter;bytes[15]=255;return bytes;
}};
const fetchImpl=async(url,opts)=>{
  calls.push({url,opts});
  if(url.endsWith('/ai-drafts'))
    return {ok:true,json:async()=>({tenant_id:'shop',
      publishing_enabled:false,drafts:[{
        tenant_id:'shop',draft_id:draftId,platform:'facebook',
        post_text:copy,image_prompt:'Generic image prompt',needs_media:true,
        media_attached:false,status:'needs_media',
        revision,publishing_enabled:false}]})};
  if(url.endsWith('/ai-settings'))
    return {ok:true,json:async()=>({tenant_id:'shop',
      provider:'openai',mode:'bam_sponsored',own_key_configured:false,
      memory:{},key_exposed:false,publishing_enabled:false})};
  if(url.endsWith('/ai/targeted-revision')){
    assert.equal(opts.method,'POST');
    assert.equal(opts.credentials,'omit');
    assert.equal(opts.headers.Authorization,'Bearer '+'t'.repeat(43));
    assert.match(opts.headers['Idempotency-Key'],/^[a-f0-9]{32}$/);
    const body=JSON.parse(opts.body);
    assert.deepEqual(body,{draft_id:draftId,expected_revision:1,
      target:'post_text',instruction:'Make this copy shorter',
      topic:'Product spotlight'});
    assert.equal(revision,1);
    copy='Short accurate copy';revision=2;
    return {ok:true,status:201,json:async()=>({
      revised:true,tenant_id:'shop',draft_id:draftId,revision,
      status:'needs_media',publishing_enabled:false})};
  }
  throw Error('Unexpected request '+url);
};
async function main(){
  assert.throws(()=>create({document,draftsContainer:drafts,
    settingsContainer:settings,origin:'https://bam.example',fetchImpl,
    enableTargetedRevisions:true}),TypeError);
  const app=create({document,draftsContainer:drafts,
    settingsContainer:settings,origin:'https://bam.example',fetchImpl,
    enableTargetedRevisions:true,secureRandom,
    onError:text=>errors.push(text)});
  app.activate({token:'t'.repeat(43),tenantId:'shop'});
  app.setCapabilities({manageFacts:false,createDrafts:true});
  assert.equal((await app.refresh()).draftCount,1);
  let article=drafts.children[0].children[2];
  const panel=article.children.find(x=>
    x.className==='bam-ai-regeneration'&&
    x.children[0].textContent==='Regenerate post copy with AI');
  assert.ok(panel);
  const instruction=panel.children.find(x=>x.tag==='textarea');
  instruction.value='Make this copy shorter';
  panel.children.find(x=>x.tag==='input').value='Product spotlight';
  const prepare=panel.children.find(x=>
    x.textContent==='Review AI regeneration request');
  await prepare.listeners.click();
  assert.equal(calls.filter(x=>
    x.url.endsWith('/ai/targeted-revision')).length,0);
  const confirm=panel.children.find(x=>
    x.textContent==='Confirm AI revision of post copy');
  assert.ok(confirm);
  await confirm.listeners.click();
  assert.equal(calls.filter(x=>
    x.url.endsWith('/ai/targeted-revision')).length,1);
  assert.equal(copy,'Short accurate copy');
  assert.equal(revision,2);
  assert.equal(errors.length,0);
  article=drafts.children[0].children[2];
  assert.equal(article.children[1].textContent,'Short accurate copy');
  assert.equal(article.children.find(x=>x.tag==='textarea').value,
    'Short accurate copy');
  // Old detached controls cannot issue any new paid request after rotation.
  app.activate({token:'q'.repeat(43),tenantId:'other'});
  await confirm.listeners.click();
  assert.equal(calls.filter(x=>
    x.url.endsWith('/ai/targeted-revision')).length,1);
  app.clear();
  await confirm.listeners.click();
  assert.equal(drafts.children.length,0);
  const disabled=create({document,draftsContainer:drafts,
    settingsContainer:settings,origin:'https://bam.example',fetchImpl});
  disabled.activate({token:'t'.repeat(43),tenantId:'shop'});
  disabled.setCapabilities({manageFacts:false,createDrafts:true});
  await disabled.refresh();
  assert.equal(drafts.children[0].children[2].children.some(x=>
    x.className==='bam-ai-regeneration'),false);
  console.log('BAM disabled-by-default AI regeneration workspace tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
