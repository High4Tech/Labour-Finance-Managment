import {useRef,useState} from 'react';
import {Badge,Button,DataTable,Dialog,Feedback,Field,Input,Panel,SummaryCards} from './components';
import {Facts,RichContent,Tabs} from './form-components';
import {changed,t} from './bridge';
import {useLiveUpdates,useResource} from './hooks';
import {ResourceEditor} from './resource-editor';
import {WarehouseStock} from './warehouse-stock';
import {BookingDialog,ResourceBookings} from './resource-bookings';
import {resourceCall,resourceError,resourceScreens,resourceStatus,resourceEditorValues,type EquipmentProfile,type Overview,type ResourceKind,type ResourceOptions,type ResourceRow} from './resource-types';

type Profile = {equipment?:EquipmentProfile; overview?:Overview; row:ResourceRow};
export default function ResourceProfile({kind,name}:{kind:ResourceKind;name:string}){
 const screen=resourceScreens[kind],[tab,setTab]=useState('inventory'),[editing,setEditing]=useState(false),[creating,setCreating]=useState(false),[booking,setBooking]=useState(false),[rate,setRate]=useState(false);
 const [pendingItem,setPendingItem]=useState(''),[failure,setFailure]=useState(''),[attaching,setAttaching]=useState(false);
 const dirty=useRef(false);
 const options=useResource(signal=>resourceCall<ResourceOptions>('form_options',{},signal),[]);
 const resource=useResource(async signal=>{
  if(kind==='equipment'){
   const equipment=await resourceCall<EquipmentProfile>('equipment_profile',{name},signal);
   return {equipment,row:{name,title:equipment.title,disabled:equipment.disabled}} as Profile;
  }
  const overview=await resourceCall<Overview>('overview',{view:kind,name},signal),row=overview.rows[0];
  if(!row)throw new Error(t('This record is unavailable.'));
  return {overview,row:{...row,title:kind==='vehicles'?row.license_plate||row.name:row.title||String((row as ResourceRow&{warehouse_name?:string}).warehouse_name||row.name)}} as Profile;
 },[kind,name]);
 useLiveUpdates([screen.doctype,'PP Vehicle Booking','PP Equipment Booking','Stock Reconciliation'],()=>{if(!dirty.current)resource.refresh();});
 const permissions=options.data?.permissions[kind],canEdit=!!permissions?.write,data=resource.data;
 async function attach(item:string){
  setPendingItem(item);setAttaching(true);setFailure('');
  try{await resourceCall('attach_item',{warehouse:name,item});setPendingItem('');changed();resource.refresh();}
  catch(cause){setFailure(resourceError(cause));}finally{setAttaching(false);}
 }
 if(!data)return <section className="pp-r-screen"><Feedback message={resource.error||options.error}/><Button disabled={resource.loading} onClick={resource.refresh}>{t(resource.loading?'Loading resource…':'Try again')}</Button></section>;
 const {row,equipment,overview}=data;
 const state=resourceStatus(kind,row);
 const initial=resourceEditorValues(kind,row,name,equipment);
 const stockTotal=(key:'on_hand'|'reserved'|'available')=>equipment?.stock.reduce((sum,item)=>sum+Number(item[key]),0)||0;
 const refresh=()=>resource.refresh();
 return <section className="pp-r-screen pp-r-resource-profile" aria-label={row.title} aria-busy={resource.loading||attaching}>
  <header className="pp-resource-heading"><div><a href={'/desk/'+screen.path}>{t('Back to '+screen.title.toLowerCase())}</a><h1>{row.title}</h1><p>{equipment?.reference||row.pp_reference||name} · <Badge tone={['Active','Available'].includes(state)?'success':state==='Assigned'?'info':'neutral'}>{t(state)}</Badge></p></div><div className="pp-actions">
   {canEdit&&<Button icon="edit" onClick={()=>setEditing(true)} disabled={dirty.current||attaching}>{t('Edit details')}</Button>}
   {kind==='vehicles'&&canEdit&&<Button tone="primary" icon="calendar" onClick={()=>setBooking(true)}>{t('Assign to event')}</Button>}
   {permissions?.delete&&<Button tone="danger" icon="delete" onClick={()=>window.plus_point.delete_records(screen.doctype,[name],()=>window.frappe.set_route('List',screen.doctype))}>{t('Delete')}</Button>}
  </div></header>
  <Feedback message={resource.error||options.error||failure}/>
  {pendingItem&&<Button disabled={attaching} onClick={()=>void attach(pendingItem)}>{t('Retry adding created equipment to warehouse')}</Button>}
  {equipment&&<>
   <SummaryCards items={[
    {label:'On hand',value:stockTotal('on_hand')+' '+equipment.uom},{label:'Reserved today',value:stockTotal('reserved')+' '+equipment.uom},
    {label:'Available today',value:stockTotal('available')+' '+equipment.uom},{label:'Daily hire rate',value:Number(equipment.daily_rate).toLocaleString()+' '+equipment.currency+' / '+equipment.uom},
   ]}/>
   <Panel title="Equipment locations" icon="warehouse"><DataTable label="Equipment locations" rows={equipment.stock} rowKey={item=>item.warehouse} columns={[
    {key:'warehouse',label:'Warehouse',render:item=><a href={'/desk/pp-inventory?view=warehouses&record='+encodeURIComponent(item.warehouse)}>{item.title}</a>},
    {key:'on_hand',label:'On hand',numeric:true,render:item=>item.on_hand+' '+equipment.uom},
    {key:'reserved',label:'Reserved today',numeric:true,render:item=>item.reserved+' '+equipment.uom},
    {key:'available',label:'Available today',numeric:true,render:item=>item.available+' '+equipment.uom},
   ]}/></Panel>
   <Panel title="Daily hire pricing" icon="money" actions={canEdit&&<Button onClick={()=>setRate(true)}>{t('Edit daily hire rate')}</Button>}><p>{Number(equipment.daily_rate).toLocaleString()} {equipment.currency} / {equipment.uom} / {t('day')}</p>{equipment.description&&<RichContent value={equipment.description}/>}</Panel>
   <Panel title="Event reservations" icon="calendar"><ResourceBookings rows={equipment.bookings} onRefresh={refresh} canEdit={canEdit}/></Panel>
  </>}
  {kind==='vehicles'&&overview&&<>
   <Panel title="Vehicle details" icon="truck"><Facts items={[
    {label:'Make / model',value:[row.make,row.model].filter(Boolean).join(' ')},
    {label:'Crew seats',value:row.pp_crew_seats||0},
    {label:'Inventory capacity',value:(row.pp_cargo_capacity||0)+' '+row.pp_cargo_uom},
    {label:'Availability today',value:state},
   ]}/></Panel>
   <Panel title="Event assignments" icon="calendar"><ResourceBookings rows={overview.bookings} onRefresh={refresh} canEdit={canEdit}/></Panel>
  </>}
  {kind==='warehouses'&&overview&&<>
   <Panel title="Warehouse details" icon="warehouse"><Facts items={[{label:'Ownership',value:['Owned','Rented'].includes(row.warehouse_type||'')?row.warehouse_type:t('Not set')},{label:'Status',value:t(state)}]}/></Panel>
   <Tabs label="Warehouse sections" value={tab} onChange={value=>{if(dirty.current){setFailure(t('Save quantity changes before changing the section.'));return;}setTab(value);setFailure('');}} panelId="warehouse-panel" items={[{key:'inventory',label:'Inventory'},{key:'reservations',label:'Event reservations'},{key:'history',label:'Stock history'}]}/>
   <div role="tabpanel" id="warehouse-panel">
    {tab==='inventory'&&<Panel title="Inventory" icon="box" actions={options.data?.permissions.equipment.create&&<Button icon="plus" tone="primary" disabled={dirty.current||attaching} onClick={()=>setCreating(true)}>{t('Add equipment')}</Button>}>
     <WarehouseStock warehouse={name} rows={overview.stock} canEdit={canEdit} canDelete={!!options.data?.permissions.equipment.delete} onRefresh={refresh} onDirty={value=>{dirty.current=value;}}/>
    </Panel>}
    {tab==='reservations'&&<Panel title="Event reservations"><ResourceBookings rows={overview.bookings} onRefresh={refresh} canEdit={canEdit}/></Panel>}
    {tab==='history'&&<Panel title="Stock history"><DataTable label="Stock history" rows={overview.history} rowKey={item=>item.creation+'/'+item.item_code} columns={[
     {key:'date',label:'Date and time',render:item=>item.posting_date+' '+String(item.posting_time).split('.')[0]},
     {key:'item',label:'Equipment',render:item=>item.item_code},
     {key:'change',label:'Change',numeric:true,render:item=>item.actual_qty},
     {key:'balance',label:'Balance',numeric:true,render:item=>item.qty_after_transaction},
     {key:'owner',label:'Updated by',render:item=>item.owner},
    ]}/></Panel>}
   </div>
  </>}
  {editing&&options.data&&<ResourceEditor kind={kind} name={name} initial={initial} options={options.data} onClose={()=>setEditing(false)} onSaved={()=>{setEditing(false);refresh();}}/>}
  {creating&&options.data&&<ResourceEditor kind="equipment" options={options.data} onClose={()=>setCreating(false)} onSaved={item=>{setCreating(false);void attach(item);}}/>}
  {booking&&<BookingDialog kind="vehicle" vehicle={name} onClose={()=>setBooking(false)} onSaved={()=>{setBooking(false);refresh();}}/>}
  {rate&&equipment&&<HireRate name={name} value={equipment.daily_rate} currency={equipment.currency} uom={equipment.uom} onClose={()=>setRate(false)} onSaved={()=>{setRate(false);refresh();}}/>}
 </section>;
}
function HireRate({name,value,currency,uom,onClose,onSaved}:{name:string;value:string;currency:string;uom:string;onClose:()=>void;onSaved:()=>void}){
 const [rate,setRate]=useState(value),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const invalid=rate.trim()===''||!Number.isFinite(Number(rate))||Number(rate)<0;
 async function save(){if(busy)return;if(invalid){setError(t('Enter zero or a positive rate.'));return;}setBusy(true);setError('');try{await resourceCall('save_equipment_rate',{name,amount:rate});changed();onSaved();}catch(cause){setError(resourceError(cause));}finally{setBusy(false);}}
 return <Dialog title="Daily hire rate" busy={busy} onClose={onClose} footer={<><Button disabled={busy} onClick={onClose}>{t('Cancel')}</Button><Button tone="primary" loading={busy} onClick={()=>void save()}>{t('Save rate')}</Button></>}><Field label={'Rate per '+uom+' / day ('+currency+')'} error={error}>{(id,help)=><Input id={id} type="number" min={0} step="any" value={rate} disabled={busy} aria-invalid={!!error} aria-describedby={help} onChange={event=>{setRate(event.target.value);setError('');}}/>}</Field></Dialog>;
}
