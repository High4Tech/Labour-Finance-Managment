frappe.ui.form.on('PP Site', {
    refresh(frm) {
        if (frm.is_new() || !frm.doc.is_active) return;
        frm.add_custom_button(__('Prepare daily attendance'), () => {
            frappe.prompt([{fieldname: 'work_date', fieldtype: 'Date', label: __('Work date'),
                default: frappe.datetime.get_today(), reqd: 1}], values => {
                frappe.call({method: 'plus_point.api.prepare_daily_register', type: 'POST',
                    args: {site: frm.doc.name, work_date: values.work_date}, freeze: true,
                    callback: r => frappe.set_route('Form', 'PP Daily Register', r.message.name)});
            }, __('Prepare daily attendance'));
        });
    }
});
