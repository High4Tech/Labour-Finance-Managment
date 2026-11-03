import {test} from 'node:test';
import assert from 'node:assert/strict';
import {workerErrors} from '../src/worker-model.mjs';
const valid={first_name:'أحمد',gender:'Male',date_of_birth:'1995-02-01',date_of_joining:'2020-02-01',status:'Active',pp_daily_rate:120,pp_monthly_rate:3200};
test('worker date, email and phone errors point to their field',()=>{const result=workerErrors({...valid,date_of_birth:'2027-01-01',personal_email:'bad',cell_number:'abc'},'2026-11-02');assert(result.date_of_birth);assert(result.date_of_joining);assert(result.personal_email);assert(result.cell_number);});
test('daily and monthly pay stay separate; loan and leave limits are enforced',()=>{assert.deepEqual(workerErrors(valid,'2026-11-02'),{});const errors=workerErrors({...valid,pp_leaves_per_month:32,pp_loan_wait_months:1.5,pp_loan_deduction_percent:101,pp_daily_rate:'NaN'},'2026-11-02');for(const key of ['pp_leaves_per_month','pp_loan_wait_months','pp_loan_deduction_percent','pp_daily_rate'])assert(errors[key]);});
