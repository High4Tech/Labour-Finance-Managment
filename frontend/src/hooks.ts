import {useEffect,useRef,useState} from 'react';
import {readCache} from './read-cache.mjs';
export function useDebounced<T>(value:T,delay=250){const [result,setResult]=useState(value);useEffect(()=>{const timer=setTimeout(()=>setResult(value),delay);return()=>clearTimeout(timer);},[value,delay]);return result;}
/* No polling; optional bounded list snapshots. Financial reads stay uncached.
   A stale/unmounted request cannot commit UI state. */
export function useResource<T>(load:(signal:AbortSignal)=>Promise<T>,keys:unknown[],cacheScope?:string){
 const [data,setData]=useState<T>(),[loading,setLoading]=useState(true),[error,setError]=useState(''),[revision,setRevision]=useState(0),sequence=useRef(0),settled=useRef('');
 const identity=JSON.stringify([cacheScope,revision,...keys]);
 useEffect(()=>{const own=++sequence.current,abort=new AbortController(),cacheKey=cacheScope+'|'+JSON.stringify(keys),cached=cacheScope?readCache.get(cacheKey):undefined;let active=true;setError('');if(cached!==undefined){settled.current=identity;setData(cached as T);setLoading(false);return;}setLoading(true);load(abort.signal).then(value=>{if(active&&own===sequence.current){if(cacheScope)readCache.set(cacheKey,value);setData(value);}}).catch(e=>{if(active&&own===sequence.current&&e.name!=='AbortError')setError(e.message||'Could not load records. Try again.');}).finally(()=>{if(active&&own===sequence.current){settled.current=identity;setLoading(false);}});return()=>{active=false;abort.abort();};},[...keys,revision,cacheScope]);
 return {data,loading:loading||settled.current!==identity,error,refresh:()=>{if(cacheScope)readCache.invalidate(cacheScope);setRevision(n=>n+1);}};
}
export function useLiveUpdates(types:string[],refresh:()=>void,events:string[]=[]){
 const latest=useRef(refresh);latest.current=refresh;const key=types.join('|'),eventKey=events.join('|');
 useEffect(()=>{const realtime=window.frappe.realtime;if(!realtime)return;const subscribed=key.split('|');let timer:ReturnType<typeof setTimeout>|undefined,last=0,dirty=false;
  const flush=()=>{timer=undefined;if(document.hidden)return;dirty=false;last=Date.now();latest.current();};
  const queue=()=>{dirty=true;if(!timer&&!document.hidden)timer=setTimeout(flush,Math.max(250,1000-(Date.now()-last)));};
  const update=(data?:{doctype?:string})=>{if(data?.doctype&&subscribed.includes(data.doctype))queue();};
  const local=eventKey.split('|').filter(Boolean);
  const wake=()=>{if(!document.hidden&&dirty&&!timer)timer=setTimeout(flush,250);},connect=()=>subscribed.forEach(name=>realtime.doctype_subscribe(name));
  connect();local.forEach(name=>document.addEventListener(name,queue));realtime.on('list_update',update);realtime.on('connect',connect);document.addEventListener('visibilitychange',wake);
  return()=>{clearTimeout(timer);local.forEach(name=>document.removeEventListener(name,queue));realtime.off('list_update',update);realtime.off('connect',connect);document.removeEventListener('visibilitychange',wake);subscribed.forEach(name=>realtime.doctype_unsubscribe(name));};
 },[key,eventKey]);
}
