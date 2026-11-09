import test from 'node:test';
import assert from 'node:assert/strict';
import {condition} from '../src/setup-conditions.mjs';
test('setup visibility supports declared choices, checks and parentheses without executing code',()=>{
 assert.equal(condition('eval:!doc.no_equipment && (doc.mode==="Add inventory item" || doc.set_stock_balance)',{no_equipment:0,mode:'Add inventory item'}),true);
 assert.equal(condition('eval:(doc.mode==="Add client agreement" || doc.edit_terms) && doc.billing_model==="Fixed"',{mode:'existing',edit_terms:1,billing_model:'Fixed'}),true);
 assert.equal(condition('eval:doc.mode==="Add client" || doc.edit_client',{mode:'existing',edit_client:0}),false);
 assert.equal(condition('eval:window.alert("bad")',{}),false);
 assert.equal(condition('eval:doc.constructor.constructor("bad")()',{}),false);
 assert.equal(condition('eval:!doc.no_vehicle',{no_vehicle:'0'}),false); // checkbox values are numeric
});
