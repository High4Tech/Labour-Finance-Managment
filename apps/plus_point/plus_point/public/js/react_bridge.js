/* Stage-by-stage React ownership. No new global observer or polling loop. */
(()=>{
 const pp=window.plus_point;let modulePromise;
 const load=()=>modulePromise||=(import('/assets/plus_point/react/index.js?v=20261109-react-finance-4').catch(error=>{modulePromise=null;throw error;}));
 pp.react_prepare_attendance_list=()=>load().then(runtime=>runtime.prepareAttendanceList());
 pp.react_prepare_finance_list=()=>load().then(runtime=>runtime.prepareFinanceList());
 async function mountSharedList(list, render){
  if(list.__pp_react_shared_list)return;
  const main=list.page.main.get(0),host=document.createElement('div'),query=location.search;
  const runtime=await load();
  const active=()=>{const [kind,doctype,view]=frappe.get_route()||[];return kind==='List'&&doctype===list.doctype&&(!view||view==='List')&&location.search===query;};
  if(!active()||list.__pp_react_shared_list)return;
  const oldRefresh=list.refresh,oldDebounced=list.debounced_refresh;
  list.__pp_react_shared_list=true;
  main.prepend(host);
  main.classList.add('pp-react-list-host');
  list.refresh=()=>{document.dispatchEvent(new Event('pp:data-changed'));return Promise.resolve();};
  list.debounced_refresh=()=>{};
  const leave=()=>{
   if(active())return;
   runtime.unmount(host);host.remove();main.classList.remove('pp-react-list-host');
   list.refresh=oldRefresh;list.debounced_refresh=oldDebounced;list.__pp_react_shared_list=false;
   frappe.router.off('change',leave);
  };
  frappe.router.on('change',leave);
  pp.react_ui=runtime;
  render(runtime,host,{canCreate:list.can_create,canDelete:frappe.model.can_delete(list.doctype)},active);
 }
 pp.react_attendance_list_mount=list=>mountSharedList(list,(runtime,host,permissions,active)=>{
  const project=new URLSearchParams(location.search).get('project')||frappe.route_options?.project;
  frappe.route_options=null;
  runtime.mountAttendanceList(host,{...permissions,project});
  pp.ensure_attendance_today?.(pp.dashboard_company||frappe.boot.plus_point?.company_identity?.name)
   ?.then(result=>{if(result?.created&&active())list.refresh();}).catch(console.error);
 });
 pp.react_finance_list_mount=list=>mountSharedList(list,(runtime,host,permissions)=>{
  const project=new URLSearchParams(location.search).get('project')||frappe.route_options?.project;
  frappe.route_options=null;
  runtime.mountFinanceList(host,{...permissions,doctype:list.doctype,project});
 });
 pp.react_prepare_resources=()=>load().then(runtime=>runtime.prepareResources());
 pp.react_resource_list_mount=list=>mountSharedList(list,(runtime,host)=>{
  runtime.mountResourceList(host,{Item:'equipment',Warehouse:'warehouses',Vehicle:'vehicles'}[list.doctype]);
 });
 pp.react_resource_profile_mount=async(host,kind,name)=>{
  const key=location.pathname+location.search;
  let runtime,disposed=false;
  const cleanup=()=>{if(disposed)return;disposed=true;runtime?.unmount(host);frappe.router.off('change',leave);host.replaceChildren();};
  const leave=()=>{if(location.pathname+location.search!==key)cleanup();};
  host.ppReactCleanup=cleanup;frappe.router.on('change',leave);
  host.textContent=__('Loading resource…');
  try{runtime=await load();if(!disposed){pp.react_ui=runtime;runtime.mountResourceProfile(host,kind,name);}}
  catch(error){if(!disposed)host.textContent=__('Resource could not load. Reopen to try again.');console.error(error);}
 };
 pp.react_finance_record_mount=async frm=>{
  if(frm.__pp_react_finance_record)return;
  frm.__pp_react_finance_record=true;
  const host=document.createElement('div'),key=location.pathname+location.search;
  frm.form_wrapper.prepend(host);frm.form_wrapper.addClass('pp-client-native-hidden');frm.page.wrapper.addClass('pp-react-accounting-page');frm.disable_save();frm.page.clear_primary_action();frm.page.clear_secondary_action();
  let runtime,disposed=false;
  const cleanup=()=>{if(disposed)return;disposed=true;runtime?.unmount(host);host.remove();frm.__pp_react_finance_record=false;frm.form_wrapper.removeClass('pp-client-native-hidden');frm.page.wrapper.removeClass('pp-react-accounting-page');frm.enable_save();frappe.router.off('change',leave);};
  const leave=()=>{if(key!==location.pathname+location.search)cleanup();};
  frappe.router.on('change',leave);
  const advanced=async values=>{if(!frm.is_new())await frm.reload_doc();await frm.set_value(values);sessionStorage.setItem('pp:finance:advanced-form',frm.doctype);cleanup();frm.refresh();};
  try{runtime=await load();if(!disposed){pp.react_ui=runtime;runtime.mountFinanceRecord(host,{doctype:frm.doctype,name:frm.is_new()?undefined:frm.doc.name,defaults:frm.is_new()||frm.is_dirty()?JSON.parse(JSON.stringify(frm.doc)):undefined,onAdvanced:advanced});}}
  catch(error){if(!disposed)host.textContent=__('Accounting record could not load. Reopen to try again.');console.error(error);}
 };
 pp.react_billing_mount=async(host,agreement,invoice)=>{
  const key=location.pathname+location.search;
  let runtime,disposed=false;
  const cleanup=()=>{if(disposed)return;disposed=true;runtime?.unmount(host);frappe.router.off('change',leave);host.replaceChildren();};
  const leave=()=>{if(location.pathname+location.search!==key)cleanup();};
  host.ppReactCleanup=cleanup;frappe.router.on('change',leave);
  try{runtime=await load();if(!disposed){pp.react_ui=runtime;runtime.mountBillingPage(host,{agreement,invoice});}}
  catch(error){if(!disposed)host.textContent=__('Billing could not load. Reopen to try again.');console.error(error);}
 };
 let resourceDialog;
 async function openResourceDialog(mount){
  resourceDialog?.();
  const host=document.createElement('div');document.body.append(host);
  let runtime,disposed=false;
  const close=()=>{if(disposed)return;disposed=true;runtime?.unmount(host);host.remove();frappe.router.off('change',close);if(resourceDialog===close)resourceDialog=null;};
  resourceDialog=close;frappe.router.on('change',close);
  try{runtime=await load();if(!disposed){pp.react_ui=runtime;await mount(runtime,host,close,()=>disposed);}}
  catch(error){close();frappe.msgprint({title:__('Resource could not load'),message:__('Reopen the action to try again.'),indicator:'red'});console.error(error);}
 }
 pp.react_resource_open=(kind,after)=>openResourceDialog(async(runtime,host,close,disposed)=>{
  const options=await pp.form_rpc('resources.form_options');
  if(disposed())return;
  runtime.mountResourceEditor(host,{kind:{inventory_items:'equipment',vehicles:'vehicles',warehouses:'warehouses'}[kind],options,onClose:close,onSaved:name=>{close();after?.({name,doctype:{inventory_items:'Item',vehicles:'Vehicle',warehouses:'Warehouse'}[kind]});}});
 });
 pp.react_resource_edit=(kind,name,after)=>openResourceDialog((runtime,host,close)=>{
  runtime.mountResourceEdit(host,{kind,name,onClose:close,onSaved:()=>{close();after?.();}});
 });
 pp.react_booking_open=(kind,options)=>openResourceDialog((runtime,host,close)=>{
  runtime.mountBooking(host,{kind,project:options.project,site:options.site,start:options.start,end:options.end,row:options.row,vehicle:options.vehicle,onClose:close,onSaved:()=>{close();options.after?.();}});
 });
 pp.react_attendance_mount=async(host,name,preview)=>{
  let runtime,disposed=false;
  const leave=()=>{
   const [kind,doctype,record]=frappe.get_route()||[];
   if(kind==='Form'&&doctype==='PP Daily Register'&&record===name)return;
   disposed=true;runtime?.unmount(host);host.remove();frappe.router.off('change',leave);
  };
  frappe.router.on('change',leave);leave();
  if(disposed)return;
  host.textContent=__('Loading attendance…');
  try{runtime=await load();if(!disposed)runtime.mountAttendanceRegister(host,name,preview);}
  catch(error){if(!disposed)host.textContent=__('Attendance could not load. Refresh to retry.');console.error(error);}
 };
 let importDialog;
 pp.react_import_open=async options=>{
  if(importDialog)return;
  const host=document.createElement('div');document.body.append(host);let runtime,disposed=false;
  const close=(notify=true)=>{if(disposed)return;disposed=true;runtime?.unmount(host);host.remove();frappe.router.off('change',leave);importDialog=null;if(notify)options.onClose?.();};
  const leave=()=>close(false);importDialog=close;frappe.router.on('change',leave);
  try{runtime=await load();if(disposed)return;pp.react_ui=runtime;runtime.mountImport(host,{...options,onSaved:()=>pp.refresh_setup_banner?.()},()=>close(true));}catch(error){close(false);frappe.msgprint({title:__('Import could not load'),message:__('Reopen the import to try again.'),indicator:'red'});console.error(error);}
 };
 pp.react_prepare_payments=()=>load().then(runtime=>runtime.preparePayments());
 pp.react_prepare_dashboard=()=>load().then(runtime=>runtime.prepareDashboard());
 pp.react_prepare_planning=()=>load().then(runtime=>runtime.preparePlanning());
 pp.react_prepare_workers=()=>load().then(runtime=>runtime.prepareWorkers());
 pp.react_prepare_clients=()=>load().then(runtime=>runtime.prepareClients());
 pp.react_agreement_builder_mount=async(host,name,draftName)=>{
  let disposed=false,runtime;const key=location.pathname+location.search;
  const cleanup=()=>{if(disposed)return;disposed=true;runtime?.unmount(host);frappe.router.off('change',leave);host.replaceChildren();};
  const leave=()=>{if(location.pathname+location.search!==key)cleanup();};frappe.router.on('change',leave);host.ppReactCleanup=cleanup;
  host.dataset.ppReactRoot='agreement-builder';host.textContent=__('Loading agreement…');
  try{runtime=await load();await runtime.prepareAgreementBuilder();if(disposed)return;pp.react_ui=runtime;runtime.mountAgreementBuilder(host,name,draftName);}catch(error){if(!disposed)host.textContent=__('Agreement could not load. Refresh to retry.');console.error(error);}
 };
 pp.react_agreement_profile_mount=async(host,name)=>{
  let disposed=false,runtime;const key=location.pathname+location.search;
  const cleanup=()=>{if(disposed)return;disposed=true;runtime?.unmount(host);frappe.router.off('change',leave);host.replaceChildren();};
  const leave=()=>{if(location.pathname+location.search!==key)cleanup();};frappe.router.on('change',leave);host.ppReactCleanup=cleanup;
  host.dataset.ppReactRoot='agreement-profile';host.textContent=__('Loading agreement…');
  try{runtime=await load();await runtime.prepareAgreementProfile();if(disposed)return;pp.react_ui=runtime;runtime.mountAgreementProfile(host,name);}catch(error){if(!disposed)host.textContent=__('Agreement could not load. Refresh to retry.');console.error(error);}
 };
 pp.react_clients_mount=async list=>{
  if(list.__pp_react_clients)return;list.__pp_react_clients=true;
  const main=list.page.main.get(0),page=list.page.wrapper.get(0),host=document.createElement('div');host.dataset.ppReactRoot='clients';host.textContent=__('Loading clients…');main.prepend(host);main.classList.add('pp-react-list-host');page.classList.add('pp-react-list-page');
  let disposed=false,runtime;const originalRefresh=list.refresh,originalDebounced=list.debounced_refresh;
  list.debounced_refresh=()=>{list.pending_document_refreshes=[];};list.refresh=()=>{document.dispatchEvent(new Event('pp:clients-refresh'));return Promise.resolve();};
  const leave=()=>{const r=frappe.get_route()||[];if(r[0]==='List'&&r[1]==='Customer')return;disposed=true;runtime?.unmount(host);host.remove();list.refresh=originalRefresh;list.debounced_refresh=originalDebounced;list.__pp_react_clients=false;main.classList.remove('pp-react-list-host');page.classList.remove('pp-react-list-page');frappe.router.off('change',leave);};frappe.router.on('change',leave);
  try{runtime=await load();await runtime.prepareClients();if(disposed)return;pp.react_ui=runtime;runtime.mountClients(host);}catch(error){if(!disposed)host.textContent=__('Clients could not load. Refresh to retry.');console.error(error);}
 };
 pp.react_client_mount=async frm=>{
  if(frm.__pp_react_client)return;frm.__pp_react_client=true;const customer=frm.is_new()?undefined:frm.doc.name,host=document.createElement('section');host.dataset.ppReactRoot='client-profile';frm.form_wrapper.prepend(host);frm.form_wrapper.addClass('pp-client-native-hidden');frm.disable_save();frm.page.clear_primary_action();frm.__pp_event_panel?.remove();
  let disposed=false,runtime;const leave=()=>{const r=frappe.get_route()||[];if(r[0]==='Form'&&r[1]==='Customer'&&r[2]===frm.doc.name)return;disposed=true;runtime?.unmount(host);host.remove();frm.__pp_react_client=false;frm.form_wrapper.removeClass('pp-client-native-hidden');frm.enable_save();frappe.router.off('change',leave);};frappe.router.on('change',leave);
  try{runtime=await load();await runtime.prepareClients();if(disposed)return;pp.react_ui=runtime;runtime.mountClientProfile(host,customer);}catch(error){if(!disposed)host.textContent=__('Client profile could not load. Refresh to retry.');console.error(error);}
 };
 let command;
 pp.react_command=async(kind,mode='search',after)=>{
  command?.();const host=document.createElement('div');document.body.append(host);let disposed=false,runtime;
  const close=()=>{if(disposed)return;disposed=true;runtime?.unmount(host);host.remove();frappe.router.off('change',close);if(command===close)command=null;};command=close;frappe.router.on('change',close);
  try{runtime=await load();if(disposed)return;pp.react_ui=runtime;runtime.mountCommand(host,kind,mode,close,after);}catch(error){close();frappe.show_alert({message:__('This action could not load. Try again.'),indicator:'red'});console.error(error);}
 };
 pp.react_workers_mount=async list=>{
  if(list.__pp_react_workers)return;list.__pp_react_workers=true;
  const main=list.page.main.get(0),page=list.page.wrapper.get(0),host=document.createElement('div');host.dataset.ppReactRoot='workers';main.prepend(host);main.classList.add('pp-react-list-host');page.classList.add('pp-react-list-page');
  let disposed=false,runtime;const originalRefresh=list.refresh,originalDebounced=list.debounced_refresh;
  list.debounced_refresh=()=>{list.pending_document_refreshes=[];};list.refresh=()=>{document.dispatchEvent(new Event('pp:workers-refresh'));return Promise.resolve();};
  const leave=()=>{const r=frappe.get_route()||[];if(r[0]==='List'&&r[1]==='Employee')return;disposed=true;runtime?.unmount(host);host.remove();list.refresh=originalRefresh;list.debounced_refresh=originalDebounced;list.__pp_react_workers=false;main.classList.remove('pp-react-list-host');page.classList.remove('pp-react-list-page');frappe.router.off('change',leave);};frappe.router.on('change',leave);
  try{runtime=await load();await runtime.prepareWorkers();if(disposed)return;pp.react_ui=runtime;runtime.mountWorkers(host);}catch(error){if(!disposed)host.textContent=__('Workers could not load. Refresh to retry.');console.error(error);}
 };
 pp.react_worker_mount=async frm=>{
  if(frm.__pp_react_worker){document.dispatchEvent(new Event('pp:worker-refresh'));return;}
  frm.__pp_react_worker=true;const employee=frm.is_new()?undefined:frm.doc.name,host=document.createElement('section');host.className='pp-worker-profile';host.dataset.ppReactRoot='worker-profile';host.dataset.ready='true';frm.form_wrapper.prepend(host);frm.form_wrapper.find('.form-layout,.form-tabs-list,.form-dashboard').hide();frm.disable_save();frm.page.clear_primary_action();frm.remove_custom_button(__('Assign to an event'));frm.remove_custom_button(__('Worker statement'));
  let disposed=false,runtime;const leave=()=>{const r=frappe.get_route()||[];if(r[0]==='Form'&&r[1]==='Employee'&&r[2]===frm.doc.name)return;disposed=true;runtime?.unmount(host);host.remove();frm.__pp_react_worker=false;frappe.router.off('change',leave);};frappe.router.on('change',leave);
  const photo=()=>pp.open_file_upload({doctype:'Employee',docname:employee,make_attachments_public:false,restrictions:{allowed_file_types:['image/png','image/jpeg','image/webp','image/gif']},on_success:async file=>{try{await pp.form_rpc('operations.set_photo',{employee,file_url:file.file_url});if(!disposed)document.dispatchEvent(new Event('pp:worker-refresh'));}catch(error){frappe.msgprint(frappe.utils.escape_html(error.message));}}});
  try{runtime=await load();await runtime.prepareWorkers();if(disposed)return;pp.react_ui=runtime;runtime.mountWorkerProfile(host,employee,photo);}catch(error){if(!disposed)host.textContent=__('Worker profile could not load. Refresh to retry.');console.error(error);}
 };
 pp.react_planning_mount=async list=>{
  if(list.__pp_react_planning)return;list.__pp_react_planning=true;
  const main=list.page.main.get(0),page=list.page.wrapper.get(0),host=document.createElement('div');host.dataset.ppReactRoot='planning';host.textContent=__('Loading records…');main.prepend(host);main.classList.add('pp-react-list-host');page.classList.add('pp-react-list-page');
  let disposed=false,runtime;const originalRefresh=list.refresh,originalDebounced=list.debounced_refresh;
  list.debounced_refresh=()=>{list.pending_document_refreshes=[];};
  list.refresh=function(...args){if(!disposed){document.dispatchEvent(new Event('pp:planning-draft-saved'));return Promise.resolve();}return originalRefresh.apply(this,args);};
  const leave=()=>{const r=frappe.get_route();if(r[0]==='List'&&r[1]===list.doctype)return;disposed=true;runtime?.unmount(host);host.remove();list.refresh=originalRefresh;list.debounced_refresh=originalDebounced;list.__pp_react_planning=false;main.classList.remove('pp-react-list-host');page.classList.remove('pp-react-list-page');frappe.router.off('change',leave);};frappe.router.on('change',leave);
  try{runtime=await load();await runtime.preparePlanning();if(disposed)return;pp.react_ui=runtime;runtime.mountPlanning(host,{doctype:list.doctype,can_create:!!list.can_create,can_delete:frappe.model.can_delete(list.doctype)});}
  catch(error){if(!disposed)host.textContent=__('Records could not load. Refresh to retry.');console.error('PLUS POINT React load',error);}
 };
 pp.react_dashboard_mount=async(host,data)=>{
  let disposed=false,runtime;host.dataset.ppReactRoot='dashboard';
  const leave=()=>{const r=frappe.get_route();if(r[0]==='Workspaces'&&r[1]==='PLUS POINT')return;cleanup();if(host.ppCurrencyHandler)document.removeEventListener('pp:display-currency',host.ppCurrencyHandler);host.closest('.pp-welcome')?.remove();};
  const cleanup=()=>{if(disposed)return;disposed=true;runtime?.unmount(host);frappe.router.off('change',leave);pp.app_shell?.clearAttention();};
  host.ppDashboardCleanup=cleanup;frappe.router.on('change',leave);
  try{runtime=await load();await runtime.prepareDashboard();if(disposed)return;pp.react_ui=runtime;runtime.mountDashboard(host,data);}
  catch(error){if(!disposed)host.textContent=__('Dashboard could not load. Refresh to retry.');console.error('PLUS POINT React load',error);}
 };
 pp.react_payments_mount=async list=>{
  if(list.__pp_wages||pp.use_native_payments())return;
  list.__pp_wages=true;
  const main=list.page.main.get(0),host=document.createElement('div');host.dataset.ppReactRoot='payments';
  main.classList.add('pp-react-payments-host');main.prepend(host);host.textContent=__('Loading worker payments…');
  let disposed=false,runtime;const originalRefresh=list.refresh,originalDebounced=list.debounced_refresh;
  list.debounced_refresh=()=>{list.pending_document_refreshes=[];};
  list.refresh=function(...args){if(!disposed){document.dispatchEvent(new Event('pp:payments-refresh'));return Promise.resolve();}return originalRefresh.apply(this,args);};
  const leave=()=>{
   const route=frappe.get_route();if(route[0]==='List'&&route[1]==='PP Wage Settlement')return;
   disposed=true;list.refresh=originalRefresh;list.debounced_refresh=originalDebounced;runtime?.unmount(host);host.remove();main.classList.remove('pp-react-payments-host');list.__pp_wages=false;frappe.router.off('change',leave);
  };
  frappe.router.on('change',leave);
  try{runtime=await load();await runtime.preparePayments();if(disposed)return;pp.react_ui=runtime;runtime.mountPayments(host,list);}
  catch(error){if(disposed)return;host.textContent=__('Payment balances could not load. Refresh to retry.');const fallback=document.createElement('a');fallback.href='/desk/pp-wage-settlement';fallback.onclick=()=>sessionStorage.setItem('pp:payments:advanced','1');fallback.textContent=__('Open advanced payment history');host.append(document.createElement('br'),fallback);console.error('PLUS POINT React load',error);}
 };
 pp.react_notifications_mount=async wrapper=>{
  const host=wrapper.pp_notifications_root;if(host.ppReactMounted)return;host.ppReactMounted=true;host.dataset.ppReactRoot='notifications';host.textContent=__('Loading notifications…');let disposed=false,runtime;
  const leave=()=>{if(frappe.get_route()[0]==='pp-notifications')return;disposed=true;runtime?.unmount(host);host.ppReactMounted=false;frappe.router.off('change',leave);};frappe.router.on('change',leave);
  try{runtime=await load();if(disposed)return;pp.react_ui=runtime;runtime.mountNotifications(host,unread=>frappe.app.sidebar.notifications?.tabs?.notifications?.update_count_badge(unread));}
  catch(error){if(!disposed){host.ppReactMounted=false;host.textContent=__('Notifications could not load. Open this page again to retry.');}console.error('PLUS POINT React load',error);}
 };
})();
