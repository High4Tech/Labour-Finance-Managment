export function eventErrors(value,agreement){
 const errors={};
 if(!String(value.event_name||'').trim())errors.event_name='Enter an event name.';
 if(!value.contract_terms&&!value.customer)errors.customer='Choose a client or an active agreement.';
 const validDate=raw=>/^\d{4}-\d{2}-\d{2}$/.test(raw||'')&&Number.isFinite(Date.parse(raw))&&new Date(raw).toISOString().slice(0,10)===raw;
 if(!validDate(value.start_date))errors.start_date='Choose a valid event start date.';
 if(!validDate(value.end_date))errors.end_date='Choose a valid event end date.';
 if(value.start_date>value.end_date)errors.end_date='Choose an end date on or after the start date.';
 if(agreement&&(value.start_date<agreement.effective_start||agreement.effective_end&&value.end_date>agreement.effective_end))errors.end_date='Keep the event inside the agreement dates.';
 if(!Number.isFinite(Number(value.budget))||Number(value.budget)<0)errors.budget='Enter a budget of zero or more.';
 return errors;
}
export function matchingAllocations(event,row){return event.allocations.filter(a=>a.site===row.site&&(!row.designation||a.designation===row.designation)&&a.start_date<=row.end_date&&(!a.end_date||a.end_date>=row.start_date));}
export function roleCoverage(event,row){const days=event.coverage.filter(c=>c.site===row.site&&c.designation===(row.designation||'All crew')&&c.date>=row.start_date&&c.date<=row.end_date);return {required:row.workers_required,assigned:days.length?Math.min(...days.map(d=>Number(d.assigned))):0,missing:days.length?Math.max(...days.map(d=>Number(d.missing))):row.workers_required};}
export const payFor=(worker,basis,override,rate=1)=>({basis,amount:basis==='Monthly'?null:override==null?Number(worker.pay_rates.daily):Number(override)*rate});
