import {memo,useEffect,useRef,useState} from 'react';
import {type ChartHandle,t} from './bridge';
import {Button} from './components';

/* An effect boundary owns the existing self-hosted ECharts engine. React owns
   the host; the engine owns its SVG subtree. Instances update, never remount on
   search/selection. Every listener, frame and observer is released on unmount. */
export const Chart=memo(function Chart({options,className='',kind}:{options:Record<string,unknown>;className?:string;kind:string}){
 const host=useRef<HTMLDivElement>(null),handle=useRef<ChartHandle|undefined>(undefined),latest=useRef(options),[error,setError]=useState(false),[retry,setRetry]=useState(0);latest.current=options;
 useEffect(()=>{let dead=false,frame=0;const node=host.current!,motion=matchMedia('(prefers-reduced-motion: reduce)');
  const resize=()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(()=>handle.current?.resize());},theme=()=>handle.current?.refresh();
  const observer=new ResizeObserver(resize);observer.observe(node);document.addEventListener('pp:theme-changed',theme);motion.addEventListener('change',theme);
  setError(false);window.plus_point.load_feature('dashboard_charts').then(()=>window.plus_point.charts.ready()).then(()=>{if(dead)return;handle.current=window.plus_point.charts.create(node,latest.current);resize();}).catch(()=>{if(!dead)setError(true);});
  return()=>{dead=true;cancelAnimationFrame(frame);observer.disconnect();document.removeEventListener('pp:theme-changed',theme);motion.removeEventListener('change',theme);handle.current?.destroy();handle.current=undefined;};
 },[retry]);
 useEffect(()=>{handle.current?.update(options);},[options]);
 return <div className={className} data-spark={kind==='attendance'?undefined:kind} data-chart={kind==='attendance'?kind:undefined} ref={host} aria-label={String(options.title||'Chart')}>{error&&<Button onClick={()=>setRetry(n=>n+1)}>{t('Retry chart')}</Button>}</div>;
});
