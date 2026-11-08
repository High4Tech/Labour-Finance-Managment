import {useEffect,useRef,useState} from 'react';
import {Button,DataTable,Dialog,Feedback,Field,Input,RadioGroup,Select,Badge} from './components';
import {changed,t,today} from './bridge';
import {useResource} from './hooks';
import {ResourceLookup} from './resource-lookup';
import {resourceCall,resourceError,type Booking} from './resource-types';

type EventOption={name:string; event_name:string; pp_reference:string; project:string; start_date:string; end_date:string};
type Site={name:string; site_name:string};
type Availability={name?:string; warehouse?:string; title?:string; available:boolean|number; license_plate?:string; make?:string; model?:string; pp_crew_seats?:number; pp_cargo_capacity?:number; pp_cargo_uom?:string; uom?:string};
export function BookingDialog({kind,row,vehicle,project,start,end,site,onClose,onSaved}: {
 kind:'vehicle'|'equipment'; row?:Booking; vehicle?:string; project?:string; start?:string; end?:string; site?:string;
 onClose:()=>void; onSaved:()=>void;
}) {
 const events=useResource(signal=>resourceCall<EventOption[]>('assignable_events',{},signal),[]);
 const [event,setEvent]=useState(row?.project||project||''),[location,setLocation]=useState(row?.site||site||'');
 const [first,setFirst]=useState(row?.start_date||start||today()),[last,setLast]=useState(row?.end_date||end||today());
 const [item,setItem]=useState(row?.item||''),[resource,setResource]=useState(row?.vehicle||vehicle||row?.warehouse||'');
 const [purpose,setPurpose]=useState(row?.purpose||'Crew'),[quantity,setQuantity]=useState(String(kind==='vehicle'?(row?.crew_count||1):(row?.quantity||1)));
 const [cargo,setCargo]=useState(String(row?.cargo_load||0)),[status,setStatus]=useState(row?.status||'Planned');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[errors,setErrors]=useState<Record<string,string>>({});
 const lock=useRef(false),form=useRef<HTMLFormElement>(null),isVehicle=kind==='vehicle';
 const locations=useResource(signal=>event?resourceCall<{sites:Site[]}>('project_resources',{project:event},signal):Promise.resolve({sites:[]}),[event]);
 const availability=useResource(signal=>event&&first&&last&&last>=first&&(isVehicle||item)?resourceCall<Availability[]>('booking_options',{project:event,kind,item,start_date:first,end_date:last,name:row?.name},signal):Promise.resolve([]),[event,kind,item,first,last,row?.name]);
 useEffect(()=>{if(!location&&locations.data?.sites.length===1)setLocation(locations.data.sites[0].name);},[locations.data,location]);
 const options=(availability.data||[]).map(option=>({value:(isVehicle?option.name:option.warehouse)!,label:isVehicle?[option.license_plate||option.name,option.make,option.model].filter(Boolean).join(' · ')+(option.available?'':' · '+t('Unavailable')):option.title+' · '+option.available+' '+option.uom+' '+t('available')}));
 const chosen=availability.data?.find(option=>(isVehicle?option.name:option.warehouse)===resource);
 async function save(){
  if(lock.current)return;
  const invalid:Record<string,string>={};
  if(!event)invalid.event=t('Choose an event.');
  if(!location)invalid.site=t('Choose a site.');
  if(!first)invalid.first=t('Choose a start date.');
  if(!last||last<first)invalid.last=t('Choose an end date on or after the start date.');
  if(status!=='Cancelled'){
   if(!resource||!chosen)invalid.resource=t('Choose a resource available for these dates.');
   if(isVehicle&&chosen&&!chosen.available)invalid.resource=t('This vehicle is already reserved for these dates.');
   if(!isVehicle&&!item)invalid.item=t('Choose equipment.');
   const value=isVehicle&&purpose==='Inventory'?cargo:quantity;
   if(value.trim()===''||!Number.isFinite(Number(value))||Number(value)<(isVehicle&&purpose==='Inventory'?0:1))invalid.quantity=t('Enter a valid quantity.');
   if(isVehicle&&purpose==='Crew'&&!Number.isInteger(Number(quantity)))invalid.quantity=t('Enter a whole number of passengers.');
   const capacity=chosen&&(isVehicle?(purpose==='Crew'?chosen.pp_crew_seats:chosen.pp_cargo_capacity):Number(chosen.available));
   if(capacity!=null&&Number(value)>capacity)invalid.quantity=t('Maximum available')+' '+capacity;
  }
  setErrors(invalid);setError('');
  if(Object.keys(invalid).length){requestAnimationFrame(()=>form.current?.querySelector<HTMLElement>('[aria-invalid=true]')?.focus());return;}
  lock.current=true;setBusy(true);
  try{
   await resourceCall('save_booking',{project:event,kind,name:row?.name,values:{site:location,start_date:first,end_date:last,status,...(isVehicle?{vehicle:resource,purpose,crew_count:Number(quantity),cargo_load:Number(cargo)}:{item,warehouse:resource,quantity:Number(quantity)})}});
   changed();onSaved();
  }catch(cause){setError(resourceError(cause));setErrors({resource:resourceError(cause)});}
  finally{lock.current=false;setBusy(false);}
 }
 return <Dialog title={isVehicle?'Assign vehicle':'Reserve warehouse equipment'} onClose={onClose} busy={busy} footer={<><Button disabled={busy} onClick={onClose}>{t('Cancel')}</Button><Button tone="primary" loading={busy} disabled={availability.loading||locations.loading} onClick={()=>void save()}>{t('Confirm reservation')}</Button></>}>
  <form ref={form} onSubmit={e=>{e.preventDefault();void save();}}>
   <Feedback message={error||events.error||locations.error||availability.error}/>
   <Field label="Event *" error={errors.event}>{id=><Select id={id} label="Event" disabled={busy||!!row||!!project} invalid={!!errors.event} value={event} options={[{value:'',label:t('Choose event')},...(events.data||[]).map(option=>({value:option.project,label:option.event_name+' · '+option.pp_reference})),...((row&&!events.data?.some(option=>option.project===row.project))?[{value:row.project,label:row.event||row.project}]:[])]} onChange={value=>{setEvent(value);setLocation('');setResource(vehicle||'');const selected=events.data?.find(option=>option.project===value);if(selected){setFirst(selected.start_date);setLast(selected.end_date);}}}/>}</Field>
   <Field label="Site *" error={errors.site}>{id=><Select id={id} label="Site" disabled={busy} invalid={!!errors.site} value={location} onChange={setLocation} options={[{value:'',label:t('Choose site')},...(locations.data?.sites||[]).map(option=>({value:option.name,label:option.site_name}))]}/>}</Field>
   {!isVehicle&&<Field label="Equipment *" error={errors.item}>{id=><ResourceLookup kind="equipment" id={id} label="Equipment" value={item} invalid={!!errors.item} disabled={busy} onChange={value=>{setItem(value);setResource('');}}/>}</Field>}
   <div className="pp-r-grid">
    <Field label="From *" error={errors.first}>{(id,help)=><Input type="date" id={id} required value={first} disabled={busy} aria-invalid={!!errors.first} aria-describedby={help} onChange={e=>setFirst(e.target.value)}/>}</Field>
    <Field label="Through *" error={errors.last}>{(id,help)=><Input type="date" id={id} required min={first} value={last} disabled={busy} aria-invalid={!!errors.last} aria-describedby={help} onChange={e=>setLast(e.target.value)}/>}</Field>
   </div>
   <Field label={isVehicle?'Vehicle *':'Warehouse *'} error={errors.resource}>{id=><Select id={id} label={isVehicle?'Vehicle':'Warehouse'} value={resource} disabled={busy||availability.loading} invalid={!!errors.resource} options={[{value:'',label:t(isVehicle?'Choose vehicle':'Choose warehouse')},...options]} onChange={setResource}/>}</Field>
   {isVehicle&&<RadioGroup label="Purpose" value={purpose} options={['Crew','Inventory']} onChange={setPurpose} disabled={busy}/>}
   <Field label={isVehicle?(purpose==='Crew'?'Crew passengers *':'Inventory load *'):'Quantity *'} error={errors.quantity}>{(id,help)=><Input id={id} type="number" min={isVehicle&&purpose==='Inventory'?0:1} step={isVehicle&&purpose==='Crew'?1:'any'} value={isVehicle&&purpose==='Inventory'?cargo:quantity} disabled={busy} aria-invalid={!!errors.quantity} aria-describedby={help} onChange={e=>(isVehicle&&purpose==='Inventory'?setCargo:setQuantity)(e.target.value)}/>}</Field>
   {chosen&&<p role="status">{isVehicle?chosen.pp_crew_seats+' '+t('crew seats')+' · '+chosen.pp_cargo_capacity+' '+chosen.pp_cargo_uom:chosen.available+' '+chosen.uom+' '+t('available for these dates')}</p>}
   <RadioGroup label="Reservation status" value={status} options={['Planned','Cancelled']} disabled={busy} onChange={setStatus}/>
  </form>
 </Dialog>;
}

export function ResourceBookings({rows,onRefresh,canEdit}:{rows:Booking[];onRefresh:()=>void;canEdit:boolean}){
 const [selected,setSelected]=useState(new Set<string>()),[editing,setEditing]=useState<Booking>(),[cancel,setCancel]=useState<Booking[]>();
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>setSelected(new Set()),[rows]);
 async function cancelRows(){
  if(!cancel||busy)return;setBusy(true);setError('');
  try{await resourceCall('bulk_bookings',{rows:cancel.map(row=>({kind:row.kind,name:row.name})),values:{status:'Cancelled'}});changed();setCancel(undefined);onRefresh();}
  catch(cause){setError(resourceError(cause));}finally{setBusy(false);}
 }
 return <>
  {!cancel&&<Feedback message={error}/>}
  <DataTable label="Event reservations" rows={rows} rowKey={row=>row.kind+'/'+row.name} selected={selected} onSelect={setSelected} actions={canEdit&&<Button tone="danger" onClick={()=>{setError('');setCancel(rows.filter(row=>selected.has(row.kind+'/'+row.name)&&row.status==='Planned'));}}>{t('Cancel selected reservations')}</Button>} columns={[
   {key:'resource',label:'Resource',render:row=>row.title},
   {key:'event',label:'Event / site',render:row=><><a href={'/desk/pp-event-plans?project='+encodeURIComponent(row.project)}>{row.event}</a><small>{row.site_title}</small></>},
   {key:'dates',label:'Dates',render:row=><span className="pp-r-no-break">{row.start_date+' – '+row.end_date}</span>},
   {key:'quantity',label:'Quantity / purpose',render:row=>row.kind==='vehicle'?row.purpose+' · '+(row.purpose==='Crew'?row.crew_count:row.cargo_load):row.quantity+' '+row.stock_uom},
   {key:'status',label:'Status',render:row=><Badge tone={row.status==='Planned'?'info':'neutral'}>{t(row.status)}</Badge>},
   {key:'actions',label:'Actions',actions:true,render:row=>canEdit&&<><Button icon="edit" aria-label={t('Edit reservation')+' '+row.title} onClick={()=>setEditing(row)}/>{row.status==='Planned'&&<Button tone="danger" icon="close" aria-label={t('Cancel reservation')+' '+row.title} onClick={()=>{setError('');setCancel([row]);}}/>}</>},
  ]}/>
  {editing&&<BookingDialog kind={editing.kind} row={editing} onClose={()=>setEditing(undefined)} onSaved={()=>{setEditing(undefined);onRefresh();}}/>}
  {cancel&&<Dialog title="Cancel reservations?" busy={busy} onClose={()=>setCancel(undefined)} footer={<><Button onClick={()=>setCancel(undefined)} disabled={busy}>{t('Keep reservations')}</Button><Button tone="danger" disabled={!cancel.length} loading={busy} onClick={()=>void cancelRows()}>{t('Cancel reservations')}</Button></>}><Feedback message={error}/><p>{cancel.length} {t('reservations will release their capacity.')}</p></Dialog>}
 </>;
}
