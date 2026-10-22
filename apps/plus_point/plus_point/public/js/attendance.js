/* Event/site/day selection and one clear, explicit attendance action per worker. */
(() => {
 frappe.provide('plus_point');
 const esc=value=>frappe.utils.escape_html(String(value??''));
 const states={'Present':1,'Half day':.5,'Absent':0,'Not marked':0};
 const rpc=(method,args)=>plus_point.form_rpc('attendance.'+method,args);
 const checks=new Map();
 plus_point.ensure_attendance_today=company=>{
  if(frappe.boot.plus_point?.is_platform||!company)return Promise.resolve();
  const key=company+frappe.datetime.get_today();
  if(!checks.has(key))checks.set(key,rpc('ensure_today',{company}).catch(error=>{checks.delete(key);throw error;}));
  return checks.get(key);
 };
 plus_point.open_attendance_picker=()=>{
  let dialog,busy=false;
  const company=plus_point.dashboard_company||frappe.boot.plus_point?.company_identity?.name;
  const error=message=>dialog.fields_dict.error.$wrapper.html(message?`<p class="pp-onboarding-errors" role="alert">${esc(message)}</p>`:'');
  dialog=new frappe.ui.Dialog({title:__('Open attendance register'),fields:[
   {fieldtype:'HTML',fieldname:'intro',options:`<p>${esc(__('Choose the event, site and work date. Crew and agreed wages come from saved allocations. Existing registers reopen.'))}</p>`},
   {fieldtype:'HTML',fieldname:'error'},
   {fieldtype:'Link',fieldname:'project',label:__('Event'),options:'Project',reqd:1,get_query:()=>({filters:{company,status:'Open'}}),onchange:async()=>{
    if(!dialog)return;await dialog.set_value('site','');dialog.set_df_property('site','read_only',!dialog.get_value('project'));
    const value=dialog.get_value('project');if(!value)return;
    const rows=await frappe.db.get_list('PP Site',{filters:{project:value,is_active:1},fields:['name'],limit:2});
    if(rows.length===1&&value===dialog.get_value('project'))dialog.set_value('site',rows[0].name);
   }},
   {fieldtype:'Link',fieldname:'site',label:__('Event site'),options:'PP Site',reqd:1,read_only:1,get_query:()=>({filters:{project:dialog.get_value('project'),is_active:1}})},
   {fieldtype:'Date',fieldname:'work_date',label:__('Work date'),default:frappe.datetime.get_today(),reqd:1}
  ],primary_action_label:__('Open register'),async primary_action(values){
   if(busy)return;busy=true;error('');dialog.disable_primary_action();
   try{const result=await rpc('prepare',values);dialog.hide();await frappe.set_route('Form','PP Daily Register',result.name);}
   catch(cause){error(cause.message);}finally{busy=false;dialog.enable_primary_action();}
  }});
  dialog.show();plus_point.enhance_selectors?.(dialog);
  frappe.db.get_list('Project',{filters:{company,status:'Open'},fields:['name'],limit:2}).then(rows=>{if(rows.length===1&&!dialog.get_value('project'))dialog.set_value('project',rows[0].name);});
 };
 function render(frm,data){
  const section=frm.__pp_attendance.get(0);let saving=false,dirty=false,correcting=false;
  const values=new Map(data.rows.map(row=>[row.id,row.status]));
  const amount=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(value);
  section.innerHTML=`<header class="pp-register-header"><div><p>${esc(data.date)} · ${esc(data.approved?__('Approved attendance'):__('Attendance to review'))}</p><h2>${esc(data.event)}</h2><p>${esc(data.site)}</p></div><a class="btn btn-default" href="/desk/pp-event-plans?${data.plan?'record='+encodeURIComponent(data.plan):'project='+encodeURIComponent(data.project)}">${esc(__('Review event plan'))}</a></header>
   <div class="pp-register-error" role="alert"></div><div class="pp-register-stats" aria-live="polite"></div>
   ${data.required!=null&&data.rows.length!==data.required?`<div class="pp-onboarding-errors">${esc(__('{0} workers planned for this site today; {1} allocated. Review the event plan before approving.',[data.required,data.rows.length]))}</div>`:''}
   <div class="pp-register-tools"><label>${esc(__('Find worker'))}<input type="search" class="form-control pp-attendance-search" placeholder="${esc(__('Search name or role'))}"></label><button type="button" class="btn btn-default pp-refresh-roster" ${data.approved?'disabled':''}>${esc(__('Refresh crew'))}</button></div>
   ${data.rows.length?`<div class="pp-register-table-wrap"><table class="pp-register-table"><thead><tr><th>${esc(__('Worker'))}</th><th>${esc(__('Attendance'))}</th><th>${esc(__('Daily wage'))}</th><th>${esc(__('Earned'))}</th></tr></thead><tbody>${data.rows.map(row=>`<tr data-line="${esc(row.id)}" data-search="${esc((row.title+' '+row.designation).toLocaleLowerCase())}"><th><a href="/desk/employee/${encodeURIComponent(row.employee)}">${esc(row.title)}</a><small>${esc(row.designation||__('Role not set'))}</small></th><td><div class="pp-attendance-choices" role="group" aria-label="${esc(__('Attendance for {0}',[row.title]))}">${['Present','Absent','Half day','Not marked'].map(state=>`<button type="button" class="btn btn-default" data-state="${esc(state)}" aria-pressed="${row.status===state}" ${row.locked?'disabled':''} ${state==='Not marked'&&(row.status==='Not marked'||row.locked)?'hidden':''}>${esc(__(state==='Not marked'?'Clear':state))}</button>`).join('')}</div><small class="pp-attendance-label">${esc(__(row.status))}${row.locked?' · '+esc(__('Recorded')):''}</small></td><td>${esc(amount(Number(row.wage_rate)))} ${esc(data.currency)}</td><td class="pp-attendance-amount"></td></tr>`).join('')}</tbody></table></div><p class="pp-no-workers-found" hidden>${esc(__('No matching worker. Try another name.'))}</p>`:`<div class="pp-crew-empty">${esc(__('No workers are allocated to this site on this date. Allocate crew in the event plan, then refresh this roster.'))}</div>`}
   ${data.can_correct?`<div class="pp-register-correction"><button type="button" class="btn btn-default pp-edit-attendance">${esc(__('Edit attendance'))}</button><label class="pp-correction-reason" hidden>${esc(__('Reason for correction'))}<textarea class="form-control" maxlength="1000"></textarea></label><button type="button" class="btn btn-primary pp-save-correction" hidden>${esc(__('Save corrections'))}</button><button type="button" class="btn btn-default pp-cancel-correction" hidden>${esc(__('Cancel'))}</button></div>`:''}
   <footer class="pp-register-footer"><p>${esc(data.approved?__('These recorded wages are included in finances. Corrections keep a reason and audit history.'):__('Present = full wage · Half day = 50% wage · Absent = zero. Draft marks affect finances only after approval.'))}</p><button type="button" class="btn btn-default pp-save-attendance" ${data.approved?'hidden':''}>${esc(__('Save draft'))}</button><button type="button" class="btn btn-primary pp-approve-attendance" ${data.approved?'hidden':''}>${esc(__('Approve attendance'))}</button></footer>`;
  const feedback=message=>{section.querySelector('.pp-register-error').innerHTML=message?`<p class="pp-onboarding-errors">${esc(message)}</p>`:'';};
  const update=()=>{
   let present=0,absent=0,half=0,unmarked=0,total=0;
   for(const row of data.rows){const state=values.get(row.id);present+=state==='Present';absent+=state==='Absent';half+=state==='Half day';unmarked+=state==='Not marked';total+=Number(row.wage_rate)*states[state];
    const tr=section.querySelector(`tr[data-line="${CSS.escape(row.id)}"]`);
    tr.querySelectorAll('[data-state]').forEach(button=>{button.setAttribute('aria-pressed',String(button.dataset.state===state));if(button.dataset.state==='Not marked')button.hidden=state==='Not marked'||row.locked||correcting;});
    tr.querySelector('.pp-attendance-label').textContent=__(state)+(row.locked?' · '+__('Recorded'):'');
    tr.querySelector('.pp-attendance-amount').textContent=state==='Not marked'?'—':`${amount(Number(row.wage_rate)*states[state])} ${data.currency}`;
   }
   section.querySelector('.pp-register-stats').innerHTML=[[__('Present'),present],[__('Half day'),half],[__('Absent'),absent],[__('Not marked'),unmarked],[__('Wages for this register'),amount(total)+' '+data.currency]].map(([label,value])=>`<div><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join('');
   section.querySelector('.pp-approve-attendance').disabled=saving||!!unmarked||!data.rows.length;
   section.querySelector('.pp-save-attendance').disabled=saving||!dirty;
  };
  section.querySelectorAll('[data-state]').forEach(button=>button.addEventListener('click',()=>{if(saving||data.approved&&!correcting)return;const row=button.closest('[data-line]');values.set(row.dataset.line,button.dataset.state);dirty=true;feedback('');update();}));
  section.querySelector('.pp-attendance-search').addEventListener('input',event=>{let visible=0;section.querySelectorAll('tr[data-line]').forEach(row=>{row.hidden=!row.dataset.search.includes(event.target.value.trim().toLocaleLowerCase());visible+=!row.hidden;});const empty=section.querySelector('.pp-no-workers-found');if(empty)empty.hidden=!!visible;});
  const marks=()=>data.rows.map(row=>({id:row.id,status:values.get(row.id)}));
  const save=async approve=>{
   if(saving)return;saving=true;update();feedback('');
   try{
    if(approve){
     const proposal=frappe.utils.deep_clone?frappe.utils.deep_clone(frm.doc):JSON.parse(JSON.stringify(frm.doc));
     for(const line of proposal.entries){line.attendance_status=values.get(line.name);line.units=String(states[line.attendance_status]);}
     const budgets=await plus_point.form_rpc('budget.preview',{document:JSON.stringify(proposal)});
     const blocked=budgets.find(b=>b.blocked);
     if(blocked)throw new Error(__('Spending budget exceeded: {0} / {1} {2}. Review the project budget or attendance before approving.',[blocked.projected,blocked.limit,blocked.currency]));
     const warning=budgets.find(b=>b.enabled&&b.level==='warning');
     if(warning){const confirmed=await new Promise(resolve=>frappe.confirm(esc(__('Attendance will bring spending to {0} of {1} {2}. Approve these reviewed wages?',[warning.projected,warning.limit,warning.currency])),()=>resolve(true),()=>resolve(false)));if(!confirmed)return;}
    }
    await rpc('save_marks',{name:frm.doc.name,marks:marks(),approve:approve?1:0});dirty=false;document.dispatchEvent(new Event('pp:data-changed'));await frm.reload_doc();frappe.show_alert({message:__(approve?'Attendance approved. Finances updated.':'Attendance draft saved.'),indicator:'green'});
   }catch(cause){feedback(cause.message);}
   finally{saving=false;if(section.isConnected)update();}
  };
  section.querySelector('.pp-edit-attendance')?.addEventListener('click',()=>{correcting=true;section.querySelectorAll('[data-state]').forEach(b=>{b.disabled=false;if(b.dataset.state==='Not marked')b.hidden=true;});section.querySelector('.pp-edit-attendance').hidden=true;for(const selector of ['.pp-correction-reason','.pp-save-correction','.pp-cancel-correction'])section.querySelector(selector).hidden=false;section.querySelector('.pp-correction-reason textarea').focus();});
  section.querySelector('.pp-cancel-correction')?.addEventListener('click',()=>render(frm,data));
  section.querySelector('.pp-save-correction')?.addEventListener('click',async()=>{if(saving)return;const reason=section.querySelector('.pp-correction-reason textarea').value.trim();if(!reason){feedback(__('Enter a reason for this attendance correction.'));return;}saving=true;const button=section.querySelector('.pp-save-correction');button.disabled=true;try{const result=await rpc('correct_marks',{name:frm.doc.name,marks:marks(),reason});const fresh=await rpc('detail',{name:frm.doc.name});render(frm,fresh);document.dispatchEvent(new Event('pp:data-changed'));frappe.show_alert({message:__('Attendance corrected. Wages updated; {0} invoice adjustments to review.',[result.invoice_adjustments.length]),indicator:'green'});}catch(error){feedback(error.message);}finally{saving=false;button.disabled=false;}});
  section.querySelector('.pp-save-attendance').onclick=()=>save(false);
  section.querySelector('.pp-approve-attendance').onclick=()=>save(true);
  section.querySelector('.pp-refresh-roster').onclick=async()=>{if(saving)return;if(dirty){feedback(__('Save your attendance marks before refreshing the crew list.'));return;}try{await rpc('refresh_roster',{name:frm.doc.name});await frm.reload_doc();}catch(cause){feedback(cause.message);}};
  update();section.dataset.ready='true';
 }
 frappe.ui.form.on('PP Daily Register',{
  async refresh(frm){
   if(frappe.boot.plus_point?.is_platform)return;
   if(frm.is_new()){plus_point.open_attendance_picker();return;}
   // Keep the native form/doc and its audit controls; replace the data-entry surface.
   frm.form_wrapper.find('.form-layout,.form-tabs-list').hide();
   if(!frm.__pp_attendance?.get(0)?.isConnected)frm.__pp_attendance=$('<section class="pp-register" aria-label="Attendance register"></section>').prependTo(frm.form_wrapper);
   frm.disable_save();frm.page.clear_primary_action();frm.page.clear_secondary_action();
   const key=frm.doc.name,sequence=frm.__pp_attendance_seq=(frm.__pp_attendance_seq||0)+1;
   try{const data=await rpc('detail',{name:key});if(sequence===frm.__pp_attendance_seq&&key===frm.doc.name)render(frm,data);}
   catch(cause){frm.__pp_attendance.html(`<p class="pp-onboarding-errors" role="alert">${esc(cause.message)}</p><button class="btn btn-default pp-retry" type="button">${esc(__('Try again'))}</button>`);frm.__pp_attendance.find('.pp-retry').on('click',()=>frm.refresh());}
  }
 });
})();
