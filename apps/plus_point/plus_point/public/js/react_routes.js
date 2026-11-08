/* Thin native permission/route host for complete React list owners.
 * Native advanced views and all other DocTypes keep their original lifecycle.
 * Do not initialize a hidden native filter/table/sidebar and fetch its records
 * before fetching the exact same records through the React screen API.
 */
(()=>{
 const pp=window.plus_point;
 const owners={
  Item:{prepare:'react_prepare_resources',mount:'react_resource_list_mount',advanced:'pp:resources:advanced',title:'Inventory & equipment'},
  Warehouse:{prepare:'react_prepare_resources',mount:'react_resource_list_mount',advanced:'pp:resources:advanced',title:'Warehouses'},
  Vehicle:{prepare:'react_prepare_resources',mount:'react_resource_list_mount',advanced:'pp:resources:advanced',title:'Vehicles'},
  'Payment Entry':{prepare:'react_prepare_finance_list',mount:'react_finance_list_mount',advanced:'pp:finance:advanced',title:'Receipts and payments'},
  'Purchase Invoice':{prepare:'react_prepare_finance_list',mount:'react_finance_list_mount',advanced:'pp:finance:advanced',title:'Expenses'},
  'Expense Claim':{prepare:'react_prepare_finance_list',mount:'react_finance_list_mount',advanced:'pp:finance:advanced',title:'Worker reimbursements'},
  'Sales Invoice':{prepare:'react_prepare_finance_list',mount:'react_finance_list_mount',advanced:'pp:finance:advanced',title:'Client invoices'},
  'PP Daily Register':{prepare:'react_prepare_attendance_list',mount:'react_attendance_list_mount',advanced:'pp:attendance:advanced',title:'Attendance registers'},
  'PP Contract Terms':{prepare:'react_prepare_planning',mount:'react_planning_mount',advanced:'pp:planning:advanced',title:'Agreements'},
  'PP Event Plan':{prepare:'react_prepare_planning',mount:'react_planning_mount',advanced:'pp:planning:advanced',title:'Jobs & Events'},
  'PP Wage Settlement':{prepare:'react_prepare_payments',mount:'react_payments_mount',advanced:'pp:payments:advanced',title:'Worker payments'},
  Employee:{prepare:'react_prepare_workers',mount:'react_workers_mount',advanced:'pp:workers:advanced',title:'Workers'},
  Customer:{prepare:'react_prepare_clients',mount:'react_clients_mount',advanced:'pp:clients:advanced',title:'Clients'}
 };
 function owner(list){const route=frappe.get_route()||[],config=owners[list.doctype];if(!config||frappe.boot.plus_point?.is_platform||route[0]!=='List'||route[1]!==list.doctype||(route[2]&&route[2]!=='List'))return null;const preference=sessionStorage.getItem(config.advanced);return preference&&(!['pp:planning:advanced','pp:finance:advanced','pp:resources:advanced'].includes(config.advanced)||preference===list.doctype)?null:config;}
 function install(){
  const proto=frappe.views?.ListView?.prototype;if(!proto||proto.__pp_react_route_adapter)return;
  const nativeShow=proto.show;
  proto.show=function(...args){
   const config=owner(this);if(!config){(this.parent?.get?.(0)||this.parent)?.classList?.remove('pp-react-list-page');return nativeShow.apply(this,args);}
   (this.parent?.get?.(0)||this.parent).classList.add('pp-react-list-page');
   if(this.__pp_react_show_pending)return this.__pp_react_show_pending;
   this.__pp_react_show_pending=(async()=>{
    // Metadata and native permission checks stay authoritative. List settings,
    // filters, row templates, counts and refresh timers belong to the React owner.
    await Promise.all([this.fetch_meta(),pp.load_feature('react_ui')]);
    if(!owner(this))return;
    this.check_permissions();
    if(!this.__pp_react_defaults){frappe.views.BaseList.prototype.setup_defaults.call(this);this.__pp_react_defaults=true;}
    this.meta=frappe.get_meta(this.doctype);this.parent.list_view=this;
    this.page=this.parent.page;this.page_name=frappe.get_route_str();this.page_title=__(config.title);
    this.can_create=frappe.model.can_create(this.doctype);this.can_write=frappe.model.can_write(this.doctype);
    this.list_view_settings||={};this.data||=[];this.fields||=[];this.filters||=[];
    this.page.main.addClass('layout-main-list');this.parent.disable_scroll_to_top=false;
    this.page.set_title(__(config.title));this.parent.page.container.find('.list-skeleton').hide();
    this.parent.page.container.find('.layout-main').show();
    await pp[config.prepare]();if(owner(this))await pp[config.mount](this);
   })().catch(error=>{if(owner(this)){this.page?.main?.find('[data-pp-route-error]').remove();const message=document.createElement('p');message.dataset.ppRouteError='true';message.role='alert';message.textContent=__('This screen could not load. Reopen it to try again.');this.parent.page.main.prepend(message);}console.error('PLUS POINT React list route',error);}).finally(()=>{this.__pp_react_show_pending=null;});
   return this.__pp_react_show_pending;
  };
  proto.__pp_react_route_adapter=true;
 }
 install();pp.watch_ui('react-list-route-adapter',install);
})();
