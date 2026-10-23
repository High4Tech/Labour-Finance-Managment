frappe.query_reports['PLUS POINT Worker Statement'] = {
    onload(report){plus_point.mount_business_report(report);},
    get_datatable_options(options){return plus_point.business_report_options(options);},
    after_datatable_render(){plus_point.fit_business_report();},
    filters: [
        {fieldname: 'company', label: __('Your company'), fieldtype: 'Link', options: 'Company', reqd: 1,
            default: frappe.defaults.get_user_default('Company')},
        {fieldname: 'employee', label: __('Worker'), fieldtype: 'Link', options: 'Employee', reqd: 1},
        {fieldname: 'view', label: __('Show'), fieldtype: 'Select',
            options: ['Work and payments', 'Assignment history'], default: 'Work and payments'},
        {fieldname: 'customer', label: __('Client company'), fieldtype: 'Link', options: 'Customer'},
        {fieldname: 'project', label: __('Project'), fieldtype: 'Link', options: 'Project',
            get_query: () => ({filters: {company: frappe.query_report.get_filter_value('company')}})},
        {fieldname: 'from_date', label: __('From date'), fieldtype: 'Date'},
        {fieldname: 'to_date', label: __('Through date'), fieldtype: 'Date'},
    ],
};
