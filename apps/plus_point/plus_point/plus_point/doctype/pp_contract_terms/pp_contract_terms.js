frappe.ui.form.on('PP Contract Terms', {
    refresh(frm) {
        if (frm.is_new()) return;
        frm.add_custom_button(__('Project finances'), () => {
            frappe.call({method: 'plus_point.api.project_summary', args: {project: frm.doc.project},
                callback: r => frappe.msgprint({title: __('Project finances'),
                    message: Object.entries(r.message).filter(([k, v]) => k !== 'contracts' && typeof v !== 'object')
                        .map(([k, v]) => `<p><b>${frappe.utils.escape_html(frappe.unscrub(k))}:</b> ${frappe.utils.escape_html(String(v))}</p>`).join('')})});
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
