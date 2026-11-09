import test from 'node:test';
import assert from 'node:assert/strict';
import {eventErrors,matchingAllocations,payFor,roleCoverage} from '../src/event-model.mjs';
import {createDraftSession,hasPlanningContent} from '../src/draft-session.mjs';

test('event dates reject impossible dates, reversed ranges and agreement overflow',()=>{
 const value={event_name:'Conference',customer:'client',start_date:'2026-11-09',end_date:'2026-11-10',budget:0};
 assert.deepEqual(eventErrors(value),{});
 assert(eventErrors({...value,end_date:'2026-02-31'}).end_date);
 assert(eventErrors({...value,end_date:'2026-11-08'}).end_date);
 assert(eventErrors(value,{effective_start:'2026-11-09',effective_end:'2026-11-09'}).end_date);
 assert(eventErrors({...value,budget:'not a number'}).budget);
});
test('event defaults never save an empty draft; queued writes keep Event identity',async()=>{
 const initial={start_date:'2026-11-09',end_date:'2026-11-09',budget:0,billing_model:'Daily'};
 assert.equal(hasPlanningContent(initial,'Event'),false);
 const writes=[],session=createDraftSession({initial:{},kind:'Event',key:'event',persist:async value=>{writes.push(value);return {name:'event-draft',revision:1};}});
 session.update(initial);await session.flush();assert.equal(writes.length,0);
 session.update({...initial,event_name:'Summit'});await session.flush();
 assert.equal(writes.length,1);assert.equal(writes[0].kind,'Event');
 session.stop();session.update({...initial,event_name:'Late edit'});await session.flush();assert.equal(writes.length,1);
});
test('staffing coverage uses the least covered day and matches role, venue and dates',()=>{
 const row={site:'venue',designation:'Driver',start_date:'2026-11-09',end_date:'2026-11-10',workers_required:2};
 const event={coverage:[{site:'venue',designation:'Driver',date:'2026-11-09',assigned:2,missing:0},{site:'venue',designation:'Driver',date:'2026-11-10',assigned:1,missing:1}],allocations:[{site:'venue',designation:'Driver',start_date:'2026-11-09',end_date:'2026-11-09'},{site:'venue',designation:'Cleaner',start_date:'2026-11-09'},{site:'other',designation:'Driver',start_date:'2026-11-09'}]};
 assert.deepEqual(roleCoverage(event,row),{required:2,assigned:1,missing:1});assert.equal(matchingAllocations(event,row).length,1);
});
test('monthly event pay uses profile salary on the server and daily overrides convert once',()=>{
 const worker={pay_rates:{daily:160,monthly:3000}};
 assert.deepEqual(payFor(worker,'Monthly','999',3.67),{basis:'Monthly',amount:null});
 assert.deepEqual(payFor(worker,'Daily',undefined,3.67),{basis:'Daily',amount:160});
 assert.deepEqual(payFor(worker,'Daily','100',3.67),{basis:'Daily',amount:367});
});
