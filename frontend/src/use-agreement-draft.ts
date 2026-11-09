import {useEffect,useRef,useState} from 'react';
import {call} from './agreement-types';
import {createDraftSession,hasPlanningContent} from './draft-session.mjs';
export type PlanningDraft={name:string;revision:number;kind:string;status:string;agreement?:string;event?:string;scheduled_for?:string;payload:Record<string,any>};
export function useAgreementDraft(payload:Record<string,any>,initialDraft?:PlanningDraft,kind='Agreement'){
 const [status,setStatus]=useState(initialDraft?'Draft saved':'Changes save automatically'),alive=useRef(true),timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined),session=useRef<ReturnType<typeof createDraftSession>|undefined>(undefined);
 const cacheKey=`pp-form-recovery:${window.frappe.session.user}:${window.frappe.boot.plus_point.company_identity?.name}`;
 const forget=(key:string)=>{try{const rows=JSON.parse(sessionStorage.getItem(cacheKey)||'[]').filter((r:any)=>r.client_key!==key);rows.length?sessionStorage.setItem(cacheKey,JSON.stringify(rows)):sessionStorage.removeItem(cacheKey);}catch{}};
 const backup=(value:any)=>{try{if(new TextEncoder().encode(JSON.stringify(value)).length>48000)return;const rows=JSON.parse(sessionStorage.getItem(cacheKey)||'[]').filter((r:any)=>r.client_key!==value.client_key&&Date.now()-r.at<43200000).slice(-4);sessionStorage.setItem(cacheKey,JSON.stringify([...rows,{...value,at:Date.now()}]));}catch{}};
 if(!session.current)session.current=createDraftSession({initial:payload,draft:initialDraft,kind,key:crypto.randomUUID(),persist:async(args:any)=>{const result=await call<PlanningDraft>('drafts.save',args);document.dispatchEvent(new Event('pp:planning-draft-saved'));return result;},notice:(value:string)=>{if(alive.current)setStatus(value);},backup,forget});
 useEffect(()=>{session.current!.update(payload);clearTimeout(timer.current);if(session.current!.dirty())timer.current=setTimeout(()=>void session.current!.flush().catch(()=>{}),1500);},[payload]);
 useEffect(()=>{
  const flush=()=>{clearTimeout(timer.current);void session.current!.flush().catch(()=>{});},visibility=()=>{if(document.hidden)flush();},pagehide=()=>{const s=session.current!;if(!s.dirty()||!hasPlanningContent(s.snapshot().payload,kind))return;const value=s.snapshot();backup(value);if(new TextEncoder().encode(JSON.stringify(value)).length<48000){const native=window.frappe as any;void fetch('/api/method/plus_point.drafts.save',{method:'POST',credentials:'same-origin',keepalive:true,headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':native.csrf_token},body:JSON.stringify(value)}).catch(()=>{});}};
  document.addEventListener('visibilitychange',visibility);window.addEventListener('pagehide',pagehide);
  return()=>{alive.current=false;clearTimeout(timer.current);document.removeEventListener('visibilitychange',visibility);window.removeEventListener('pagehide',pagehide);flush();};
 },[]);
 return {status,name:session.current!.name(),stop:()=>session.current!.stop(),flush:()=>{clearTimeout(timer.current);return session.current!.flush();},finish:async(record:string)=>{clearTimeout(timer.current);await session.current!.flush();const name=session.current!.name();if(name)await call('drafts.finish',{name,record});session.current!.stop();}};
}
