/* One native list per planning workflow, including its unfinished drafts. */
(()=>{
 frappe.provide('plus_point');
 const types={'PP Contract Terms':'Agreement','PP Event Plan':'Event'},route=doctype=>doctype==='PP Contract Terms'?'pp-agreements':'pp-event-plans';
 const link=(doctype,doc)=>'/desk/'+route(doctype)+(doc.pp_draft_name?'?draft='+encodeURIComponent(doc.pp_draft_name):'?record='+encodeURIComponent(doc.name)+(doc.planning_state==='Draft'?'&edit=1':''));
 function attach(list){
  if(list.__pp_combined||frappe.boot.plus_point?.is_platform)return;
  list.__pp_combined=true;list.method='plus_point.planning_list.rows';
  list.page.wrapper.addClass('pp-planning-list');
  const prepare=list.prepare_data.bind(list),args=list.get_args.bind(list);
  list.prepare_data=response=>{const data=response.message||{};list.ppPlanningTotal=data.total||0;return prepare({...response,message:data.rows||[]});};
  list.get_args=()=>{const value=args(),status=value.filters.find(row=>row[1]==='pp_planning_status')?.[3];return {...value,filters:value.filters.filter(row=>row[1]!=='pp_planning_status'),planning_status:list.ppPlanningStatus||status||''};};
  list.get_count_str=async()=>{list.total_count=list.ppPlanningTotal||0;return __('{0} of {1}',[format_number(list.data.length,null,0),format_number(list.total_count,null,0)]);};
  list.settings.get_form_link=doc=>link(list.doctype,doc);
  const statusColumn=()=>{list.columns=list.columns.filter(column=>!['status','planning_state'].includes(column.df?.fieldname));if(!list.columns.some(column=>column.type==='Status'))list.columns.splice(1,0,{type:'Status'});};
  const columns=list.setup_columns.bind(list);list.setup_columns=async(...args)=>{await columns(...args);statusColumn();};statusColumn();
  const menu=list.get_actions_menu_items.bind(list);list.get_actions_menu_items=()=>menu().map(item=>({...item,action:()=>{const selected=list.get_checked_items();if(item.label===__('Delete',null,'Button in list view actions menu'))return plus_point.delete_records(list.doctype,selected.map(row=>row.name),()=>{list.clear_checked_items();list.last_args=null;return list.refresh();});if(selected.some(row=>row.pp_draft_name)){frappe.msgprint(__('Open the draft to edit it, or use Delete selected to discard it. Create it before using actions for completed records.'));return;}return item.action();}}));
  list.page.actions.empty();list.set_actions_menu_items();
  const accessible=()=>{const root=list.page.wrapper.get(0);if(!root.getClientRects().length)return;const byName=new Map(list.data.map(row=>[row.name,row]));root.querySelectorAll('.list-row-checkbox').forEach(input=>{const doc=byName.get(input.dataset.name);input.setAttribute('aria-label',__('Select {0}',[doc?.agreement_title||doc?.event_name||input.dataset.name]));});root.querySelectorAll('button[data-original-title="Reload List"]').forEach(button=>button.setAttribute('aria-label',__('Reload list')));root.querySelectorAll('.match-type-dropdown-btn').forEach(button=>button.setAttribute('aria-label',__('Choose match type for {0}',[button.closest('.input-group').querySelector('input')?.placeholder||__('filter')])));};
  const nameMobile=()=>{const root=list.page.wrapper.get(0);root.querySelectorAll('button[data-label]').forEach(button=>{if(button.dataset.label)button.setAttribute('aria-label',decodeURIComponent(button.dataset.label));});root.querySelectorAll('.sidebar-toggle-btn').forEach(button=>button.setAttribute('aria-label',__('Toggle navigation')));root.querySelectorAll('.filter-toggle').forEach(button=>button.setAttribute('aria-label',__('Show filters')));root.querySelectorAll('.filter-button').forEach(button=>button.setAttribute('aria-label',(button.textContent.trim()||__('Filter'))+' '+__('records')));root.querySelectorAll('.sort-selector-button').forEach(button=>button.setAttribute('aria-label',__('Sort by {0}',[button.textContent.trim()||__('field')])));};
  const rendered=list.after_render.bind(list);list.after_render=(...args)=>{const result=rendered(...args);accessible();nameMobile();return result;};
  plus_point.watch_ui('planning-list-'+list.doctype,()=>{if(list.page.wrapper.get(0).getClientRects().length){accessible();nameMobile();}});
  const invalidate=()=>{list.last_args=null;const current=frappe.get_route();if(current[0]==='List'&&current[1]===list.doctype)list.refresh();};
  document.addEventListener('pp:planning-draft-saved',invalidate);document.addEventListener('pp:data-changed',invalidate);
  const filter=list.page.add_field({fieldtype:'Select',fieldname:'pp_planning_status',label:__('Record status'),options:[{label:__('All records'),value:''},{label:__('Draft'),value:'Draft'},{label:__('Created'),value:'Created'}],default:'',change:()=>{list.ppPlanningStatus=filter.get_value();list.start=0;list.last_args=null;list.refresh();}});
  filter.$input.attr('aria-label',__('Record status'));
  const choices=document.createElement('fieldset');choices.className='pp-record-filter-choices';choices.innerHTML='<legend>'+frappe.utils.escape_html(__('Record status'))+'</legend>'+[['','All records'],['Draft','Draft'],['Created','Created']].map(([value,label])=>'<label><input type="radio" name="record-status-'+list.doctype.replaceAll(' ','-')+'" value="'+value+'" '+(!value?'checked':'')+'>'+frappe.utils.escape_html(__(label))+'</label>').join('');filter.$wrapper.get(0).append(choices);filter.$wrapper.addClass('pp-record-filter-host');choices.onchange=event=>filter.set_value(event.target.value);plus_point.ui.nativeFilters(list.page.wrapper.get(0));
  accessible();
  list.$result.on('click.pp-draft-source','.list-row-container a[data-name]',event=>{const doc=list.data.find(row=>row.name===event.currentTarget.dataset.name);if(!doc?.pp_draft_name)return;event.preventDefault();event.stopImmediatePropagation();frappe.set_route(route(list.doctype),{draft:doc.pp_draft_name});});
 }
 for(const doctype of Object.keys(types)){
  const previous=frappe.listview_settings[doctype]||{},indicator=previous.get_indicator;
  frappe.listview_settings[doctype]={...previous,add_fields:[...new Set([...(previous.add_fields||[]),'pp_reference',...(doctype==='PP Event Plan'?['start_date','end_date','pp_archived','planning_state']:['status'])])],get_form_link:doc=>link(doctype,doc),onload:list=>{previous.onload?.(list);attach(list);},get_indicator:doc=>{
   if(doc.pp_draft_name||doc.planning_state==='Draft')return [__('Draft'),doc.pp_draft_status==='Failed'?'red':'grey',''];
   if(indicator&&doctype!=='PP Event Plan')return indicator(doc);
   const status=doctype==='PP Contract Terms'?doc.status:doc.pp_project_status==='Cancelled'?'Cancelled':doc.pp_archived||doc.pp_record_archived?'Archived':frappe.datetime.get_today()<doc.start_date?'Upcoming':frappe.datetime.get_today()>doc.end_date?'Completed':'Active';
   return [__(status),status==='Active'?'green':status==='Upcoming'?'blue':'grey',''];
  }};
 }
 plus_point.planning_list={attach,link};
 // Old bookmarked Drafts routes remain useful, but no longer form a separate screen.
 frappe.router.on('change',()=>{const current=frappe.get_route();if(current[0]==='List'&&current[1]==='PP Planning Draft'&&!frappe.boot.plus_point?.is_platform){const kind=frappe.route_options?.kind;frappe.set_route('List',kind==='Event'?'PP Event Plan':'PP Contract Terms','List');}});
})();
