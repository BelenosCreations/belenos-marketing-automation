'use strict';

const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');
const { webcrypto } = require('node:crypto');

const html = readFileSync(join(__dirname, '..', 'personal-post-studio.html'), 'utf8');
const script = html.match(/<script>([\s\S]+)<\/script>/)[1];

function element(value = '') {
  return {
    value, children: [], listeners: {}, attributes: {},
    append(child) { this.children.push(child); },
    replaceChildren() { this.children = []; },
    addEventListener(event, listener) { this.listeners[event] = listener; },
    setAttribute(name, value) { this.attributes[name] = value; },
    reportValidity() { return true; },
    focus() {},
    select() { this.textSelected = true; },
    classList: { toggle() {} }
  };
}

function open(storage, clipboard) {
  const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
  const fields = Object.fromEntries(ids.map(id => [id, element()]));
  fields.business.options = [...html.matchAll(/<option(?: value="([^"]+)")?>([^<]+)/g)]
    .map(([, value, label]) => ({ value: value ?? label }));
  fields.composer.reset = () => {
    fields.business.value = fields.business.options[0].value;
    for (const name of ['custom', 'topic', 'facts', 'post']) fields[name].value = '';
  };
  fields.composer.reset();
  const window = { confirm: () => true };
  runInNewContext(script, {
    document: { getElementById: id => fields[id], createElement: () => element() },
    localStorage: storage, navigator: { clipboard }, crypto: webcrypto, window
  });
  return { fields, window };
}

async function verify() {
  const saved = new Map();
  const storage = {
    getItem: key => saved.get(key) ?? null,
    setItem: (key, value) => saved.set(key, value)
  };
  const copied = [];
  const clipboard = { writeText: async text => copied.push(text) };
  const submit = fields => fields.composer.listeners.submit({ preventDefault() {} });
  let { fields } = open(storage, clipboard);
  fields.topic.value = 'Custom pet portraits';
  fields.facts.value = 'Combine separate photos.';
  fields['copy-prompt'].listeners.click();
  await new Promise(setImmediate);
  assert.match(copied[0], /Belenos Creations/);
  assert.match(copied[0], /Combine separate photos/);
  assert.match(copied[0], /Leave out unconfirmed hours, prices/);
  fields.post.value = 'Bring your favorite photos together in a custom pet portrait.';
  submit(fields);
  assert.match(fields.status.textContent, /Draft saved/);

  ({ fields } = open(storage, clipboard));
  fields.drafts.children[0].children[0].listeners.click();
  assert.match(fields.post.value, /favorite photos/);
  fields.post.value = 'Edited post.';
  submit(fields);
  assert.equal(fields.drafts.children.length, 1);
  fields['copy-post'].listeners.click();
  await new Promise(setImmediate);
  assert.equal(copied.at(-1), 'Edited post.');

  fields['new-draft'].listeners.click();
  fields.business.value = 'Busy B Cleaning Service LLC';
  fields.business.listeners.change();
  fields.topic.value = 'Office cleaning';
  fields['copy-prompt'].listeners.click();
  await new Promise(setImmediate);
  assert.match(copied.at(-1), /commercial cleaning/);
  assert.doesNotMatch(copied.at(-1), /Belenos Creations|Combine separate photos/);

  const blockedClipboard = { writeText: async () => { throw new Error('Unavailable'); } };
  const reopened = open(storage, blockedClipboard);
  fields = reopened.fields;
  fields.business.value = 'custom';
  fields.business.listeners.change();
  fields.custom.value = 'Another shop';
  fields.topic.value = 'New products';
  fields['copy-prompt'].listeners.click();
  await new Promise(setImmediate);
  assert.match(fields['prompt-text'].value, /Another shop/);
  assert.equal(fields['prompt-text'].textSelected, true);
  assert.equal(fields['prompt-fallback'].hidden, false);
  fields.post.value = 'Unsaved post.';
  fields.composer.listeners.input();
  reopened.window.confirm = () => false;
  fields.drafts.children[0].children[0].listeners.click();
  assert.equal(fields.post.value, 'Unsaved post.');
  assert.match(html, /href="https:\/\/chatgpt\.com\/" target="_blank" rel="noopener noreferrer"/);

  const broken = open({ getItem() { throw new Error('Blocked'); } }, clipboard);
  assert.match(broken.fields.status.textContent, /Saved drafts are unavailable/);
  console.log('BAM Personal Post Studio flow tests passed');
}

verify().catch(error => { console.error(error); process.exitCode = 1; });
