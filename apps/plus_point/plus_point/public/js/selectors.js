/* Searchable record pickers. Keep native validation, permissions and keyboard selection. */
(()=>{
 frappe.provide('plus_point');
 plus_point.enhance_selectors=layout=>{
  for(const control of Object.values(layout.fields_dict||{})){
   if(control.df.fieldtype!=='Link'||!control.$input||control.pp_picker)continue;
   control.pp_picker=true;control.df.only_select=1;control.$wrapper.addClass('pp-search-picker');
   const input=control.$input,awesomplete=control.awesomplete;let sequence=0;
   input.attr({autocomplete:'off',placeholder:__('Choose or search…'),'aria-autocomplete':'list'});
   control.$link?.hide();
   const status=$('<span class="pp-picker-status" role="status"></span>').appendTo(control.$wrapper);
   const button=$('<button type="button" class="pp-picker-toggle" tabindex="-1"><span aria-hidden="true">⌄</span></button>')
    .attr('aria-label',__('Choose {0}',[__(control.df.label||control.df.options)])).appendTo(control.$input_area.find('.link-field'));
   const search=async term=>{
    if(control.df.read_only||control.df.hidden)return;const own=++sequence,args=control.get_search_args(term);if(!args)return;
    status.text(__('Searching…'));
    try{
     const result=await frappe.call({method:'frappe.desk.search.search_link',type:'POST',no_spinner:true,args:{...args,page_length:30}});
     if(own!==sequence||!input.is(':focus'))return;
     const rows=control.merge_duplicates(result.message||[]);
     rows.forEach(row=>frappe.utils.add_link_title(control.get_options(),row.value,row.label||row.value));
     awesomplete.list=rows;awesomplete.evaluate();if(rows.length)awesomplete.open();
     status.text(rows.length?'':__('No matches. Try another search.'));
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
})();
