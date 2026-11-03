/* React command dialogs; native resource actions remain explicit migration adapters. */
(()=>{frappe.provide('plus_point');const pp=plus_point;
 pp.create_record=async kind=>{
  if(kind==='agreements'||kind==='events'){frappe.set_route(kind==='agreements'?'pp-agreements':'pp-event-plans',{record:'new'});return;}
  if(['workers','clients'].includes(kind)){await pp.load_feature('react_ui');return pp.react_command(kind,'create');}
  return pp.open_resource(kind==='inventory'?'inventory_items':kind,()=>document.dispatchEvent(new Event('pp:data-changed')));
 };
 pp.scoped_search=kind=>pp.load_feature('react_ui').then(()=>pp.react_command(kind,'search'));
 pp.mount_notifications=wrapper=>pp.load_feature('react_ui').then(()=>pp.react_notifications_mount(wrapper));
})();
