/* Pure state rules shared by the screen and deterministic regression tests. */
export const balanceKey=row=>JSON.stringify([row.event,row.employee]);
export const payable=row=>Number(row.outstanding)>0;
export function selectedRows(rows,selected,key=balanceKey){return rows.filter(row=>selected.has(key(row)));}
/** @param {any[]} rows @param {Set<string>} selected @param {(row:any)=>string} key @param {(row:any)=>boolean} eligible */
export function toggleAll(rows,selected,key=balanceKey,eligible=(_row)=>true){
 const keys=rows.filter(eligible).map(key),all=keys.length>0&&keys.every(k=>selected.has(k));
 return new Set(all?[]:keys);
}
export function paymentErrors(values,today){
 const errors={};
 if(!values.account)errors.account='Choose the account these wages were paid from.';
 if(!/^\d{4}-\d{2}-\d{2}$/.test(values.posting_date)||values.posting_date>today)errors.posting_date='Choose the actual payment date, today or earlier.';
 if(values.reference.length>140)errors.reference='Use a payment reference of up to 140 characters.';
 if(!values.confirmed)errors.confirmed='Confirm that these wages have actually been paid.';
 return errors;
}
