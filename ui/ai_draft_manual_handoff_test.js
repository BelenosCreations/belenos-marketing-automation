'use strict';
const assert=require('node:assert/strict');
const {render}=require('./ai_draft_view.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},
  append(...children){this.children.push(...children)},
  replaceChildren(...children){this.children=children},
  addEventListener(name,fn){this.listeners[name]=fn}}}
const document={createElement:node},container=node('main');
const copied=[],opened=[];
const payload={tenant_id:'shop',publishing_enabled:false,drafts:[{
  tenant_id:'shop',draft_id:'a'.repeat(32),platform:'facebook',
  post_text:'Unpublished post',image_prompt:'A safe product photograph',
  needs_media:true,media_attached:false,status:'needs_media',
  revision:1,publishing_enabled:false}]};
render({document,container,payload,expectedTenantId:'shop',
  copyText:x=>copied.push(x),openUrl:x=>opened.push(x)});
assert.equal(copied.length,0);
assert.equal(opened.length,0);
const article=container.children[0].children[2];
const handoff=article.children[4].children[0];
handoff.children[3].listeners.click();
handoff.children[4].listeners.click();
assert.deepEqual(copied,['A safe product photograph']);
assert.deepEqual(opened,['https://chatgpt.com/']);
const attached=JSON.parse(JSON.stringify(payload));
attached.drafts[0].media_attached=true;
attached.drafts[0].status='draft_pending_verification';
render({document,container,payload:attached,expectedTenantId:'shop',
  copyText:x=>copied.push(x),openUrl:x=>opened.push(x)});
assert.equal(container.children[0].children[2].children.length,5);
console.log('BAM held-draft manual ChatGPT handoff tests passed');
