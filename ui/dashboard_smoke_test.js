/* Offline BAM dashboard behavior smoke test (Node.js, no dependencies).
 * Minimal DOM stub only; run a real-browser accessibility test before release.
 */
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');

function makeNode(tag='div'){
  return {
    tag,children:[],style:{},dataset:{},listeners:{},
    get lastChild(){return this.children[this.children.length-1]},
    append(...children){this.children.push(...children)},
    replaceChildren(...children){this.children=children},
    addEventListener(name,fn){this.listeners[name]=fn},
    setAttribute(name,value){this[name]=value},
    setCustomValidity(){},reportValidity(){}
  };
}
const nodes={};
const document={
  documentElement:makeNode('html'),
  getElementById(id){return nodes[id]||(nodes[id]=makeNode())},
  createElement(tag){return makeNode(tag)}
};
const window={scrollTo(){}};
const html=fs.readFileSync(path.join(__dirname,'bam_dashboard_prototype.html'),'utf8');
const match=html.match(/<script>([\s\S]*?)<\/script>/);
assert.ok(match,'Embedded UI JavaScript must exist');
const context=vm.createContext({document,window,structuredClone:x=>JSON.parse(JSON.stringify(x))});
vm.runInContext(match[1],context,{filename:'bam_dashboard_prototype.html'});
const read=expression=>vm.runInContext(expression,context);

assert.equal(nodes.business.children.length,2,'Both demo businesses available');
assert.equal(read('counts().content'),2,'Belenos content-needed count');
assert.equal(read('counts().approval'),1,'Belenos approval count');
assert.equal(nodes.view.children.length,2,'Home cards and attention panel');

assert.equal(read('state.theme'),'auto','Auto follows device by default');
nodes.settingsButton.listeners.click();
assert.equal(nodes.heading.textContent,'Settings');
assert.equal(nodes.view.children.length,2,'Appearance and preferences sections');
const appearance=nodes.view.children[0];
const choices=appearance.children.find(node=>node.className==='setting-options');
assert.ok(choices,'Appearance options exist in Settings');
assert.equal(choices.children.length,3);
choices.children[0].listeners.click();
assert.equal(document.documentElement.dataset.theme,'light');
choices.children[1].listeners.click();
assert.equal(document.documentElement.dataset.theme,'dark');
const updated=nodes.view.children[0].children.find(node=>node.className==='setting-options');
updated.children[2].listeners.click();
assert.equal(read('state.theme'),'auto');

read("navigate('content')");
assert.equal(nodes.heading.textContent,'Content Studio');
read("navigate('content','c1')");
assert.ok(nodes.view.children.length>=2,'Draft detail view');
read("navigate('new')");
assert.equal(nodes.heading.textContent,'Create Draft');

nodes.business.listeners.change({target:{value:'cleaning'}});
assert.equal(read('state.business'),'cleaning');
assert.equal(read('counts().approval'),0,'No cross-business approvals');
assert.equal(read('posts().length'),2,'Only cleaning sample drafts visible');
assert.equal(nodes.heading.textContent,'Dashboard');

read("navigate('analytics')");
assert.equal(nodes.heading.textContent,'Analytics');
read("navigate('calendar')");
assert.equal(nodes.heading.textContent,'Calendar');
assert.equal(read("state.scheduling.cleaning.mode"),'smart');
let scheduleOptions=nodes.view.children[1].children.find(n=>n.className==='setting-options');
assert.equal(scheduleOptions.children.length,2);
scheduleOptions.children[1].listeners.click();
assert.equal(read("state.scheduling.cleaning.mode"),'manual');
let form=nodes.view.children[1].children.find(n=>n.tag==='form');
assert.ok(form,'Manual time entry form');
form.children[0].value='10:30';
form.listeners.submit({preventDefault(){}});
assert.equal(read("state.scheduling.cleaning.times[0]"),'10:30');
nodes.business.listeners.change({target:{value:'creations'}});
assert.equal(read("state.scheduling.creations.mode"),'smart');
assert.equal(read("state.scheduling.creations.times.length"),0);
assert.equal(read("state.scheduling.cleaning.times.length"),1);
console.log('BAM UI prototype smoke tests passed (stub DOM; not real browser)');
