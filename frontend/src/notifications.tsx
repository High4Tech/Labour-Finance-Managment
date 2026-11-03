import {useState} from 'react';
import {t,relativeDate} from './bridge';
import {Button,Feedback,Icon,Pagination,Panel} from './components';
import {useResource} from './hooks';
type Notice={name?:string;title:string;label?:string;date:string;href?:string;entity:string;read?:boolean};
type Activity={notifications:Notice[];feed:Notice[];more:boolean};
const call=<T,>(method:string,args:Record<string,unknown>)=>window.plus_point.form_rpc<T>('company_tools.'+method,args);
const allowedIcons=new Set(['overview','agreements','jobs','workers','attendance','clients','warehouses','vehicles','billing','payments','loans','worker-statement','inventory','receipts','expenses','event-finances']);
function Cards({rows}:{rows:Notice[]}){return rows.length?<div className="pp-notification-cards">{rows.map((r,i)=><article key={r.name||r.date+'-'+i} className="pp-notification-card" data-unread={!r.read&&!!r.name}>{allowedIcons.has(r.entity)?<img className="pp-entity-icon" width="20" height="20" alt="" src={'/assets/plus_point/images/navigation/'+r.entity+'.svg'}/>:<Icon name="bell"/>}<div><strong>{r.href?<a href={r.href}>{r.title}</a>:r.title}</strong>{r.label&&<p>{t(r.label)}</p>}<time dateTime={r.date}>{relativeDate(r.date)}</time></div></article>)}</div>:<div className="pp-empty-state"><strong>{t('No notifications')}</strong><p>{t('You’re up to date.')}</p></div>;}
export default function Notifications({onRead}:{onRead:(unread:number)=>void}){
 const [mode,setMode]=useState('All'),[page,setPage]=useState(1),[saving,setSaving]=useState(false),[failure,setFailure]=useState('');
 const {data,loading,error,refresh}=useResource(()=>call<Activity>('activity',{mode,page}),[mode,page]);
 const unread=data?.notifications.filter(r=>!r.read&&r.name).map(r=>r.name)||[];
 const mark=async()=>{if(saving||!unread.length)return;setSaving(true);setFailure('');try{const result=await call<{unread:number}>('mark_read',{names:unread});onRead(result.unread);refresh();}catch(e){setFailure((e as Error).message);}finally{setSaving(false);}};
 return <section className="pp-r-screen pp-r-notifications" aria-label={t('Notifications & activity')} aria-busy={loading||saving}><header className="pp-resource-heading"><div><h1>{t('Notifications & activity')}</h1><p>{t('Your alerts and recent company updates.')}</p></div><div className="pp-actions"><Button disabled={loading||saving||!unread.length} onClick={mark}>{t(saving?'Saving…':'Mark visible alerts read')}</Button><Button icon="refresh" disabled={saving} onClick={refresh}>{t('Refresh')}</Button></div></header><div className="pp-notification-tabs" role="group" aria-label={t('Notification filter')}>{['All','Unread'].map(v=><Button key={v} aria-pressed={mode===v} onClick={()=>{setMode(v);setPage(1);}}>{t(v)}</Button>)}</div><Feedback message={error||failure}/>{loading&&!data&&<p role="status">{t('Loading notifications…')}</p>}{data&&<><Panel title="Notifications"><Cards rows={data.notifications}/></Panel>{data.feed.length>0&&<Panel title="Company activity"><Cards rows={data.feed}/></Panel>}<Pagination page={page} pages={data.more?page+1:page} disabled={loading||saving} onPage={setPage}/></>}</section>;
}
