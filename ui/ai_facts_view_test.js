'use strict';
const assert=require('node:assert/strict');
const {render}=require('./ai_facts_view.js');
function node(tag){return {tag,textContent:'',children:[],
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items}}}
const document={createElement:node},container=node('main');
const empty={tenant_id:'shop',facts:{},revision:0,
  provenance:'not_configured',confirmed_at:null,publishing_enabled:false};
render({document,container,payload:empty,expectedTenantId:'shop'});
assert.match(container.children[0].children[1].textContent,/remain on hold/);
const verified={tenant_id:'shop',facts:{name:'<script>alert(1)</script>'},
  revision:1,provenance:'owner_confirmed',confirmed_at:100,
  publishing_enabled:false};
render({document,container,payload:verified,expectedTenantId:'shop'});
assert.equal(container.children[0].children[2].textContent,
  'name: <script>alert(1)</script>');
const old=container.children[0];
assert.throws(()=>render({document,container,payload:verified,
  expectedTenantId:'other'}),TypeError);
assert.equal(container.children[0],old);
console.log('BAM AI facts view tests passed');
