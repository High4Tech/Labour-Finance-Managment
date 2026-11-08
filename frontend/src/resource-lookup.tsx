import {useState} from 'react';
import {Select} from './components';
import {useDebounced,useResource} from './hooks';
import {resourceCall,type ResourceKind,type ResourceRow} from './resource-types';
export function ResourceLookup({kind,id,label,value,onChange,invalid=false,disabled=false}: {
 kind:ResourceKind; id:string; label:string; value:string; onChange:(name:string)=>void; invalid?:boolean; disabled?:boolean;
}) {
 const [query,setQuery]=useState(''),search=useDebounced(query);
 const resource=useResource(signal=>resourceCall<{rows:ResourceRow[]}>('list_records',{view:kind,search},signal),[kind,search]);
 const options=(resource.data?.rows||[]).map(row=>({value:row.name,label:row.title}));
 if(value&&!options.some(option=>option.value===value))options.unshift({value,label:value});
 return <><Select id={id} label={label} value={value} disabled={disabled} invalid={invalid} loading={resource.loading} options={[{value:'',label:'Choose '+label.toLowerCase()},...options]} onSearch={setQuery} onChange={onChange}/>{resource.error&&<small role="alert">{resource.error}</small>}</>;
}
