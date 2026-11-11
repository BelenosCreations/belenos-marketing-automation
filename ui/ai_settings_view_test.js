'use strict';
const assert=require('node:assert/strict');
const {render}=require('./ai_settings_view.js');
function node(tag){return {tag,textContent:'',children:[],
  append(...children){this.children.push(...children)},
  replaceChildren(...children){this.children=children}}}
const document={createElement:node},container=node('main');
const payload={tenant_id:'shop',provider:'openai',mode:'own_openai_key',
  own_key_configured:true,memory:{tone:'<img src=x onerror=alert(1)>'},
  key_exposed:false,publishing_enabled:false};
const model=render({document,container,payload,expectedTenantId:'shop'});
assert.equal(model.mode,'own_openai_key');
const section=container.children[0];
assert.equal(section.children[3].textContent,'Personal key: configured (hidden)');
assert.equal(section.children[5].textContent,
             'tone: <img src=x onerror=alert(1)>');
assert.ok(!JSON.stringify(section).includes('vault:'));
const old=container.children[0];
assert.throws(()=>render({document,container,payload,
  expectedTenantId:'other'}),TypeError);
assert.equal(container.children[0],old);
console.log('BAM OpenAI settings DOM tests passed');
