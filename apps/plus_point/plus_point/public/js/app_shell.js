/* React owns company chrome. Native Sidebar retains layout/permissions and advanced navigation. */
(()=>{
 frappe.provide('plus_point');const pp=plus_point;let host,header,sidebar,context={},attention=[],opening;
 function title(){const r=frappe.get_route()||[],aliases={'pp-agreements':'Agreements','pp-event-plans':'Jobs & Events','pp-client-billing':'Billing and invoices','pp-daily-register':'Attendance','pp-onboarding':'Company setup','pp-notifications':'Notifications & activity'};if(r[0]==='Workspaces')return __('Overview');if(r[0]==='pp-section')return new URL(location.href).searchParams.get('section')||'';if(r[0]==='pp-inventory')return ({equipment:'Inventory & equipment',warehouses:'Warehouses',vehicles:'Vehicles'})[new URL(location.href).searchParams.get('view')]||'Warehouses';return aliases[r[0]]||(frappe.boot.plus_point.navigation?.items||[]).find(i=>i.link_to===r[1]||i.link_to===r[0])?.label||r[1]||r[0]||'Overview';}
 async function update(data){
  if(frappe.boot?.plus_point?.is_platform||!pp.load_feature)return;
  if(data)Object.assign(context,data);
  const body=document.getElementById('body'),nativeSidebar=document.querySelector('.body-sidebar');if(!body||!nativeSidebar)return;
  if(!host){host=document.createElement('div');host.className='pp-react-shell-owner';document.body.append(host);}
  if(!header?.isConnected){header=document.createElement('header');header.className='pp-global-bar pp-app-header';header.dataset.ppReactRoot='shell-header';header.setAttribute('aria-label',__('Company and page controls'));body.prepend(header);}
  if(!sidebar?.isConnected){sidebar=document.createElement('div');sidebar.className='pp-react-sidebar';sidebar.dataset.ppReactRoot='shell-navigation';nativeSidebar.prepend(sidebar);nativeSidebar.classList.add('pp-react-navigation-owner');}
  if(!pp.react_shell){opening||=pp.load_feature('react_ui').finally(()=>opening=null);await opening;}
  const identity=context.companies?.find(c=>c.name===context.company)?.company_name||frappe.boot.plus_point.company_identity?.title||__('Your company'),currency=frappe.boot.plus_point.display_currency||context.currency||frappe.boot.plus_point.company_currency||'USD',person=frappe.user_info(frappe.session.user)||{};
  pp.react_shell(host,{header,sidebar,title:__(title()),identity,currency,currencies:context.currency_options||frappe.boot.plus_point.currency_options||[currency],items:frappe.boot.plus_point.navigation?.items||[],unread:Math.max(0,Number(document.querySelector('.sidebar-notification .notification-count')?.textContent)||0),user:{name:person.fullname||frappe.session.user,email:person.email||frappe.boot.user.email||'',image:person.image},attention:[...attention]});
 }
 pp.app_shell={update,account:()=>{},setContext:update,setAttention:rows=>{attention=rows;update();},clearAttention:()=>{attention=[];update();}};
})();
