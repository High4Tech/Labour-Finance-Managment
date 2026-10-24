/* Shared input guidance, saved-context defaults and explicit record removal. */
(()=>{
 frappe.provide('plus_point');
 const esc=value=>frappe.utils.escape_html(String(value??''));
 const person=new Set(['first_name','middle_name','last_name','contact_name','person_to_be_contacted']);
 const phone=new Set(['phone','cell_number','emergency_phone_number','phone_number','mobile_no']);
 const code=new Set(['employee_number','passport_number','license_plate']);
 const numeric=new Set(['Int','Float','Currency','Percent']);
 const coordinates=new Set(['latitude','longitude']);
 const read=(layout,key)=>layout.get_value?layout.get_value(key):layout.doc?.[key];
 const write=(layout,values)=>layout.set_values?layout.set_values(values):layout.set_value(values);
 const nameChars=/^[\p{L}\p{M} .\-'’ʼ]*$/u,phoneChars=/^\+?[0-9 ()-]*$/,codeChars=/^[\p{L}\p{N} ./_-]*$/u;
 function rule(df){if(numeric.has(df.fieldtype)||coordinates.has(df.fieldname))return 'number';if(df.fieldtype!=='Data')return '';return df.options==='Email'||['email','personal_email'].includes(df.fieldname)?'email':person.has(df.fieldname)?'person':phone.has(df.fieldname)?'phone':code.has(df.fieldname)?'code':'';}
 function allowed(df,value,partial=false){
  if(!value)return true;
  switch(rule(df)){
   case 'number':return (df.fieldtype==='Int'?/^-?[\d,]*$/:/^-?[\d,]*(?:\.\d*)?$/).test(value)&&(partial||Number.isFinite(Number(value.replaceAll(',',''))));
   case 'person':return nameChars.test(value)&&(partial||/\p{L}/u.test(value));
   case 'phone':return phoneChars.test(value)&&value.length<=40&&(partial||value.replace(/\D/g,'').length>=7&&value.replace(/\D/g,'').length<=15);
   case 'email':return partial||/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
   case 'code':return codeChars.test(value);
   default:return true;
  }
 }
 function hint(df){switch(rule(df)){case 'number':return df.fieldtype==='Int'?__('Use whole numbers only.'):__('Use numbers only.');case 'person':return __('Use letters, spaces, apostrophes, hyphens or periods.');case 'phone':return __('Enter 7–15 digits; +, spaces, parentheses and hyphens are allowed.');case 'email':return __('Enter an email such as name@example.com.');case 'code':return __('Use letters, numbers, spaces, periods, slashes, underscores or hyphens.');default:return '';}}
 const limits={workers_required:[1,500],pp_salary_amount:[0],pp_daily_rate:[0],pp_monthly_rate:[0],pp_pay_amount:[0],pp_leaves_per_month:[0,31],pp_loan_wait_months:[0],pp_loan_deduction_percent:[0,100],latitude:[-90,90],longitude:[-180,180]};
 let errorSequence=0;
 plus_point.field_error=(control,text,source='input')=>{
  if(!control?.$wrapper)return;control.pp_errors||={};control.pp_errors[source]=text||'';
  const message=Object.values(control.pp_errors).find(Boolean)||'';
  let feedback=control.$wrapper.find('.pp-input-hint');if(!feedback.length)feedback=$('<span class="pp-input-hint" role="alert"></span>').appendTo(control.$wrapper);
  if(!feedback.attr('id'))feedback.attr('id','pp-field-error-'+(++errorSequence));feedback.text(message);
  const input=control.$input||control.$wrapper.find('[contenteditable]').first(),node=input.get(0),ids=new Set((input.attr('aria-describedby')||'').split(/\s+/).filter(Boolean));ids.add(feedback.attr('id'));
  input.attr({'aria-describedby':[...ids].join(' '),'aria-invalid':String(!!message)});node?.setCustomValidity?.(message);
 };
 function error(control,required=true){
  const {df}=control,raw=String(control.$input.val()??'').trim();
  if(!raw)return required&&df.reqd?__('Enter {0}.',[df.label||df.fieldname]):'';
  if(df.fieldtype==='Date'&&!moment(raw,control.date_format||frappe.defaultDateFormat,true).isValid())return __('Enter a date in {0} format.',[control.date_format||frappe.defaultDateFormat]);
  if(!allowed(df,raw))return hint(df);
  if(rule(df)==='number'){
   const n=Number(raw.replaceAll(',','')),range=limits[df.fieldname]||[],min=df.min??range[0],max=df.max??range[1];
   if(df.positive&&n<=0)return __('Enter a number greater than zero.');
   if(min!=null&&n<min||max!=null&&n>max)return min!=null&&max!=null?__('Enter a number from {0} to {1}.',[min,max]):min!=null?__('Enter {0} or more.',[min]):__('Enter {0} or less.',[max]);
  }
  return '';
 }
 function contactErrors(layout,enforce=false){
  const fields=layout.fields_dict||{},email=fields.email,phone=fields.phone;if(!fields.customer_name||!email?.$input||!phone?.$input)return true;
  const missing=!String(email.$input.val()||'').trim()&&!String(phone.$input.val()||'').trim(),message=missing&&enforce?__('Enter an email or phone number for this client contact.'):'';
  for(const field of [email,phone])plus_point.field_error(field,message,'contact');return !missing;
 }
 plus_point.enhance_inputs=layout=>{
  for(const control of Object.values(layout.fields_dict||{})){
   const {df,$input:input}=control;if(!input)continue;
   const autocomplete=({customer_name:'organization',company_name:'organization',email:'email',personal_email:'email',address_line1:'address-line1',address_line2:'address-line2',city:'address-level2',state:'address-level1',postal_code:'postal-code'})[df.fieldname];if(autocomplete&&df.fieldtype==='Data')input.attr('autocomplete',autocomplete);
   if(control.pp_input_rule||!input.get(0)?.setCustomValidity)continue;
   control.pp_input_rule=true;const kind=rule(df),node=input.get(0);
   input.attr('inputmode',kind==='number'?(df.fieldtype==='Int'?'numeric':'decimal'):kind==='phone'?'tel':kind==='email'?'email':'text');
   if(kind==='email'){input.attr({type:'email',autocomplete:'email'});control.validate=value=>value;}
   if(kind==='phone')input.attr({type:'tel',autocomplete:df.fieldname==='emergency_phone_number'?'off':'tel',maxlength:40});
   if(kind==='person')input.attr({autocomplete:({first_name:'given-name',middle_name:'additional-name',last_name:'family-name',contact_name:'name'})[df.fieldname]||'off',maxlength:140});
   const feedback=text=>plus_point.field_error(control,text);
   const prospective=text=>node.value.slice(0,node.selectionStart??node.value.length)+text+node.value.slice(node.selectionEnd??node.value.length);
   input.on('beforeinput.pp-rule',event=>{const e=event.originalEvent;if(e.isComposing||!e.inputType?.startsWith('insert')||e.data==null)return;if(!allowed(df,prospective(e.data),true)){e.preventDefault();feedback(hint(df));}});
   input.on('paste.pp-rule',event=>{const text=event.originalEvent.clipboardData?.getData('text');if(text!=null&&!allowed(df,prospective(text),true)){event.preventDefault();feedback(hint(df));}});
   let lastValid=node.value;
   input.on('input.pp-rule',()=>{const valid=allowed(df,node.value,true);if(valid)lastValid=node.value;else node.value=lastValid;feedback(valid?error(control,false):hint(df));contactErrors(layout,!!(layout.fields_dict?.email?.pp_errors?.contact||layout.fields_dict?.phone?.pp_errors?.contact));});
   input.on('blur.pp-rule',()=>feedback(error(control)));
  }
 };
 // Quiet readiness checks must not mark untouched steps as invalid or move focus.
 plus_point.inputs_complete=layout=>{
  const controls=Object.values(layout.fields_dict||{});
  for(const c of controls){if(c.df.hidden||c.df.read_only||['Section Break','Column Break','HTML','Button'].includes(c.df.fieldtype))continue;const value=c.get_value?.();if(c.df.reqd&&(value==null||value===''||Array.isArray(value)&&!value.length))return false;if(c.$input?.get(0)?.setCustomValidity&&error(c))return false;}
  const f=layout.fields_dict||{};return !f.customer_name||!f.email||!f.phone||!!String(f.email.get_value()||f.phone.get_value()||'').trim();
 };
 plus_point.validate_inputs=layout=>{
  const bad=[];for(const c of Object.values(layout.fields_dict||{})){
   if(!c.$input||!c.$input.get(0)?.setCustomValidity||c.df.hidden||c.df.read_only||c.$wrapper?.css('display')==='none')continue;
   const message=error(c);plus_point.field_error(c,message);if(message)bad.push(c);
  }
  if(!contactErrors(layout,true)&&!bad.length)bad.push(layout.fields_dict.email);
  if(bad[0]){plus_point.reveal_control?.(bad[0]);bad[0].set_focus?.();}return !bad.length;
 };
 plus_point.fill_saved_context=async(layout,{project,site,replace=false}={})=>{
  if(frappe.boot.plus_point?.is_platform)return;
  const identity=plus_point.dashboard_company||frappe.boot.plus_point?.company_identity?.name;
  if(layout.fields_dict.company&&!read(layout,'company')&&identity)await layout.set_value('company',identity);
  const own=layout.pp_defaults_request=(layout.pp_defaults_request||0)+1;
  const keys=['company','customer','site','contract_terms','start_date','end_date','wage_rate','client_rate','warehouse'],before=Object.fromEntries(keys.map(key=>[key,layout.fields_dict[key]?read(layout,key):undefined]));
  const data=await plus_point.form_rpc('form_defaults.context',{project:project||read(layout,'project'),site,company:read(layout,'company')||identity});
  if(own!==layout.pp_defaults_request)return;
  const updates={};for(const key of keys){
   if(layout.fields_dict[key]&&data[key]!=null&&read(layout,key)===before[key]&&(replace||before[key]==null||before[key]===''||key==='wage_rate'&&Number(before[key])===0))updates[key]=data[key];
  }
  await write(layout,updates);return data;
 };
 plus_point.bind_saved_context=layout=>{
  if(layout.pp_defaults_bound||frappe.boot.plus_point?.is_platform)return;layout.pp_defaults_bound=true;
  const load=async(replace=false)=>{if(layout.doctype&&!layout.is_new?.())return;try{await plus_point.fill_saved_context(layout,{replace});}catch{const control=layout.fields_dict.project;control&&layout.set_df_property('project','description',__('Saved details could not load. Choose the site, dates and agreement below.'));}};
  const project=layout.fields_dict.project;
  if(project){const original=project.df.onchange;project.df.onchange=async function(){await original?.call(this);await load(true);};}
  load(!!read(layout,'project'));
 };
 const removable=new Set(['Employee','Customer','Contract','Project','PP Site','PP Assignment','PP Event Plan','PP Contract Terms','PP Work Entry','PP Daily Register','PP Milestone','PP Vehicle Booking','PP Equipment Booking','Vehicle','Item','Warehouse','Sales Invoice','Payment Entry','Purchase Invoice','Expense Claim','PP Worker Loan']);
 plus_point.delete_records=async(doctype,names,after)=>{
  if(!names.length){frappe.msgprint(__('Select records using the checkboxes first.'));return;}
  let review;try{review=await plus_point.form_rpc('record_actions.review_many',{doctype,names});}catch(error){frappe.msgprint(esc(error.message));return;}
  const eligible=review.records.filter(r=>!r.blocked).map(r=>r.name),blocked=!eligible.length;
  const dialog=new frappe.ui.Dialog({title:__(names.length===1?'Delete record':'Delete selected records'),fields:[
   {fieldtype:'HTML',fieldname:'summary',options:`<p>${esc(__('Review these records before deleting. Existing links and permissions are checked again. Approved work and posted financial history are protected.'))}</p>${review.records[0].message?`<p>${esc(__(review.records[0].message))}</p>`:''}<ul>${review.records.map(r=>`<li><strong>${esc(r.title||r.name)}</strong>${r.blocked?`<p>${esc(r.blocked)}</p>`:''}${r.dependency&&frappe.boot.plus_point?.navigation?.doctypes?.includes(r.dependency.doctype)?` <a href="/desk/${frappe.router.slug(r.dependency.doctype)}/${encodeURIComponent(r.dependency.name)}" data-delete-dependency>${esc(__('Open blocking record'))}: ${esc(r.dependency.title)}</a>`:''}</li>`).join('')}</ul>`},
   {fieldtype:'HTML',fieldname:'delete_error',label:' '}],secondary_action_label:__('Cancel'),secondary_action(){dialog.hide();},primary_action_label:blocked?__('Cannot delete linked records'):eligible.length===names.length?__('Delete'):__('Delete {0} available',[eligible.length]),async primary_action(){
    dialog.disable_primary_action();try{await plus_point.form_rpc('record_actions.remove_many',{doctype,names:eligible});dialog.hide();document.dispatchEvent(new Event('pp:data-changed'));await after?.();}catch(error){dialog.fields_dict.delete_error.$wrapper.empty().append($('<p class="text-danger" role="alert"></p>').text(error.message));}finally{if(!blocked)dialog.enable_primary_action();}
   }});
  dialog.show();dialog.$wrapper.addClass('pp-delete-dialog');dialog.$wrapper.find('[data-delete-dependency]').on('click',()=>dialog.hide());dialog.$wrapper.one('hidden.bs.modal',()=>dialog.$wrapper.remove());if(blocked)dialog.disable_primary_action();
 };
 plus_point.add_record_delete=(holder,doctype,name,after)=>{if(!holder||!name||holder.querySelector('[data-delete-record]')||!frappe.model.can_delete(doctype))return;const b=document.createElement('button');b.type='button';b.className='btn btn-default';b.dataset.deleteRecord='true';b.textContent=__('Delete');b.onclick=()=>plus_point.delete_records(doctype,[name],after);holder.append(b);};
 plus_point.enhance_record_list=list=>{
  if(!list?.page?.wrapper||frappe.boot.plus_point?.is_platform||!removable.has(list.doctype)||!frappe.model.can_delete(list.doctype)||$(list.page.wrapper).find('.pp-delete-selected').length)return;
  list.page.add_inner_button(__('Delete selected'),()=>plus_point.delete_records(list.doctype,list.get_checked_items().map(r=>r.name),()=>list.refresh())).addClass('pp-delete-selected');
 };
 $(document).on('form-refresh.pp-forms',(_event,frm)=>{
  plus_point.enhance_inputs(frm);
  if(frappe.boot.plus_point?.is_platform)return;
  if(frm.is_new()&&removable.has(frm.doctype))plus_point.bind_saved_context(frm);
  if(removable.has(frm.doctype)&&!frm.is_new()&&frappe.model.can_delete(frm.doctype))frm.add_custom_button(__('Delete'),()=>plus_point.delete_records(frm.doctype,[frm.doc.name],()=>frappe.set_route('List',frm.doctype)));
 });
 for(const dt of removable)frappe.ui.form.on(dt,{validate(frm){if(!plus_point.validate_inputs(frm))frappe.validated=false;}});
})();
