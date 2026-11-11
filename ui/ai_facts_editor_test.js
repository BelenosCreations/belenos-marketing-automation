'use strict';
const assert=require('node:assert/strict');
const {render}=require('./ai_facts_editor.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},
  value:'',append(...x){this.children.push(...x)},
  replaceChildren(...x){this.children=x},
  addEventListener(name,fn){this.listeners[name]=fn}}}
const document={createElement:node},container=node('main');
const payload={tenant_id:'shop',facts:{name:'Example Shop'},
  revision:1,provenance:'owner_confirmed',confirmed_at:100,
  publishing_enabled:false};
const saved=[];
const args={document,container,payload,expectedTenantId:'shop',
  canManage:true,onSave:data=>saved.push(data)};
assert.equal(render(args).editable,true);
const root=container.children[0],rows=root.children[2];
assert.equal(rows.children[0].children[0].value,'name');
assert.equal(saved.length,0);
root.children[4].listeners.click();
assert.deepEqual(saved,[{facts:{name:'Example Shop'},
  expectedRevision:1,expectedTenantId:'shop'}]);
root.children[3].listeners.click();
rows.children[1].children[0].value='name';
rows.children[1].children[1].value='Override';
assert.throws(()=>root.children[4].listeners.click(),TypeError);
assert.equal(saved.length,1);
render({...args,canManage:false,onSave:undefined});
assert.equal(container.children[0].children.length,3);
assert.throws(()=>render({...args,expectedTenantId:'other'}),TypeError);
console.log('BAM owner-confirmed facts editor tests passed');
