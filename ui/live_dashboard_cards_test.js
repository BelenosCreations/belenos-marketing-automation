'use strict';
const assert=require('node:assert/strict');
const {create}=require('./live_dashboard_cards.js');
function node(tag){
  return {tag,textContent:'',children:[],listeners:{},
    append(...items){this.children.push(...items)},
    replaceChildren(...items){this.children=items},
    addEventListener(name,fn){this.listeners[name]=fn}};
}
const document={createElement:node},container=node('main');
function payload(tenant='shop'){
  return {schema_version:1,tenant_id:tenant,
    businesses:[{tenant_id:tenant,display_name:'Example Shop'}],
    cards:[
      {id:'scheduled',label:'Scheduled',value:null,availability:'not_connected'},
      {id:'approvals',label:'Approvals',value:1,availability:'available'},
      {id:'content',label:'Content',value:1,availability:'available'},
      {id:'connections',label:'Connections',value:0,availability:'available'}
    ],
    drafts:[{request_id:'r1',channel:'facebook',
      draft_text:'<script>not HTML</script>',
      suggestion:'Add a photo',status:'needs_content',
      missing_items:['product photo']}],
    analytics:{availability:'not_connected',series:null},
    schedule:{availability:'not_connected',posts:null},
    publishing_enabled:false};
}
async function main(){
  let responder=()=>payload(),pending=null,errors=[];
  const fetchImpl=async()=>({ok:true,json:async()=>responder()});
  const app=create({document,container,fetchImpl,
    origin:'https://bam.example',onError:e=>errors.push(e)});
  app.activate({token:'valid',tenantId:'shop'});
  assert.equal((await app.refresh()).stale,false);
  const cards=container.children[0].children[1].children;
  assert.equal(cards.length,4);
  assert.equal(cards[0].children[1].textContent,'Not available');
  cards[2].listeners.click();
  assert.equal(container.children[0].children[2].children[1].textContent,
    '<script>not HTML</script>');
  app.show('scheduled');
  assert.match(container.children[0].children[2].textContent,
    /Scheduling is not connected/);
  responder=()=>payload('other');
  assert.equal((await app.refresh()).error,true);
  assert.equal(container.children.length,0);
  assert.equal(errors.length,1);
  app.activate({token:'valid',tenantId:'shop'});
  responder=()=>new Promise(resolve=>{pending=resolve});
  const old=app.refresh();
  await Promise.resolve();
  app.clear();
  pending(payload());
  assert.equal((await old).stale,true);
  assert.equal(container.children.length,0);
  console.log('BAM live dashboard card tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
