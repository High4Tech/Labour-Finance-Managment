/* Payment dates follow the agreement, not a second calendar. */
(()=>{
 frappe.provide('plus_point');
 const esc=v=>frappe.utils.escape_html(String(v??'')),rpc=(method,args)=>plus_point.form_rpc('daily_billing.'+method,args);
 plus_point.daily_checkpoints_editor=(root,{rows=[],dates,currency,agreement,readonly=false})=>{
  rows=rows.map(r=>({...r}));const original=JSON.stringify(rows);let overview=[];
  const changed=()=>root.dispatchEvent(new Event('pp:flow-change',{bubbles:true}));
  function draw(){
   const schedule=rows.find(r=>r.schedule_id);root.dataset.cardSummary=schedule?__('{0} payments · due {1} days after each period.',[__(schedule.frequency),schedule.payment_days||0]):__('Payment periods follow the agreement dates automatically.');
   root.innerHTML='<div class="pp-section-heading"><h3>'+esc(__('Payment schedule'))+'</h3>'+(!readonly?'<button type="button" class="btn btn-default" data-set-payments>'+esc(__(rows.length?'Change payment schedule':'Set payment schedule'))+'</button>':'')+'</div><p>'+esc(schedule?__('{0} payments. Invoice drafts are created after each period ends, using approved attendance only. Payment is due {1} days later.',[__(schedule.frequency),schedule.payment_days||0]):__('Select a payment frequency. Dates follow the agreement automatically.'))+'</p>'+plus_point.render_table(['Payment','Attendance period','Payment due','Approved to invoice','Status','Actions'],rows.map(r=>{const live=overview.find(x=>x.id===r.id);return '<tr><th scope="row">'+esc(r.title)+'</th><td>'+esc(r.from_date)+' – '+esc(r.to_date)+'</td><td>'+esc(r.due_date)+'</td><td>'+esc(new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(live?.amount||0))+' '+esc(currency())+'</td><td>'+esc(r.invoice?__('Invoice created'):live?.status||__('Scheduled'))+'</td><td><div class="pp-actions">'+[r.invoice,...(r.supplemental_invoices||[])].filter(Boolean).map(name=>'<a class="btn btn-default" href="/desk/pp-client-billing?record='+encodeURIComponent(agreement)+'&invoice='+encodeURIComponent(name)+'">'+esc(__('Review invoice'))+'</a>').join('')+(!r.invoice&&live?.status==='Ready to invoice'&&JSON.stringify(rows)===original?'<button type="button" class="btn btn-default" data-invoice-period="'+esc(r.id)+'">'+esc(__('Create invoice draft now'))+'</button>':'')+'</div></td></tr>';}))+'<p class="pp-checkpoint-feedback" role="status" aria-live="polite"></p>';
   root.querySelector('[data-set-payments]')?.addEventListener('click',edit);root.dispatchEvent(new Event('pp:component-render'));
   root.querySelectorAll('[data-invoice-period]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{const result=await rpc('invoice',{agreement,checkpoint:b.dataset.invoicePeriod});frappe.set_route('pp-client-billing',{record:agreement,invoice:result.name});}catch(error){root.querySelector('.pp-checkpoint-feedback').textContent=error.message;}finally{b.disabled=false;}});
  }
  function edit(){
   const current=rows.find(r=>r.schedule_id)||{},span=dates();
   const d=new frappe.ui.Dialog({title:__('Payment schedule'),fields:[
    {fieldtype:'Select',fieldname:'frequency',label:__('Payment frequency'),options:[{value:'Daily',label:__('Daily payment')},{value:'Weekly',label:__('Weekly payment')},{value:'Biweekly',label:__('Every two weeks')},{value:'Monthly',label:__('Monthly payment')},{value:'Quarterly',label:__('Quarterly payment')}],default:current.frequency||'Weekly',reqd:1},
    {fieldtype:'Int',fieldname:'payment_days',label:__('Payment due after period ends (days)'),default:current.payment_days||0,description:__('0 means due at the end of each period. Use up to 90 days.')},
    {fieldtype:'HTML',fieldname:'preview',options:'<p class="pp-payment-preview" role="status" aria-live="polite"></p>'}
   ],primary_action_label:__('Save payment schedule'),primary_action:async v=>{
    if(!plus_point.validate_inputs(d))return;d.disable_primary_action();
    try{const generated=await rpc('periods',{...v,start:span.start,end:span.end,schedule_id:current.schedule_id});const locked=rows.filter(r=>r.invoice);for(const row of locked){const match=generated.find(r=>r.id===row.id);if(!match||['from_date','to_date','due_date','frequency'].some(k=>match[k]!==row[k]))throw Error(__('Invoiced periods are protected. Keep the current frequency and payment terms.'));}rows=generated.map(r=>rows.find(old=>old.id===r.id&&old.invoice)||r);d.hide();draw();changed();}
    catch(error){d.fields_dict.preview.$wrapper.find('p').text(error.message);}finally{d.enable_primary_action();}
   }});
   let request=0;const preview=async()=>{const token=++request;try{const generated=await rpc('periods',{start:span.start,end:span.end,frequency:d.get_value('frequency'),payment_days:d.get_value('payment_days')||0,schedule_id:current.schedule_id});if(token!==request)return;d.fields_dict.preview.$wrapper.find('p').text(__('{0} payments from {1} to {2}. The last period adjusts to the agreement end date.',[generated.length,span.start,span.end]));}catch(error){if(token===request)d.fields_dict.preview.$wrapper.find('p').text(error.message);}};
   for(const name of ['frequency','payment_days'])d.fields_dict[name].df.onchange=preview;
   d.$wrapper.one('hidden.bs.modal',()=>d.$wrapper.remove());d.show();plus_point.enhance_selectors(d);for(const c of Object.values(d.fields_dict))c.$input?.attr('aria-label',c.df.label||'');preview();
  }
  draw();if(agreement)rpc('overview',{agreement}).then(result=>{if(!root.isConnected)return;overview=result;draw();}).catch(error=>{if(root.isConnected)root.querySelector('.pp-checkpoint-feedback').textContent=error.message;});
  return {get_value:()=>rows.map(r=>({...r})),edit};
 };
})();
