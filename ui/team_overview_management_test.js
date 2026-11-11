'use strict';
const assert=require('node:assert/strict');
const {create}=require('./team_overview_workspace.js');
function node(tag){
  return {tag,children:[],listeners:{},textContent:'',value:'',
    append(...x){this.children.push(...x)},
    replaceChildren(...x){this.children=x},
    addEventListener(k,cb){this.listeners[k]=cb},
    setAttribute(k,v){this[k]=v}};
}
const doc={createElement:node};
const summary={tenant_id:'shop',
 roles:{owner:1,marketing_manager:0,content_creator:1,employee:0,viewer:0},
 active_members:2,inactive_members:0,invitation_status:'not_connected',
 publishing_enabled:false};
const initial=[
 {member_id:'o'.repeat(32),role:'owner',active:true,revision:1,
  email:'boss@example.com',is_self:true},
 {member_id:'m'.repeat(32),role:'content_creator',active:true,revision:1,
  email:'member@example.com',is_self:false}
];
let roster=structuredClone(initial),writes=[],readWait=null,release=null;
const fetchImpl=async(url,opts)=>{
  if(url.endsWith('/team-overview'))return {ok:true,json:async()=>summary};
  if(url.endsWith('/team/members')){
    if(readWait)await readWait;
    return {ok:true,json:async()=>({tenant_id:'shop',
      status:'private_team_preview',members:structuredClone(roster),
      publishing_enabled:false})};
  }
  if(url.endsWith('/team/membership')){
    const body=JSON.parse(opts.body);writes.push({body,opts});
    const item=roster.find(x=>x.member_id===body.member_id);
    if(body.expected_revision!==item.revision)return {ok:false,status:409};
    if(body.action==='deactivate')item.active=false;
    else item.role=body.role;
    item.revision++;
    summary.roles.content_creator=roster.filter(x=>x.active&&x.role==='content_creator').length;
    summary.roles.viewer=roster.filter(x=>x.active&&x.role==='viewer').length;
    summary.active_members=roster.filter(x=>x.active).length;
    summary.inactive_members=roster.filter(x=>!x.active).length;
    return {ok:true,json:async()=>({tenant_id:'shop',
      member_id:item.member_id,status:body.action==='deactivate'?'deactivated':'updated',
      revision:item.revision,sessions_revoked:1,publishing_enabled:false})};
  }
  throw new Error('Unknown route '+url);
};
function flatten(root){return [root,...(root.children||[]).flatMap(flatten)];}
function byText(container,value){return flatten(container).find(x=>x.textContent===value);}
async function settle(){for(let i=0;i<4;i++)await new Promise(resolve=>setImmediate(resolve));}
async function main(){
  const container=node('main'),notices=[],errors=[];
  const app=create({document:doc,container,fetchImpl,origin:'https://bam.example',
    enableMemberManagement:true,onNotice:x=>notices.push(x),
    onError:x=>errors.push(x)});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  assert.equal((await app.refresh()).restricted,true);
  app.setOwner(true);
  assert.equal((await app.refresh()).activeMembers,2);
  assert.ok(byText(container,'member@example.com'));
  assert.ok(!byText(container,'Change owner'));
  assert.ok(!JSON.stringify(container).includes('access_token'));
  const remove=byText(container,'Remove access');
  remove.listeners.click();
  assert.equal(writes.length,0); // first click is not authorization
  assert.ok(byText(container,'Confirm team change'));
  byText(container,'Cancel team change').listeners.click();
  assert.equal(writes.length,0);
  byText(container,'Remove access').listeners.click();
  byText(container,'Confirm team change').listeners.click();
  await settle();
  assert.equal(writes.length,1);
  assert.equal(writes[0].body.action,'deactivate');
  assert.equal(writes[0].body.expected_revision,1);
  assert.equal(writes[0].opts.credentials,'omit');
  assert.equal(roster[1].active,false);
  assert.equal(summary.inactive_members,1);
  assert.ok(notices.some(x=>/removed/.test(x)));
  assert.equal(byText(container,'Remove access'),undefined);
  assert.equal(errors.length,0);
  // Replacing the business erases member emails and suppresses in-flight data.
  readWait=new Promise(resolve=>{release=resolve});
  const pending=app.refresh();
  await Promise.resolve();
  app.clear();
  release();
  assert.equal((await pending).stale,true);
  assert.equal(container.children.length,0);
  console.log('BAM two-step private team controls and tenant-switch tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
