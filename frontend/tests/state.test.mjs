import test from 'node:test';
import assert from 'node:assert/strict';
import {balanceKey,payable,selectedRows,toggleAll,paymentErrors} from '../src/model.mjs';
test('same worker in two events remains two independent balances',()=>{assert.notEqual(balanceKey({event:'A',employee:'1'}),balanceKey({event:'B',employee:'1'}));});
test('selection includes only eligible balances and clears all',()=>{const rows=[{event:'A',employee:'1',outstanding:'50'},{event:'B',employee:'1',outstanding:'0'}];const selected=toggleAll(rows,new Set(),balanceKey,payable);assert.deepEqual(selectedRows(rows,selected),[rows[0]]);assert.equal(toggleAll(rows,selected,balanceKey,payable).size,0);});
test('reference is optional, explicit actual-payment consent is mandatory',()=>{const values={account:'Cash',posting_date:'2026-11-01',reference:'',confirmed:true};assert.deepEqual(paymentErrors(values,'2026-11-02'),{});assert.ok(paymentErrors({...values,confirmed:false},'2026-11-02').confirmed);});
test('invalid dates, missing account and excessive references are field errors',()=>{const result=paymentErrors({account:'',posting_date:'2026-11-03',reference:'a'.repeat(141),confirmed:true},'2026-11-02');assert.deepEqual(Object.keys(result),['account','posting_date','reference']);});
test('keys cannot collide when identifiers contain separators',()=>{assert.notEqual(balanceKey({event:'a|b',employee:'c'}),balanceKey({event:'a',employee:'b|c'}));});
