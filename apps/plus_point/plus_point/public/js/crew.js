/* One available-worker checklist for onboarding, event plans and manual allocations. */
(()=>{
 frappe.provide('plus_point');const esc=value=>frappe.utils.escape_html(String(value??''));
 plus_point.crew_rpc=async(method,args={})=>{
  const response=await fetch('/api/method/plus_point.'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':frappe.csrf_token},body:JSON.stringify(args)});
  const data=await response.json();if(!response.ok||data.exc_type){let message=__('Could not save. Review the worker list and try again.');try{if(data._server_messages)message=JSON.parse(data._server_messages).map(v=>JSON.parse(v).message).join(' ');}catch{}throw new Error(message.replace(/<[^>]*>/g,''));}return data.message;
 };
 const importFor=(dialog,company,refresh)=>{dialog.$wrapper.one('hidden.bs.modal',()=>plus_point.open_import(company,()=>setTimeout(()=>{dialog.show();refresh();},0),'employees','Return to crew selection'));dialog.hide();};
 plus_point.quick_worker_fields=({designation='Event crew',categories=['Event crew'],locked=false}={})=>[
  {fieldtype:'Data',fieldname:'first_name',label:__('First name'),reqd:1},
  {fieldtype:'Data',fieldname:'last_name',label:__('Last name')},
  {fieldtype:'Select',fieldname:'designation',label:__('Crew category'),options:[...new Set([designation,...categories])],default:designation,reqd:1,read_only:locked},
  {fieldtype:'Link',fieldname:'gender',label:__('Gender'),options:'Gender',only_select:1,reqd:1},
  {fieldtype:'Date',fieldname:'date_of_birth',label:__('Date of birth'),max_date:frappe.datetime.get_today(),reqd:1},
  {fieldtype:'Date',fieldname:'date_of_joining',label:__('Joining date'),default:frappe.datetime.get_today(),reqd:1},
  {fieldtype:'Data',fieldname:'cell_number',label:__('Phone')},
  {fieldtype:'Data',fieldname:'personal_email',label:__('Email'),options:'Email'}
 ];
 plus_point.quick_worker_form=(body,{company,designation,categories,locked=false,onSaved,onCancel,label='Save worker'})=>{
  body.replaceChildren();const heading=document.createElement('h4');heading.textContent=__('Add crew');body.append(heading);
  const fields=plus_point.quick_worker_fields({designation,categories,locked}),form=new frappe.ui.FieldGroup({fields,body:$(body)});form.make();plus_point.enhance_selectors?.(form);
  for(const c of Object.values(form.fields_dict))c.$input?.attr('aria-label',c.df.label||'');
  const feedback=document.createElement('p');feedback.setAttribute('role','alert');feedback.hidden=true;body.append(feedback);
  const actions=document.createElement('div');actions.className='pp-actions';body.append(actions);
  const save=document.createElement('button');save.type='button';save.className='btn btn-primary';save.textContent=__(label);actions.append(save);
  const cancel=document.createElement('button');cancel.type='button';cancel.className='btn btn-default';cancel.textContent=__('Cancel');actions.append(cancel);cancel.onclick=()=>onCancel?.();
  save.onclick=async()=>{
   feedback.hidden=true;if(!plus_point.validate_inputs(form))return;const values=form.get_values(true)||{};let valid=true;
   for(const df of fields)if(df.reqd&&!values[df.fieldname]){plus_point.field_error(form.fields_dict[df.fieldname],__('Enter {0}.',[df.label]));if(valid)form.fields_dict[df.fieldname].set_focus();valid=false;}if(!valid)return;
   save.disabled=cancel.disabled=true;
   try{const worker=await plus_point.crew_rpc('crew.add_worker',{company,values});if(body.isConnected){await onSaved(worker);document.dispatchEvent(new Event('pp:data-changed'));}}
   catch(error){feedback.textContent=error.message;feedback.hidden=false;}finally{save.disabled=cancel.disabled=false;}
  };
  form.fields_dict.first_name.set_focus();return form;
 };
 plus_point.CrewPicker=class{
  constructor(root,options){this.root=root;this.options=options;this.selected=[...(options.selected||[])];this.rows=[];this.labels=new Map();this.ready=false;this.limit=Number.MAX_SAFE_INTEGER;this.build();this.refresh();}
  build(){
   this.root.classList.add('pp-crew-picker');this.root.innerHTML=`<p class="pp-crew-dates"></p><div class="pp-crew-selected" aria-label="${esc(__('Selected workers'))}"></div><div class="pp-crew-tools"><label>${esc(__('Search workers'))}<input type="search" class="form-control pp-crew-search" placeholder="${esc(__('Name, worker ID or phone'))}"></label><button type="button" class="btn btn-default pp-crew-refresh">${esc(__('Refresh list'))}</button><button type="button" class="btn btn-default pp-crew-import">${esc(__('Import workers'))}</button><button type="button" class="btn btn-default pp-crew-add">${esc(__('Add worker'))}</button></div><div class="pp-crew-new" hidden></div><p class="pp-crew-count" role="status"></p><div class="pp-crew-error" role="alert" tabindex="-1" hidden></div><div class="pp-crew-list"></div><button type="button" class="btn btn-default pp-crew-more" hidden>${esc(__('Show more workers'))}</button><p class="pp-crew-excluded"></p>`;
   this.root.querySelector('.pp-crew-search').oninput=()=>{this.limit=Number.MAX_SAFE_INTEGER;this.render();};
   this.root.querySelector('.pp-crew-refresh').onclick=()=>this.refresh();
   this.root.querySelector('.pp-crew-import').onclick=()=>{if(this.options.onImport)this.options.onImport(()=>this.refresh());else plus_point.open_import(this.options.company,()=>this.refresh(),'employees');};
   this.root.querySelector('.pp-crew-add').onclick=()=>this.addForm();
   this.root.querySelector('.pp-crew-more').onclick=()=>{this.limit+=80;this.render();};
  }
  values(){return [...this.selected];}
  valid(){return this.ready&&this.selected.length>0&&this.selected.every(name=>this.rows.some(row=>row.name===name&&row.available));}
  changed(){this.options.onChange?.(this.values(),this.valid());}
  error(message=''){const el=this.root.querySelector('.pp-crew-error');el.textContent=message;el.hidden=!message;}
  async refresh(context={}){
   Object.assign(this.options,context);const request=this.request=(this.request||0)+1;this.ready=false;this.root.dataset.ready='false';this.changed();this.root.setAttribute('aria-busy','true');this.error();
   this.root.querySelector('.pp-crew-count').textContent=__('Checking workers…');
   try{const data=await plus_point.crew_rpc('crew.available',{company:this.options.company,start_date:this.options.start,end_date:this.options.end});if(request!==this.request)return;this.rows=data.rows;this.rows.forEach(r=>this.labels.set(r.name,r.worker));this.ready=true;this.render();}
   catch(error){if(request===this.request){this.error(error.message);this.root.querySelector('.pp-crew-count').textContent=__('Could not load workers. Refresh the list to retry.');}}
   finally{if(request===this.request){this.root.setAttribute('aria-busy','false');this.root.dataset.ready=String(this.ready);this.changed();}}
  }
  render(){
   const focused=this.root.contains(document.activeElement)?document.activeElement?.dataset.worker:undefined;
   const chosen=this.root.querySelector('.pp-crew-selected');chosen.innerHTML='';
   for(const name of this.selected){const row=this.rows.find(r=>r.name===name),tag=document.createElement('span');tag.className='pp-crew-tag'+(!row?.available?' is-unavailable':'');tag.innerHTML=`${plus_point.worker_capsule(this.labels.get(name)||name,row?.image)}<button type="button" aria-label="${esc(__('Remove {0}',[this.labels.get(name)||name]))}">×</button>`;tag.querySelector('button').onclick=()=>{this.selected=this.selected.filter(v=>v!==name);this.render();this.root.querySelector('.pp-crew-search').focus();};chosen.append(tag);}
   if(!this.selected.length)chosen.textContent=__('No workers selected yet. Tick workers below.');
   this.root.querySelector('.pp-crew-dates').textContent=__('Available for {0} through {1}. Workers with overlapping assignments are excluded.',[this.options.start,this.options.end]);
   const query=this.root.querySelector('.pp-crew-search').value.trim().toLowerCase(),available=this.rows.filter(r=>r.available),visible=available.filter(r=>[r.worker,r.name,r.phone].some(v=>v.toLowerCase().includes(query))),list=this.root.querySelector('.pp-crew-list');
   list.innerHTML='';for(const row of visible.slice(0,this.limit)){const label=document.createElement('label');label.className='pp-crew-row';label.innerHTML=`<input type="checkbox" ${this.selected.includes(row.name)?'checked':''}><span>${plus_point.worker_capsule(row.worker,row.image)}<small>${esc([row.name,row.phone].filter(Boolean).join(' · '))}</small></span>`;label.querySelector('input').dataset.worker=row.name;label.querySelector('input').setAttribute('aria-label',__('Select {0}',[row.worker]));label.querySelector('input').onchange=event=>{this.selected=event.target.checked?[...this.selected,row.name]:this.selected.filter(v=>v!==row.name);this.render();};list.append(label);}
   if(!visible.length)list.innerHTML=`<p class="pp-crew-empty">${esc(query?__('No workers match your search.'):this.rows.length?__('No workers are available for these dates. Change the dates, add crew or review existing assignments.'):__('No workers yet. Import your worker sheet or add a worker above.'))}</p>`;
   this.root.querySelector('.pp-crew-more').hidden=visible.length<=this.limit;
   this.root.querySelector('.pp-crew-count').textContent=__('{0} selected · {1} available',[this.selected.length,available.length]);
   this.root.querySelector('.pp-crew-excluded').textContent=this.rows.length>available.length?__('{0} workers excluded because of bookings or employment dates.',[this.rows.length-available.length]):'';
   const blocked=this.selected.filter(name=>!this.rows.some(r=>r.name===name&&r.available));this.error(blocked.length?__('Some selected workers are no longer available. Remove the highlighted tags or change the dates.'): '');if(focused)[...this.root.querySelectorAll('input[data-worker]')].find(input=>input.dataset.worker===focused)?.focus({preventScroll:true});this.changed();
  }
  addForm(){
   const body=this.root.querySelector('.pp-crew-new');if(body.childElementCount){body.hidden=!body.hidden;return;}body.hidden=false;
   this.add_form=plus_point.quick_worker_form(body,{company:this.options.company,categories:[...new Set(['Event crew',...this.rows.map(r=>r.designation).filter(Boolean)])],label:'Create and select worker',onCancel:()=>{body.hidden=true;body.replaceChildren();},onSaved:async worker=>{this.labels.set(worker.name,worker.worker);this.selected.push(worker.name);await this.refresh();body.hidden=true;body.replaceChildren();}});
  }
 };
 plus_point.choose_event_crew=async(frm)=>{
  if(frm.is_dirty()){frm.set_intro(__('Save the event plan before choosing crew.'),'orange');return;}
  if(frm.doc.crew_allocated){frappe.set_route('List','PP Assignment',{pp_event_plan:frm.doc.name});return;}
  let picker,previewId=0;const dialog=new frappe.ui.Dialog({title:__('Choose event crew'),size:'extra-large',fields:[{fieldtype:'HTML',fieldname:'crew'},{fieldtype:'HTML',fieldname:'proposal'}],primary_action_label:__('Allocate selected crew'),async primary_action(){
   if(!picker.valid())return;dialog.disable_primary_action();try{await plus_point.crew_rpc('crew.save_selection',{plan:frm.doc.name,employees:JSON.stringify(picker.values())});const result=await plus_point.crew_rpc('events.allocate_crew',{plan:frm.doc.name});dialog.hide();await frm.reload_doc();frm.set_intro(__('{0} crew assignments saved. Attendance is recorded separately.',[result.created]),'green');}catch(error){await picker.refresh();picker.error(error.message);}
  }});
  dialog.$wrapper.addClass('pp-crew-dialog');dialog.show();dialog.disable_primary_action();
  const changed=async(names,valid)=>{dialog.disable_primary_action();const own=++previewId,box=dialog.fields_dict.proposal.$wrapper;box.empty();if(!valid)return;
   try{const proposal=await plus_point.crew_rpc('events.preview_crew',{plan:frm.doc.name,employees:JSON.stringify(names)});if(own!==previewId)return;
    box.html(`<div class="pp-crew-proposal"><p>${esc(__('{0} selected · {1} new assignments planned. Staffing requirements control how many workers each phase uses.',[names.length,proposal.assignments.length]))}</p>${proposal.shortages.length?`<p role="status">${esc(__('Select more available workers or reduce the site staffing requirement.'))}</p><ul>${proposal.shortages.map(r=>`<li>${esc(r.site)}: ${esc(r.missing)} ${esc(__('workers missing'))}</li>`).join('')}</ul>`:`<ul>${proposal.assignments.map(r=>`<li>${esc(r.worker)} · ${esc(r.site)} · ${esc(r.start_date)} – ${esc(r.end_date)}</li>`).join('')}</ul>`}</div>`);if(!proposal.shortages.length)dialog.enable_primary_action();
   }catch(error){if(own===previewId)picker?.error(error.message);}
  };
  picker=new plus_point.CrewPicker(dialog.fields_dict.crew.$wrapper.get(0),{company:frm.doc.company,start:frm.doc.start_date,end:frm.doc.end_date,selected:JSON.parse(frm.doc.selected_crew||'[]'),onChange:changed,onImport:refresh=>importFor(dialog,frm.doc.company,refresh)});
 };
 plus_point.assign_workers=(defaults={},after)=>{
  let picker;const field=(fieldtype,fieldname,label,extra={})=>({fieldtype,fieldname,label:__(label),reqd:1,...(fieldtype==='Link'?{only_select:1}:{}),...extra});
  const dialog=new frappe.ui.Dialog({title:__('Assign workers'),size:'extra-large',fields:[
   field('Link','project','Event project',{options:'Project',default:defaults.project}),
   field('Link','site','Event site',{options:'PP Site',default:defaults.site,get_query:()=>({filters:{project:dialog.get_value('project'),is_active:1}})}),
   field('Link','contract_terms','Client agreement',{options:'PP Contract Terms',get_query:()=>({filters:{project:dialog.get_value('project'),status:'Active'}})}),
   field('Date','start_date','From date',{default:defaults.start||frappe.datetime.get_today()}),field('Date','end_date','Through date',{default:defaults.end||frappe.datetime.get_today()}),
   field('Currency','wage_rate','Daily worker wage'),field('Currency','client_rate','Daily client rate',{reqd:0,default:0}),{fieldtype:'HTML',fieldname:'crew'}
  ],primary_action_label:__('Assign selected workers'),async primary_action(){if(!plus_point.validate_inputs(dialog))return;const values=dialog.get_values(true)||{};
   if(!picker?.valid()){picker?.error(__('Choose at least one available worker.'));return;}
   const missing=dialog.fields.filter(f=>f.reqd&&!values[f.fieldname]);if(missing.length){picker.error(__('Complete: {0}',[missing.map(f=>f.label).join(', ')]));return;}
   dialog.disable_primary_action();try{const result=await plus_point.crew_rpc('crew.assign',{...values,employees:JSON.stringify(picker.values())});dialog.hide();after?.();frappe.container.page?.page?.set_indicator?.(__('{0} workers assigned.',[result.created]),'green');}catch(error){picker.error(error.message);await picker.refresh();picker.error(error.message);}finally{if(picker?.valid())dialog.enable_primary_action();else dialog.disable_primary_action();}
  }});
  dialog.$wrapper.addClass('pp-crew-dialog');dialog.show();dialog.disable_primary_action();plus_point.enhance_selectors(dialog);
  let request=0;const refresh=async()=>{const project=dialog.get_value('project'),start=dialog.get_value('start_date'),end=dialog.get_value('end_date'),own=++request;if(!project||!start||!end)return;
   try{const doc=await frappe.db.get_doc('Project',project);if(own!==request)return;
    if(picker)await picker.refresh({company:doc.company,start,end});else picker=new plus_point.CrewPicker(dialog.fields_dict.crew.$wrapper.get(0),{company:doc.company,start,end,selected:defaults.employees||[],onChange:(_names,valid)=>valid?dialog.enable_primary_action():dialog.disable_primary_action(),onImport:done=>importFor(dialog,picker.options.company,done)});
   }catch{dialog.fields_dict.crew.$wrapper.text(__('Could not load this project. Choose it again.'));}
  };
  dialog.fields_dict.project.df.onchange=async()=>{await dialog.set_values({site:'',contract_terms:''});await refresh();};
  for(const name of ['start_date','end_date'])dialog.fields_dict[name].df.onchange=refresh;
  plus_point.bind_saved_context(dialog);
  refresh();return dialog;
 };
})();
