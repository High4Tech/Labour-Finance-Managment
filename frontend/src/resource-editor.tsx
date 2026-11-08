import {useResource} from './hooks';
import {resourceEditorValues,type EquipmentProfile,type Overview,type ResourceRow} from './resource-types';
import {useRef,useState} from 'react';
import {Button,Dialog,Feedback,Field,Input,RadioGroup,Select} from './components';
import {changed,t} from './bridge';
import {resourceCall,resourceError,resourceScreens,type ResourceKind,type ResourceOptions} from './resource-types';

type Definition = {key:string; label:string; required?:boolean; type?:'number'; options?:string[]; disabled?:boolean};
export function ResourceEditor({kind,name,initial={},options,onClose,onSaved}: {
 kind:ResourceKind; name?:string; initial?:Record<string,string>; options:ResourceOptions;
 onClose:()=>void; onSaved:(name:string)=>void;
}) {
 const [values,setValues]=useState<Record<string,string>>({purpose:'Crew',status:'Active',stock_uom:'Nos',warehouse_type:'Owned',crew_seats:'0',cargo_capacity:'0',cargo_uom:'units',fuel_type:'Diesel',...initial});
 const [errors,setErrors]=useState<Record<string,string>>({}),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const saving=useRef(false),form=useRef<HTMLFormElement>(null);
 const screen=resourceScreens[kind];
 const fields:Definition[]=kind==='equipment' ? [
  {key:'item_code',label:'Equipment code',required:true,disabled:!!name},
  {key:'item_name',label:'Equipment name',required:true},
  {key:'stock_uom',label:'Stock unit',required:true,options:options.units},
 ] : kind==='warehouses' ? (name?[]:[{key:'warehouse_name',label:'Warehouse name',required:true}]) : [
  ...(!name?[{key:'license_plate',label:'Registration / vehicle ID',required:true}]:[]),
  {key:'make',label:'Make',required:true},{key:'model',label:'Model',required:true},
  ...((name||values.purpose==='Crew')?[{key:'crew_seats',label:'Crew seats (driver excluded)',type:'number' as const}]:[]),
  ...((name||values.purpose==='Inventory')?[
   {key:'cargo_capacity',label:'Inventory load capacity',type:'number' as const},
   {key:'cargo_uom',label:'Inventory load unit',options:['units','kg','m³']},
  ]:[]),
  ...(!name?[{key:'fuel_type',label:'Fuel type',options:['Petrol','Diesel','Natural Gas','Electric']}]:[]),
 ];
 const update=(key:string,value:string)=>{setValues(previous=>({...previous,[key]:value}));setErrors(previous=>({...previous,[key]:''}));};
 async function save() {
  if(saving.current)return;
  const validation:Record<string,string>={};
  for(const field of fields){
   if(field.required&&!values[field.key]?.trim())validation[field.key]=t('Enter')+' '+t(field.label)+'.';
   if(field.type==='number'&&(!values[field.key]?.trim()||!Number.isFinite(Number(values[field.key]))||Number(values[field.key])<0))validation[field.key]=t('Enter zero or a positive number.');
  }
  if(kind==='vehicles'&&values.crew_seats&&!Number.isInteger(Number(values.crew_seats)))validation.crew_seats=t('Enter a whole number of crew seats.');
  setErrors(validation);
  if(Object.keys(validation).length){requestAnimationFrame(()=>form.current?.querySelector<HTMLElement>('[aria-invalid=true]')?.focus());return;}
  saving.current=true;setBusy(true);setError('');
  try {
   let result:{name:string};
   if(name)result=await resourceCall('update_profile',{view:kind,name,values:kind==='vehicles'?{
    make:values.make,model:values.model,pp_event_enabled:Number(values.status==='Active'),pp_crew_seats:Number(values.crew_seats),pp_cargo_capacity:Number(values.cargo_capacity),pp_cargo_uom:values.cargo_uom,
   }:kind==='equipment'?{item_name:values.item_name,stock_uom:values.stock_uom,disabled:Number(values.status==='Inactive')}:{warehouse_type:values.warehouse_type,disabled:Number(values.status==='Inactive')}});
   else result=await window.plus_point.form_rpc('events.save_resource',{kind:screen.kind,company:options.company,values});
   changed();onSaved(result.name);
  }catch(cause){setError(resourceError(cause));}
  finally{saving.current=false;setBusy(false);}
 }
 return <Dialog title={name?'Edit '+screen.singular.toLowerCase():screen.create} busy={busy} onClose={onClose} footer={<><Button disabled={busy} onClick={onClose}>{t('Cancel')}</Button><Button tone="primary" loading={busy} onClick={()=>void save()}>{t('Save')}</Button></>}>
  <form ref={form} onSubmit={event=>{event.preventDefault();void save();}}>
   <Feedback message={error}/>
   {kind==='vehicles'&&!name&&<RadioGroup label="Transport purpose" value={values.purpose} options={['Crew','Inventory']} disabled={busy} onChange={value=>update('purpose',value)}/>}
   <div className="pp-r-grid">{fields.map(field=><Field key={field.key} label={field.label+(field.required?' *':'')} error={errors[field.key]}>{(id,help)=>field.options?
    <Select id={id} label={field.label} value={values[field.key]||''} describedBy={help} invalid={!!errors[field.key]} disabled={busy||field.disabled} options={field.options.map(value=>({value,label:value}))} onChange={value=>update(field.key,value)}/>:
    <Input id={id} type={field.type||'text'} min={field.type==='number'?0:undefined} step={field.key==='crew_seats'?1:'any'} required={field.required} value={values[field.key]||''} disabled={busy||field.disabled} aria-invalid={!!errors[field.key]} aria-describedby={help} onChange={event=>update(field.key,event.target.value)}/>
   }</Field>)}</div>
   {kind==='warehouses'&&<RadioGroup label="Ownership" value={values.warehouse_type} options={['Owned','Rented']} disabled={busy} onChange={value=>update('warehouse_type',value)}/>}
   {(kind!=='warehouses'||name)&&<RadioGroup label="Status" value={values.status} options={['Active','Inactive']} disabled={busy} onChange={value=>update('status',value)}/>}
  </form>
 </Dialog>;
}

export function ResourceEditDialog({kind,name,onClose,onSaved}:{kind:ResourceKind;name:string;onClose:()=>void;onSaved:()=>void}){
 const data=useResource(async signal=>{
  const [options,profile]=await Promise.all([
   resourceCall<ResourceOptions>('form_options',{},signal),
   kind==='equipment'?resourceCall<EquipmentProfile>('equipment_profile',{name},signal):resourceCall<Overview>('overview',{view:kind,name},signal),
  ]);
  const equipment=kind==='equipment'?profile as EquipmentProfile:undefined;
  const row:ResourceRow=equipment?{name,title:equipment.title,disabled:equipment.disabled}:(profile as Overview).rows[0];
  if(!row)throw new Error(t('This record is unavailable.'));
  return {options,initial:resourceEditorValues(kind,row,name,equipment)};
 },[kind,name]);
 if(!data.data)return <Dialog title="Edit resource" onClose={onClose} footer={<Button onClick={onClose}>{t('Close')}</Button>}><Feedback message={data.error}/><Button onClick={data.refresh} disabled={data.loading}>{t(data.loading?'Loading resource…':'Try again')}</Button></Dialog>;
 return <ResourceEditor kind={kind} name={name} options={data.data.options} initial={data.data.initial} onClose={onClose} onSaved={onSaved}/>;
}
