import test from 'node:test';import assert from 'node:assert/strict';
import {builderInitial,builderValues,builderErrors} from '../src/agreement-builder-model.mjs';
test('legacy partial drafts retain details and display-currency prices',()=>{
 const state=builderInitial({}, {details:{agreement_title:'Expo'},terms:{agreement_currency:'SAR'},staffing:[{site:'temporary',site_name:'Hall',designation:'Event crew',client_rate:90,workers_required:3}]},{default_currency:'AED'},'2026-11-03');
 const value=builderValues(state);assert.equal(state.terms.agreement_currency,'SAR');assert.equal(value.staffing[0].site,undefined);assert.equal(value.staffing[0].client_rate,90);assert.equal(value.staffing[0].start_date,'2026-11-03');assert.equal(value.agreement_title,'Expo');
});
test('rate card is authoritative and fixed billing never posts per-person charges',()=>{
 const state=builderInitial({}, {}, {default_currency:'SAR'},'2026-11-03');state.resource_mode='Rate card';state.rate_card=[{designation:'Driver',client_rate:400}];state.staffing=[{designation:'Driver',client_rate:12,workers_required:1}];assert.equal(builderValues(state).staffing[0].client_rate,400);state.terms.billing_model='Fixed';state.terms.fixed_amount=500;assert.equal(builderValues(state).staffing[0].client_rate,0);
});
test('dates, required payment plan and final email validation gate creation',()=>{
 const state=builderInitial({}, {}, {default_currency:'SAR'},'2026-11-03');state.details.effective_start='2026-11-02';state.details.effective_end='2026-11-01';assert.ok(builderErrors(0,state,{},'2026-11-03').effective_start);assert.ok(builderErrors(0,state,{},'2026-11-03').effective_end);assert.ok(builderErrors(1,state).payments);state.sharing={send_email:true,recipient:'invalid',cc:'also invalid'};assert.ok(builderErrors(2,state).recipient);assert.ok(builderErrors(2,state).cc0);
});
