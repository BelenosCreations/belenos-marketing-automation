'use strict';
const assert=require('node:assert/strict');
const {read}=require('./review_readiness_client.js');
const rid='a'.repeat(32);
const base={origin:'https://bam.example',token:'t'.repeat(43),
  expectedTenantId:'shop'};
const sample={tenant_id:'shop',status:'review_preview_only',
  held_count:1,editorial_material_complete_count:0,
  items:[{request_id:rid,revision:1,channel:'facebook',
    status:'needs_content',missing_items:['image'],
    unverified_items:[],editorial_material_complete:false,
    blockers:['missing_required_content','truthguard_review_required',
      'owner_approval_not_implemented','social_publishing_disabled'],
    approved:false,publishing_enabled:false}],
  approved_count:0,publishing_enabled:false};
const calls=[];
const make=body=>async(url,options)=>{
 calls.push({url,options});
 return {ok:true,status:200,json:async()=>body};
};
async function main(){
 const result=await read({...base,fetchImpl:make(sample)});
 assert.equal(result.heldCount,1);
 assert.equal(result.items[0].missingItems[0],'image');
 assert.equal(result.editorialMaterialCompleteCount,0);
 assert.ok(Object.isFrozen(result.items));
 assert.equal(calls[0].options.method,'GET');
 assert.equal(calls[0].options.credentials,'omit');
 assert.ok(calls[0].url.endsWith('/api/v1/review-readiness'));
 assert.equal(calls[0].options.body,undefined);
 const malformed=[
   {...sample,tenant_id:'other'},
   {...sample,status:'approved'},
   {...sample,approved_count:1},
   {...sample,held_count:2},
   {...sample,editorial_material_complete_count:1},
   {...sample,publishing_enabled:true},
   {...sample,items:[{...sample.items[0],approved:true}]},
   {...sample,items:[{...sample.items[0],blockers:['missing_required_content']}]},
   {...sample,items:[{...sample.items[0],publishing_enabled:true}]},
   {...sample,items:[...sample.items,...sample.items],held_count:2}
 ];
 for(const body of malformed)
  await assert.rejects(()=>read({...base,fetchImpl:make(body)}),TypeError);
 for(const invalid of [{origin:'http://bam.example'}, {token:'bad'},
                        {expectedTenantId:''}])
  await assert.rejects(
   ()=>read({...base,...invalid,fetchImpl:make(sample)}),TypeError);
 console.log('BAM private read-only editorial review client tests passed');
}
main().catch(error=>{console.error(error);process.exitCode=1});
