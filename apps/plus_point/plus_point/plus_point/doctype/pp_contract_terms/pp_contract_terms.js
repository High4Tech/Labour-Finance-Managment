frappe.ui.form.on('PP Contract Terms', {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.add_custom_button(__('Project finances'), async () => {
            const result = await frappe.db.get_value('Project', frm.doc.project, 'company');
            frappe.set_route('query-report', 'PLUS POINT Project Finances', {project: frm.doc.project, company: result.message.company});
        });
        if (frm.doc.status === 'Active') frm.add_custom_button(__('Prepare client invoice'), () => {
            frappe.prompt([
                {fieldname: 'item_code', fieldtype: 'Link', options: 'Item', label: __('Service item'), reqd: 1},
                {fieldname: 'from_date', fieldtype: 'Date', label: __('From date')},
                {fieldname: 'to_date', fieldtype: 'Date', label: __('To date')}
            ], values => frappe.call({method: 'plus_point.billing.create_invoice', type: 'POST',
                args: {...values, contract_terms: frm.doc.name}, freeze: true,
                callback: r => frappe.set_route('Form', 'Sales Invoice', r.message.name)}), __('Prepare draft invoice'));
        });
    }
});
