'use strict';
const assert=require('node:assert/strict');
const {render}=require('./ai_draft_view.js');
function element(tag){return {tag,textContent:'',children:[],listeners:{},
  value:'',disabled:false,
  append(...children){this.children.push(...children)},
  replaceChildren(...children){this.children=children},
  addEventListener(event,listener){this.listeners[event]=listener}}}
const document={createElement:element},mount=element('main');
const draftId='a'.repeat(32);
const data={tenant_id:'shop',publishing_enabled:false,drafts:[{
  tenant_id:'shop',draft_id:draftId,platform:'facebook',
  post_text:'Product post text',image_prompt:'A neutral product photo',
  needs_media:true,media_attached:false,
  status:'needs_media',revision:3,publishing_enabled:false}]};
async function main(){
  const calls=[];
  render({document,container:mount,payload:data,
    expectedTenantId:'shop',canEdit:true,onRevise:()=>{}});
  let article=mount.children[0].children[2];
  assert.equal(article.children.filter(x=>x.className==='bam-ai-regeneration').length,0);
  render({document,container:mount,payload:data,
    expectedTenantId:'shop',canEdit:true,onRevise:()=>{},
    canRegenerate:true,onRegenerate:args=>calls.push(args)});
  article=mount.children[0].children[2];
  const panels=article.children.filter(x=>x.className==='bam-ai-regeneration');
  assert.equal(panels.length,2);
  assert.equal(panels[0].children[0].textContent,
    'Regenerate post copy with AI');
  assert.equal(panels[1].children[0].textContent,
    'Regenerate image prompt with AI');
  const copy=panels[0];
  const copyInput=copy.children.find(x=>x.tag==='textarea');
  const topic=copy.children.find(x=>x.tag==='input');
  const preview=copy.children.find(x=>
    x.textContent==='Review AI regeneration request');
  await preview.listeners.click();
  assert.equal(copy.children.some(x=>x.textContent==='Confirm AI revision of post copy'),false);
  copyInput.value='Make it shorter but keep facts accurate';
  topic.value='Product spotlight';
  await preview.listeners.click();
  await preview.listeners.click();
  const confirm=copy.children.find(x=>
    x.textContent==='Confirm AI revision of post copy');
  assert.ok(confirm);
  assert.equal(copy.children.filter(x=>
    x.textContent==='Confirm AI revision of post copy').length,1);
  assert.ok(copy.children.some(x=>/sponsored OpenAI quota/.test(x.textContent)));
  await confirm.listeners.click();
  assert.deepEqual(calls[0],{
    draftId,target:'post_text',
    instruction:'Make it shorter but keep facts accurate',
    topic:'Product spotlight',expectedRevision:3
  });
  const promptPanel=panels[1];
  promptPanel.children.find(x=>x.tag==='textarea').value='Change lighting only';
  await promptPanel.children.find(x=>
    x.textContent==='Review AI regeneration request').listeners.click();
  await promptPanel.children.find(x=>
    x.textContent==='Confirm AI revision of image prompt').listeners.click();
  assert.deepEqual(calls[1],{
    draftId,target:'image_prompt',instruction:'Change lighting only',
    topic:'Revise existing facebook draft',expectedRevision:3
  });
  assert.equal(calls.length,2);
  assert.throws(()=>render({document,container:mount,payload:data,
    expectedTenantId:'shop',canEdit:true,canRegenerate:true,
    onRevise:()=>{}}),TypeError);
  assert.throws(()=>render({document,container:mount,payload:data,
    expectedTenantId:'shop',canEdit:false,canRegenerate:true,
    onRegenerate:()=>{}}),TypeError);
  render({document,container:mount,payload:data,
    expectedTenantId:'shop',canEdit:false});
  assert.equal(mount.children[0].children[2].children.some(x=>
    x.className==='bam-ai-regeneration'),false);
  console.log('BAM explicit two-stage AI revision view tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
