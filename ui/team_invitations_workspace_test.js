'use strict';
const assert=require('node:assert/strict');
const {create}=require('./team_overview_workspace.js');
function el(tag){return {tag,children:[],listeners:{},textContent:'',value:'',
  append(...x){this.children.push(...x)},replaceChildren(...x){this.children=x},
  addEventListener(k,f){this.listeners[k]=f},setAttribute(k,v){this[k]=v}};}
const document={createElement:el};
const overview={tenant_id:'shop',
 roles:{owner:1,marketing_manager:0,content_creator:0,employee:0,viewer:0},
 active_members:1,inactive_members:0,invitation_status:'not_connected',
 publishing_enabled:false};
const roster={tenant_id:'shop',status:'private_team_preview',
 members:[{member_id:'o'.repeat(32),role:'owner',active:true,revision:1,
   email:'boss@example.com',is_self:true}],publishing_enabled:false};
const history={tenant_id:'shop',status:'private_team_activity',
 events:[],publishing_enabled:false};
let pending=[{invitation_id:'a'.repeat(32),email:'guest@example.com',
  role:'viewer',expires_at:700000}];
let posts=[];
let pauseCancel=null;
const fetchImpl=async(url,opts)=>{
  if(url.endsWith('/team-overview'))
    return {ok:true,json:async()=>overview};
  if(url.endsWith('/team/members'))
    return {ok:true,json:async()=>roster};
  if(url.endsWith('/team/activity'))
    return {ok:true,json:async()=>history};
  if(url.endsWith('/team/invitations'))
    return {ok:true,json:async()=>({tenant_id:'shop',
      status:'private_pending_invitations',items:[...pending],
      publishing_enabled:false})};
  if(url.endsWith('/team/invitations/cancel')){
    const body=JSON.parse(opts.body);posts.push({body,opts});
    if(pauseCancel)await pauseCancel;
    pending=pending.filter(x=>x.invitation_id!==body.invitation_id);
    return {ok:true,json:async()=>({tenant_id:'shop',
      invitation_id:body.invitation_id,status:'cancelled',
      publishing_enabled:false})};
  }
  throw new Error('Unsupported endpoint');
};
function flatten(node){return [node,...(node.children||[]).flatMap(flatten)];}
function find(node,text){return flatten(node).find(x=>x.textContent===text);}
async function settle(){for(let i=0;i<5;i++)
  await new Promise(resolve=>setImmediate(resolve));}
async function main(){
  const root=el('main'),notices=[];
  const app=create({document,container:root,fetchImpl,
    origin:'https://bam.example',enableMemberManagement:true,
    enableInvitationPreview:true,onNotice:x=>notices.push(x)});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  app.setOwner(true);
  assert.equal((await app.refresh()).activeMembers,1);
  assert.ok(find(root,'guest@example.com'));
  assert.ok(find(root,'Cancel invitation'));
  find(root,'Cancel invitation').listeners.click();
  assert.equal(posts.length,0);
  find(root,'Keep invitation').listeners.click();
  assert.equal(posts.length,0);
  find(root,'Cancel invitation').listeners.click();
  find(root,'Confirm invitation cancellation').listeners.click();
  await settle();
  assert.equal(posts.length,1);
  assert.deepEqual(posts[0].body,{invitation_id:'a'.repeat(32)});
  assert.equal(posts[0].opts.credentials,'omit');
  assert.equal(pending.length,0);
  assert.ok(notices.some(x=>/cancelled/.test(x)));
  assert.equal(find(root,'Cancel invitation'),undefined);
  app.clear();
  assert.equal(root.children.length,0);
  // Logout while cancellation transport is still outstanding: the former
  // owner session must never render a success notice into a cleared workspace.
  const earlierNotices=notices.length;
  pending=[{invitation_id:'b'.repeat(32),email:'later@example.com',
    role:'viewer',expires_at:700000}];
  let releaseCancel;
  pauseCancel=new Promise(resolve=>{releaseCancel=resolve;});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  app.setOwner(true);
  await app.refresh();
  find(root,'Cancel invitation').listeners.click();
  find(root,'Confirm invitation cancellation').listeners.click();
  await Promise.resolve();
  app.clear();
  releaseCancel();
  await settle();
  pauseCancel=null;
  assert.equal(root.children.length,0);
  assert.equal(notices.length,earlierNotices);
  assert.throws(()=>create({document,container:el('main'),fetchImpl,
    origin:'https://bam.example',enableInvitationPreview:true}),TypeError);
  console.log('BAM optional offline invitation cancellation UI tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
