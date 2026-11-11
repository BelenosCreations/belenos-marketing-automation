'use strict';
const assert=require('node:assert/strict');
const {create}=require('./team_overview_workspace.js');
function node(tag){return {tag,children:[],textContent:'',
 append(...items){this.children.push(...items)},
 replaceChildren(...items){this.children=items}};}
const document={createElement:node},container=node('main');
let pending=null,resolve=null,reads=0;
const response={tenant_id:'shop',roles:{owner:1,marketing_manager:0,
 content_creator:1,employee:0,viewer:0},active_members:2,inactive_members:1,
 invitation_status:'not_connected',publishing_enabled:false};
const fetchImpl=async(url,opts)=>{
 reads++;
 assert.ok(url.endsWith('/team-overview'));
 assert.equal(opts.credentials,'omit');
 if(pending)await pending;
 return {ok:true,json:async()=>response};
};
async function main(){
 const app=create({document,container,fetchImpl,origin:'https://bam.example'});
 app.activate({token:'a'.repeat(43),tenantId:'shop'});
 assert.equal((await app.refresh()).restricted,true);
 assert.equal(reads,0);
 app.setOwner(true);
 const result=await app.refresh();
 assert.equal(result.activeMembers,2);
 assert.equal(container.children[0].children[1].textContent,
   'Active team members: 2');
 assert.ok(container.children[0].children.some(x=>
   x.textContent==='Content creators: 1'));
 assert.equal(JSON.stringify(container).includes('subject_id'),false);
 pending=new Promise(r=>{resolve=r});
 const stale=app.refresh();
 await Promise.resolve();
 app.setOwner(false);
 resolve();
 assert.equal((await stale).stale,true);
 assert.match(container.children[0].children[1].textContent,/Only the current/);
 const other=create({document,container:node('main'),fetchImpl:async()=>({
   ok:true,json:async()=>({...response,tenant_id:'other'})}),
   origin:'https://bam.example'});
 other.activate({token:'a'.repeat(43),tenantId:'shop'});
 other.setOwner(true);
 assert.equal((await other.refresh()).error,true);
 app.clear();
 assert.equal(container.children.length,0);
 console.log('BAM owner-only team access workspace tests passed');
}
main().catch(e=>{console.error(e);process.exitCode=1});
