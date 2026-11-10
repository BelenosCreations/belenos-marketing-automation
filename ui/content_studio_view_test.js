'use strict';
const assert=require('node:assert/strict');
const {render}=require('./content_studio_view.js');
function node(tag){return {tag,textContent:'',children:[],
  append(...children){this.children.push(...children)},
  replaceChildren(...children){this.children=children}}}
const document={createElement:node},container=node('main');
const payload={tenant_id:'shop',publishing_enabled:false,drafts:[
  {request_id:'a'.repeat(32),channel:'facebook',draft_text:'<script>bad()</script>',
   suggestion:'Need image',status:'needs_content',missing_items:['photo'],priority:0},
  {request_id:'b'.repeat(32),channel:'instagram',draft_text:'Deferred',
   suggestion:'Wait for approval',status:'postponed',missing_items:[],priority:0}
]};
const model=render({document,container,payload,expectedTenantId:'shop'});
assert.equal(model.drafts.length,2);
const root=container.children[0];
assert.equal(root.children.length,6);
assert.equal(root.children[2].children[1].children[1].textContent,
             '<script>bad()</script>');
assert.equal(root.children[4].children[1].children[1].textContent,'Deferred');
const original=container.children[0];
assert.throws(()=>render({document,container,payload,
  expectedTenantId:'other'}),TypeError);
assert.equal(container.children[0],original);
console.log('BAM Content Studio read-only DOM tests passed');
