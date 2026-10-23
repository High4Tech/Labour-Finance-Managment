/* Worker pages open as an operational overview; native profile editing stays available. */
(() => {
 const esc=value=>frappe.utils.escape_html(String(value??''));
 const number=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(value)||0);
 const stateClass=state=>({'Present':'present','Half day':'half','Absent':'absent','Pending approval':'pending','Not marked':'unmarked'}[state]||'off');
 function calendar(data){
  const offset=(new Date(data.start+'T12:00:00').getDay()+6)%7,weeks=Math.ceil((offset+data.calendar.length)/7),months=[];
  for(let week=0;week<weeks;week++){
   const day=data.calendar[Math.max(0,Math.min(data.calendar.length-1,week*7+3-offset))],key=day.date.slice(0,7);
   if(months.at(-1)?.key!==key)months.push({key,week,date:day.date});
  }
  const visible=months.filter((month,index)=>index!==0||months.length===1||months[1].week>=2);
  return `<p class="pp-calendar-range">${esc(data.start.slice(0,4)===data.end.slice(0,4)?data.end.slice(0,4):data.start.slice(0,4)+" / "+data.end.slice(0,4))}</p><div class="pp-worker-calendar-scroll"><div class="pp-worker-calendar" role="group" aria-label="${esc(__('Worker attendance calendar'))}" style="--pp-weeks:${weeks}">
   ${visible.map((month,index)=>{const start=Math.min(month.week,Math.max(0,weeks-2)),next=visible[index+1]?Math.min(visible[index+1].week,Math.max(0,weeks-2)):weeks;return `<span class="pp-calendar-month" style="grid-column:${start+2}/span ${Math.max(1,next-start)}">${esc(new Intl.DateTimeFormat(undefined,{month:'short'}).format(new Date(month.date+'T12:00:00')))}</span>`;}).join('')}
   ${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((day,index)=>`<span class="pp-calendar-weekday" style="grid-row:${index+2}">${esc(__(day))}</span>`).join('')}
   ${data.calendar.map((day,index)=>{const position=offset+index,label=day.date+': '+__(day.status);return `<button type="button" class="pp-worker-day pp-day-${stateClass(day.status)}" style="grid-column:${Math.floor(position/7)+2};grid-row:${position%7+2}" data-date="${day.date}" data-status="${esc(day.status)}" title="${esc(label)}" aria-label="${esc(label)}" tabindex="${index===data.calendar.length-1?0:-1}"></button>`;}).join('')}</div></div>`;
 }
 async function mount(frm,days=91){
  const name=frm.doc.name,sequence=frm.__pp_worker_seq=(frm.__pp_worker_seq||0)+1;
  if(!frm.__pp_worker?.get(0)?.isConnected)frm.__pp_worker=$('<section class="pp-worker-profile" aria-label="Worker overview"></section>').prependTo(frm.form_wrapper);
  const root=frm.__pp_worker.get(0);
  if(frm.__pp_worker_name!==name){frm.__pp_worker_name=name;frm.__pp_worker_edit=false;}
  frm.form_wrapper.find('.form-layout,.form-tabs-list,.form-dashboard').hide();
  if(frm.__pp_worker_edit)frm.enable_save();else{frm.__pp_worker_groups=null;frm.disable_save();frm.page.clear_primary_action();}
  root.innerHTML=`<p role="status">${esc(__('Loading worker overview…'))}</p>`;
  try{
   const data=await plus_point.form_rpc('worker_profile.overview',{employee:name,days});
   if(sequence!==frm.__pp_worker_seq||frm.doc.name!==name)return;
   if(frm.__pp_worker_edit){await plus_point.render_worker_editor(frm,root,data);root.dataset.ready='true';return;}
   frm.remove_custom_button(__('Create User'));
   const money=value=>number(value)+' '+data.currency;
   root.innerHTML=`<header class="pp-worker-heading"><div class="pp-person-heading">${plus_point.worker_avatar(data.title,data.image)}<div><p>${esc(__('Worker overview'))}</p><h2>${esc(data.title)}</h2></div></div><button type="button" class="btn btn-default pp-worker-edit">${esc(__(frm.__pp_worker_edit?'Back to overview':'Edit profile'))}</button></header>
    <div class="pp-worker-overview" ${frm.__pp_worker_edit?'hidden':''}><div class="pp-worker-layout"><aside class="pp-worker-identity"><span class="pp-worker-avatar" aria-hidden="true">${data.image?`<img src="${esc(data.image)}" alt="">`:esc(data.title.split(/\s+/).slice(0,2).map(s=>s[0]).join(''))}</span><button type="button" class="btn btn-default pp-worker-photo">${esc(__(data.image?'Update photo':'Add photo'))}</button>${data.image?`<button type="button" class="btn btn-default pp-remove-photo">${esc(__('Remove photo'))}</button>`:''}<h3>${esc(data.title)}</h3><p>${esc(data.designation||__('Role not set'))}</p><span class="pp-worker-status">${esc(__(data.status))}</span> <span class="pp-worker-status">${esc(__(data.allocation_status))}</span><dl>${[[__('Worker ID'),data.employee],[__('Department'),data.department||'—'],[__('Joined'),data.joining||'—'],[__('Phone'),data.phone||'—'],[__('Email'),data.email||'—']].map(([label,value])=>`<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`).join('')}</dl><button type="button" class="btn btn-default pp-worker-assign">${esc(__('Assign to an event'))}</button></aside>
    <div class="pp-worker-main"><div class="pp-worker-metrics">${[[__('Present days'),data.full_days],[__('Half days'),data.half_days],[__('Absent days'),data.absent_days],[__('Paid day equivalents'),number(data.paid_days)]].map(([label,value])=>`<article><span>${esc(label)}</span><strong>${esc(value)}</strong></article>`).join('')}</div>
    <section class="pp-worker-panel"><h3>${esc(__('Wages at a glance'))}</h3><div class="pp-worker-finances">${[[__('Earned'),data.earned],[__('Paid'),data.paid],[__('Outstanding'),data.outstanding]].map(([label,value])=>`<div><span>${esc(label)}</span><strong>${esc(money(value))}</strong></div>`).join('')}</div><p>${esc(__('Approved earnings and submitted payments across all dates. Draft attendance does not change these totals.'))}</p></section>
    <section class="pp-worker-panel"><header><h3>${esc(__('Attendance activity'))}</h3><label>${esc(__('Period'))}<select class="form-control pp-worker-period"><option value="91" ${days===91?'selected':''}>${esc(__('Last 3 months'))}</option><option value="366" ${days===366?'selected':''}>${esc(__('Last year'))}</option></select></label></header>
    ${calendar(data)}<div class="pp-worker-legend">${['Present','Half day','Absent','Pending approval','Not marked','No scheduled work'].map(state=>`<span><i class="pp-day-${stateClass(state)}"></i>${esc(__(state))}</span>`).join('')}</div><p>${esc(__('{0} to {1}. Longest recorded work streak: {2} days. Unmarked days are not counted as absence.',[data.start,data.end,data.longest_streak]))}</p></section>
    <section class="pp-worker-panel"><h3>${esc(__('Current event allocations'))}</h3>${data.assignments.length?data.assignments.map(row=>`<article class="pp-worker-allocation"><a href="/desk/pp-event-plans?record=${encodeURIComponent(row.plan||'')}"><strong>${esc(row.event)}</strong></a><p>${esc(row.site)} · ${esc(row.start)}${row.end?' – '+esc(row.end):''}</p><span>${esc(money(row.wage_rate))} ${esc(__('per full day'))}</span><a class="btn btn-default" href="/desk/pp-event-plans?record=${encodeURIComponent(row.plan||'')}">${esc(__('View event / move worker'))}</a></article>`).join(''):`<p>${esc(__('No active event allocation. Assign this worker to a site to include them in its daily register.'))}</p><button type="button" class="btn btn-default pp-worker-assign">${esc(__('Assign to an event'))}</button>`}</section>
    <section class="pp-worker-panel"><header><h3>${esc(__('Recent attendance'))}</h3><button type="button" class="btn btn-default pp-worker-history">${esc(__('View full statement'))}</button></header>${data.history.length?`<div class="pp-register-table-wrap"><table class="pp-register-table"><thead><tr>${['Date','Event / site','Attendance','Earned'].map(label=>`<th>${esc(__(label))}</th>`).join('')}</tr></thead><tbody>${data.history.map(row=>`<tr><th><a href="/desk/pp-work-entry/${encodeURIComponent(row.name)}">${esc(row.date)}</a></th><td>${esc(row.event)}<small>${esc(row.site)}</small></td><td>${esc(__(row.status))}</td><td>${esc(money(row.amount))}</td></tr>`).join('')}</tbody></table></div><p>${esc(__('Showing {0} of {1} recorded entries.',[data.history.length,data.history_count]))}</p>`:`<p>${esc(__('No approved attendance yet. Mark and approve a site register after work takes place.'))}</p><button type="button" class="btn btn-default pp-worker-attendance">${esc(__('Open attendance'))}</button>`}</section>
    </div></div></div>`;
   root.querySelector('.pp-worker-edit').onclick=()=>{frm.__pp_worker_edit=true;mount(frm,days);};
   root.querySelector('.pp-worker-period').onchange=event=>mount(frm,Number(event.target.value));
   root.querySelector('.pp-worker-photo').onclick=()=>new frappe.ui.FileUploader({doctype:'Employee',docname:name,make_attachments_public:false,restrictions:{allowed_file_types:['image/png','image/jpeg','image/webp','image/gif']},on_success:async file=>{try{await plus_point.form_rpc('operations.set_photo',{employee:name,file_url:file.file_url});await frm.reload_doc();}catch(error){frappe.msgprint(esc(error.message));}}});
   root.querySelector('.pp-remove-photo')?.addEventListener('click',async()=>{await plus_point.form_rpc('operations.set_photo',{employee:name});await frm.reload_doc();});
   root.querySelectorAll('.pp-worker-assign').forEach(button=>button.onclick=()=>frappe.set_route('pp-event-plans'));
   root.querySelector('.pp-worker-history').onclick=()=>frappe.set_route('query-report','PLUS POINT Worker Statement',{employee:name,company:data.company_id});
   root.querySelector('.pp-worker-attendance')?.addEventListener('click',()=>plus_point.open_attendance_picker());
   const buttons=[...root.querySelectorAll('.pp-worker-day')];
   buttons.forEach((button,index)=>{
    button.onclick=()=>{if(['Present','Half day','Absent'].includes(button.dataset.status))frappe.set_route('List','PP Work Entry',{employee:name,work_date:button.dataset.date});else plus_point.open_attendance_picker();};
    button.onkeydown=event=>{const moves={ArrowLeft:-7,ArrowRight:7,ArrowUp:-1,ArrowDown:1};if(!(event.key in moves))return;event.preventDefault();buttons.forEach(b=>b.tabIndex=-1);const target=buttons[Math.max(0,Math.min(buttons.length-1,index+moves[event.key]))];target.tabIndex=0;target.focus();};
   });
   root.dataset.ready='true';
  }catch(error){if(sequence!==frm.__pp_worker_seq)return;root.innerHTML=`<p class="pp-onboarding-errors" role="alert">${esc(error.message)}</p><button type="button" class="btn btn-default pp-profile-retry">${esc(__('Try again'))}</button>`;root.querySelector('button').onclick=()=>mount(frm,days);}
 }
 plus_point.open_worker_profile=mount;
 frappe.ui.form.on('Employee',{refresh(frm){if(frappe.boot.plus_point?.is_platform||!frappe.user.has_role('System Manager'))return;if(!frm.is_new())mount(frm);else{frm.form_wrapper.find('.form-layout,.form-tabs-list,.form-dashboard').hide();if(!frm.__pp_worker?.get(0)?.isConnected)frm.__pp_worker=$('<section class="pp-worker-profile"></section>').prependTo(frm.form_wrapper);plus_point.render_worker_editor(frm,frm.__pp_worker.get(0));}}});
})();
