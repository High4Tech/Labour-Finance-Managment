import {useRef,useState} from 'react';
import {Badge,Button,DataTable,Dialog,Feedback,Field,Input,Panel,Select,SummaryCards,Textarea} from './components';
import {changed,t} from './bridge';
import {useDebounced,useLiveUpdates,useResource} from './hooks';
import {AgreementPayments} from './agreement-payments';
import {call,date,money,type Agreement,type DocumentFile} from './agreement-types';
import {DocumentPreview} from './documents';
import {RichContent} from './form-components';

type Invoice={name:string;posting_date:string;due_date:string;grand_total:number;outstanding_amount:number;currency:string;docstatus:number;status:string};
type Billing={agreement:Agreement & {project:string};totals:Record<string,string>;unbilled_count:number;invoices:Invoice[]};
export default function BillingPage({agreement,invoice}:{agreement?:string;invoice?:string}){
 const [selected,setSelected]=useState(agreement||''),[query,setQuery]=useState(''),[preview,setPreview]=useState<DocumentFile>(),[editing,setEditing]=useState(invoice),[creating,setCreating]=useState<'work'|'extra'>();
 const search=useDebounced(query);
 const choices=useResource(signal=>!selected?call<{name:string;title:string}[]>('company_tools.search',{kind:'agreements',text:search},signal):Promise.resolve([]),[selected,search]);
 const data=useResource(signal=>selected?call<Billing>('operations.billing',{contract_terms:selected},signal):Promise.resolve(undefined),[selected]);
 useLiveUpdates(['Sales Invoice','PP Work Entry','PP Milestone','Payment Entry'],data.refresh,['pp:data-changed']);
 const agreementData=data.data?.agreement;
 return <section className="pp-r-screen pp-r-billing" aria-label={t('Billing and invoices')} aria-busy={data.loading}>
  <header className="pp-resource-heading"><h1>{t('Billing and invoices')}</h1><div className="pp-actions"><a className="btn btn-default" href="/desk/sales-invoice">{t('All client invoices')}</a><Button icon="refresh" disabled={data.loading} onClick={data.refresh} aria-label={t('Refresh billing')}/>{selected&&<Button onClick={()=>{setSelected('');setEditing(undefined);}}>{t('Change agreement')}</Button>}</div></header>
  <Feedback message={data.error||choices.error}/>{data.error&&<Button onClick={data.refresh}>{t('Try again')}</Button>}
  {!selected&&<Panel title="Choose agreement" icon="document"><Field label="Agreement">{id=><Select id={id} label="Agreement" value={selected} onChange={setSelected} onSearch={setQuery} loading={choices.loading} options={[{value:'',label:t('Choose agreement')},...(choices.data||[]).map(row=>({value:row.name,label:row.title}))]}/>}</Field></Panel>}
  {data.data&&agreementData&&<>
   <Panel title={agreementData.agreement_title} icon="document" actions={<a className="btn btn-default" href={'/desk/pp-agreements?record='+encodeURIComponent(selected)}>{t('Open agreement')}</a>}><p>{agreementData.pp_reference} · {t(agreementData.billing_model)} · {agreementData.agreement_currency}</p></Panel>
   <SummaryCards items={[
    ['Earned revenue','earned_revenue'],['Wages earned','labour_cost'],['Other costs','other_project_costs'],['Operational contribution','operational_profit'],['Client outstanding','client_outstanding_gross'],['Cash received','cash_collected_gross'],['Wages paid','wages_paid'],['Wages outstanding','wages_outstanding'],
   ].map(([label,key])=>({label,value:money(Number(data.data!.totals[key]||0)/(Number(agreementData.agreement_rate)||1),agreementData.agreement_currency)}))}/>
   <AgreementPayments data={agreementData} canEdit={window.frappe.model.can_write('PP Contract Terms')} onSaved={data.refresh} onPreview={setPreview}/>
   <Panel title="Client invoices" icon="invoice" actions={<div className="pp-actions"><Button tone="primary" icon="plus" onClick={()=>setCreating('work')}>{t('Generate from approved work')}</Button><Button onClick={()=>setCreating('extra')}>{t('Add extra invoice')}</Button></div>}>
    <DataTable label="Client invoices" rows={data.data.invoices} rowKey={row=>row.name} columns={[
     {key:'invoice',label:'Invoice',render:row=><Button tone="link" onClick={()=>setEditing(row.name)}>{row.name}</Button>},
     {key:'date',label:'Date',render:row=>date(row.posting_date)},
     {key:'total',label:'Amount',numeric:true,render:row=>money(row.grand_total,row.currency)},
     {key:'outstanding',label:'Outstanding',numeric:true,render:row=>money(row.outstanding_amount,row.currency)},
     {key:'status',label:'Status',render:row=><Badge tone={row.docstatus===1?'success':row.docstatus===2?'error':'neutral'}>{t(row.status)}</Badge>},
     {key:'actions',label:'Actions',actions:true,render:row=><Button icon="eye" aria-label={t('Review invoice')+' '+row.name} onClick={()=>setEditing(row.name)}/>},
    ]}/>
   </Panel>
   <Panel title="Costs and payments"><div className="pp-actions">{[['purchase-invoice','Project expenses'],['pp-wage-settlement','Worker payments'],['payment-entry','Client receipts']].map(([path,label])=><a key={path} className="btn btn-default" href={'/desk/'+path+'?project='+encodeURIComponent(agreementData.project)}>{t(label)}</a>)}</div></Panel>
   <BrandingSettings/>
  </>}
  {creating&&agreementData&&<CreateInvoice agreement={agreementData} kind={creating} onClose={()=>setCreating(undefined)} onSaved={name=>{setCreating(undefined);setEditing(name);data.refresh();}}/>}
  {editing&&<InvoiceDialog name={editing} onClose={()=>setEditing(undefined)} onSaved={data.refresh} onPreview={file=>{setEditing(undefined);setPreview(file);}}/>}
  {preview&&<DocumentPreview file={preview} onClose={()=>setPreview(undefined)}/>}
 </section>;
}
function CreateInvoice({agreement,kind,onClose,onSaved}:{agreement:Agreement;kind:'work'|'extra';onClose:()=>void;onSaved:(name:string)=>void}){
 const [description,setDescription]=useState(''),[value,setValue]=useState(''),[first,setFirst]=useState(''),[last,setLast]=useState('');
 const [error,setError]=useState(''),[busy,setBusy]=useState(false),[errors,setErrors]=useState<Record<string,string>>({}),lock=useRef(false);
 async function save(){
  if(lock.current)return;
  const validation:Record<string,string>={};
  if(kind==='extra'){
   if(!description.trim())validation.description=t('Describe the extra charge.');
   if(!(Number(value)>0))validation.amount=t('Enter an amount greater than zero.');
  }
  if(kind==='work'&&((first&&!last)||(!first&&last)||first&&last<first))validation.dates=t('Choose both dates with the end on or after the start.');
  setErrors(validation);if(Object.keys(validation).length)return;
  lock.current=true;setBusy(true);setError('');
  try{
   const options=await call<{item:string;currency:string;exchange_rate:number}>('operations.prepare_billing',{contract_terms:agreement.name});
   const args={contract_terms:agreement.name,item_code:options.item,invoice_currency:agreement.agreement_currency,exchange_rate:agreement.agreement_rate};
   const result=kind==='work'?await call<{name:string}>('billing.create_invoice',{...args,from_date:first||undefined,to_date:last||undefined}):await call<{name:string}>('operations.extra_invoice',{...args,description,amount:value});
   changed();onSaved(result.name);
  }catch(cause){setError((cause as Error).message);}finally{setBusy(false);lock.current=false;}
 }
 return <Dialog title={kind==='work'?'Generate from approved work':'Extra client charge'} busy={busy} onClose={onClose} footer={<><Button disabled={busy} onClick={onClose}>{t('Cancel')}</Button><Button tone="primary" loading={busy} onClick={()=>void save()}>{t('Create invoice draft')}</Button></>}>
  <p>{agreement.agreement_title} · {agreement.agreement_currency}</p><Feedback message={error}/>
  {kind==='extra'?<><Field label="Charge description *" error={errors.description}>{(id,help)=><Textarea id={id} disabled={busy} value={description} aria-invalid={!!errors.description} aria-describedby={help} onChange={e=>setDescription(e.target.value)}/>}</Field><Field label={'Amount ('+agreement.agreement_currency+') *'} error={errors.amount}>{(id,help)=><Input id={id} type="number" min={0} step="any" disabled={busy} value={value} aria-invalid={!!errors.amount} aria-describedby={help} onChange={e=>setValue(e.target.value)}/>}</Field></>:<>
   <Feedback tone="info" message="The invoice uses approved work that has not already been invoiced."/>
   <Field label="From date (optional)" error={errors.dates}>{id=><Input id={id} type="date" value={first} disabled={busy} aria-invalid={!!errors.dates} onChange={e=>setFirst(e.target.value)}/>}</Field>
   <Field label="Through date (optional)" error={errors.dates}>{id=><Input id={id} type="date" min={first} value={last} disabled={busy} aria-invalid={!!errors.dates} onChange={e=>setLast(e.target.value)}/>}</Field>
  </>}
 </Dialog>;
}
type InvoiceDetail={name:string;project:string;docstatus:number;due_date:string;remarks:string;currency:string;exchange_rate:number;items:{name:string;description:string;qty:number;rate:number;amount:number;locked:boolean}[]};
function InvoiceDialog({name,onClose,onSaved,onPreview}:{name:string;onClose:()=>void;onSaved:()=>void;onPreview:(file:DocumentFile)=>void}){
 const resource=useResource(signal=>call<InvoiceDetail>('operations.invoice',{name},signal),[name]);
 return <Dialog title={'Invoice '+name} onClose={onClose} footer={<Button onClick={onClose}>{t('Close')}</Button>}><Feedback message={resource.error}/>{resource.data?<InvoiceFields key={resource.data.name+'-'+resource.data.docstatus} data={resource.data} onSaved={()=>{resource.refresh();onSaved();}} onPreview={onPreview}/>:<Button disabled={resource.loading} onClick={resource.refresh}>{t(resource.loading?'Loading invoice…':'Try again')}</Button>}</Dialog>;
}
function InvoiceFields({data,onSaved,onPreview}:{data:InvoiceDetail;onSaved:()=>void;onPreview:(file:DocumentFile)=>void}){
 const [due,setDue]=useState(data.due_date||''),[remarks,setRemarks]=useState(data.remarks||''),[rates,setRates]=useState<Record<string,string>>({});
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[confirm,setConfirm]=useState(false),[email,setEmail]=useState(false),lock=useRef(false);
 async function action(kind:'save'|'post'|'pdf'){
  if(lock.current)return;lock.current=true;setBusy(true);setError('');
  try{
   if(kind==='save')await call('operations.update_invoice',{name:data.name,values:{due_date:due,remarks,items:Object.entries(rates).map(([name,rate])=>({name,rate}))}});
   if(kind==='post')await call('operations.post_invoice',{name:data.name});
   if(kind==='pdf')onPreview(await call<DocumentFile>('agreement_documents.invoice_pdf',{name:data.name}));
   else{changed();setRates({});setConfirm(false);onSaved();}
  }catch(cause){setError((cause as Error).message);}finally{setBusy(false);lock.current=false;}
 }
 return <>
  <Feedback message={error}/><p>{data.currency} · {t(data.docstatus===1?'Submitted':data.docstatus===2?'Cancelled':'Draft')}</p>
  <Field label="Payment due">{id=><Input id={id} type="date" value={due} disabled={busy||!!data.docstatus} onChange={e=>setDue(e.target.value)}/>}</Field>
  <DataTable label="Invoice items" rows={data.items} rowKey={row=>row.name} columns={[
   {key:'description',label:'Description',render:row=><RichContent value={row.description}/>},
   {key:'qty',label:'Quantity',numeric:true,render:row=>row.qty},
   {key:'rate',label:'Rate',numeric:true,render:row=>row.locked||data.docstatus?money(row.rate,data.currency):<Field label="Rate">{id=><Input id={id} type="number" min={0} step="any" value={rates[row.name]??row.rate} disabled={busy} onChange={e=>setRates(previous=>({...previous,[row.name]:e.target.value}))}/>}</Field>},
   {key:'amount',label:'Amount',numeric:true,render:row=>money(row.qty*Number(rates[row.name]??row.rate),data.currency)},
  ]}/>
  <Field label="Remarks">{id=><Textarea id={id} value={remarks} disabled={busy||!!data.docstatus} onChange={e=>setRemarks(e.target.value)}/>}</Field>
  <div className="pp-actions">{data.docstatus===0&&<><Button disabled={busy} onClick={()=>void action('save')}>{t('Save draft')}</Button><Button tone="primary" disabled={busy||due!==data.due_date||remarks!==(data.remarks||'')||Object.keys(rates).length>0} onClick={()=>setConfirm(true)}>{t('Submit invoice')}</Button></>}<Button disabled={busy} icon="document" onClick={()=>void action('pdf')}>{t('PDF preview')}</Button><Button disabled={busy} icon="mail" onClick={()=>setEmail(true)}>{t('Email invoice')}</Button><a className="btn btn-default" href={'/desk/sales-invoice/'+encodeURIComponent(data.name)}>{t('Advanced accounting controls')}</a></div>
  {confirm&&<Dialog title="Submit invoice?" busy={busy} onClose={()=>setConfirm(false)} footer={<><Button disabled={busy} onClick={()=>setConfirm(false)}>{t('Cancel')}</Button><Button tone="primary" loading={busy} onClick={()=>void action('post')}>{t('Submit saved invoice')}</Button></>}><p>{t('This posts the saved invoice to the accounts. Save any changes before submitting.')}</p><Feedback message={error}/></Dialog>}
  {email&&<InvoiceEmail name={data.name} onClose={()=>setEmail(false)}/>}
 </>;
}
function InvoiceEmail({name,onClose}:{name:string;onClose:()=>void}){
 const options=useResource(signal=>call<{recipient:string;configured:boolean}>('operations.email_options',{name},signal),[name]);
 const [recipient,setRecipient]=useState<string>(),[subject,setSubject]=useState('Invoice '+name),[body,setBody]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function send(){if(busy)return;const email=recipient??options.data?.recipient??'';if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)){setError(t('Enter a valid email address.'));return;}setBusy(true);try{await call('operations.email_invoice',{name,recipient:email,subject,body});onClose();}catch(cause){setError((cause as Error).message);}finally{setBusy(false);}}
 return <Dialog title="Email invoice" busy={busy} onClose={onClose} footer={<><Button disabled={busy} onClick={onClose}>{t('Cancel')}</Button><Button tone="primary" disabled={!options.data?.configured} loading={busy} onClick={()=>void send()}>{t('Send invoice')}</Button></>}><Feedback message={error||options.error}/>{options.data&&!options.data.configured&&<Feedback tone="info" message="Connect an outgoing email account before sending invoices."/>}<Field label="Recipient email *" error={error}>{id=><Input id={id} type="email" value={recipient??options.data?.recipient??''} onChange={e=>setRecipient(e.target.value)} aria-invalid={!!error}/>}</Field><Field label="Subject *">{id=><Input id={id} maxLength={140} value={subject} onChange={e=>setSubject(e.target.value)}/>}</Field><Field label="Message">{id=><Textarea id={id} value={body} onChange={e=>setBody(e.target.value)}/>}</Field></Dialog>;
}
function InvoiceBranding(){
 const resource=useResource(signal=>call<Record<string,string>>('experience.branding',{},signal),[]);
 const [draft,setDraft]=useState<Record<string,string>>({}),[busy,setBusy]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState(false);
 async function save(){if(busy)return;setBusy(true);setError('');try{await call('experience.save_branding',{values:draft});setDraft({});setSaved(true);resource.refresh();}catch(cause){setError((cause as Error).message);}finally{setBusy(false);}}
 return <Panel title="Invoice branding" icon="document" actions={<Button disabled={busy||!Object.keys(draft).length} onClick={()=>void save()}>{t('Save invoice branding')}</Button>}><Feedback message={error||resource.error}/>{saved&&<Feedback tone="success" message="Invoice branding saved."/>}{resource.data&&<><p>{resource.data.title}</p><Button icon="upload" onClick={()=>window.plus_point.open_file_upload({doctype:'Company',docname:resource.data!.name,restrictions:{allowed_file_types:['.png','.jpg','.jpeg','.webp']},make_attachments_public:false,on_success:async(file:{file_url:string})=>{try{await call('experience.save_branding',{values:{logo:file.file_url}});resource.refresh();}catch(cause){setError((cause as Error).message);}}})}>{t('Upload company logo')}</Button><div className="pp-r-grid">{[['email','Company email'],['phone','Company phone'],['address','Company address'],['tax_id','Tax / registration number']].map(([key,label])=><Field key={key} label={label}>{id=><Input id={id} type={key==='email'?'email':'text'} value={draft[key]??resource.data![key]} onChange={e=>{setDraft(previous=>({...previous,[key]:e.target.value}));setSaved(false);}}/>}</Field>)}</div></>}</Panel>;
}

function BrandingSettings(){
 const [open,setOpen]=useState(false);
 return <><Button aria-expanded={open} onClick={()=>setOpen(value=>!value)}>{t('Invoice branding settings')}</Button>{open&&<InvoiceBranding/>}</>;
}
