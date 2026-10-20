frappe.pages['pp-onboarding'].on_page_load=function(wrapper){
 const page=frappe.ui.make_app_page({parent:wrapper,title:__('Onboarding'),single_column:true});
 const root=document.createElement('div');root.className='pp-onboarding-shell';page.main.append(root);wrapper.pp_onboarding_root=root;
};
frappe.pages['pp-onboarding'].on_page_show=async function(wrapper){
 if(frappe.boot.plus_point?.is_platform){frappe.set_route('/desk/high4tech');return;}
 if(wrapper.pp_loading_setup)return;wrapper.pp_loading_setup=true;
 try{await plus_point.setup_rpc('plus_point.event_setup.control',{action:'resume'});await plus_point.load_onboarding(wrapper);}
 catch{await plus_point.load_onboarding(wrapper);}
 finally{wrapper.pp_loading_setup=false;}
};
