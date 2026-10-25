/* One bounded UI observer. Enhancements cannot observe their own DOM writes. */
(()=>{
 frappe.provide('plus_point');
 // Native equivalents of the Empty/Skeleton composition reviewed on 21st.dev.
 // Text only: callers retain ownership of their actions and event listeners.
 const escape=v=>frappe.utils.escape_html(String(v??''));
 plus_point.empty_state=(title,description='')=>`<div class="pp-empty-state"><strong>${escape(__(title))}</strong>${description?`<p>${escape(__(description))}</p>`:''}</div>`;
 plus_point.loading_state=(label='Loading your records…')=>`<div class="pp-loading-state" role="status"><p>${escape(__(label))}</p><div class="pp-loading-placeholder" aria-hidden="true"><span></span><span></span><span></span></div></div>`;
 plus_point.render_table=(labels,rows,{emptyTitle='No records yet',emptyDescription='Records will appear here when they are added.'}={})=>{
  const esc=v=>frappe.utils.escape_html(String(v??'')),template=document.createElement('template');
  template.innerHTML=`<div class="pp-op-table-scroll" tabindex="0" role="region" aria-label="${esc(__('Table: {0}',[labels.map(t=>__(t)).join(', ')]))}"><table class="pp-register-table"><thead><tr>${labels.map(t=>`<th scope="col">${esc(__(t))}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr class="pp-table-empty"><td colspan="${Math.max(1,labels.length)}">${plus_point.empty_state(emptyTitle,emptyDescription)}</td></tr>`}</tbody></table></div>`;
  template.content.querySelectorAll('tbody>tr:not(.pp-table-empty)').forEach(row=>[...row.children].forEach((cell,i)=>{cell.dataset.label=__(labels[i]||'Actions');if(cell.tagName==='TH')cell.scope='row';}));
  return template.innerHTML;
 };
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
