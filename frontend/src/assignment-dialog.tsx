import {useState} from 'react';
import {Button,Dialog,Feedback,Field,Select} from './components';
import {call} from './agreement-types';
import {useResource} from './hooks';
import EventStaffing from './event-staffing';
import type {Catalogue,EventData} from './event-types';
export default function AssignmentDialog({project,onClose,onSaved}:{project?:string;onClose:()=>void;onSaved:()=>void}){
 const [name,setName]=useState(''),catalogue=useResource(signal=>call<Catalogue>('operations.catalogue',{},signal),[]),chosen=name||catalogue.data?.plans.find((row:any)=>row.project===project)?.name||'',record=useResource(signal=>chosen?call<EventData>('operations.plan',{name:chosen},signal):Promise.resolve(undefined),[chosen]);
 return <Dialog title="Assign workers" onClose={onClose} footer={<Button onClick={onClose}>Close</Button>}><Feedback message={catalogue.error||record.error}/><Field label="Event">{id=><Select id={id} label="Event" value={chosen} options={[{value:'',label:'Choose event'},...(catalogue.data?.plans||[]).map((row:any)=>({value:row.name,label:row.event_name||row.name}))]} onChange={setName}/>}</Field>{record.data&&catalogue.data&&<EventStaffing data={record.data} catalogue={catalogue.data} onSaved={()=>{record.refresh();onSaved();}}/>}</Dialog>;
}
