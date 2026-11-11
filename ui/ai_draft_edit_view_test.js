'use strict';
const assert=require('node:assert/strict');
const {render}=require('./ai_draft_view.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},value:'',
  append(...children){this.children.push(...children)},
  replaceChildren(...children){this.children=children},
  addEventListener(name,callback){this.listeners[name]=callback}}}
const document={createElement:node},container=node('main');
const id='a'.repeat(32);
const payload={tenant_id:'shop',publishing_enabled:false,drafts:[{
  tenant_id:'shop',draft_id:id,platform:'facebook',post_text:'Initial copy',
  image_prompt:'Original concept',needs_media:true,media_attached:false,
  status:'needs_media',revision:2,publishing_enabled:false
}]};
async function main(){
  const calls=[];
  render({document,container,payload,expectedTenantId:'shop',
    canEdit:true,onRevise:args=>calls.push(args)});
  const article=container.children[0].children[2];
  const textField=article.children.find(x=>x.tag==='textarea'&&x.value==='Initial copy');
  const imageField=article.children.find(x=>x.tag==='textarea'&&x.value==='Original concept');
  const saveText=article.children.find(x=>x.textContent==='Save post copy');
  const savePrompt=article.children.find(x=>x.textContent==='Save image prompt');
  assert.ok(textField&&imageField&&saveText&&savePrompt);
  textField.value='Updated text only';
  await saveText.listeners.click();
  assert.deepEqual(calls[0],{
    draftId:id,target:'post_text',revisedText:'Updated text only',expectedRevision:2});
  imageField.value='Different conceptual image';
  await savePrompt.listeners.click();
  assert.deepEqual(calls[1],{
    draftId:id,target:'image_prompt',revisedText:'Different conceptual image',
    expectedRevision:2});
  assert.equal(calls.length,2);
  render({document,container,payload,expectedTenantId:'shop',canEdit:false});
  assert.equal(container.children[0].children[2].children.some(
    x=>x.textContent==='Save post copy'),false);
  assert.throws(()=>render({document,container,payload,
    expectedTenantId:'shop',canEdit:true}),TypeError);
  assert.equal(container.children[0].children[2].children.some(
    x=>x.textContent==='Save post copy'),false);
  console.log('BAM targeted AI draft editor DOM tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
