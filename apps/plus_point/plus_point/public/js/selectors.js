/* Searchable record pickers. Keep native validation, permissions and keyboard selection. */
(()=>{
 frappe.provide('plus_point');
 plus_point.form_rpc=async(method,args={})=>{
  const response=await fetch('/api/method/plus_point.'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':frappe.csrf_token},body:JSON.stringify(args)}),data=await response.json();
  if(!response.ok||data.exc_type){let message=__('Could not load or save. Please try again.');try{message=JSON.parse(data._server_messages).map(v=>JSON.parse(v).message).join(' ');}catch{}throw new Error(message.replace(/<[^>]*>/g,''));}return data.message;
 };
 plus_point.bind_country_currency=async form=>{let seq=0;const suggest=async()=>{const own=++seq,before=form.get_value('default_currency');try{const data=await plus_point.setup_rpc('plus_point.locations.country_defaults',{country:form.get_value('country')});if(own===seq&&form.get_value('default_currency')===before)await form.set_value('default_currency',data.currency);}catch{form.set_df_property('default_currency','description',__('Choose the currency you bill this client in.'));}};form.fields_dict.country.df.onchange=suggest;if(!form.get_value('default_currency'))await suggest();};
 plus_point.enhance_selectors=layout=>{
  plus_point.enhance_inputs?.(layout);
  for(const control of Object.values(layout.fields_dict||{})){
   if(!['Link','Dynamic Link'].includes(control.df.fieldtype)||!control.$input||control.pp_picker)continue;
   const input=control.$input,awesomplete=control.awesomplete;let sequence=0;if(!awesomplete)continue;
   control.pp_picker=true;control.df.only_select=1;control.$wrapper.addClass('pp-search-picker');
   awesomplete.maxItems=Number.MAX_SAFE_INTEGER;awesomplete.minChars=0;awesomplete.sort=()=>0;awesomplete.filter=()=>true;
   input.attr({autocomplete:'off',placeholder:__('Choose or search…'),'aria-autocomplete':'list'});
   control.$link?.hide();
   const status=$('<span class="pp-picker-status" role="status"></span>').appendTo(control.$wrapper);
   const button=$('<button type="button" class="pp-picker-toggle" tabindex="-1">'+plus_point.icon('down')+'</button>')
    .attr('aria-label',__('Choose {0}',[__(control.df.label||control.df.options)])).appendTo(control.$input_area.find('.link-field'));
   const search=async term=>{
    if(control.df.read_only||control.df.hidden)return;const own=++sequence,args=control.get_search_args(term);if(!args)return;
    status.text(__('Loading all choices…'));awesomplete.close();
    try{
     const found=new Map();let start=0;
     while(true){
      const {page_length,...searchArgs}=args,result=await plus_point.form_rpc('choices.page',{...searchArgs,start});
      if(own!==sequence||!input.is(':focus'))return;
      let added=0;for(const row of result.rows){if(!found.has(row.value)){found.set(row.value,row);added++;}}
      if(!result.more)break;
      if(!added||result.next_start<=start)throw new Error('This lookup did not advance.');
      start=result.next_start;status.text(__('Loading all choices… {0} loaded',[found.size]));
     }
     const rows=control.merge_duplicates([...found.values()]).sort((a,b)=>String(a.label||a.value).localeCompare(String(b.label||b.value),undefined,{sensitivity:'base',numeric:true})||String(a.value).localeCompare(String(b.value)));
     rows.forEach(row=>frappe.utils.add_link_title(control.get_options(),row.value,row.label||row.value));
     awesomplete.list=rows;awesomplete.evaluate();if(rows.length)awesomplete.open();
     status.text(rows.length?__('All {0} choices · A–Z',[rows.length]):__('No matches. Try another search.'));
    }catch{if(own===sequence)status.text(__('Search could not load. Try again.'));}
   };
   // Replace the native half-second search; keep native selection/blur validation.
   control.on_input=()=>search(input.val());
   input.off('input',control._debounced_input_handler);control._debounced_input_handler?.cancel();
   control._debounced_input_handler=frappe.utils.debounce(()=>search(input.val()),180);
   input.on('input',()=>{sequence++;awesomplete.close();control._debounced_input_handler();});
   input.on('focus.pp-picker',()=>{if(control.df.read_only)return;input.get(0).select();search('');});
   input.on('blur.pp-picker',()=>{sequence++;status.text('');});
   button.on('mousedown',event=>event.preventDefault()).on('click',()=>{input.trigger('focus');search('');});
  }
 };
 $(document).on('form-refresh.pp-pickers',(_event,frm)=>plus_point.enhance_selectors(frm));
 $(document).on('frappe.ui.Dialog:shown.pp-pickers',()=>{if(window.cur_dialog)plus_point.enhance_selectors(cur_dialog);});
 $(document).on('grid-row-render.pp-pickers',(_event,row)=>{plus_point.enhance_selectors({fields_dict:row.on_grid_fields_dict||{}});if(row.grid_form)plus_point.enhance_selectors(row.grid_form);});
})();
