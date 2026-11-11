'use strict';
const assert=require('node:assert/strict');
const {create}=require('./ai_workspace.js');
function node(tag){return {tag,textContent:'',children:[],
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items}}}
const document={createElement:node};
const drafts=node('main'),settings=node('main');
const draft=(tenant)=>({tenant_id:tenant,publishing_enabled:false,drafts:[{
  tenant_id:tenant,draft_id:'a'.repeat(32),platform:'facebook',
  post_text:'Private '+tenant,image_prompt:'Image '+tenant,
  needs_media:true,media_attached:false,status:'needs_media',
  revision:1,publishing_enabled:false
}]});
const prefs=(tenant)=>({tenant_id:tenant,provider:'openai',
  mode:'bam_sponsored',own_key_configured:false,memory:{tone:tenant},
  key_exposed:false,publishing_enabled:false});
let pending=[];
const fetchImpl=(url,options)=>new Promise(resolve=>{
  pending.push({url,options,resolve});
});
const errors=[];
const workspace=create({document,draftsContainer:drafts,
  settingsContainer:settings,fetchImpl,origin:'https://bam.example',
  onError:m=>errors.push(m)});
function flush(tenant){
  const requests=pending.splice(0);
  assert.equal(requests.length,2);
  for(const item of requests){
    assert.equal(item.options.credentials,'omit');
    item.resolve({ok:true,json:async()=>item.url.endsWith('/ai-drafts')
      ?draft(tenant):prefs(tenant)});
  }
}
async function main(){
  workspace.activate({token:'first',tenantId:'a'});
  const old=workspace.refresh();
  workspace.activate({token:'second',tenantId:'b'});
  flush('a');
  assert.equal((await old).stale,true);
  assert.equal(drafts.children.length,0);
  const fresh=workspace.refresh();
  flush('b');
  assert.equal((await fresh).tenantId,'b');
  assert.equal(drafts.children[0].children[2].children[1].textContent,
               'Private b');
  assert.equal(settings.children[0].children[5].textContent,'tone: b');
  const after=workspace.refresh();
  workspace.clear();
  flush('b');
  assert.equal((await after).stale,true);
  assert.equal(drafts.children.length,0);
  assert.equal(settings.children.length,0);
  await assert.rejects(()=>workspace.refresh(),TypeError);
  assert.deepEqual(errors,[]);
  console.log('BAM AI workspace stale-session tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
