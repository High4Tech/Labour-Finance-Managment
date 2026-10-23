frappe.query_reports['PLUS POINT Project Finances'] = {
    onload(report){document.addEventListener('pp:display-currency',()=>{if(frappe.query_report===report){report.set_filter_value('display_currency',frappe.boot.plus_point.display_currency);report.refresh();}});},
    filters: [
        {fieldname:'display_currency',label:__('Reporting currency'),fieldtype:'Link',options:'Currency',default:frappe.boot.plus_point?.display_currency||''},
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
