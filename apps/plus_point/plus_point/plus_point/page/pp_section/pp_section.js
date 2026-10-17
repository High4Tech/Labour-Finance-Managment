frappe.pages['pp-section'].on_page_load = function(wrapper) {
    frappe.ui.make_app_page({parent:wrapper,title:__('Section overview'),single_column:true});
    const root=document.createElement('div');root.className='pp-section-home';wrapper.page.main.append(root);
    wrapper.pp_section_root=root;
};
frappe.pages['pp-section'].on_page_show = function(wrapper) { plus_point.mount_section(wrapper); };
