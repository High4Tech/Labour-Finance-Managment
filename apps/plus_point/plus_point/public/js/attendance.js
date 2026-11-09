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
  return plus_point.load_feature('react_ui').then(()=>plus_point.react_attendance_picker());
  /* Native advanced picker retained below until authorized native consumers retire. */
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
 frappe.ui.form.on('PP Daily Register', {
  async refresh(frm) {
   if (frappe.boot.plus_point?.is_platform) return;
   if (frm.is_new()) {plus_point.open_attendance_picker(); return;}
   if (frm.__pp_attendance?.isConnected) return;
   const name = frm.doc.name;
   const host = document.createElement('section');
   frm.__pp_attendance = host;
   frm.form_wrapper.prepend(host);
   frm.form_wrapper.addClass('pp-client-native-hidden');
   frm.disable_save();
   frm.page.clear_primary_action();
   frm.page.clear_secondary_action();
   await plus_point.load_feature('react_ui').catch(error => {
    host.textContent = __('Attendance could not load. Refresh to retry.');
    console.error(error);
   });
   if (plus_point.react_attendance_mount && host.isConnected) {
    plus_point.react_attendance_mount(host, name, async marks => {
     const proposal = await frappe.db.get_doc('PP Daily Register', name);
     const statuses = new Map(marks.map(row => [row.id, row.status]));
     for (const line of proposal.entries) {
      if (!statuses.has(line.name)) throw new Error(__('The crew list changed. Refresh before approving.'));
      line.attendance_status = statuses.get(line.name);
      line.units = String(states[line.attendance_status]);
     }
     return plus_point.form_rpc('budget.preview', {document: JSON.stringify(proposal)});
    });
   }
  }
 });
})();
