import {useEffect,useState} from 'react';
import {Button,DataTable,Dialog,Feedback,Field,Input,RadioGroup} from './components';
import {changed,t} from './bridge';
import {resourceCall,resourceError,type Stock} from './resource-types';
import {ResourceLookup} from './resource-lookup';

type Draft = {quantity:string; expected_quantity:number};
export function WarehouseStock({warehouse,rows,canEdit,canDelete,onRefresh,onDirty}: {
 warehouse:string; rows:Stock[]; canEdit:boolean; canDelete:boolean; onRefresh:()=>void; onDirty:(value:boolean)=>void;
}) {
 const [selected,setSelected]=useState(new Set<string>()),[drafts,setDrafts]=useState<Record<string,Draft>>({});
 const [query,setQuery]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[dialog,setDialog]=useState<'attach'|'bulk'>();
 const [item,setItem]=useState(''),[operation,setOperation]=useState('Set quantity'),[quantity,setQuantity]=useState('0');
 useEffect(()=>{setDrafts({});setSelected(new Set());},[rows]);
 useEffect(()=>{onDirty(Object.keys(drafts).length>0);return()=>onDirty(false);},[drafts]);
 const current=(row:Stock)=>drafts[row.name]?.quantity??String(row.on_hand);
 const issue=(row:Stock)=>{
  const value=current(row);
  if(value.trim()===''||!Number.isFinite(Number(value)))return t('Enter a quantity such as 12 or 12.5.');
  if(Number(value)<Number(row.reserved))return t('Quantity must cover reserved stock.')+' '+row.reserved+' '+row.uom;
  if(Number(value)<0)return t('Enter zero or a positive number.');
  return '';
 };
 function update(row:Stock,value:string){setDrafts(previous=>{
  const next={...previous};
  if(value.trim()!==''&&Number(value)===Number(row.on_hand))delete next[row.name];
  else next[row.name]={quantity:value,expected_quantity:Number(row.on_hand)};
  return next;
 });}
 async function save(){
  if(busy||!Object.keys(drafts).length||rows.some(issue))return;
  setBusy(true);setError('');
  try{await resourceCall('update_stock',{warehouse,rows:Object.entries(drafts).map(([item,draft])=>({item,quantity:Number(draft.quantity),expected_quantity:draft.expected_quantity}))});changed();onRefresh();}
  catch(cause){setError(resourceError(cause));}finally{setBusy(false);}
 }
 async function attach(){
  if(!item||busy)return;
  setBusy(true);setError('');
  try{await resourceCall('attach_item',{warehouse,item});changed();setDialog(undefined);onRefresh();}
  catch(cause){setError(resourceError(cause));}finally{setBusy(false);}
 }
 function bulk(){
  const value=Number(quantity);
  if(quantity.trim()===''||!Number.isFinite(value)||value<0){setError(t('Enter zero or a positive quantity.'));return;}
  const changes=rows.filter(row=>selected.has(row.name)).map(row=>({row,value:operation==='Add quantity'?Number(current(row))+value:operation==='Reduce quantity'?Number(current(row))-value:value}));
  if(changes.some(change=>change.value<Number(change.row.reserved)||change.value<0)){setError(t('The change would reduce stock below reserved quantities. Adjust the amount.'));return;}
  for(const change of changes)update(change.row,String(change.value));
  setDialog(undefined);setError('');
 }
 return <>
  <div className="pp-r-list-filters"><Field label="Search equipment">{id=><Input id={id} type="search" value={query} onChange={event=>{setQuery(event.target.value);setSelected(new Set());}}/>}</Field>
   {canEdit&&<><Button onClick={()=>{setError('');setItem('');setDialog('attach');}} disabled={busy||Object.keys(drafts).length>0}>{t('Add existing equipment')}</Button>
   <Button tone="primary" onClick={()=>void save()} disabled={busy||!Object.keys(drafts).length||rows.some(issue)}>{t('Save quantities')}</Button></>}
  </div>
  {!dialog&&<Feedback message={error}/>}
  {Object.keys(drafts).length>0&&<p role="status">{Object.keys(drafts).length} {t('unsaved quantity changes. Saving records the date and time automatically.')}</p>}
  <DataTable label="Warehouse equipment" rows={rows.filter(row=>row.title.toLowerCase().includes(query.toLowerCase()))} rowKey={row=>row.name} selected={selected} onSelect={setSelected}
   actions={<>{canEdit&&<Button disabled={busy} onClick={()=>{setError('');setDialog('bulk');}}>{t('Bulk update quantities')}</Button>}{canDelete&&<Button tone="danger" disabled={busy} onClick={()=>window.plus_point.delete_records('Item',[...selected],onRefresh)}>{t('Delete selected equipment')}</Button>}</>}
   columns={[
    {key:'equipment',label:'Equipment',render:row=><><strong>{row.title}</strong><small>{row.uom}</small></>},
    {key:'on_hand',label:'On hand',numeric:true,render:row=>canEdit?<div className="pp-r-stock-quantity"><Field label={'Quantity for '+row.title} error={drafts[row.name]?issue(row):''}>{(id,help)=><Input id={id} type="number" min={Math.max(0,Number(row.reserved))} step="any" value={current(row)} disabled={busy||!!row.disabled} aria-invalid={!!drafts[row.name]&&!!issue(row)} aria-describedby={help} onChange={event=>update(row,event.target.value)}/>}</Field></div>:row.on_hand},
    {key:'reserved',label:'Reserved today',numeric:true,render:row=>row.reserved},
    {key:'available',label:'Available today',numeric:true,render:row=>issue(row)?'—':Number(current(row))-Number(row.reserved)},
    {key:'updated',label:'Last updated',render:row=>row.updated_at?new Date(row.updated_at.replace(' ','T')).toLocaleString():'—'},
   ]}/>
  {dialog&&<Dialog title={dialog==='attach'?'Add existing equipment':'Bulk update quantities'} busy={busy} onClose={()=>setDialog(undefined)} footer={<><Button disabled={busy} onClick={()=>setDialog(undefined)}>{t('Cancel')}</Button><Button tone="primary" loading={busy} disabled={dialog==='attach'&&!item} onClick={()=>dialog==='attach'?void attach():bulk()}>{t(dialog==='attach'?'Add to warehouse':'Apply to selected rows')}</Button></>}>
   <Feedback message={error}/>
   {dialog==='attach'?<Field label="Equipment *">{id=><ResourceLookup kind="equipment" id={id} label="Equipment" value={item} onChange={setItem} disabled={busy}/>}</Field>:<>
    <RadioGroup label="Update method" value={operation} options={['Set quantity','Add quantity','Reduce quantity']} onChange={setOperation}/>
    <Field label="Quantity *">{id=><Input id={id} type="number" min={0} step="any" value={quantity} onChange={event=>setQuantity(event.target.value)}/>}</Field>
   </>}
  </Dialog>}
 </>;
}
