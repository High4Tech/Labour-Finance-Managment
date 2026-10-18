frappe.pages['pp-inventory'].on_page_load=function(wrapper){
 const page=frappe.ui.make_app_page({parent:wrapper,title:__('Warehouse availability'),single_column:true});
 const root=document.createElement('div');root.className='pp-section-home';page.main.append(root);wrapper.pp_inventory_root=root;
 const reload=()=>plus_point.load_inventory(wrapper);
 wrapper.pp_inventory_company=page.add_field({fieldname:'company',fieldtype:'Link',label:__('Your company'),options:'Company',change:reload});
 wrapper.pp_inventory_from=page.add_field({fieldname:'from_date',fieldtype:'Date',label:__('From'),default:frappe.datetime.get_today(),change:reload});
 wrapper.pp_inventory_to=page.add_field({fieldname:'to_date',fieldtype:'Date',label:__('Through'),default:frappe.datetime.get_today(),change:reload});
 page.set_primary_action(__('Add inventory item'),()=>plus_point.open_resource('inventory_items',reload),'plus');
 page.set_secondary_action(__('Import'),()=>plus_point.open_import(wrapper.pp_inventory_company.get_value(),reload,'stock_balances'),'upload');
};
frappe.pages['pp-inventory'].on_page_show=async function(wrapper){
 if(!wrapper.pp_inventory_company.get_value()){
  const companies=await frappe.db.get_list('Company',{fields:['name'],limit:100});
  await wrapper.pp_inventory_company.set_value(plus_point.dashboard_company||companies[0]?.name);
 }
 plus_point.load_inventory(wrapper);
};
