'use strict';
const assert=require('node:assert/strict');
const {parse}=require('./held_draft_csv_import.js');
const header='channel,draft_text,suggestion,required_items';
const rows=parse(header+'\r\n'+
 'facebook,"New, local tumbler",Use verified photo,image|permission\r\n'+
 'instagram,"Custom ""3D"" design",Need image,\r\n');
assert.equal(rows.length,2);
assert.equal(rows[0].draftText,'New, local tumbler');
assert.deepEqual([...rows[0].requiredItems],['image','permission']);
assert.equal(rows[1].draftText,'Custom "3D" design');
assert.deepEqual([...rows[1].requiredItems],['image']);
assert.ok(Object.isFrozen(rows));
const multiline=parse(header+'\n'+
 'facebook,"New work\non canvas",Include real image,image');
assert.equal(multiline[0].draftText,'New work\non canvas');
const bom=parse('\uFEFF'+header+'\nfacebook,Post,Tip,image');
assert.equal(bom[0].channel,'facebook');
for(const text of [
 '',header,header+'\n',
 'draft_text,suggestion,channel,required_items\nPost,Tip,facebook,image',
 header+'\nfacebook,post,tip',
 header+'\nfacebook,post,tip,image,image',
 header+'\nfacebook,"unterminated,tip,image',
 header+'\nfacebook,"quoted"x,tip,image',
 header+'\nfacebook,post,tip,image|image',
 header+'\nunknown,post,tip,image',
 header+'\nfacebook,post,,image',
 header+'\nfacebook,post,tip,image\nfacebook, POST ,tip,image',
 header+'\nfacebook,post,tip,image\n'.repeat(22),
 header+'\nfacebook,'+'a'.repeat(2001)+',tip,image',
 header+'\nfacebook,post,tip,'+'a'.repeat(81)
])assert.throws(()=>parse(text),TypeError);
console.log('BAM strict unpublished draft CSV parser tests passed');
