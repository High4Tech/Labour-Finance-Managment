import {test} from 'node:test';
import assert from 'node:assert/strict';
import {clientErrors} from '../src/client-model.mjs';
const base={customer_name:'مؤسسة النور',customer_type:'Company',contact_name:'Ali',country:'Saudi Arabia',city:'Riyadh',address_line1:'8 King Fahd Road',default_currency:'SAR',email:'ali@example.invalid',phone:''};
test('client contact requires at least one usable contact method and validates each entered value',()=>{
 assert.deepEqual(clientErrors(base),{});
 assert(clientErrors({...base,email:'',phone:''}).email);
 assert(clientErrors({...base,email:'bad'}).email);
 assert(clientErrors({...base,phone:'123ABC456'}).phone);
 assert.deepEqual(clientErrors({...base,email:'',phone:'+966 500 000 123'}),{});
});
test('client address, currency and type errors belong to their fields',()=>{
 const errors=clientErrors({...base,country:'',city:'',default_currency:'',customer_type:'Other'});
 for(const key of ['country','city','default_currency','customer_type'])assert(errors[key]);
});
