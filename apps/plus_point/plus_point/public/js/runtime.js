/* One bounded UI observer. Enhancements cannot observe their own DOM writes. */
(()=>{
 frappe.provide('plus_point');
 // Native equivalents of the Empty/Skeleton composition reviewed on 21st.dev.
 // Text only: callers retain ownership of their actions and event listeners.
 plus_point.close_dialog=d=>{const native=d.$wrapper.data('bs.modal');if(native?._isTransitioning)d.$wrapper.one('shown.bs.modal',()=>d.hide());else d.hide();};
 const escape=v=>frappe.utils.escape_html(String(v??''));
 plus_point.empty_state=(title,description='')=>`<div class="pp-empty-state"><strong>${escape(__(title))}</strong>${description?`<p>${escape(__(description))}</p>`:''}</div>`;
 plus_point.loading_state=(label='Loading your records…',{avatar=true}={})=>`<div class="pp-loading-state" role="status"><span class="sr-only">${escape(__(label))}</span><div class="pp-loading-placeholder" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span></div>${avatar?'<img class="pp-loading-logo" src="/assets/plus_point/images/freddy/thinking.svg?v=20261027" width="88" height="88" alt="" aria-hidden="true">':''}</div>`;
 plus_point.render_table=(labels,rows,{emptyTitle='No records yet',emptyDescription='Records will appear here when they are added.'}={})=>{
  const esc=v=>frappe.utils.escape_html(String(v??'')),template=document.createElement('template');
  template.innerHTML=`<div class="pp-op-table-scroll" tabindex="0" role="region" aria-label="${esc(__('Table: {0}',[labels.map(t=>__(t)).join(', ')]))}"><table class="pp-register-table"><thead><tr>${labels.map(t=>`<th scope="col">${esc(__(t))}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.join(''):`<tr class="pp-table-empty"><td colspan="${Math.max(1,labels.length)}">${plus_point.empty_state(emptyTitle,emptyDescription)}</td></tr>`}</tbody></table></div>`;
  template.content.querySelectorAll('thead th').forEach((cell,i)=>{if(/^(amount|rate|daily wage|client rate|balance|revenue|cost|outstanding|paid|estimated total|approved to invoice|wages|fixed contract value)/i.test(labels[i]||''))cell.dataset.numeric='true';});
  const kind=labels.includes('Attendance period')?'payments':labels.includes('Event pay')?'crew':'',weights=kind==='payments'?[16,21,12,14,14,9,30]:kind==='crew'?[24,10,10,14,12,16,10,22]:null;
  if(weights?.length===labels.length){const table=template.content.querySelector('table'),cols=document.createElement('colgroup'),total=weights.reduce((sum,n)=>sum+n,0);table.dataset.tableKind=kind;for(const n of weights){const col=document.createElement('col');col.style.width=(n/total*100)+'%';cols.append(col);}table.prepend(cols);}
  template.content.querySelectorAll('tbody>tr:not(.pp-table-empty)').forEach(row=>[...row.children].forEach((cell,i)=>{cell.dataset.label=__(labels[i]||'Actions');if(cell.tagName==='TH')cell.scope='row';if(/^(amount|rate|daily wage|client rate|balance|revenue|cost|outstanding|paid|estimated total|approved to invoice|wages|fixed contract value)/i.test(labels[i]||''))cell.dataset.numeric='true';}));
  return template.innerHTML;
 };
 // Shared selection for owned tables. Feature owners supply permitted mutations;
 // read-only tables still support selection and copying without unlocking history.
 plus_point.table_selection=(root,{actions=[],keys=null,eligible=()=>true}={})=>{
  const table=root?.matches?.('table.pp-register-table')?root:root?.querySelector('table.pp-register-table');if(!table)return;
  if(table.ppSelection){if(actions.length)table.ppSelection.setActions(actions);return table.ppSelection;}
  const rows=[...table.querySelectorAll('tbody>tr:not(.pp-table-empty)')];
  if(!rows.length||rows.some(row=>row.querySelector('input[type=checkbox]')))return;
  let region=table.closest('.pp-op-table-scroll');if(!region){region=document.createElement('div');region.className='pp-op-table-scroll';region.tabIndex=0;region.setAttribute('role','region');region.setAttribute('aria-label',__('Table'));table.before(region);region.append(table);}const toolbar=document.createElement('div');toolbar.className='pp-table-selection-tools';toolbar.hidden=true;region.before(toolbar);
  const colgroup=table.querySelector('colgroup'),originalWidths=colgroup?[...colgroup.children].map(col=>col.style.width):[];if(colgroup){for(const col of colgroup.children){const weight=parseFloat(col.style.width);if(col.style.width.endsWith('%'))col.style.width='calc((100% - 44px) * '+(weight/100)+')';}const col=document.createElement('col');col.style.width='44px';colgroup.prepend(col);}
  const heading=document.createElement('th');heading.scope='col';heading.className='pp-table-select';heading.innerHTML='<span class="sr-only">'+escape(__('Select'))+'</span><label class="pp-table-checkbox-label"><input type="checkbox" aria-label="'+escape(__('Select all rows'))+'"></label>';table.querySelector('thead tr').prepend(heading);
  const selected=()=>rows.flatMap((row,i)=>row.querySelector('[data-table-select]').checked?[keys?.[i]??i]:[]);
  const update=()=>{const ids=selected(),enabled=rows.filter((row,i)=>eligible(keys?.[i]??i)),all=heading.querySelector('input'),compact=toolbar.querySelector('input');for(const input of [all,compact]){input.checked=!!enabled.length&&ids.length===enabled.length;input.indeterminate=ids.length>0&&ids.length<enabled.length;}toolbar.hidden=!ids.length;toolbar.querySelector('[role=status]').textContent=__('{0} selected',[ids.length]);toolbar.querySelectorAll('button').forEach(button=>button.disabled=!ids.length);};
  rows.forEach((row,i)=>{const cell=document.createElement('td');cell.className='pp-table-select';cell.innerHTML='<label class="pp-table-checkbox-label"><input type="checkbox" data-table-select aria-label="'+escape(__('Select {0}',[row.querySelector('th,td')?.textContent.trim()||i+1]))+'" '+(!eligible(keys?.[i]??i)?'disabled':'')+'></label>';row.prepend(cell);cell.querySelector('input').onchange=update;});
  heading.querySelector('input').onchange=e=>{for(const row of rows){const input=row.querySelector('[data-table-select]');if(!input.disabled)input.checked=e.target.checked;}update();};
  const setActions=items=>{toolbar.replaceChildren();const compact=document.createElement('label');compact.className='pp-table-select-compact';compact.innerHTML='<input type="checkbox" aria-label="'+escape(__('Select all rows'))+'">'+escape(__('Select all'));compact.querySelector('input').onchange=event=>{heading.querySelector('input').checked=event.target.checked;heading.querySelector('input').dispatchEvent(new Event('change'));};toolbar.append(compact);const count=document.createElement('span');count.role='status';toolbar.append(count);for(const action of items){const button=document.createElement('button');button.type='button';button.className='btn '+(action.danger?'btn-danger':'btn-default');button.textContent=__(action.label);button.onclick=()=>action.run(selected(),api);toolbar.append(button);}const copy=document.createElement('button');copy.type='button';copy.className='btn btn-default';copy.textContent=__('Copy selected');copy.onclick=()=>{const values=rows.filter(row=>row.querySelector('[data-table-select]').checked).map(row=>[...row.cells].slice(1).map(cell=>cell.innerText.trim()).join('\t')).join('\n');frappe.utils.copy_to_clipboard(values);};toolbar.append(copy);update();};
  const api={selected,clear:()=>{rows.forEach(row=>row.querySelector('[data-table-select]').checked=false);update();},setActions,dispose:()=>{toolbar.remove();heading.remove();rows.forEach(row=>row.querySelector('.pp-table-select')?.remove());colgroup?.firstElementChild?.remove();if(colgroup)[...colgroup.children].forEach((col,i)=>col.style.width=originalWidths[i]);delete table.ppSelection;}};table.ppSelection=api;setActions(actions);return api;
 };
 plus_point.bulk_edit=({title='Edit selected rows',fields,apply})=>{
  const d=new frappe.ui.Dialog({title:__(title),fields:[{fieldtype:'HTML',fieldname:'intro',options:'<p>'+escape(__('Choose the fields to change. Other values stay the same.'))+'</p>'},...fields.flatMap(field=>[{fieldtype:'Check',fieldname:'change_'+field.fieldname,label:__('Change {0}',[field.label])},{...field,depends_on:'eval:doc.change_'+field.fieldname}]),{fieldtype:'HTML',fieldname:'feedback'}],primary_action_label:__('Apply to selected'),primary_action:async values=>{
   if(!plus_point.validate_inputs(d))return;const changes=Object.fromEntries(fields.filter(f=>values['change_'+f.fieldname]).map(f=>[f.fieldname,values[f.fieldname]]));if(!Object.keys(changes).length){plus_point.ui.feedback(d.fields_dict.feedback.$wrapper[0],{tone:'error',message:__('Choose at least one field to change.')});return;}
   d.disable_primary_action();try{const result=await apply(changes);if(result!==false)d.hide();}catch(error){for(const [key,message] of Object.entries(error.field_errors||{})){const field=d.fields_dict[key];if(field){plus_point.field_error(field,message,'bulk');field.$input?.one('input.pp-bulk change.pp-bulk',()=>plus_point.field_error(field,'','bulk'));}}plus_point.ui.feedback(d.fields_dict.feedback.$wrapper[0],{tone:'error',message:error.message});}finally{d.enable_primary_action();}
  }});d.show();plus_point.enhance_selectors(d);d.$wrapper.one('hidden.bs.modal',()=>d.$wrapper.remove());return d;
 };
 // Only call before discarding a PLUS POINT-owned FieldGroup, never native cached forms.
 plus_point.dispose_owned_forms=root=>{
  if(!root)return;plus_point.ui?.close_select(root);const nodes=[...(root.matches?.('[data-pp-form]')?[root]:[]),...root.querySelectorAll('[data-pp-form]')];
  for(const node of nodes){const group=node.pp_form;if(!group||group.pp_disposed)continue;group.pp_disposed=true;
   for(const control of Object.values(group.fields_dict||{})){control.ppDisposePicker?.();if(control.datepicker?.destroy){control.datepicker.destroy();control.datepicker=null;}}
  }
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
 plus_point.watch_ui=(name,callback)=>{watchers.set(name,callback);stats.watchers=watchers.size;if(!observer){observer=new MutationObserver(records=>{if(records.some(record=>!(record.target.nodeType===1?record.target:record.target.parentElement)?.closest('[contenteditable=true],.pp-freddy__motion,.pp-chart-plot')))schedule();});observer.observe(document.body,{childList:true,subtree:true});}schedule();};
 const wake=()=>{bursts=0;schedule();};
 document.addEventListener('visibilitychange',wake);document.addEventListener('pp:data-changed',wake);
 // Typing and pointer movement do not require rescanning every screen. DOM changes and routes wake the enhancements.
 frappe.router.on('change',()=>{wake();requestAnimationFrame(()=>{const page=frappe.container?.page;page?.querySelectorAll('.pp-operations,.pp-worker-profile').forEach(node=>{node.closest('.layout-main-section-wrapper')?.scrollTo(0,0);});});});
})();
