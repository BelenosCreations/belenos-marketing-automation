'use strict';
const assert=require('node:assert/strict');
const {render,CHATGPT_URL}=require('./ai_manual_image_handoff.js');
function node(tag){return {tag,textContent:'',children:[],listeners:{},
  append(...items){this.children.push(...items)},
  replaceChildren(...items){this.children=items},
  addEventListener(event,fn){this.listeners[event]=fn}}}
const document={createElement:node},container=node('main');
const copied=[],opened=[];
const args={document,container,imagePrompt:'A blue tumbler on a desk',
  copyText:value=>copied.push(value),
  openUrl:url=>opened.push(url),needsMedia:true};
const result=render(args);
assert.equal(result.mediaNeeded,true);
assert.equal(result.publishingEnabled,false);
assert.equal(copied.length,0);
assert.equal(opened.length,0);
const section=container.children[0];
section.children[3].listeners.click();
assert.deepEqual(copied,['A blue tumbler on a desk']);
section.children[4].listeners.click();
assert.deepEqual(opened,[CHATGPT_URL]);
assert.equal(CHATGPT_URL,'https://chatgpt.com/');
const original=container.children[0];
assert.throws(()=>render({...args,needsMedia:false}),TypeError);
assert.throws(()=>render({...args,imagePrompt:''}),TypeError);
assert.equal(container.children[0],original);
console.log('BAM manual ChatGPT image handoff tests passed');
