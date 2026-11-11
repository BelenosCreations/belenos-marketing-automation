'use strict';
const assert=require('node:assert/strict');
const {render}=require('./ai_settings_view.js');
function node(tag){
  return {tag,textContent:'',children:[],listeners:{},value:'',disabled:false,
    append(...children){this.children.push(...children)},
    replaceChildren(...children){this.children=children},
    addEventListener(name,listener){this.listeners[name]=listener}};
}
const document={createElement:node},mount=node('main');
const payload={tenant_id:'shop',provider:'openai',mode:'bam_sponsored',
  own_key_configured:false,memory:{tone:'Brief posts'},
  key_exposed:false,publishing_enabled:false};
async function main(){
  const saved=[];
  render({document,container:mount,payload,expectedTenantId:'shop',
    canEdit:true,onSave:args=>saved.push(args)});
  const section=mount.children[0];
  const editor=section.children.at(-1);
  assert.equal(editor.className,'bam-ai-memory-editor');
  assert.ok(editor.children.some(x=>
    x.textContent==='Edit your AI writing preferences'));
  const old=editor.children.find(x=>x.className==='bam-ai-memory-row');
  assert.equal(old.children[0].value,'tone');
  assert.equal(old.children[1].value,'Brief posts');
  const add=editor.children.find(x=>
    x.textContent==='Add writing preference');
  await add.listeners.click();
  const rows=editor.children.filter(x=>x.className==='bam-ai-memory-row');
  assert.equal(rows.length,2);
  rows[1].children[0].value='audience';
  rows[1].children[1].value='Marion customers';
  await editor.children.find(x=>
    x.textContent==='Save AI writing preferences').listeners.click();
  assert.deepEqual(saved[0],{
    expectedMemory:{tone:'Brief posts'},
    memory:{tone:'Brief posts',audience:'Marion customers'}});
  rows[0].children[0].value='audience';
  await editor.children.find(x=>
    x.textContent==='Save AI writing preferences').listeners.click();
  assert.equal(saved.length,1);
  assert.match(editor.children.find(x=>x.tag==='p'&&
    /unique, nonempty/.test(x.textContent)).textContent,/unique/);
  assert.throws(()=>render({document,container:mount,payload,
    expectedTenantId:'shop',canEdit:true}),TypeError);
  render({document,container:mount,payload,
    expectedTenantId:'shop',canEdit:false});
  assert.equal(mount.children[0].children.some(x=>
    x.className==='bam-ai-memory-editor'),false);
  console.log('BAM per-user AI writing preference editor DOM tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
