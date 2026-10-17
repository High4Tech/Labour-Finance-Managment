frappe.query_reports['PLUS POINT Project Finances'] = {
    filters: [
        {fieldname: 'company', label: __('Your company'), fieldtype: 'Link', options: 'Company', reqd: 1,
            default: frappe.defaults.get_user_default('Company')},
        {fieldname: 'view', label: __('Show'), fieldtype: 'Select',
            options: ['Financial results', 'Deployment overview'], default: 'Financial results'},
        {fieldname: 'customer', label: __('Client company'), fieldtype: 'Link', options: 'Customer'},
        {fieldname: 'project', label: __('Project'), fieldtype: 'Link', options: 'Project',
            get_query: () => ({filters: {company: frappe.query_report.get_filter_value('company')}})},
        {fieldname: 'status', label: __('Project status'), fieldtype: 'Select', options: '\nOpen\nCompleted\nCancelled'},
    ],
};
