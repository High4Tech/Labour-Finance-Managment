/* Small, finite choices are visible. Native controls remain the source of values. */
(()=>{
 frappe.provide('plus_point');let sequence=0;
 plus_point.action_class=(label,kind='btn-default')=>kind+(/\b(?:remove|delete|cancel reservation|unassign|revoke|discard)\b/i.test(label)?' pp-destructive':/\bdraft\b/i.test(label)?' pp-draft-action':'');
 plus_point.phase_values=value=>String(value||'Event').split(',').map(v=>v.trim()).filter(Boolean);
 plus_point.enhance_choices=layout=>{
  if(frappe.boot?.plus_point?.is_platform)return;
  for(const c of Object.values(layout.fields_dict||{})){
   const df=c.df;if(c.ppChoices||df.read_only||!c.$input||!c.$wrapper)continue;
   const multi=df.fieldname==='phase',budget=df.fieldname==='enforce_budget',finite=['billing_model','pp_salary_basis','pp_pay_basis','pay_basis','frequency','status','basis','leave_kind','leave_type','purpose','warehouse_type','customer_type','billing_period','action','validity_mode','event_path','commercial_status','method'].includes(df.fieldname);
   let options=multi?['Setup','Event','Pack-down','Other']:budget?[{value:'0',label:__('Warn before spending above budget')},{value:'1',label:__('Block spending above budget')}]:finite&&df.fieldtype==='Select'?(Array.isArray(df.options)?df.options:String(df.options||'').split('\n')).filter(Boolean):[];
   if(options.length<2||options.length>4)continue;
   if(multi&&df.fieldtype==='Select'){df.options=Array.from({length:15},(_,n)=>options.filter((_,i)=>(n+1)&(1<<i)).join(', '));c.refresh();}options=options.map(v=>typeof v==='object'?v:{value:v,label:__(v)});const fieldset=document.createElement('fieldset');fieldset.className='pp-choice-field';fieldset.dataset.required=String(!!df.reqd);const legend=document.createElement('legend');legend.textContent=budget?__('Budget limit'):df.label;fieldset.setAttribute('aria-label',legend.textContent);fieldset.append(legend);const name='pp-choice-'+(++sequence);
   c.ppChoices=fieldset;c.$wrapper.addClass('pp-choice-control');c.$input.prop('hidden',true).attr({'aria-hidden':'true',tabindex:'-1'}).addClass('pp-choice-native');c.$wrapper.find('.control-label').hide();c.$input.closest('label').hide();c.$wrapper.find('.control-input-wrapper').hide();c.$wrapper.find('.select-icon').hide();c.$wrapper.append(fieldset);
   options.forEach(option=>{const label=document.createElement('label'),input=document.createElement('input'),text=document.createElement('span');input.type=multi?'checkbox':'radio';input.name=name;input.value=String(option.value);text.textContent=option.label;label.append(input,text);fieldset.append(label);input.onchange=async()=>{const checked=[...fieldset.querySelectorAll('input:checked')];if(multi&&!checked.length){input.checked=true;return;}await c.set_value(multi?checked.map(i=>i.value).join(', '):budget?Number(input.value):input.value);fieldset.dispatchEvent(new Event('pp:flow-change',{bubbles:true}));};});
   const sync=()=>{const value=c.get_value(),selected=multi?plus_point.phase_values(value):[budget?String(Number(value)||0):String(value??'')];for(const input of fieldset.querySelectorAll('input'))input.checked=selected.includes(input.value);};const original=c.set_input.bind(c);c.set_input=(...args)=>{const result=original(...args);queueMicrotask(sync);return result;};c.set_focus=()=>fieldset.querySelector('input:checked,input')?.focus();c.ppChoiceInputs=$(fieldset).find('input');sync();
  }
 };
})();
