/* React worker owner; native Employee controls remain available on request. */
(()=>{
 const pp=window.plus_point,advanced=()=>sessionStorage.getItem('pp:workers:advanced')==='1';
 async function mount(frm){
  if(advanced()){frm.page.add_inner_button(__('Back to worker overview'),()=>{sessionStorage.removeItem('pp:workers:advanced');location.assign(location.pathname);});return;}
  if(frappe.boot.plus_point?.is_platform)return;
  await pp.load_feature('react_ui');return pp.react_worker_mount(frm);
 }
 pp.open_worker_profile=mount;
 frappe.ui.form.on('Employee',{
  before_load(frm){if(!frappe.boot.plus_point?.is_platform&&frappe.user.has_role('System Manager')&&!advanced())frm.form_wrapper?.addClass('pp-worker-native-hidden');},
  refresh(frm){if(frappe.boot.plus_point?.is_platform||!frappe.user.has_role('System Manager'))return;mount(frm).catch(error=>console.error('PLUS POINT worker profile',error));}
 });
 pp.watch_ui('react-worker-list',()=>{const r=frappe.get_route()||[],list=window.cur_list;if(frappe.boot.plus_point?.is_platform||advanced()||r[0]!=='List'||r[1]!=='Employee'||list?.doctype!=='Employee'||!list.page?.main||!list.list_view_settings||list.__pp_react_workers||list.__pp_react_workers_pending)return;list.__pp_react_workers_pending=true;pp.load_feature('react_ui').then(()=>{if(window.cur_list===list&&(frappe.get_route()||[])[0]==='List')return pp.react_workers_mount(list);}).catch(error=>console.error('PLUS POINT workers',error)).finally(()=>list.__pp_react_workers_pending=false);});
})();
