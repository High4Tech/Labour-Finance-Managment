/* Searchable record pickers. Keep native validation, permissions and keyboard selection. */
(()=>{
 frappe.provide('plus_point');
 plus_point.form_rpc=async(method,args={},options={})=>{
  const response=await fetch('/api/method/plus_point.'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':frappe.csrf_token},body:JSON.stringify(args),signal:options.signal}),data=await response.json();
  if(!response.ok||data.exc_type){let message=__('Could not load or save. Please try again.');try{message=JSON.parse(data._server_messages).map(v=>JSON.parse(v).message).join(' ');}catch{}const error=new Error(message.replace(/<[^>]*>/g,''));error.field_errors=data.field_errors||{};throw error;}return data.message;
 };
 plus_point.bind_country_currency=async form=>{let seq=0;const suggest=async()=>{const own=++seq,before=form.get_value('default_currency');try{const data=await plus_point.setup_rpc('plus_point.locations.country_defaults',{country:form.get_value('country')});if(own===seq&&form.get_value('default_currency')===before)await form.set_value('default_currency',data.currency);}catch{form.set_df_property('default_currency','description',__('Choose the currency you bill this client in.'));}};form.fields_dict.country.df.onchange=suggest;if(!form.get_value('default_currency'))await suggest();};
 plus_point.enhance_selectors=layout=>{
  plus_point.enhance_inputs?.(layout);plus_point.bind_category_choice?.(layout);plus_point.enhance_choices?.(layout);
  for(const c of Object.values(layout.fields_dict||{}))plus_point.ui?.field(c);
  for(const c of Object.values(layout.fields_dict||{}))if(c.df.fieldtype==='Select'&&c.$input&&!c.ppChoices&&!c.ppSelectBound){c.ppSelectBound=true;c.$input.get(0).ppControl=c;const native=c.set_input.bind(c);c.set_input=(...args)=>{const result=native(...args);queueMicrotask(()=>{plus_point.ui?.selects(c.$wrapper.get(0));plus_point.ui?.sync_select(c.$input?.get(0));});return result;};const refresh=c.refresh.bind(c);c.refresh=(...args)=>{const result=refresh(...args);plus_point.ui?.sync_select(c.$input?.get(0));return result;};c.set_focus=()=>{const input=c.$input?.get(0);(input?.ppSelect?.button||input)?.focus();};plus_point.ui?.selects(c.$wrapper.get(0));}
  for(const control of Object.values(layout.fields_dict||{})){
   if(control.df.label)control.$input?.attr('aria-label',control.df.label);
   if(!['Link','Dynamic Link'].includes(control.df.fieldtype)||!control.$input||control.pp_picker)continue;
   const input=control.$input,awesomplete=control.awesomplete;let sequence=0;if(!awesomplete)continue;
   const originalOnlySelect=!!control.df.only_select;control.pp_picker=true;control.df.only_select=1;control.$wrapper.addClass('pp-search-picker');
   awesomplete.maxItems=Number.MAX_SAFE_INTEGER;awesomplete.minChars=0;awesomplete.sort=()=>0;awesomplete.filter=()=>true;
   input.attr({autocomplete:'off',placeholder:__('Choose or search…'),'aria-autocomplete':'list'});
   control.$link?.hide();
   // Native FieldGroup binds Enter-to-submit on the input. A selection must consume
   // that keypress while leaving Enter on a closed picker available to the form.
   let selectingWithEnter=false;
   input.get(0).addEventListener('keydown',event=>{if(event.key==='Enter')selectingWithEnter=awesomplete.opened;},true);
   input.get(0).addEventListener('keypress',event=>{if(event.key==='Enter'&&selectingWithEnter){event.preventDefault();event.stopImmediatePropagation();}},true);
   input.get(0).addEventListener('keyup',event=>{if(event.key==='Enter')selectingWithEnter=false;},true);

   const status=$('<span class="pp-picker-status" role="status"></span>').appendTo(control.$wrapper);
   const picker=control.$input_area.find('.awesomplete').first(),tools=$('<div class="pp-picker-tools"></div>').appendTo(picker),more=$('<button type="button" class="btn btn-default btn-sm pp-picker-more" hidden>'+__('Load more results')+'</button>').appendTo(tools);
   const toggle=$('<button type="button" class="pp-picker-toggle" tabindex="-1"><img src="/assets/plus_point/images/figma/chevron-down.svg" alt="" aria-hidden="true"></button>').attr('aria-label',__('Choose {0}',[__(control.df.label||control.df.options)])).appendTo(control.$input_area.find('.link-field'));
   let controller,found=new Map(),cursor=0,currentTerm='',hasMore=false,skipFocus=false;
   const sizeTools=()=>{const active=tools.find('button:not([hidden])').length>0;control.$wrapper.toggleClass('pp-picker-has-tools',active);if(active)picker.get(0).style.setProperty('--pp-picker-tools-height',tools.get(0).offsetHeight+'px');};
   const search=async(term,append=false)=>{
    if(control.df.read_only||control.df.hidden)return;controller?.abort();controller=new AbortController();const own=++sequence,args=control.get_search_args(term);if(!args)return;
    if(!append){found=new Map();cursor=0;currentTerm=term;}status.text(__('Loading choices…'));more.prop('disabled',true);
    try{
     const {page_length,...searchArgs}=args,result=await plus_point.form_rpc('choices.page',{...searchArgs,start:cursor},{signal:controller.signal});
     if(own!==sequence||!input.is(':focus'))return;
     for(const row of result.rows)found.set(row.value,row);hasMore=!!result.more;cursor=result.next_start;
     const rows=control.merge_duplicates([...found.values()]).sort((a,b)=>String(a.label||a.value).localeCompare(String(b.label||b.value),undefined,{sensitivity:'base',numeric:true})||String(a.value).localeCompare(String(b.value)));
     rows.forEach(row=>frappe.utils.add_link_title(control.get_options(),row.value,row.label||row.value));awesomplete.list=rows;awesomplete.evaluate();if(rows.length)awesomplete.open();
     more.prop('hidden',!hasMore);sizeTools();status.text(rows.length?__('{0} choices shown',[rows.length])+(hasMore?' · '+__('Search to narrow results, or load more.'):''):__('No matches. Try another search.'));
    }catch(error){if(error.name!=='AbortError'&&own===sequence)status.text(__('Search could not load. Try again.'));}finally{if(own===sequence)more.prop('disabled',false);}
   };
   control.ppDisposePicker=()=>{sequence++;controller?.abort();control._debounced_input_handler?.cancel();};
   control.on_input=()=>search(input.val());input.off('input',control._debounced_input_handler);control._debounced_input_handler?.cancel();
   control._debounced_input_handler=frappe.utils.debounce(()=>search(input.val()),180);
   input.on('input.pp-picker',()=>{sequence++;controller?.abort();awesomplete.close();control._debounced_input_handler();});
   input.on('focus.pp-picker',()=>{if(control.df.read_only)return;control.$wrapper.addClass('pp-picker-open');sizeTools();if(skipFocus){skipFocus=false;return;}input.get(0).select();search('');});
   input.on('blur.pp-picker',()=>{sequence++;controller?.abort();control._debounced_input_handler?.cancel();status.text('');requestAnimationFrame(()=>{if(!tools.get(0).contains(document.activeElement)){control.$wrapper.removeClass('pp-picker-open');more.prop('hidden',true);}});});
   toggle.on('mousedown',event=>event.preventDefault()).on('click',()=>{if(input.is(':focus')){if(awesomplete.opened)awesomplete.close();else search(input.val());}else input.trigger('focus');});
   more.on('mousedown',event=>event.preventDefault()).on('click',()=>{if(!input.is(':focus')){skipFocus=true;input.get(0).focus();}search(currentTerm,true);});
   const creatable={Customer:['clients','Client'],Item:['inventory_items','Inventory item'],Warehouse:['warehouses','Warehouse'],Vehicle:['vehicles','Vehicle']},creation=creatable[control.df.options];
   if(creation&&(!originalOnlySelect||control.df.pp_allow_create)&&(control.df.options!=='Item'||control.get_search_args('').filters?.is_stock_item===1)&&frappe.model.can_create(control.df.options)&&typeof plus_point.open_resource==='function'){
    const add=$('<button type="button" class="btn btn-link pp-picker-create"></button>').text(__('+ Add new {0}',[__(creation[1]).toLowerCase()])).prependTo(tools);
    add.on('mousedown',event=>event.preventDefault()).on('click',async()=>{const before=control.get_value();await plus_point.open_resource(creation[0],async saved=>{const value=saved.name||saved.customer||saved.item;if(value){await control.set_value(value);input.trigger('focus');}});const dialog=window.cur_dialog;dialog?.$wrapper.one('hidden.bs.modal',()=>{if(!control.get_value()&&before)control.set_value(before);});});
   }

  }
 };
 $(document).on('form-refresh.pp-pickers',(_event,frm)=>plus_point.enhance_selectors(frm));
 $(document).on('frappe.ui.Dialog:shown.pp-pickers',()=>{if(window.cur_dialog)plus_point.enhance_selectors(cur_dialog);});
 $(document).on('grid-row-render.pp-pickers',(_event,row)=>{plus_point.enhance_selectors({fields_dict:row.on_grid_fields_dict||{}});if(row.grid_form)plus_point.enhance_selectors(row.grid_form);});
})();
