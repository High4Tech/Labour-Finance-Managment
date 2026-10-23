/* Shared product controls. Native lists retain filters, selection, sorting and views. */
(()=>{
 frappe.provide('plus_point');const esc=v=>frappe.utils.escape_html(String(v??''));let queued=false,bar,lastSummary=0,summaryBusy=false,started=false;
 plus_point.reveal_control=control=>{const node=control?.$wrapper?.get(0),panel=node?.closest('[role=tabpanel]');if(panel?.hidden)document.querySelector(`[aria-controls="${CSS.escape(panel.id)}"]`)?.click();control?.set_focus?.();};
 const ranges=[['start_date','end_date'],['effective_start','effective_end'],['from_date','to_date'],['expected_start_date','expected_end_date'],['posting_date','due_date'],['date_of_birth','date_of_joining']];
 const dateOptions=frappe.ui.form.ControlDate.prototype.set_date_options;
 frappe.ui.form.ControlDate.prototype.set_date_options=function(){dateOptions.call(this);for(const key of ['minDate','maxDate'])if(typeof this.datepicker_options[key]==='string')this.datepicker_options[key]=frappe.datetime.str_to_obj(this.datepicker_options[key]);};
 plus_point.validate_dates=layout=>{
  let valid=true;const read=k=>layout.get_value?layout.get_value(k):layout.doc?.[k];
  for(const field of Object.values(layout.fields_dict||{})){
   if(field.df.fieldtype!=='Date'||field.df.hidden)continue;
   const iso=v=>v instanceof Date?frappe.datetime.obj_to_str(v):String(v),first=ranges.find(([,b])=>b===field.df.fieldname)?.[0],start=first&&read(first),value=read(field.df.fieldname),limits=[field.df.min_date,start].filter(Boolean).map(iso).sort(),min=limits.at(-1),max=field.df.max_date?iso(field.df.max_date):null;
   if(field.datepicker){field.datepicker.update('minDate',min?frappe.datetime.str_to_obj(min):false);field.datepicker.update('maxDate',max?frappe.datetime.str_to_obj(max):false);}
   const bad=value&&((min&&value<min)||(max&&value>max));
   plus_point.field_error(field,bad?(min&&value<min?__('Choose {0} or a later date.',[min]):__('Choose {0} or an earlier date.',[max])):'','date');
   if(bad){if(valid)plus_point.reveal_control(field);valid=false;}
  }
  for(const field of Object.values(layout.fields_dict||{}))if(field.df.fieldtype==='Table')for(const row of field.get_value()||[])for(const [a,b] of ranges)if(row[a]&&row[b]&&row[b]<row[a]){frappe.show_alert({message:__('Row {0}: end date must be on or after start date.',[row.idx]),indicator:'red'});valid=false;}
  return valid;
 };
 plus_point.bind_date_ranges=layout=>{for(const field of Object.values(layout.fields_dict||{})){if(field.df.fieldtype!=='Date'||field.__pp_date_bound)continue;field.__pp_date_bound=true;const original=field.df.onchange;field.df.onchange=async(...args)=>{await original?.(...args);plus_point.validate_dates(layout);};field.$input?.on('change.pp-dates blur.pp-dates',()=>plus_point.validate_dates(layout));}plus_point.validate_dates(layout);};
 const enhance=plus_point.enhance_selectors;plus_point.enhance_selectors=layout=>{enhance?.(layout);plus_point.bind_date_ranges(layout);};
 const validate=plus_point.validate_inputs;plus_point.validate_inputs=layout=>{const a=validate?.(layout)!==false,b=plus_point.validate_dates(layout);return a&&b;};
 function guidance(){
  document.querySelectorAll('.help-box:not([data-pp-info]),.pp-op-heading>div>p:not([data-pp-info]),.pp-op-section>p:not([data-pp-info]),.pp-event-plan-panel>p:not([data-pp-info])').forEach(note=>{
   if(note.closest('.pp-onboarding-shell,.pp-onboarding-pane')||note.closest('[role=alert],.pp-onboarding-errors,.pp-op-message,.pp-register-error')||!note.textContent.trim())return;
   const control=note.closest('.frappe-control'),label=control?.querySelector('.control-label')||note.closest('.pp-op-heading')?.querySelector('h2')||note.parentElement.querySelector(':scope > h3,:scope > h4')||note.closest('.pp-op-section')?.querySelector('.control-label'),target=label||note;
   const info=document.createElement('span');info.className='pp-info';const button=document.createElement('button');button.type='button';button.className='pp-info-trigger';button.textContent='i';button.setAttribute('aria-label',__('More information'));button.setAttribute('aria-expanded','false');const body=document.createElement('span');body.className='pp-info-body';body.role='note';body.hidden=true;body.textContent=note.textContent.trim();info.append(button,body);button.onclick=e=>{e.stopPropagation();plus_point.show_info(button,body.textContent);};info.onkeydown=e=>{if(e.key==='Escape'){body.hidden=true;button.setAttribute('aria-expanded','false');button.focus();}};
   note.dataset.ppInfo='true';note.hidden=true;if(label&&/^H[234]$/.test(label.tagName)){let line=label.parentElement;if(!line.classList.contains('pp-heading-line')){line=document.createElement('div');line.className='pp-heading-line';label.before(line);line.append(label);}line.append(info);}else if(label){label.classList.add('pp-label-line');label.append(info);}else{const title=note.closest('[role=tabpanel]')?.dataset.tab;if(title){const line=document.createElement('div');line.className='pp-heading-line pp-section-info';const text=document.createElement('span');text.textContent=title.replaceAll('-',' ');line.append(text,info);note.after(line);}else note.after(info);}
  });
 }
 function lists(){
  if(frappe.boot.plus_point?.is_platform)return;const list=window.cur_list;if(frappe.get_route()?.[0]!=='List'||!list?.filter_area?.filter_list||!Array.isArray(list.data)||list.doctype!==frappe.get_route()?.[1])return;
  if(['Vehicle','Warehouse'].includes(list.doctype)){list.settings.get_form_link=doc=>list.doctype==='Warehouse'&&doc.is_group?'/desk/warehouse/view/list?parent_warehouse='+encodeURIComponent(doc.name):'/desk/pp-inventory?view='+(list.doctype==='Vehicle'?'vehicles':'warehouses')+'&record='+encodeURIComponent(doc.name);list.make_new_doc=()=>plus_point.open_resource(list.doctype==='Vehicle'?'vehicles':'warehouses',()=>list.refresh());return;}
  const routes={'PP Contract Terms':'pp-agreements','PP Event Plan':'pp-event-plans','Sales Invoice':'pp-client-billing'},mode=routes[list.doctype];if(!mode||list.__pp_native_operation)return;list.__pp_native_operation=true;
  list.settings.get_form_link=doc=>mode==='pp-client-billing'?`/desk/${mode}?invoice=${encodeURIComponent(doc.name)}`:`/desk/${mode}?record=${encodeURIComponent(doc.name)}`;
  if(list.doctype==='Sales Invoice'&&Array.isArray(list.fields)&&!list.fields.includes('project'))list.fields.push('project');
  list.make_new_doc=()=>frappe.set_route(mode,{record:'new'});
  // Native list filters belong to the user; opening a section adds none.
 }
 async function totals(force=false){
  if(!bar||!frappe.boot.plus_point.company_identity?.name||summaryBusy||!force&&Date.now()-lastSummary<30000||frappe.boot.plus_point.is_platform)return;
  summaryBusy=true;try{const data=await plus_point.form_rpc('dashboard.overview',{display_currency:frappe.boot.plus_point.display_currency||undefined});lastSummary=Date.now();const choice=bar.querySelector('.pp-app-currency');if(choice&&!choice.options.length){choice.innerHTML=(data.currency_options||[data.currency]).map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');}if(choice)choice.value=data.currency;bar.querySelector('.pp-currency-status').textContent=data.fx?.status==='unavailable'?__('Rates unavailable; showing {0}.',[data.currency]):data.fx?.status==='converted'?__('Daily rate · {0}',[String(data.fx.as_of).slice(0,10)]):'';bar.querySelector('.pp-top-totals').innerHTML=[['Revenue',data.earned_revenue],['Profit',data.contribution],['Outstanding',data.client_balance]].map(([label,n])=>`<span><small>${esc(__(label))}</small><strong>${esc(new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(n)||0))} ${esc(data.currency)}</strong></span>`).join('');}catch{}finally{summaryBusy=false;}
 }
 function shell(){
  if(!frappe.boot.plus_point)return;const body=document.getElementById('body');if(!body)return;
  if(!bar?.isConnected){bar=document.createElement('div');bar.className='pp-global-bar';bar.innerHTML=`<div class="pp-top-totals" aria-label="${esc(__('Company financial totals'))}"></div><div class="pp-top-controls"><label class="pp-app-currency-label"><span class="sr-only">${esc(__("App reporting currency"))}</span><select class="form-control pp-app-currency" aria-label="${esc(__("App reporting currency"))}"></select><small class="pp-currency-status" role="status"></small></label><span class="pp-top-appearance"></span><button type="button" class="btn btn-default pp-global-help">${esc(__('Help and support'))}</button><button type="button" class="btn btn-default pp-language" aria-disabled="true">${esc(__('Language'))}</button></div>`;body.prepend(bar);bar.querySelector('.pp-app-currency').onchange=async e=>{const value=e.target.value;e.target.disabled=true;try{await plus_point.form_rpc('workflows.display_currency',{currency:value});frappe.boot.plus_point.display_currency=value;document.dispatchEvent(new Event('pp:display-currency'));await totals(true);}finally{e.target.disabled=false;}};bar.querySelector('.pp-global-help').onclick=()=>{const help=[...document.querySelectorAll('.pp-top-help')].find(b=>b.closest('.page-container')?.style.display!=='none');if(help)help.click();else frappe.msgprint({title:__('Help and support'),message:__('Use the information icons beside fields for help. Contact your software provider for account or billing support.')});};bar.querySelector('.pp-language').onclick=()=>frappe.show_alert({message:__('Language selection is coming soon.'),indicator:'blue'});}
  const appearance=document.querySelector('.pp-theme-toggle');if(appearance&&!bar.contains(appearance))bar.querySelector('.pp-top-appearance').append(appearance);
  const overview=/\/desk\/(plus-point|high4tech)\/?$/.test(location.pathname);bar.querySelector('.pp-top-totals').hidden=overview||frappe.boot.plus_point.is_platform;
  bar.querySelector('.pp-app-currency-label').hidden=!!frappe.boot.plus_point.is_platform;totals();
  const context=frappe.boot.plus_point;
  document.querySelectorAll('.body-sidebar a[href*="pp-onboarding"]').forEach(a=>{if(context.onboarding_complete)a.closest('.sidebar-item-container,.sidebar-item')?.remove();});
  if(context.onboarding_required&&frappe.get_route()?.[0]!=='pp-onboarding')frappe.set_route('pp-onboarding');
  document.body.classList.toggle('pp-onboarding-required',!!context.onboarding_required);
 }
 function update(){queued=false;guidance();lists();shell();document.querySelectorAll('.pp-register-table').forEach(table=>{const labels=[...table.querySelectorAll('thead th')].map(c=>c.textContent||__('Actions'));table.querySelectorAll('tbody>tr').forEach(row=>[...row.children].forEach((cell,i)=>{if(!cell.dataset.label)cell.dataset.label=labels[i]||__('Actions');}));});}
 function schedule(){if(queued)return;queued=true;requestAnimationFrame(update);}
 $(document).on('form-refresh.pp-experience',(_e,frm)=>{plus_point.bind_date_ranges(frm);schedule();});
 document.addEventListener('click',event=>{if(frappe.boot.plus_point?.is_platform||frappe.get_route()?.[0]!=='List'||frappe.get_route()?.[1]!=='Sales Invoice')return;const anchor=event.target.closest('a[href]');if(!anchor?.closest('.list-row-container'))return;const match=new URL(anchor.href,location.href).pathname.match(/\/(?:desk|app)\/(?:[^/]+\/)?sales-invoice\/([^/]+)$/);if(match){event.preventDefault();event.stopImmediatePropagation();frappe.set_route('pp-client-billing',{invoice:decodeURIComponent(match[1])});}},true);
 let totalsTimer;document.addEventListener('pp:data-changed',()=>{clearTimeout(totalsTimer);totalsTimer=setTimeout(()=>totals(true),400);});document.addEventListener('pp:onboarding',schedule);
 const start=()=>{if(started||!frappe.boot?.plus_point)return;started=true;plus_point.watch_ui('experience',update);frappe.router.on('change',schedule);schedule();};
 $(document).on('app_ready.pp-experience',start);if(frappe.app?.sidebar)start();
})();
