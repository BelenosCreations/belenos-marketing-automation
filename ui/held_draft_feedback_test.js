'use strict';
const assert=require('node:assert/strict');
const {create}=require('./held_draft_workspace.js');
function node(tag){return {tag,textContent:'',className:'',value:'',
 children:[],listeners:{},append(...x){this.children.push(...x)},
 replaceChildren(...x){this.children=x},
 addEventListener(name,fn){this.listeners[name]=fn},
 setAttribute(name,value){this[name]=value}};}
const document={createElement:node},container=node('main');
const rid='a'.repeat(32),version='b'.repeat(32),calls=[],errors=[];
let tenant='shop',revision=1,failNotes=false;
const fetchImpl=async(url,options)=>{
 calls.push({url,options});
 if(url.endsWith('/drafts'))return {ok:true,json:async()=>({
  tenant_id:tenant,publishing_enabled:false,drafts:[{
   request_id:rid,channel:'facebook',priority:0,revision,
   draft_text:tenant==='shop'?'Custom print':'Separate business item',
   suggestion:'Check proof of rights',status:'needs_content',
   missing_items:['image']}]})};
 if(url.endsWith('/review-feedback')){
  if(failNotes)return {ok:false,status:503};
  return {ok:true,status:200,json:async()=>({
   tenant_id:tenant,status:'feedback_only',approval_granted:false,
   publishing_enabled:false,
   items:tenant==='shop'?[{
    request_id:rid,draft_revision:1,current_revision:revision,
    stale:revision!==1,note:'Confirm image consent first',
    feedback_token:version,updated_at:103,
    approval_granted:false,publishing_enabled:false}]:[]
  })};
 }
 throw Error('Only unpublished draft and feedback reads are allowed');
};
function article(){
 const root=container.children[0];
 const section=root.children.find(x=>x.tag==='section'&&
    x.children[0]?.textContent?.startsWith('needs content'));
 assert.ok(section);
 return section.children.find(x=>x.tag==='article');
}
function feedback(){
 return article().children.find(x=>x.className==='bam-editorial-feedback');
}
async function main(){
 const app=create({document,container,fetchImpl,origin:'https://bam.example',
  onError:x=>errors.push(x),enableReviewFeedback:true});
 app.activate({token:'t'.repeat(43),tenantId:'shop'});
 app.setCanEdit(false);
 assert.equal((await app.refresh()).heldCount,1);
 assert.ok(feedback());
 assert.equal(feedback().children[1].textContent,'Confirm image consent first');
 assert.ok(!feedback().children.some(x=>/earlier draft/.test(x.textContent)));
 assert.equal(article().children.some(x=>x.textContent.includes('Approve')),false);
 revision=2;
 await app.refresh();
 assert.match(feedback().children[2].textContent,/earlier draft revision/);
 failNotes=true;
 await app.refresh();
 assert.equal(feedback(),undefined);
 assert.ok(article().children.some(x=>
    /editorial comments are unavailable/.test(x.textContent)));
 assert.ok(errors.some(x=>/Editorial feedback could not be loaded/.test(x)));
 failNotes=false;
 const previous=article();
 app.clear();
 tenant='other';revision=1;
 app.activate({token:'u'.repeat(43),tenantId:'other'});
 await app.refresh();
 assert.equal(feedback(),undefined);
 assert.match(article().children[1].textContent,/Separate business item/);
 assert.ok(calls.every(x=>x.options.method==='GET'));
 assert.ok(calls.every(x=>!x.options.body));
 assert.ok(calls.some(x=>x.url.endsWith('/review-feedback')));
 assert.ok(previous!==article());
 app.clear();
 assert.equal(container.children.length,0);
 assert.throws(()=>create({document,container:node('main'),fetchImpl,
  origin:'https://bam.example',enableReviewFeedback:'yes'}),TypeError);
 console.log('BAM role-safe draft reviewer comments and tenant reset tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
