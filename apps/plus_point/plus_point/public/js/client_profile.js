/* React owns company client screens. Authorized native Customer views remain available. */
(()=>{
 const pp=window.plus_point,advanced=()=>sessionStorage.getItem('pp:clients:advanced')==='1',company=()=>!frappe.boot.plus_point?.is_platform&&frappe.user.has_role('System Manager');
 frappe.ui.form.on('Customer',{
  before_load(frm){if(company()&&!advanced())frm.form_wrapper?.addClass('pp-client-native-hidden');},
  refresh(frm){if(!company())return;if(advanced()){frm.page.add_inner_button(__('Back to client profile'),()=>{sessionStorage.removeItem('pp:clients:advanced');location.assign(location.pathname);});return;}pp.load_feature('react_ui').then(()=>pp.react_client_mount(frm)).catch(error=>console.error('PLUS POINT client profile',error));}
 });
 pp.watch_ui('react-client-list',()=>{const r=frappe.get_route()||[],list=window.cur_list;if(!company()||advanced()||r[0]!=='List'||r[1]!=='Customer'||list?.doctype!=='Customer'||!list.page?.main||!list.list_view_settings||list.__pp_react_clients||list.__pp_react_clients_pending)return;list.__pp_react_clients_pending=true;pp.load_feature('react_ui').then(()=>{if(window.cur_list===list&&(frappe.get_route()||[])[0]==='List')return pp.react_clients_mount(list);}).catch(error=>console.error('PLUS POINT clients',error)).finally(()=>list.__pp_react_clients_pending=false);});
})();
