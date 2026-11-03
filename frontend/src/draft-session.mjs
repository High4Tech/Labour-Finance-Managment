// One serialized write queue per form. Never poll or retry conflicts automatically.
export function hasAgreementContent(data={}) {
 const text=v=>String(v||'').replace(/<[^>]*>|&nbsp;/g,' ').trim();
 return !!(data.record||text(data.details?.agreement_title)||text(data.details?.scope)||data.customer||['staffing','sites','transport','milestones','daily_checkpoints','rate_card'].some(k=>data[k]?.length)||(data.conditions||[]).some(text)||data.client_mode==='Add new client'&&['customer_name','contact_name','email','phone','city','address_line1','address_line2','state','postal_code'].some(k=>text(data.client?.[k])));
}
export function createDraftSession({initial,draft,key,persist,notice=(_value)=>{},backup=(_value)=>{},forget=(_key)=>{}}) {
 let payload=initial,saved=JSON.stringify(initial),name=draft?.name,revision=draft?.revision,dirty=false,pending,stopped=false,conflict=false;
 const snapshot=()=>({kind:'Agreement',payload,name,client_key:key,revision});
 const flush=async()=>{
  if(stopped)return;
  if(pending){await pending;return dirty?flush():{name,revision};}
  if(conflict)throw Error('This draft changed in another window. Reopen it before saving more changes.');
  const serialized=JSON.stringify(payload);
  if(!dirty||serialized===saved){dirty=false;return {name,revision};}
  if(!name&&!hasAgreementContent(payload)){notice('Add details to start a draft');dirty=false;return {skipped:true};}
  const value=snapshot();backup(value);notice('Saving…');
  pending=(async()=>{try{const result=await persist(value);name=result.name;revision=result.revision;saved=serialized;dirty=JSON.stringify(payload)!==serialized;notice(result.skipped?'Add details to start a draft':'Draft saved');if(!dirty)forget(key);return result;}catch(error){conflict=/changed in another window|current draft before editing/i.test(error.message);notice(error.message);throw error;}})();
  try{await pending;}finally{pending=undefined;}
  return dirty?flush():{name,revision};
 };
 return {update(value){if(stopped)return;payload=value;dirty=JSON.stringify(value)!==saved;if(dirty&&(name||hasAgreementContent(value)))backup(snapshot());},flush,snapshot,dirty:()=>dirty,stop(){stopped=true;forget(key);},name:()=>name};
}
