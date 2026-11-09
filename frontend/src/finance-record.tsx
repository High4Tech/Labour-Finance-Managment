import {ReferenceDialog} from './payments';
import {useEffect,useRef,useState} from 'react';
import {Badge,Button,Checkbox,DataTable,Dialog,Feedback,Field,Input,Panel,Select,SummaryCards,Textarea} from './components';
import {changed,t} from './bridge';
import {useDebounced,useResource,useLiveUpdates} from './hooks';
import {call,money} from './agreement-types';
import {DocumentPreview,type PreviewData} from './documents';

type Value=string|number|null|undefined;
type Values=Record<string,Value|Line[]>;
type Line=Record<string,Value>;
type Definition={key:string;label:string;type:string;required:boolean;options:string;readonly:boolean;fields?:Definition[]};
type RecordData={name?:string;doctype:string;company:string;currency:string;modified:string;docstatus:number;fields:Definition[];values:Values;totals:Record<string,Value>;can_write:boolean;can_submit:boolean;advanced:string[]};
const paths:Record<string,string>={'PP Wage Settlement':'pp-wage-settlement','Payment Entry':'payment-entry','Purchase Invoice':'purchase-invoice','Sales Invoice':'sales-invoice','Expense Claim':'expense-claim'};
const titles:Record<string,string>={'PP Wage Settlement':'Worker wage payment','Payment Entry':'Receipt / payment','Purchase Invoice':'Supplier expense','Sales Invoice':'Client invoice','Expense Claim':'Worker reimbursement'};

export default function FinanceRecord({doctype,name,defaults,onAdvanced}:{doctype:string;name?:string;defaults?:Record<string,unknown>;onAdvanced:(values:Record<string,unknown>)=>Promise<void>}){
 const dirty=useRef(false);
 const initial=useRef(defaults);
 const record=useResource(signal=>call<RecordData>('finance_records.detail',{doctype,name,defaults:initial.current},signal),[doctype,name]);
 useLiveUpdates([doctype],()=>{if(!dirty.current)record.refresh();});
 return <section className="pp-r-screen pp-r-finance-record" aria-label={t(titles[doctype])} aria-busy={record.loading}>
  <Feedback message={record.error}/>{record.error&&<Button onClick={record.refresh}>{t('Try again')}</Button>}
  {record.data?<RecordForm key={(record.data.name||'new')+'-'+record.data.modified} data={record.data} onAdvanced={onAdvanced} onDirty={value=>{dirty.current=value;}} onSaved={saved=>{
   initial.current=undefined;changed();if(name)record.refresh();else window.frappe.set_route('Form',doctype,saved);
  }}/>:!record.error&&<p role="status">{t('Loading accounting record…')}</p>}
 </section>;
}

function RecordForm({data,onSaved,onDirty,onAdvanced}:{data:RecordData;onAdvanced:(values:Record<string,unknown>)=>Promise<void>;onDirty:(dirty:boolean)=>void;onSaved:(name:string)=>void}){
 const [values,setValues]=useState<Values>(data.values),[error,setError]=useState(''),[errors,setErrors]=useState<Record<string,string>>({});
 const [busy,setBusy]=useState(false),[posting,setPosting]=useState(false),lock=useRef(false),[confirm,setConfirm]=useState(false),[reference,setReference]=useState(false);
 const [preview,setPreview]=useState<(()=>Promise<PreviewData>)>();
 const disabled=!!data.docstatus||!data.can_write;
 const dirty=JSON.stringify(values)!==JSON.stringify(data.values);
 useEffect(()=>{onDirty(dirty);return()=>onDirty(false);},[dirty,onDirty]);
 const update=(key:string,value:Value|Line[])=>{setValues(previous=>({...previous,[key]:value,...(key==='currency'&&previous.currency!==value?{conversion_rate:''}:{}),...(key==='paid_from'&&previous.paid_from!==value?{source_exchange_rate:''}:{}),...(key==='paid_to'&&previous.paid_to!==value?{target_exchange_rate:''}:{}),...(key==='party_type'&&previous.party_type!==value?{party:'',paid_from:'',paid_to:''}:{})}));setErrors(previous=>({...previous,[key]:''}));};
 const currencies=useResource(signal=>data.doctype==='Payment Entry'&&(values.paid_from||values.paid_to)?call<{source?:string;target?:string}>('finance_records.payment_currencies',{paid_from:values.paid_from,paid_to:values.paid_to},signal):Promise.resolve({source:undefined,target:undefined}),[values.paid_from,values.paid_to]);
 useEffect(()=>{
  if(disabled)return;
  const rates:Values={};
  if(currencies.data?.source===data.currency)rates.source_exchange_rate=1;
  if(currencies.data?.target===data.currency)rates.target_exchange_rate=1;
  if(Object.keys(rates).length)setValues(previous=>({...previous,...rates}));
 },[currencies.data,data.currency,disabled]);
 const visibleFields=data.fields.filter(field=>field.key!=='source_exchange_rate'||currencies.data?.source&&currencies.data.source!==data.currency).filter(field=>field.key!=='target_exchange_rate'||currencies.data?.target&&currencies.data.target!==data.currency);
 const writable=Object.fromEntries(data.fields.filter(field=>!field.readonly).map(field=>[field.key,field.type==='Table'?(values[field.key] as Line[]||[]).map(row=>Object.fromEntries(Object.entries(row).filter(([key])=>key==='name'||field.fields?.some(child=>child.key===key&&!child.readonly)))):values[field.key]]));
 async function save(){
  if(lock.current)return;
  const missing=Object.fromEntries(visibleFields.filter(field=>!field.readonly&&field.required&&(!values[field.key]||(Array.isArray(values[field.key])&&!(values[field.key] as Line[]).length))).map(field=>[field.key,t('Enter ')+t(field.label)+'.']));
  for(const field of data.fields.filter(field=>field.type==='Table'&&!field.readonly)){
   const invalid=(values[field.key] as Line[]||[]).findIndex(row=>field.fields?.some(child=>child.required&&!child.readonly&&(row[child.key]==null||row[child.key]==='')));
   if(invalid>=0)missing[field.key]=t('Complete required fields in line ')+(invalid+1)+'.';
  }
  setErrors(missing);if(Object.keys(missing).length){requestAnimationFrame(()=>document.querySelector<HTMLElement>('[data-pp-react-root=finance-record] [aria-invalid=true]')?.focus());return;}
  lock.current=true;setBusy(true);setError('');
  try{const result=await call<{name:string}>('finance_records.save',{doctype:data.doctype,name:data.name,modified:data.modified,values:writable});onSaved(result.name);}
  catch(cause){const message=(cause as Error).message;setError(message);setErrors(Object.fromEntries(data.fields.filter(field=>message.toLocaleLowerCase().includes(field.label.toLocaleLowerCase())).map(field=>[field.key,message])));}
  finally{lock.current=false;setBusy(false);}
 }
 async function submit(){
  if(lock.current)return;lock.current=true;setPosting(true);setError('');
  try{await call('finance_records.submit',{doctype:data.doctype,name:data.name,modified:data.modified});setConfirm(false);onSaved(data.name!);}
  catch(cause){setError((cause as Error).message);}finally{lock.current=false;setPosting(false);}
 }
 async function advanced(){if(lock.current)return;lock.current=true;setBusy(true);setError('');try{await onAdvanced(disabled?{}:writable);}catch(cause){setError((cause as Error).message);setBusy(false);lock.current=false;}}
 const amounts=Object.entries(data.totals).filter(([key])=>!key.endsWith('_currency')).map(([key,value])=>({label:key.replaceAll('_',' '),value:money(Number(value||0),key==='paid_amount'?String(data.totals.paid_from_account_currency||data.currency):key==='received_amount'?String(data.totals.paid_to_account_currency||data.currency):data.currency)}));
 return <>
  <header className="pp-resource-heading"><div><a href={'/desk/'+paths[data.doctype]}>{t('Back to records')}</a><h1>{data.name||t('New '+titles[data.doctype].toLocaleLowerCase())}</h1><Badge tone={data.docstatus===1?'success':data.docstatus===2?'error':'neutral'}>{t(data.docstatus===1?'Submitted':data.docstatus===2?'Cancelled':'Draft')}</Badge></div><div className="pp-actions">
   {data.doctype==='PP Wage Settlement'&&data.docstatus===1&&data.can_write&&<Button icon="edit" onClick={()=>setReference(true)}>{t('Add / change reference')}</Button>}
   <Button disabled={busy||posting} onClick={()=>void advanced()}>{t('Advanced accounting controls')}</Button>
   {data.name&&<Button icon="document" disabled={busy||posting} onClick={()=>setPreview(()=>()=>call<PreviewData>('finance_records.print_data',{doctype:data.doctype,name:data.name}))}>{t('PDF preview')}</Button>}
   {data.name&&data.doctype==='Sales Invoice'&&values.project&&<a className="btn btn-default" href={'/desk/pp-client-billing?invoice='+encodeURIComponent(data.name)}>{t('Invoice workspace')}</a>}
   {!disabled&&!data.advanced.length&&<Button tone="primary" loading={busy} disabled={posting||currencies.loading} onClick={()=>void save()}>{t('Save draft')}</Button>}
   {data.name&&data.can_submit&&!data.docstatus&&<Button disabled={dirty||busy||posting} onClick={()=>setConfirm(true)}>{t('Submit record')}</Button>}
  </div></header>
  <Feedback message={error||currencies.error||''}/>
  {!!data.advanced.length&&<Feedback tone="info" message={t('This draft includes advanced accounting details. Open Advanced accounting controls to keep its allocations and taxes.')}/>}
  {disabled&&<Feedback tone="info" message="This record is read-only. Posted financial history is protected."/>}
  {data.doctype==='PP Wage Settlement'&&<Feedback tone="info" message="Link an already submitted employee payment for this worker and job. Submitting allocates that payment against approved wages; it does not send money."/>}
  <Panel title="Accounting details" icon="document"><p>{data.company} · {data.currency}</p><div className="pp-r-grid">
   {visibleFields.filter(field=>field.type!=='Table').map(field=><AccountField key={field.key} field={{...field,label:field.label+(['paid_amount','received_amount'].includes(field.key)?' ('+(field.key==='paid_amount'?currencies.data?.source||data.currency:currencies.data?.target||data.currency)+')':'')}} doctype={data.doctype} values={values} update={update} disabled={disabled||busy||posting} error={errors[field.key]}/>)}
  </div>{data.doctype==='Payment Entry'&&<PaymentAccounts values={values} update={update} disabled={disabled||busy}/>}</Panel>
  {data.fields.filter(field=>field.type==='Table').map(field=><Lines key={field.key} field={field} doctype={data.doctype} values={(values[field.key]||[]) as Line[]} update={rows=>update(field.key,rows)} disabled={disabled||field.readonly||busy||posting} currency={data.currency} error={errors[field.key]}/>)}
  <SummaryCards items={amounts}/>
  {dirty&&data.name&&<p>{t('Save your changes before submitting this record.')}</p>}
  {confirm&&<Dialog title="Submit accounting record?" busy={posting} onClose={()=>setConfirm(false)} footer={<><Button disabled={posting} onClick={()=>setConfirm(false)}>{t('Cancel')}</Button><Button tone="primary" loading={posting} onClick={()=>void submit()}>{t('Confirm and submit')}</Button></>}><p>{t('This posts the saved document using the existing accounting rules. Review its amounts and accounts first.')}</p><Feedback message={error||''}/></Dialog>}
  {reference&&<ReferenceDialog names={[data.name!]} onClose={()=>setReference(false)} onSaved={()=>{setReference(false);onSaved(data.name!);}}/>}
  {preview&&<DocumentPreview load={preview} onClose={()=>setPreview(undefined)}/>}
 </>;
}

function AccountField({field,doctype,values,update,disabled,error,parentfield}:{field:Definition;doctype:string;values:Values;update:(key:string,value:Value)=>void;disabled:boolean;error?:string;parentfield?:string}){
 const value=values[field.key],readonly=disabled||field.readonly;
 if(field.type==='Check')return <Field label={field.label} error={error}>{id=><Checkbox id={id} aria-label={field.label} checked={!!value} disabled={readonly} onChange={next=>update(field.key,Number(next.target.checked))}/>}</Field>;
 return <Field label={field.label+(field.required?' *':'')} error={error}>{(id,help)=>{
  const common={id,disabled:readonly,'aria-invalid':!!error,'aria-describedby':help};
  if(['Link','Dynamic Link'].includes(field.type))return <AccountLookup field={field} doctype={doctype} values={values} disabled={readonly} parentfield={parentfield} update={next=>update(field.key,next)} id={id} error={error}/>;
  if(field.type==='Select')return <Select {...common} invalid={!!error} label={field.label} value={String(value||'')} onChange={next=>update(field.key,next)} options={String(field.options||'').split('\n').map(option=>({value:option,label:option||t('Choose…')}))}/>;
  if(['Text','Small Text','Long Text','Text Editor'].includes(field.type))return <Textarea {...common} value={String(value||'')} onChange={event=>update(field.key,event.target.value)}/>;
  const numeric=['Currency','Float','Int','Percent'].includes(field.type);
  return <Input {...common} type={field.type==='Date'?'date':numeric?'number':'text'} step={field.type==='Int'?1:numeric?'any':undefined} value={String(value??'')} onChange={event=>update(field.key,event.target.value)}/>;
 }}</Field>;
}

function AccountLookup({field,doctype,values,update,disabled,parentfield,id,error}:{field:Definition;doctype:string;values:Values;update:(next:string)=>void;disabled:boolean;parentfield?:string;id:string;error?:string}){
 const [active,setActive]=useState(false),[query,setQuery]=useState(''),search=useDebounced(query),value=String(values[field.key]||''),partyType=String(values.party_type||'');
 const choices=useResource(signal=>!active||disabled||field.type==='Dynamic Link'&&!partyType?Promise.resolve([]):call<{value:string;label:string}[]>('finance_records.choices',{doctype,field:field.key,text:search,parentfield,party_type:partyType},signal),[doctype,field.key,parentfield,search,partyType,disabled,active]);
 const options=[{value:'',label:t('Choose…')},...(choices.data||[])];if(value&&!options.some(option=>option.value===value))options.push({value,label:value});
 return <><Select id={id} label={field.label} value={value} options={options} onChange={update} onSearch={next=>{setActive(true);setQuery(next);}} loading={choices.loading} disabled={disabled} invalid={!!error}/><Feedback message={choices.error}/></>;
}

function Lines({field,doctype,values,update,disabled,currency,error}:{field:Definition;doctype:string;values:Line[];update:(rows:Line[])=>void;disabled:boolean;currency:string;error?:string}){
 const [selected,setSelected]=useState(new Set<string>()),[editing,setEditing]=useState<number>(),[draft,setDraft]=useState<Line>({}),[errors,setErrors]=useState<Record<string,string>>({});
 const fields=field.fields||[];
 const edit=(index:number)=>{setEditing(index);setDraft(index<values.length?{...values[index]}:{});setErrors({});};
 function apply(){
  const missing=Object.fromEntries(fields.filter(item=>item.required&&!item.readonly&&!draft[item.key]).map(item=>[item.key,t('Enter ')+t(item.label)+'.']));setErrors(missing);if(Object.keys(missing).length)return;
  const rows=values.slice();rows[editing!]=draft;update(rows);setEditing(undefined);
 }
 return <Panel title={field.label} actions={!disabled&&<Button icon="plus" onClick={()=>edit(values.length)}>{t('Add line')}</Button>}><Feedback message={error||''}/>
  <DataTable label={field.label} rows={values} rowKey={row=>String(values.indexOf(row))} selected={selected} onSelect={disabled?undefined:setSelected} actions={<Button tone="danger" onClick={()=>{update(values.filter((_,index)=>!selected.has(String(index))));setSelected(new Set());}}>{t('Remove selected')}</Button>} columns={[
   ...fields.filter(item=>['item_code','description','qty','rate','expense_date','expense_type','amount','sanctioned_amount'].includes(item.key)).map(item=>({key:item.key,label:item.label,render:(row:Line)=>['Currency'].includes(item.type)?money(Number(row[item.key]||0),currency):String(row[item.key]||'—')})),
   {key:'actions',label:'Actions',actions:true,render:row=><Button icon="edit" aria-label={t('Edit line')} disabled={disabled} onClick={()=>edit(values.indexOf(row))}/>},
  ]}/>
  {editing!==undefined&&<Dialog title="Accounting line" onClose={()=>setEditing(undefined)} footer={<><Button onClick={()=>setEditing(undefined)}>{t('Cancel')}</Button><Button tone="primary" onClick={apply}>{t('Apply line')}</Button></>}><div className="pp-r-grid">{fields.map(item=><AccountField key={item.key} field={item} doctype={doctype} values={draft} parentfield={field.key} disabled={disabled} error={errors[item.key]} update={(key,value)=>{setDraft(previous=>({...previous,[key]:value}));setErrors(previous=>({...previous,[key]:''}));}}/>)}</div></Dialog>}
 </Panel>;
}

function PaymentAccounts({values,update,disabled}:{values:Values;update:(key:string,value:Value)=>void;disabled:boolean}){
 const [error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function fill(){if(busy)return;setBusy(true);setError('');try{
  const result=await call<{account:string;currency:string}>('finance_records.payment_accounts',{party_type:values.party_type,party:values.party,payment_type:values.payment_type,posting_date:values.posting_date});
  update(values.payment_type==='Receive'?'paid_from':'paid_to',result.account);
 }catch(cause){setError((cause as Error).message);}finally{setBusy(false);}}
 return <><Feedback message={error||''}/><Button disabled={disabled||!values.party||!values.party_type||values.payment_type==='Internal Transfer'} loading={busy} onClick={()=>void fill()}>{t('Use party’s accounting account')}</Button></>;
}
