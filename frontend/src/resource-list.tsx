import {useEffect,useState} from 'react';
import {Badge,Button,DataTable,Feedback,Field,Icon,Input,Pagination,type Column} from './components';
import {t} from './bridge';
import {useDebounced,useLiveUpdates,useResource} from './hooks';
import {ResourceEditor} from './resource-editor';
import {resourceCall,resourceScreens,resourceStatus,resourceUrl,type ResourceKind,type ResourceOptions,type ResourceRow} from './resource-types';

type Result = {rows:ResourceRow[]; more:boolean};
export default function ResourceList({kind}:{kind:ResourceKind}) {
 const screen=resourceScreens[kind];
 const [query,setQuery]=useState(''),[page,setPage]=useState(1),[selected,setSelected]=useState(new Set<string>()),[creating,setCreating]=useState(false);
 const search=useDebounced(query);
 const list=useResource(signal=>resourceCall<Result>('list_records',{view:kind,search,offset:(page-1)*20},signal),[kind,search,page]);
 const options=useResource(signal=>resourceCall<ResourceOptions>('form_options',{},signal),[]);
 useLiveUpdates([screen.doctype,'PP Vehicle Booking','PP Equipment Booking'],list.refresh,['pp:data-changed']);
 useEffect(()=>setSelected(new Set()),[list.data]);
 const permissions=options.data?.permissions[kind];
 const columns:Column<ResourceRow>[]=[
  {key:'name',label:screen.singular,render:row=><><a className="pp-r-record-name" href={resourceUrl(kind,row.name)}>{row.title}</a><small>{row.pp_reference||row.name}</small></>},
  {key:'status',label:'Status',render:row=>{const status=resourceStatus(kind,row);return <Badge tone={status==='Assigned'?'info':status==='Active'||status==='Available'?'success':'neutral'}>{t(status)}</Badge>;}},
 ];
 if(kind==='equipment')columns.push({key:'unit',label:'Stock unit',render:row=>row.stock_uom});
 if(kind==='warehouses')columns.push({key:'ownership',label:'Ownership',render:row=>['Owned','Rented'].includes(row.warehouse_type||'')?row.warehouse_type:t('Not set')});
 if(kind==='vehicles')columns.push(
  {key:'model',label:'Make / model',render:row=>[row.make,row.model].filter(Boolean).join(' ')},
  {key:'seats',label:'Crew seats',render:row=>row.pp_crew_seats??0},
  {key:'capacity',label:'Inventory capacity',render:row=>(row.pp_cargo_capacity??0)+' '+(row.pp_cargo_uom||'units')},
 );
 columns.push({key:'actions',label:'Actions',actions:true,render:row=><a className="btn btn-default pp-list-action" href={resourceUrl(kind,row.name)} aria-label={t('Open')+' '+row.title} title={t('Open')}><Icon name="eye"/></a>});
 return <section className="pp-r-screen pp-r-planning" aria-label={t(screen.title)} aria-busy={list.loading}>
  <header className="pp-resource-heading"><h1>{t(screen.title)}</h1><div className="pp-actions">
   <Button icon="refresh" aria-label={t('Refresh records')} disabled={list.loading} onClick={list.refresh}/>
   <Button icon="upload" onClick={()=>void window.plus_point.open_import(options.data?.company,list.refresh,screen.kind)}>{t('Import')}</Button>
   {permissions?.create&&<Button icon="plus" tone="primary" onClick={()=>setCreating(true)}>{t(screen.create)}</Button>}
  </div></header>
  <div className="pp-r-list-filters"><Field label="Name or ID">{id=><Input id={id} type="search" value={query} onChange={event=>{setQuery(event.target.value);setPage(1);setSelected(new Set());}}/>}</Field>
   <Button onClick={()=>{sessionStorage.setItem('pp:resources:advanced',screen.doctype);location.assign('/desk/'+screen.path);}}>{t('Advanced filters & exports')}</Button>
  </div>
  <Feedback message={list.error||options.error}/>
  {(list.error||options.error)&&<Button onClick={()=>{list.refresh();options.refresh();}}>{t('Try again')}</Button>}
  <DataTable label={screen.title} rows={list.data?.rows||[]} rowKey={row=>row.name} selected={selected} onSelect={setSelected} columns={columns}
   actions={permissions?.delete&&<Button icon="delete" tone="danger" disabled={list.loading} onClick={()=>window.plus_point.delete_records(screen.doctype,[...selected],()=>{setSelected(new Set());setPage(1);list.refresh();})}>{t('Delete selected')}</Button>}
   empty={list.loading?'Loading records…':'No records match this search'}/>
  <Pagination page={page} pages={page+Number(Boolean(list.data?.more))} disabled={list.loading} onPage={value=>{setPage(value);setSelected(new Set());}}/>
  {creating&&options.data&&<ResourceEditor kind={kind} options={options.data} onClose={()=>setCreating(false)} onSaved={name=>{setCreating(false);window.frappe.set_route('pp-inventory',{view:kind,record:name});}}/>}
 </section>;
}
