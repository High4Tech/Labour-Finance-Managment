/* Task shortcuts and guidance layered onto native, permission-checked Desk. */
(() => {
    const appHelp = {
        'PLUS POINT': 'Start here for work sites, worker assignments, dehadi and contractor billing.',
        'ERPNext': 'Client records, projects, invoices, receipts and accounting. Other ERP modules are optional.',
        'Frappe HR': 'Employee records, leave, shifts and payroll. Contractor dehadi is recorded in PLUS POINT.',
        'Framework': 'User accounts, permissions and system configuration. Mainly for administrators.',
        'High4Tech admin': 'A separate platform site for subscriber organizations, plans, trials and access limits. It does not share the customer’s workforce database.',
    };
    const appSummary = {
        'PLUS POINT': 'Sites, dehadi and billing', 'ERPNext': 'Clients and accounting',
        'Frappe HR': 'Employee HR and payroll', 'Framework': 'Users and settings',
        'High4Tech admin': 'Subscribers and billing',
    };
    const steps = [
        {title: 'Set up the client and job', text: 'Your Company is your own business. A Client company is the customer paying you. Link its agreement and project before assigning workers.',
            links: [['Company', 'Your company'], ['Customer', 'Client companies'], ['Contract', 'Client contracts'], ['Project', 'Projects']]},
        {title: 'Agree how the client will be billed', text: 'Daily billing uses approved worker-days × client rate. Fixed billing uses approved milestones; workers still earn their daily wages.',
            links: [['PP Contract Terms', 'Billing terms'], ['PP Milestone', 'Fixed milestones']]},
        {title: 'Choose where each worker will work', text: 'Create work sites under a project. Add workers, then allocate them to a site with dates, a wage rate and the agreed client rate.',
            links: [['PP Site', 'Work sites'], ['Employee', 'Workers'], ['PP Assignment', 'Worker allocations']]},
        {title: 'Record daily attendance and dehadi', text: 'Choose Mark attendance on Workforce home, then select a work site and date. Review each worker: 1 = full day, 0.5 = half day, 0 = absent. Submit the register to approve earnings.',
            links: [['PP Daily Register', 'Daily attendance'], ['PP Work Entry', 'Worker earnings']]},
        {title: 'Invoice the client and record receipts', text: 'Open active Billing terms and choose Prepare client invoice. Review and submit the invoice, then record the client payment as a receipt.',
            links: [['PP Contract Terms', 'Prepare an invoice'], ['Sales Invoice', 'Client invoices'], ['Payment Entry', 'Receipts and payments']]},
        {title: 'Pay workers and review the project', text: 'Record a submitted payment to the employee, then link it in Worker payments. Open Billing terms → Project finances to compare earnings, receipts, wages and outstanding balances.',
            links: [['PP Wage Settlement', 'Worker payments'], ['PP Contract Terms', 'Project finances']]},
    ];
    const screens = {
        'PP Site': ['Work sites', 'A physical work location within a project: a construction site, compound or warehouse. Use Prepare daily attendance after workers have active allocations.', ['site_name', 'project', 'parent_site']],
        'PP Assignment': ['Worker allocations', 'Connect one worker to a site, billing agreement and date range. These agreed rates are copied into work records so later rate changes cannot rewrite past earnings.', ['employee', 'contract_terms', 'site', 'start_date', 'wage_rate', 'client_rate']],
        'PP Contract Terms': ['Billing terms', 'Choose daily worker-day billing or a fixed contract amount. Prepare client invoices and review Project finances from this screen.', ['contract', 'project', 'billing_model', 'fixed_amount', 'status']],
        'PP Daily Register': ['Daily attendance', 'One register records a site and date. Saving keeps a draft; Submit creates approved work entries and earnings for the listed workers. Review before submitting.', ['work_date', 'site', 'entries']],
        'PP Work Entry': ['Worker earnings', 'A worker-day and its locked wage and client billing amounts. Earnings are not proof of payment. Prefer the site attendance register for bulk daily entry.', ['assignment', 'units', 'status', 'wage_amount', 'billable_amount']],
        'PP Milestone': ['Fixed contract milestones', 'A completed portion of a fixed-price agreement. Approved milestones earn client revenue; daily worker wages are calculated separately.', ['contract_terms', 'amount', 'status']],
        'PP Wage Settlement': ['Worker payments', 'Link a real, submitted employee Payment Entry to approved wages. Saving is a draft; Submit allocates the payment. This does not create a bank payment or payroll run.', ['employee', 'project', 'payment_entry', 'amount']],
        'Customer': ['Client companies', 'The organization that hires and pays your labour contracting business. This is different from your own Company record.', []],
        'Company': ['Your company', 'Your own legal business and accounting records. Organizations that hire you belong under Client companies instead.', []],
        'Contract': ['Client contracts', 'The client agreement. Add PLUS POINT Billing terms to select daily or fixed billing for its project.', []],
        'Project': ['Projects', 'The job for a client. A project can contain multiple PLUS POINT work sites. Review contractor figures from Billing terms → Project finances.', []],
        'Employee': ['Workers', 'The shared employee profile used by PLUS POINT and HR. Assign this worker to a site for dehadi. Link User ID only if the worker needs their own employee login.', []],
        'Sales Invoice': ['Client invoices', 'A bill raised to your client. Use Billing terms → Prepare client invoice to include approved PLUS POINT work or milestones. An invoice is not a cash receipt.', []],
        'Payment Entry': ['Receipts and payments', 'Record money received from clients or paid to employees. A submitted employee payment can be linked in PLUS POINT Worker payments.', []],
        'User': ['User accounts', 'A person who can log in. Users and workers are different: not every worker needs a login. Permissions come from native roles.', []],
        'PP Tenant': ['Customer organizations', 'High4Tech manages each subscriber and its separate site here. The subscription and limits control access; the operator worker applies changes to the tenant site.', ['organization_name', 'site_hostname', 'subscription', 'suspended']],
        'Subscription': ['Subscriptions', 'The subscriber’s billing period, trial and renewal state. High4Tech uses this to determine whether the customer site can accept changes.', []],
        'Subscription Plan': ['Subscription plans', 'The recurring service and price charged to a subscriber. Tenant worker, user and work-site limits are configured separately on the customer organization.', []],
    };
    const workspaceHelp = {
        'Client companies': screens.Customer[1], 'Client contracts': screens.Contract[1],
        'Projects': screens.Project[1], 'Workers': screens.Employee[1],
        'Work sites': screens['PP Site'][1], 'Worker allocations': screens['PP Assignment'][1],
        'Daily attendance': screens['PP Daily Register'][1], 'Worker earnings': screens['PP Work Entry'][1],
        'Billing terms': screens['PP Contract Terms'][1], 'Fixed contract milestones': screens['PP Milestone'][1],
        'Client invoices': screens['Sales Invoice'][1], 'Receipts and payments': screens['Payment Entry'][1],
        'Worker payments': screens['PP Wage Settlement'][1],
    };
    const customerLists = {
        'PP Site': ['Work sites', 'Add work site'],
        'PP Assignment': ['Worker assignments', 'Assign worker'],
        'PP Contract Terms': ['Client billing', 'Add billing terms'],
        'PP Daily Register': ['Daily attendance', 'Add attendance'],
        'PP Work Entry': ['Wages earned', 'Add work entry'],
        'PP Milestone': ['Fixed contract milestones', 'Add milestone'],
        'PP Wage Settlement': ['Worker payments', 'Record payment'],
    };
    const shortPurpose = {
        'PP Site': 'Choose a work site to prepare daily attendance.',
        'PP Assignment': 'Agree who works where, for which dates and rates.',
        'PP Contract Terms': 'Choose daily or fixed client billing for a project.',
        'PP Daily Register': 'Review each worker, then Submit to approve earnings.',
        'PP Work Entry': 'Wages earned from approved work. Payments are recorded separately.',
        'PP Milestone': 'Client earnings for fixed contracts. Worker wages remain separate.',
        'PP Wage Settlement': 'Link a submitted employee payment to wages earned.',
    };
    let started = false, queued = false, driver;
    const esc = value => frappe.utils.escape_html(String(value));
    const platform = () => !!frappe.boot.plus_point?.is_platform;
    const home = () => frappe.boot.plus_point?.home || '/desk/plus-point';
    const link = ([doctype, label]) => frappe.model.can_read(doctype)
        ? `<a class="pp-guide-link" href="/desk/${frappe.router.slug(doctype)}">${esc(__(label))}</a>` : '';
    const key = () => `pp-quick-start-v2:${location.host}:${frappe.session.user}`;
    const expanded = () => { try { return localStorage.getItem(key()) === 'expanded'; } catch { return false; } };

    function attendancePicker() {
        let opening = false;
        const dialog = new frappe.ui.Dialog({title: __('Mark attendance'), fields: [
            {fieldtype: 'HTML', fieldname: 'explanation', options: `<p>${esc(__('Choose a work site and date. You will review a draft before approving any earnings. A saved register will reopen.'))}</p>`},
            {fieldtype: 'Link', fieldname: 'site', label: __('Work site'), options: 'PP Site', reqd: 1,
                get_query: () => ({filters: {is_active: 1}})},
            {fieldtype: 'Date', fieldname: 'work_date', label: __('Date'), reqd: 1, default: frappe.datetime.get_today()},
        ], primary_action_label: __('Review attendance'), async primary_action(values) {
            if (opening) return;
            opening = true;
            dialog.get_primary_btn().prop('disabled', true);
            try {
                const saved = await frappe.db.get_list('PP Daily Register', {filters: {site: values.site, work_date: values.work_date},
                    fields: ['name', 'docstatus'], limit: 1});
                let name = saved[0]?.name;
                if (!name) {
                    const result = await frappe.call({method: 'plus_point.api.prepare_daily_register', type: 'POST',
                        args: values, freeze: true, freeze_message: __('Preparing an attendance draft…')});
                    name = result.message.name;
                }
                dialog.hide();
                await frappe.set_route('Form', 'PP Daily Register', name);
                frappe.show_alert({message: __(saved.length ? 'Opened your saved attendance register.' : 'Draft ready. Review workers before Submit.'), indicator: 'blue'});
            } catch {
                // Native calls display permission/validation details. Keep selections for retry.
                frappe.show_alert({message: __('Attendance was not opened. Review the message and try again.'), indicator: 'red'});
            } finally {
                opening = false;
                dialog.get_primary_btn().prop('disabled', false);
            }
        }});
        dialog.show();
        frappe.db.get_list('PP Site', {filters: {is_active: 1}, fields: ['name'], limit: 2})
            .then(sites => { if (sites.length === 1 && !dialog.get_value('site')) dialog.set_value('site', sites[0].name); })
            .catch(() => { /* The native Link picker remains available. */ });
    }

    function taskHome() {
        return `<div class="pp-task-home">
            <div class="pp-task-heading"><div><h2>${esc(__('Workforce overview'))}</h2><p>${esc(__('What would you like to do?'))}</p></div>
                <button type="button" class="btn btn-default pp-start-tour">${esc(__('Show me around'))}</button></div>
            <div class="pp-daily-focus"><div><span class="pp-task-date">${esc(frappe.datetime.str_to_user(frappe.datetime.get_today()))}</span>
                <h3>${esc(__('Start with attendance'))}</h3><p>${esc(__('Choose a site, review workers, and record a full day, half-day or absence.'))}</p></div>
                <button type="button" class="btn btn-primary pp-mark-attendance" ${frappe.model.can_create('PP Daily Register') ? '' : 'disabled'}>${esc(__('Mark attendance'))}</button></div>
            <div class="pp-task-rows">
                <div class="pp-task-row"><div><h3>${esc(__('Workers and work sites'))}</h3><p>${esc(__('Add workers and assign them to the right site.'))}</p></div>
                    <div class="pp-task-links">${link(['Employee', 'Workers'])}${link(['PP Site', 'Work sites'])}${link(['PP Assignment', 'Assign workers'])}</div></div>
                <div class="pp-task-row"><div><h3>${esc(__('Client billing'))}</h3><p>${esc(__('Set the agreement, prepare an invoice and record client receipts.'))}</p></div>
                    <div class="pp-task-links">${link(['PP Contract Terms', 'Billing terms'])}${link(['Sales Invoice', 'Invoices'])}</div></div>
                <div class="pp-task-row"><div><h3>${esc(__('Worker payments'))}</h3><p>${esc(__('Keep wages earned separate from money actually paid.'))}</p></div>
                    <div class="pp-task-links">${link(['PP Wage Settlement', 'Record payment'])}${link(['PP Work Entry', 'Wages earned'])}</div></div>
                ${frappe.user.has_role('System Manager') ? `<div class="pp-task-row"><div><h3>${esc(__('Business reports'))}</h3><p>${esc(__('Review project results, deployment and each worker’s history.'))}</p></div>
                    <div class="pp-task-links"><a href="/desk/query-report/PLUS%20POINT%20Project%20Finances">${esc(__('Project finances'))}</a>
                    <a href="/desk/query-report/PLUS%20POINT%20Worker%20Statement">${esc(__('Worker statement'))}</a></div></div>` : ''}
            </div></div>`;
    }

    function tip(element, text) {
        const $element = $(element);
        if ($element.attr('data-pp-tip') === text) return;
        if ($element.data('bs.tooltip')) $element.tooltip('dispose');
        $element.attr({'data-pp-tip': text, 'title': text, 'aria-description': text});
        $element.tooltip({title: text, trigger: 'hover focus', container: 'body', html: false,
            template: '<div class="tooltip pp-tooltip" role="tooltip"><div class="arrow"></div><div class="tooltip-inner"></div></div>'});
    }

    function workflow() {
        return `<ol class="pp-workflow">${steps.map((step, index) => `
            <li class="pp-workflow-step" data-pp-step="${index}">
                <h3>${esc(__(step.title))}</h3><p>${esc(__(step.text))}</p>
                <div class="pp-workflow-links">${step.links.map(link).join('')}</div>
            </li>`).join('')}</ol>`;
    }

    function appMap() {
        return `<dl class="pp-app-map">${Object.entries(appHelp).map(([name, text]) =>
            `<div><dt>${esc(__(name))}</dt><dd>${esc(__(text))}</dd></div>`).join('')}</dl>`;
    }

    function showGuide() {
        const dialog = new frappe.ui.Dialog({title: __('How PLUS POINT works'), size: 'large',
            fields: [{fieldname: 'guide', fieldtype: 'HTML', options: `<div class="pp-guide-dialog">
                <h2>${esc(__('Which app should I use?'))}</h2>${appMap()}
                <h2>${esc(__('Follow a job from contract to payment'))}</h2>${workflow()}
                <p class="pp-guide-note">${esc(__('PLUS POINT daily registers calculate contractor wages and billing. They do not automatically create HR Attendance or run HR payroll. Earned, invoiced and paid amounts are tracked separately.'))}</p>
            </div>`}], primary_action_label: __('Got it'), primary_action() { dialog.hide(); }});
        dialog.$wrapper.on('click', '.pp-guide-link', () => dialog.hide());
        dialog.show();
    }

    function tour(items) {
        const trigger = document.activeElement;
        if (driver) driver.reset();
        driver = new frappe.Driver({className: 'frappe-driver', allowClose: true, keyboardControl: true,
            opacity: 0.25, padding: 8, nextBtnText: __('Next'), prevBtnText: __('Back'),
            doneBtnText: __('Finish'), closeBtnText: __('Close'),
            onHighlighted() {
                const popover = document.getElementById('driver-popover-item');
                if (!popover) return;
                popover.setAttribute('role', 'dialog');
                const title = popover.querySelector('.driver-popover-title');
                const description = popover.querySelector('.driver-popover-description');
                if (title) { title.id = 'pp-tour-title'; popover.setAttribute('aria-labelledby', title.id); }
                if (description) { description.id = 'pp-tour-description'; popover.setAttribute('aria-describedby', description.id); }
                popover.querySelector('.driver-next-btn')?.focus({preventScroll: true});
            },
            onReset() { if (trigger?.isConnected && $(trigger).is(':visible')) trigger.focus({preventScroll: true}); },
        });
        driver.defineSteps(items.map(item => ({...item,
            popover: {...item.popover, title: esc(item.popover.title), description: esc(item.popover.description)},
        })));
        // Driver listens on document clicks. Start after this button's click has
        // finished bubbling, otherwise allowClose immediately dismisses the tour.
        const pending = driver;
        setTimeout(() => { if (driver === pending) pending.start(); }, 0);
    }

    function homeTour(root) {
        const details = root.querySelector('.pp-quick-start');
        details.open = true;
        tour(steps.map((step, index) => ({element: root.querySelector(`[data-pp-step="${index}"]`),
            popover: {title: __(step.title), description: __(step.text), position: 'bottom'}})));
    }

    function formGuide(frm) {
        const [title, purpose, fields] = screens[frm.doctype];
        const described = fields.map(name => frm.get_field(name)).filter(field => field?.df.description);
        const dialog = new frappe.ui.Dialog({title: __(title), fields: [{fieldtype: 'HTML', fieldname: 'explanation',
            options: `<p>${esc(__(purpose))}</p><dl class="pp-form-explanation">${described.map(field =>
                `<div><dt>${esc(__(field.df.label))}</dt><dd>${esc(__(field.df.description))}</dd></div>`).join('')}</dl>`}],
            primary_action_label: described.length ? __('Show field tips') : __('Got it'), primary_action() {
                dialog.hide();
                if (!described.length) return;
                const items = described.filter(field => $(field.wrapper).is(':visible')).map(field => ({
                    element: $(field.wrapper).get(0), popover: {title: __(field.df.label), description: __(field.df.description), position: 'bottom'},
                }));
                if (items.length) setTimeout(() => tour(items), 200);
            }});
        dialog.show();
    }

    function addFieldTips(frm) {
        if (!screens[frm.doctype] || !frm.doctype.startsWith('PP ')) return;
        Object.values(frm.fields_dict).forEach(field => {
            if (!field.df.description || !field.$wrapper?.is(':visible')) return;
            const label = field.$wrapper.find('.control-label').first();
            if (!label.length || label.find('.pp-field-tip').length) return;
            const button = $('<button type="button" class="pp-field-tip">?</button>')
                .attr('aria-label', __('Help: {0}', [field.df.label])).appendTo(label);
            tip(button, __(field.df.description));
            button.on('click', event => { event.preventDefault(); event.stopPropagation(); button.tooltip('show'); });
            button.on('keydown', event => { if (event.key === 'Escape') button.tooltip('hide'); });
            if (!platform()) {
                field.$wrapper.find('.help-box').filter((_index, node) => node.textContent.trim() === field.df.description.trim())
                    .addClass('pp-supplementary-help');
            }
        });
    }

    function formRefreshed(frm) {
        if (!screens[frm.doctype]) return;
        frm.add_custom_button(__('Explain this screen'), () => formGuide(frm));
        if (!platform() && !frm.is_new() && frappe.user.has_role('System Manager')) {
            if (frm.doctype === 'Employee') frm.add_custom_button(__('Worker statement'), () =>
                frappe.set_route('query-report', 'PLUS POINT Worker Statement', {employee: frm.doc.name, company: frm.doc.company}));
            if (frm.doctype === 'Project') frm.add_custom_button(__('Project finances'), () =>
                frappe.set_route('query-report', 'PLUS POINT Project Finances', {project: frm.doc.name, company: frm.doc.company}));
        }
        schedule();
    }

    function context(route) {
        if (platform()) return __('High4Tech · Manage subscriber organizations, subscriptions and access limits here.');
        if (route[0] === 'query-report' && route[1] === 'PLUS POINT Project Finances')
            return __('Project results and workforce deployment. Choose a client or project to narrow the report.');
        if (route[0] === 'query-report' && route[1] === 'PLUS POINT Worker Statement')
            return __('Worker earnings, payments and assignment history. Dates filter this statement’s activity.');
        if (route[0] === 'Form' || route[0] === 'List') {
            return shortPurpose[route[1]] ? __(shortPurpose[route[1]]) : screens[route[1]] ? __(screens[route[1]][1]) : __('Additional ERP tools. Your contractor workflow starts in PLUS POINT.');
        }
        if (route[0] === 'Workspaces' && route[1] === 'PLUS POINT') return __('Your workspace for labour contracts, daily attendance, wages and client billing.');
        if (route[0] === 'Workspaces' && route[1] === 'Manufacturing') return __('Manufacturing is an optional ERPNext module for production and factories. Use PLUS POINT for labour contracting.');
        if (route[0] === 'Workspaces' && /hr|employee|payroll|leave/i.test(route[1] || '')) return __('HR manages employee records, leave and payroll. Record contractor dehadi and client billing in PLUS POINT.');
        return __('ERPNext and HR provide shared business tools. Start in PLUS POINT for the contractor workflow.');
    }

    function render() {
        const route = frappe.get_route();
        const active = frappe.container?.page;
        if (!active || !$(active).is(':visible')) return;
        const main = active.querySelector('.layout-main-section');
        if (!main) return;
        active.classList.toggle('pp-customer-screen', !platform());
        if (!platform() && route[0] === 'List' && customerLists[route[1]]) {
            const [title, action] = customerLists[route[1]];
            const page = active.page;
            if (page?.title !== __(title)) page?.set_title(__(title));
            const listview = frappe.get_list_view(route[1]);
            if (listview?.can_create && page?.btn_primary?.is(':visible') && page.btn_primary.attr('data-label') !== __(action)) {
                page.set_primary_action({label: __(action), short_label: __('Add')}, () => listview.make_new_doc(), 'plus');
            }
        }
        let bar = main.querySelector(':scope > .pp-context-bar');
        if (!bar) {
            bar = document.createElement('aside'); bar.className = 'pp-context-bar';
            bar.setAttribute('aria-label', __('PLUS POINT guidance')); main.prepend(bar);
        }
        const routeKey = JSON.stringify(route);
        if (bar.dataset.route !== routeKey) {
            bar.dataset.route = routeKey;
            bar.innerHTML = `<span class="pp-context-copy">${esc(context(route))}</span>
                <div class="pp-context-actions"><a class="pp-home-link" href="${home()}">${esc(__(platform() ? 'Platform home' : 'Workforce home'))}</a>
                <button type="button" class="btn btn-default btn-sm pp-open-guide">${esc(__('How it works'))}</button></div>`;
            bar.querySelector('.pp-open-guide').addEventListener('click', showGuide);
        }
        const isHome = !platform() && route[0] === 'Workspaces' && route[1] === 'PLUS POINT';
        bar.classList.toggle('pp-home-context', isHome);
        let welcome = main.querySelector(':scope > .pp-welcome');
        if (isHome && !welcome) {
            welcome = document.createElement('section'); welcome.className = 'pp-welcome';
            welcome.setAttribute('aria-label', __('Getting started with PLUS POINT'));
            welcome.innerHTML = `${taskHome()}
                <details class="pp-quick-start" ${expanded() ? 'open' : ''}><summary>${esc(__('Quick start: six steps from contract to payment'))}</summary>
                ${workflow()}<p class="pp-guide-note">${esc(__('Use PLUS POINT for contractor attendance and dehadi. HR Attendance and payroll are separate workflows. Recording earnings does not record a payment.'))}</p></details>`;
            bar.after(welcome);
            welcome.querySelector('.pp-start-tour').addEventListener('click', () => homeTour(welcome));
            welcome.querySelector('.pp-mark-attendance').addEventListener('click', attendancePicker);
            welcome.querySelector('details').addEventListener('toggle', event => {
                try { localStorage.setItem(key(), event.target.open ? 'expanded' : 'collapsed'); } catch { /* Storage is optional. */ }
            });
        } else if (!isHome && welcome) welcome.remove();
        // Keep native records available without making thirteen setup links the home screen.
        let allRecords = main.querySelector('.pp-all-records');
        const editor = main.querySelector('.editor-js-container');
        if (isHome && editor && !allRecords) {
            allRecords = document.createElement('details'); allRecords.className = 'pp-all-records';
            allRecords.innerHTML = `<summary>${esc(__('More tools and setup'))}</summary>`;
            editor.before(allRecords); allRecords.append(editor);
        } else if (!isHome && allRecords) {
            if (editor) allRecords.before(editor);
            allRecords.remove();
        }
        if (isHome) main.querySelectorAll('a').forEach(anchor => {
            const text = workspaceHelp[anchor.textContent.trim()];
            if (text) tip(anchor, __(text));
        });
        active.querySelectorAll('.desktop-icon').forEach(icon => {
            const title = icon.querySelector('.icon-title');
            const text = appHelp[title?.textContent.trim()];
            if (!text) return;
            tip(title, __(text));
            if (!icon.querySelector('.pp-app-purpose')) {
                const description = document.createElement('p'); description.className = 'pp-app-purpose';
                description.textContent = __(appSummary[title.textContent.trim()]); icon.append(description);
            }
        });
        document.querySelectorAll('.body-sidebar a').forEach(anchor => {
            const screen = screens[anchor.textContent.trim()];
            if (screen) tip(anchor, `${__(screen[0])}: ${__(screen[1])}`);
        });
        if (route[0] === 'Form' && window.cur_frm?.doctype === route[1]) addFieldTips(cur_frm);
    }

    function schedule() {
        if (queued) return;
        queued = true;
        requestAnimationFrame(() => { queued = false; render(); });
    }

    function start() {
        if (started) return;
        started = true;
        frappe.provide('frappe.listview_settings');
        if (!platform()) Object.keys(customerLists).forEach(doctype => {
            frappe.listview_settings[doctype] = {...frappe.listview_settings[doctype], hide_name_column: true, hide_name_filter: true};
        });
        frappe.router.on('change', () => {
            if (driver) { driver.reset(); driver = null; }
            $('.pp-field-tip, [data-pp-tip]').tooltip('hide');
            schedule();
        });
        $(document).on('form-refresh.pp-onboarding', (_event, frm) => formRefreshed(frm));
        new MutationObserver(schedule).observe(document.getElementById('body') || document.body, {childList: true, subtree: true});
        schedule();
    }
    $(document).on('app_ready.pp-onboarding', start);
    if (frappe.app?.sidebar) start();
})();
