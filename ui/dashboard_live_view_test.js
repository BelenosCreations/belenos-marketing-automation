'use strict';
const assert=require('node:assert/strict');
const {render,clear}=require('./dashboard_live_view.js');
function node(tag){
  return {tag,children:[],textContent:'',className:'',
    append(...children){this.children.push(...children)},
    replaceChildren(...children){this.children=children}};
}
const document={createElement:node};
const container=node('main');
const payload={
  schema_version:1,tenant_id:'belenos',role:'owner',
  businesses:[{tenant_id:'belenos',display_name:'Belenos Creations',role:'owner'}],
  cards:[
    {id:'scheduled',label:'Scheduled posts',value:null,availability:'not_connected'},
    {id:'approvals',label:'Needs review',value:0,availability:'available'},
    {id:'content',label:'Content needed',value:1,availability:'available'},
    {id:'connections',label:'Social connections',value:null,availability:'restricted'}
  ],
  drafts:[{request_id:'a'.repeat(32),channel:'facebook',
    draft_text:'<img src=x onerror=alert(1)>',suggestion:'Provide product photo',
    status:'needs_content',missing_items:['photo'],priority:0}],
  analytics:{availability:'not_connected',series:null},
  schedule:{availability:'not_connected',posts:null},
  publishing_enabled:false
};
const model=render({document,container,payload});
assert.equal(model.tenantId,'belenos');
assert.equal(container.children.length,1);
const root=container.children[0];
assert.equal(root.children[0].textContent,'Belenos Creations');
const cards=root.children[2];
assert.equal(cards.children.length,4);
assert.equal(cards.children[0].children[1].textContent,'Not connected');
assert.equal(cards.children[3].children[1].textContent,'Restricted');
const draft=root.children[3].children[1];
assert.equal(draft.children[1].textContent,'<img src=x onerror=alert(1)>');
assert.equal(draft.children[3].textContent,'Needed: photo');
const oldRoot=container.children[0];
assert.throws(()=>render({document,container,
  payload:{...payload,publishing_enabled:true}}),TypeError);
assert.equal(container.children[0],oldRoot,
  'Bad payload must not partially replace the dashboard');
assert.throws(()=>render({document,container,payload,expectedTenantId:'other'}),TypeError);
clear({container});
assert.equal(container.children.length,0,'Business switch clears prior tenant data');
console.log('BAM authenticated dashboard DOM rendering tests passed');
