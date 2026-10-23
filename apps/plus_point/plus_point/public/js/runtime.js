/* One bounded UI observer. Enhancements cannot observe their own DOM writes. */
(()=>{
 frappe.provide('plus_point');
 const watchers=new Map();let timer,observer,running=false,bursts=0,lastRun=0;
 const stats=plus_point.runtime_stats={passes:0,suppressed:0,watchers:0};
 function schedule(){if(document.hidden||timer||running)return;timer=setTimeout(flush,120);}
 function flush(){
  timer=null;if(document.hidden)return;
  const now=Date.now();bursts=now-lastRun<400?bursts+1:0;lastRun=now;
  if(bursts>8){stats.suppressed++;return;}
  observer.disconnect();running=true;
  try{for(const callback of watchers.values())try{callback();}catch(error){console.warn('PLUS POINT enhancement',error);}stats.passes++;}
  finally{running=false;observer.observe(document.body,{childList:true,subtree:true});}
 }
 plus_point.watch_ui=(name,callback)=>{watchers.set(name,callback);stats.watchers=watchers.size;if(!observer){observer=new MutationObserver(schedule);observer.observe(document.body,{childList:true,subtree:true});}schedule();};
 const wake=()=>{bursts=0;schedule();};
 document.addEventListener('visibilitychange',wake);document.addEventListener('pp:data-changed',wake);
 for(const type of ['pointerdown','keydown'])document.addEventListener(type,wake,{passive:true});
 frappe.router.on('change',()=>{wake();requestAnimationFrame(()=>{const page=frappe.container?.page;page?.querySelectorAll('.pp-operations,.pp-worker-profile').forEach(node=>{node.closest('.layout-main-section-wrapper')?.scrollTo(0,0);});});});
})();
