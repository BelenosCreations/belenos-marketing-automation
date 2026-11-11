'use strict';
const assert=require('node:assert/strict');
const {render}=require('./ai_draft_view.js');
function node(tag){return {tag,textContent:'',children:[],
  append(...children){this.children.push(...children)},
  replaceChildren(...children){this.children=children}}}
const document={createElement:node},container=node('main');
const payload={tenant_id:'shop',publishing_enabled:false,drafts:[{
  tenant_id:'shop',draft_id:'a'.repeat(32),platform:'facebook',
  post_text:'<script>alert(1)</script>',
  image_prompt:'Neutral background',needs_media:true,media_attached:false,
  status:'needs_media',revision:1,publishing_enabled:false
}]};
const result=render({document,container,payload,expectedTenantId:'shop'});
assert.equal(result.drafts.length,1);
const article=container.children[0].children[2];
assert.equal(article.children[1].textContent,'<script>alert(1)</script>');
assert.equal(article.children[3].textContent,'Neutral background');
assert.match(article.children[4].textContent,/on hold/);
const previous=container.children[0];
assert.throws(()=>render({document,container,payload,
  expectedTenantId:'other'}),TypeError);
assert.equal(container.children[0],previous);
console.log('BAM AI draft view DOM tests passed');
