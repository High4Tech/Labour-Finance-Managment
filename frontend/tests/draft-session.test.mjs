import test from 'node:test';
import assert from 'node:assert/strict';
import {createDraftSession,hasAgreementContent} from '../src/draft-session.mjs';
test('defaults and rich-text blanks do not become empty drafts',async()=>{
 let writes=0;const initial={details:{scope:'<p><br></p>',effective_start:'2026-11-03'},terms:{billing_model:'Daily'}};
 const s=createDraftSession({initial:{},key:'x',persist:async()=>{writes++;}});s.update(initial);await s.flush();assert.equal(writes,0);assert.equal(hasAgreementContent(initial),false);assert.equal(hasAgreementContent({...initial,details:{agreement_title:'Festival'}}),true);
});
test('edits during a draft write serialize with the returned revision',async()=>{
 const writes=[];let release;const first=new Promise(r=>{release=r;});const s=createDraftSession({initial:{},key:'x',persist:async value=>{writes.push(value);if(writes.length===1)await first;return {name:'DRAFT-1',revision:writes.length};}});
 s.update({details:{agreement_title:'First'}});const a=s.flush();s.update({details:{agreement_title:'Latest'}});const b=s.flush();release();await Promise.all([a,b]);assert.equal(writes.length,2);assert.equal(writes[1].revision,1);assert.equal(writes[1].name,'DRAFT-1');assert.equal(writes[1].payload.details.agreement_title,'Latest');assert.equal(s.dirty(),false);
});
test('revision conflicts keep recovery and do not silently retry stale data',async()=>{
 let writes=0,forgot=0;const s=createDraftSession({initial:{},draft:{name:'d',revision:1},key:'x',forget:()=>forgot++,persist:async()=>{writes++;throw Error('This draft changed in another window. Reopen it before editing.');}});s.update({details:{agreement_title:'Changed'}});await assert.rejects(s.flush());await assert.rejects(s.flush());assert.equal(writes,1);assert.equal(forgot,0);
});
