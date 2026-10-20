frappe.ui.form.on('PP Signup Request', {
    refresh(frm) {
        clearTimeout(frm.pp_activation_timer);
        const status = frm.doc.activation_status || 'Not requested';
        const escape = value => frappe.utils.escape_html(String(value || ''));
        const action = async (method, args = {}) => {
            await frappe.call({method, type: 'POST', args: {reference: frm.doc.name, ...args}, freeze: true});
            await frm.reload_doc();
        };
        frm.dashboard.set_headline_alert(__(frm.doc.activation_message ||
            'Payment is simulated. Approval creates a separate company workspace; the owner chooses their password.'),
            status === 'Failed' ? 'red' : ['Ready', 'Active'].includes(status) ? 'green' : 'blue');
        if (frm.doc.review_status === 'Awaiting approval') {
            frm.add_custom_button(__('Approve & create workspace'), () => action('plus_point.signup.review', {decision: 'Approved'}));
            frm.add_custom_button(__('Reject signup'), () => action('plus_point.signup.review', {decision: 'Rejected'}));
        }
        if (frm.doc.review_status !== 'Approved') return;
        if (['Not requested', 'Failed'].includes(status)) {
            frm.add_custom_button(__(status === 'Failed' ? 'Retry workspace setup' : 'Create company workspace'),
                () => action('plus_point.activation.activate'));
        } else if (['Queued', 'Creating'].includes(status)) {
            frm.add_custom_button(__('Refresh progress'), () => frm.reload_doc());
            frm.pp_activation_timer = setTimeout(() => {
                if (cur_frm === frm) frm.reload_doc();
            }, 5000);
        } else if (['Ready', 'Active'].includes(status)) {
            frm.add_custom_button(__('Company login'), async () => {
                const {message: data} = await frappe.call({method: 'plus_point.activation.account_details',
                    type: 'POST', args: {reference: frm.doc.name}});
                let body = `<p><strong>${__('Login email')}:</strong> ${escape(data.login_email)}</p>`;
                if (data.login_username) body += `<p><strong>${__('Company login ID')}:</strong> ${escape(data.login_username)}</p>`;
                body += `<p><a href="${escape(data.login_url)}" target="_blank" rel="noopener noreferrer">${__('Open company login')}</a></p>`;
                body += data.setup_url
                    ? `<p><a class="btn btn-primary" href="${escape(data.setup_url)}" target="_blank" rel="noopener noreferrer">${__('Set your password')}</a></p><p>${__('Private, one-time link. The owner chooses their password. No email was sent.')}</p>`
                    : `<p>${__(status === 'Ready' ? 'The setup link expired. Close this message and choose Refresh password setup link.' : 'Use the password chosen by the company owner. Customer support can help with account recovery.')}</p>`;
                frappe.msgprint({title: __('Company login'), message: body});
            });
            if (status === 'Ready') frm.add_custom_button(__('Refresh password setup link'),
                () => action('plus_point.activation.refresh_setup'));
        }
    }
});
