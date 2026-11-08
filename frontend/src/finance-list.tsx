import {useEffect, useState} from 'react';
import {amount, t} from './bridge';
import {Badge, Button, DataTable, Feedback, Field, Icon, Input, Pagination} from './components';
import {useDebounced, useLiveUpdates, useResource} from './hooks';

const screens = {
 'Payment Entry': {title:'Receipts and payments', create:'Record payment', path:'payment-entry', party:'Party'},
 'Sales Invoice': {title:'Client invoices', create:'Create invoice', path:'sales-invoice', party:'Client'},
 'Purchase Invoice': {title:'Expenses', create:'Record expense', path:'purchase-invoice', party:'Supplier'},
 'Expense Claim': {title:'Worker reimbursements', create:'Record reimbursement', path:'expense-claim', party:'Worker'},
};
type Kind = keyof typeof screens;
type Row = {
 name:string; docstatus:number; posting_date:string; payment_type?:string;
 party_name?:string; party?:string; customer_name?:string; supplier_name?:string; employee_name?:string;
 grand_total?:number; total_claimed_amount?:number; paid_amount?:number;
 currency?:string; paid_from_account_currency?:string;
};
type Result = {rows:Row[]; has_more:boolean; project?:{name:string;title:string}};

export default function FinanceList({doctype, canCreate, canDelete,project}: {doctype:Kind; canCreate:boolean; canDelete:boolean;project?:string}) {
 const screen = screens[doctype];
 const [input,setInput] = useState('');
 const [page,setPage] = useState(1);
 const [selected,setSelected] = useState(new Set<string>());
 const search = useDebounced(input);
 const {data,error,loading,refresh} = useResource(signal => window.plus_point.form_rpc<Result>(
  'finance_hub.list_records', {doctype,search,start:(page-1)*20,project}, {signal}
 ), [doctype,search,page,project]);
 useLiveUpdates([doctype],refresh,['pp:data-changed']);
 useEffect(() => {setSelected(new Set());},[data]);
 const url = (row:Row) => '/desk/'+screen.path+'/'+encodeURIComponent(row.name);
 const switchExpenses = doctype === 'Purchase Invoice' || doctype === 'Expense Claim';
 return <section className="pp-r-screen pp-r-planning" aria-label={t(screen.title)} aria-busy={loading}>
  <header className="pp-resource-heading"><h1>{t(screen.title)}</h1><div className="pp-actions">
   <Button icon="refresh" aria-label={t('Refresh records')} onClick={refresh} disabled={loading}/>
   {switchExpenses && <a className="btn btn-default" href={doctype === 'Purchase Invoice' ? '/desk/expense-claim' : '/desk/purchase-invoice'}>{t(doctype === 'Purchase Invoice' ? 'Worker reimbursements' : 'Supplier expenses')}</a>}
   {canCreate && <Button tone="primary" icon="plus" onClick={() => window.frappe.new_doc(doctype,project&&doctype!=='Expense Claim'?{project}:undefined)}>{t(screen.create)}</Button>}
  </div></header>
  {data?.project&&<p>{t('Work')}: <strong>{data.project.title}</strong> · <a href={'/desk/'+screen.path}>{t('Show all records')}</a></p>}
  <div className="pp-r-list-filters">
   <Field label="Record ID">{id => <Input id={id} type="search" value={input} onChange={event => {setInput(event.target.value); setPage(1); setSelected(new Set());}}/>}</Field>
   <Button onClick={() => {sessionStorage.setItem('pp:finance:advanced',doctype); location.assign('/desk/'+screen.path);}}>{t('Advanced filters & exports')}</Button>
  </div>
  <Feedback message={error}/>{error && <Button onClick={refresh}>{t('Try again')}</Button>}
  <DataTable label={screen.title} rows={data?.rows ?? []} rowKey={row=>row.name} selected={selected} onSelect={setSelected}
   actions={canDelete && <Button tone="danger" disabled={loading} onClick={() => window.plus_point.delete_records(doctype,[...selected],() => {setPage(1); setSelected(new Set()); refresh();})}>{t('Delete selected')}</Button>}
   empty={loading?'Loading records…':'No records match this search'}
   columns={[
    {key:'record',label:'Record ID',render:row=><><a className="pp-r-record-name" href={url(row)}>{row.name}</a>{row.payment_type&&<small>{t(row.payment_type)}</small>}</>},
    {key:'status',label:'Status',render:row=><Badge tone={row.docstatus===1?'success':row.docstatus===2?'error':'neutral'}>{t(row.docstatus===1?'Submitted':row.docstatus===2?'Cancelled':'Draft')}</Badge>},
    {key:'party',label:screen.party,render:row=>row.party_name||row.party||row.customer_name||row.supplier_name||row.employee_name||'—'},
    {key:'date',label:'Posting date',render:row=>row.posting_date},
    {key:'total',label:'Total',numeric:true,render:row=>amount(row.paid_amount??row.grand_total??row.total_claimed_amount)+' '+(row.paid_from_account_currency||row.currency||'')},
    {key:'actions',label:'Actions',actions:true,render:row=><a className="btn btn-default pp-list-action" href={url(row)} aria-label={t('Open record')+' '+row.name}><Icon name="eye"/></a>},
   ]}/>
  <Pagination page={page} pages={page+Number(Boolean(data?.has_more))} disabled={loading} onPage={value=>{setPage(value);setSelected(new Set());}}/>
 </section>;
}
