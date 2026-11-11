'use strict';
/* Exercise the actual HTML script order in browser-global mode instead of
 * CommonJS require() mode. No server, browser, storage or network necessary.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'bam_signed_in_shell.html'),'utf8');
const scripts=[...html.matchAll(/<script\s+src="([^"]+)"\s*><\/script>/g)].map(x=>x[1]);
assert.ok(scripts.length>15);
assert.equal(new Set(scripts).size,scripts.length);
const context=vm.createContext({console});
for(const name of scripts){
  assert.match(name,/^[a-z0-9_-]+\.js$/i);
  const code=fs.readFileSync(path.join(__dirname,name),'utf8');
  assert.doesNotThrow(()=>vm.runInContext(code,context,{filename:name,
    timeout:2000}),name+' should load with previous browser globals');
}
for(const key of [
  'BAMDashboardData','BAMReadClient','BAMLiveDashboard',
  'BAMAIWorkspace','BAMAuthenticatedWorkspace','BAMSessionController',
  'BAMSignedInShell','BAMHeldDraftWorkspace','BAMPostingPreferencesWorkspace',
  'BAMAIDraftEditClient','BAMLocalProductDraftClient',
  'BAMReviewReadinessClient','BAMReviewFeedbackClient'
]){
  assert.equal(typeof context[key],'object',key+' browser API missing');
}
assert.equal(typeof context.BAMSignedInShell.mount,'function');
assert.equal(typeof context.BAMAuthenticatedWorkspace.create,'function');
console.log('BAM complete browser-global module graph passed');
