'use strict';
const assert=require('node:assert/strict');
const {create}=require('./team_overview_workspace.js');
function el(tag){return {tag,children:[],listeners:{},textContent:'',
  value:'',append(...x){this.children.push(...x)},
  replaceChildren(...x){this.children=x},
  addEventListener(k,f){this.listeners[k]=f},
  setAttribute(k,v){this[k]=v}};}
const document={createElement:el};
function flatten(node){return [node,...(node.children||[]).flatMap(flatten)];}
function find(root,text){return flatten(root).find(x=>x.textContent===text);}
async function settle(){for(let i=0;i<7;i++)
  await new Promise(resolve=>setImmediate(resolve));}
const overview={tenant_id:'shop',
  roles:{owner:1,marketing_manager:0,content_creator:0,employee:0,viewer:0},
  active_members:1,inactive_members:0,invitation_status:'not_connected',
  publishing_enabled:false};
const roster={tenant_id:'shop',status:'private_team_preview',
  members:[{member_id:'o'.repeat(32),role:'owner',active:true,revision:1,
            email:'boss@example.com',is_self:true}],publishing_enabled:false};
const history={tenant_id:'shop',status:'private_team_activity',
  events:[],publishing_enabled:false};
let pending=[],posts=[],blockIssue=null;
const fetchImpl=async(url,opts)=>{
  if(url.endsWith('/team-overview'))
    return {ok:true,json:async()=>overview};
  if(url.endsWith('/team/members'))
    return {ok:true,json:async()=>roster};
  if(url.endsWith('/team/activity'))
    return {ok:true,json:async()=>history};
  if(url.endsWith('/team/invitations/activity'))
    return {ok:true,json:async()=>({tenant_id:'shop',
      status:'private_invitation_activity',events:[],
      publishing_enabled:false})};
  if(url.endsWith('/team/invitations'))
    return {ok:true,json:async()=>({tenant_id:'shop',
      status:'private_pending_invitations',
      items:[...pending],publishing_enabled:false})};
  if(url.endsWith('/team/invitations/create')){
    const body=JSON.parse(opts.body);
    posts.push({body,opts});
    if(blockIssue)await blockIssue;
    const id='b'.repeat(32);
    pending.push({invitation_id:id,email:body.email,
                  role:body.role,expires_at:604901});
    return {ok:true,json:async()=>({tenant_id:'shop',
      invitation_created:true,invitation_id:id,expires_at:604901,
      publishing_enabled:false})};
  }
  throw new Error('Unsupported offline endpoint');
};
async function main(){
  const root=el('main'),notices=[],errors=[];
  const app=create({document,container:root,fetchImpl,
    origin:'https://bam.example',enableMemberManagement:true,
    enableInvitationPreview:true,enableInvitationIssuing:true,
    onNotice:x=>notices.push(x),onError:x=>errors.push(x)});
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  app.setOwner(true);
  assert.equal((await app.refresh()).activeMembers,1);
  assert.ok(find(root,'Review invitation'));
  let input=find(root,'Invitee email').children[0];
  input.value='bad-email';
  find(root,'Review invitation').listeners.click();
  assert.equal(posts.length,0);
  assert.ok(errors.some(x=>/Valid recipient/.test(x)));
  input.value=' FRIEND@EXAMPLE.COM ';
  find(root,'Review invitation').listeners.click();
  assert.ok(flatten(root).some(x=>
    x.textContent.includes('friend@example.com')));
  assert.equal(posts.length,0);
  find(root,'Cancel invitation issue').listeners.click();
  assert.equal(posts.length,0);
  find(root,'Invitee email').children[0].value='friend@example.com';
  find(root,'Review invitation').listeners.click();
  find(root,'Confirm invitation issue').listeners.click();
  await settle();
  assert.equal(posts.length,1);
  assert.deepEqual(posts[0].body,
    {email:'friend@example.com',role:'viewer'});
  assert.equal(posts[0].opts.credentials,'omit');
  assert.equal(pending.length,1);
  assert.ok(notices.some(x=>/trusted delivery/.test(x)));
  assert.ok(find(root,'friend@example.com'));
  // A non-owner cannot see issuer controls or send an invitation.
  app.setOwner(false);
  assert.equal(find(root,'Review invitation'),undefined);
  const noticeCount=notices.length;
  app.activate({token:'a'.repeat(43),tenantId:'shop'});
  app.setOwner(true);
  await app.refresh();
  let release;
  blockIssue=new Promise(resolve=>{release=resolve;});
  find(root,'Invitee email').children[0].value='second@example.com';
  find(root,'Review invitation').listeners.click();
  find(root,'Confirm invitation issue').listeners.click();
  await Promise.resolve();
  assert.equal(posts.length,2);
  app.clear();
  release();
  await settle();
  blockIssue=null;
  assert.equal(root.children.length,0);
  assert.equal(notices.length,noticeCount);
  assert.throws(()=>create({document,container:el('main'),fetchImpl,
    origin:'https://bam.example',enableMemberManagement:true,
    enableInvitationIssuing:true}),TypeError);
  const defaultRoot=el('main');
  const disabled=create({document,container:defaultRoot,fetchImpl,
    origin:'https://bam.example',enableMemberManagement:true,
    enableInvitationPreview:true});
  disabled.activate({token:'a'.repeat(43),tenantId:'shop'});
  disabled.setOwner(true);
  await disabled.refresh();
  assert.equal(find(defaultRoot,'Review invitation'),undefined);
  disabled.clear();
  console.log('BAM opt-in two-step invitation issuing UI tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
