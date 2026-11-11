'use strict';
const assert=require('node:assert/strict');
const {normalize}=require('./connections_contract.js');
const facebook={platform:'facebook',account_id:'main-page',scope:'read_insights',
  status:'connected',updated_at:100,expires_at:1000,publishing_enabled:false};
const body={tenant_id:'shop',visibility:'authorized',
  connections:[facebook],publishing_enabled:false};
const result=normalize(body);
assert.equal(result.tenantId,'shop');
assert.equal(result.connections[0].status,'connected');
assert.equal(result.connections[0].publishingEnabled,false);
assert.ok(Object.isFrozen(result.connections));
assert.deepEqual(normalize({...body,connections:[]}).connections,[]);
for(const bad of [
  {...body,publishing_enabled:true},
  {...body,visibility:'all_tenants'},
  {...body,tenant_id:''},
  {...body,connections:[{...facebook,vault_reference:'vault/secret'}]},
  {...body,connections:[{...facebook,token:'secret'}]},
  {...body,connections:[{...facebook,scope:'publish_posts'}]},
  {...body,connections:[{...facebook,scope:'write_insights'}]},
  {...body,connections:[{...facebook,status:'publishable'}]},
  {...body,connections:[{...facebook,publishing_enabled:true}]},
  {...body,connections:[{...facebook,expires_at:true}]},
  {...body,connections:[{...facebook,updated_at:-1}]},
  {...body,connections:[facebook,facebook]},
  {...body,connections:[{...facebook,account_id:' '}]},
  {...body,connections:[{...facebook,expires_at:'tomorrow'}]}
])assert.throws(()=>normalize(bad),TypeError);
console.log('BAM scoped connection status contract tests passed');
