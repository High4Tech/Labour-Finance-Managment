/* One confirmation and pay editor for event and worker entry points. */
(()=>{
 frappe.provide('plus_point');
 plus_point.confirm_pay_warning=(warning,label='Continue with these costs')=>new Promise(resolve=>{
  const d=frappe.confirm(frappe.utils.escape_html(warning),()=>resolve(true),()=>resolve(false));
  d.set_primary_action(__(label),()=>{resolve(true);d.hide();});
  d.$wrapper.one('hidden.bs.modal',()=>resolve(false));
 });
 plus_point.with_pay_confirmation=async run=>{
  try{return await run(0);}catch(error){
   if(!String(error.message).includes('Confirm to continue'))throw error;
   if(!await plus_point.confirm_pay_warning(error.message))throw Error(__('No changes saved.'));
   return run(1);
  }
 };
 plus_point.edit_event_pay=(assignment,done,options={})=>{
  const rate=Number(options.rate)||1,currency=options.currency||frappe.boot.plus_point.company_identity?.default_currency||frappe.boot.sysdefaults.currency;
  const d=new frappe.ui.Dialog({title:__('Event pay — {0}',[assignment.worker]),fields:[
   {fieldtype:'Select',fieldname:'basis',label:__('Pay basis for this event'),options:'Daily\nMonthly',default:assignment.pp_pay_basis||'Daily',reqd:1},
   {fieldtype:'Currency',fieldname:'amount',label:__('Pay amount ({0})',[currency]),default:(assignment.pp_pay_amount||assignment.wage_rate)/rate,reqd:1,positive:true,description:__('Monthly pay ÷ 30 is earned per full attended day. Recorded attendance locks existing rates; create a new dated assignment to change them.')},
   {fieldtype:'HTML',fieldname:'comparison',options:'<p>'+frappe.utils.escape_html(assignment.client_rate?__('Client rate: {0} {1} per worker-day.',[assignment.client_rate/rate,currency]):__('Client revenue uses the fixed agreement price.'))+'</p>'}
  ],primary_action_label:__('Save event pay'),primary_action:async v=>{if(!plus_point.validate_inputs(d))return;d.disable_primary_action();try{await plus_point.with_pay_confirmation(confirm_over_budget=>plus_point.form_rpc('planning.save_pay',{assignment:assignment.name,...v,amount:Number(v.amount)*rate,confirm_over_budget}));d.hide();await done();}catch(error){frappe.msgprint(frappe.utils.escape_html(error.message));}finally{d.enable_primary_action();}}});
  d.show();plus_point.enhance_selectors(d);for(const control of Object.values(d.fields_dict))control.$input?.attr('aria-label',control.df.label||'');
 };
})();
