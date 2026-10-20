/* Task shortcuts and guidance layered onto native, permission-checked Desk. */
(() => {
    const appHelp = {
        'PLUS POINT': 'Start here for event sites, crew plans, vehicles, equipment, daily attendance and client billing.',
        'ERPNext': 'Client records, projects, invoices, receipts and accounting. Other ERP modules are optional.',
        'Frappe HR': 'Employee records, leave, shifts and payroll. Contractor dehadi is recorded in PLUS POINT.',
        'Framework': 'User accounts, permissions and system configuration. Mainly for administrators.',
        'High4Tech admin': 'A separate platform site for subscriber organizations, plans, trials and access limits. It does not share the customer’s workforce database.',
    };
    const appSummary = {
        'PLUS POINT': 'Events, crew and billing', 'ERPNext': 'Clients and accounting',
        'Frappe HR': 'Employee HR and payroll', 'Framework': 'Users and settings',
        'High4Tech admin': 'Subscribers and billing',
    };
    const productSides = {
        'PLUS POINT': 'For each customer business: manage its clients, event plans, crew, vehicles, equipment, attendance, wages and invoices.',
        'High4Tech admin': 'For High4Tech: manage customer businesses, subscription plans, trials, billing and access. This is a separate site, not an extra app for the customer to use.',
    };
    const steps = [
        {title: 'Set up the client and event', text: 'Your Company is your own business. A Client company is the customer paying you. Link its agreement and project before assigning workers.',
            links: [['Company', 'Your company'], ['Customer', 'Client companies'], ['Contract', 'Client contracts'], ['Project', 'Projects']]},
        {title: 'Agree how the client will be billed', text: 'Daily billing uses approved worker-days × client rate. Fixed billing uses approved milestones; workers still earn their daily wages.',
            links: [['PP Contract Terms', 'Billing terms'], ['PP Milestone', 'Fixed milestones']]},
        {title: 'Choose where each worker will work', text: 'Plan venue phases and workers per day in an Event plan. Preview availability, allocate crew, then reserve vehicles and warehouse equipment.',
            links: [['PP Site', 'Event sites'], ['Employee', 'Workers'], ['PP Assignment', 'Worker allocations']]},
        {title: 'Record daily attendance and dehadi', text: 'Choose Mark attendance on Event operations, then select a work site and date. Review each worker: 1 = full day, 0.5 = half day, 0 = absent. Submit the register to approve earnings.',
            links: [['PP Daily Register', 'Daily attendance'], ['PP Work Entry', 'Worker earnings']]},
        {title: 'Invoice the client and record receipts', text: 'Open active Billing terms and choose Prepare client invoice. Review and submit the invoice, then record the client payment as a receipt.',
            links: [['PP Contract Terms', 'Prepare an invoice'], ['Sales Invoice', 'Client invoices'], ['Payment Entry', 'Receipts and payments']]},
        {title: 'Pay workers and review the project', text: 'Record a submitted payment to the employee, then link it in Worker payments. Open Billing terms → Project finances to compare earnings, receipts, wages and outstanding balances.',
            links: [['PP Wage Settlement', 'Worker payments'], ['PP Contract Terms', 'Project finances']]},
    ];
    const screens = {
        'PP Event Plan':['Event plan','Set the inclusive event dates, venue phases and daily worker requirements. Preview available crew before allocation. Plans create no approved attendance, wages or invoices.',['project','contract_terms','start_date','end_date','staffing']],
        'PP Vehicle Booking':['Vehicle assignment','Reserve one vehicle for a venue and date range, for crew OR an inventory load. Crew seats exclude the driver. Inventory uses the vehicle’s load unit; individual equipment is not linked to cars.',['vehicle','site','purpose','start_date','end_date','crew_count','cargo_load']],
        'PP Equipment Booking':['Event equipment','Reserve warehouse equipment for event dates. Stock is counted in the item’s own unit. Reservations do not move stock, consume it or invoice a client.',['item','warehouse','site','quantity','start_date','end_date']],
        'Vehicle':['Event vehicles','Company vehicles with crew passenger seats and an inventory load capacity. Future event bookings prevent conflicting use or unsafe capacity reductions.',[]],
        'Item':['Equipment and billing catalog','Stock items represent reusable event equipment; non-stock services are used for client billing. A catalog item alone does not add warehouse quantities.',[]],
        'Warehouse':['Warehouses','Physical storage locations for the event company. Import counted balances to establish quantities, then reserve equipment for event dates.',[]],
        'Stock Reconciliation':['Warehouse balances','A reviewed absolute stock count with a value per unit. Submitting updates native stock and stock book value. This is not a receipt, payment or inventory-to-car manifest.',[]],
        'PP Site': ['Event sites', 'A venue, hall, stage or setup area within a client event. Prepare daily attendance after workers have active allocations.', ['site_name', 'project', 'parent_site']],
        'PP Assignment': ['Worker allocations', 'Choose available workers together for a site, billing agreement and date range. These agreed rates are copied into work records so later rate changes cannot rewrite past earnings.', ['employee', 'contract_terms', 'site', 'start_date', 'wage_rate', 'client_rate']],
        'PP Contract Terms': ['Billing terms', 'Choose daily worker-day billing or a fixed contract amount. Prepare client invoices and review Project finances from this screen.', ['contract', 'project', 'billing_model', 'fixed_amount', 'status']],
        'PP Daily Register': ['Daily attendance', 'One register records a site and date. Saving keeps a draft; Submit creates approved work entries and earnings for the listed workers. Review before submitting.', ['work_date', 'site', 'entries']],
        'PP Work Entry': ['Worker earnings', 'A worker-day and its locked wage and client billing amounts. Earnings are not proof of payment. Prefer the site attendance register for bulk daily entry.', ['assignment', 'units', 'status', 'wage_amount', 'billable_amount']],
        'PP Milestone': ['Fixed contract milestones', 'A completed portion of a fixed-price agreement. Approved milestones earn client revenue; daily worker wages are calculated separately.', ['contract_terms', 'amount', 'status']],
        'PP Wage Settlement': ['Worker payments', 'Link a real, submitted employee Payment Entry to approved wages. Saving is a draft; Submit allocates the payment. This does not create a bank payment or payroll run.', ['employee', 'project', 'payment_entry', 'amount']],
        'Customer': ['Clients', 'The organization or person hiring your event company. This is different from your own Company record.', []],
        'Company': ['Your company', 'Your own legal business and accounting records. Organizations that hire you belong under Client companies instead.', []],
        'Contract': ['Client contracts', 'The client agreement. Add PLUS POINT Billing terms to select daily or fixed billing for its project.', []],
        'Project': ['Event projects', 'The client event. Plan setup, event and pack-down phases across venues, then review daily staffing, transport and equipment.', []],
        'Employee': ['Workers', 'A crew member’s contact and employment record. Assign this person to event venues for daily work. This does not create a software login.', []],
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
        'Customer':['Clients','Add client'],
        'PP Site': ['Event sites', 'Add event site'],
        'PP Event Plan':['Event plans','Plan an event'], 'Project':['Event projects','Plan an event'],
        'Vehicle':['Event vehicles','Add vehicle'],'Item':['Inventory items','Add inventory item'],
        'Warehouse':['Warehouses','Add warehouse'],'Stock Reconciliation':['Warehouse balances','Update warehouse balances'],
        'PP Vehicle Booking':['Vehicle assignments','Assign vehicle'],'PP Equipment Booking':['Event equipment','Reserve equipment'],
        'PP Assignment': ['Worker assignments', 'Assign workers'],
        'PP Contract Terms': ['Client billing', 'Add billing terms'],
        'PP Daily Register': ['Daily attendance', 'Add attendance'],
        'PP Work Entry': ['Wages earned', 'Add work entry'],
        'PP Milestone': ['Fixed contract milestones', 'Add milestone'],
        'PP Wage Settlement': ['Worker payments', 'Record payment'],
    };
    const platformLists = {
        'PP Signup Request':['Signup approvals','Review signup'],
        'PP Tenant':['PLUS POINT customers','Add customer'], 'PP Support Request':['Customer support','New support request'],
        'Subscription Plan':['Pricing plans','Add pricing plan'], 'Subscription':['Subscriptions','Add subscription'],
        'Sales Invoice':['Software invoices','Create invoice'], 'Payment Entry':['Receipts and payments','Record payment'],
        'Purchase Invoice':['Business expenses','Record expense'], 'Customer':['Billing contacts','Add billing contact'],
    };
    const listImports = {
        Customer:'clients','PP Site':'event_sites','PP Event Plan':'events',Project:'events',Vehicle:'vehicles',Item:'inventory_items',Warehouse:'warehouses','Stock Reconciliation':'stock_balances',
        Employee:'employees', 'PP Work Entry':'work', 'PP Milestone':'milestones',
        'Purchase Invoice':'expenses', 'Sales Invoice':'invoices',
        'Payment Entry':'receipts', 'PP Wage Settlement':'worker_payments',
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
    let started = false, queued = false, redirecting = false, driver;
    const esc = value => frappe.utils.escape_html(String(value));
    const platform = () => !!frappe.boot.plus_point?.is_platform;
    const home = () => frappe.boot.plus_point?.home || '/desk/plus-point';
    const link = ([doctype, label]) => frappe.model.can_read(doctype)
        ? `<a class="pp-guide-link" href="/desk/${frappe.router.slug(doctype)}">${esc(__(label))}</a>` : '';

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
            <div class="pp-task-heading"><div><h2>${esc(__('Event operations'))}</h2><p>${esc(__('Event timelines, crew, equipment, transport and finances in one view.'))}</p></div></div>
            <section class="pp-setup-banner" aria-label="${esc(__('Business setup and imports'))}"></section>
            <section class="pp-dashboard" aria-label="${esc(__('Business dashboard'))}"></section>
            <h3 class="pp-tools-heading">${esc(__('Work tools'))}</h3>
            <div class="pp-daily-focus"><div><span class="pp-task-date">${esc(frappe.datetime.str_to_user(frappe.datetime.get_today()))}</span>
                <h3>${esc(__('Start with attendance'))}</h3><p>${esc(__('Choose a site, review workers, and record a full day, half-day or absence.'))}</p></div>
                <button type="button" class="btn btn-primary pp-mark-attendance" ${frappe.model.can_create('PP Daily Register') ? '' : 'disabled'}>${esc(__('Mark attendance'))}</button></div>
            <div class="pp-task-rows">
                <div class="pp-task-row"><div><h3>${esc(__('Event plans and crew'))}</h3><p>${esc(__('Plan each venue day, then assign available workers.'))}</p></div>
                    <div class="pp-task-links">${link(['PP Event Plan', 'Event plans'])}${link(['Employee', 'Workers'])}${link(['PP Site', 'Event sites'])}${link(['PP Assignment', 'Assign workers'])}</div></div>
                <div class="pp-task-row"><div><h3>${esc(__('Inventory and transport'))}</h3><p>${esc(__('Check warehouse availability and reserve vehicles or equipment for an event.'))}</p></div><div class="pp-task-links"><a href="/desk/pp-inventory">${esc(__('Warehouse availability'))}</a>${link(['Vehicle','Vehicles'])}${link(['PP Vehicle Booking','Vehicle assignments'])}</div></div>
                <div class="pp-task-row"><div><h3>${esc(__('Client billing'))}</h3><p>${esc(__('Set the agreement, prepare an invoice and record client receipts.'))}</p></div>
                    <div class="pp-task-links">${link(['PP Contract Terms', 'Billing terms'])}${link(['Sales Invoice', 'Invoices'])}</div></div>
                <div class="pp-task-row"><div><h3>${esc(__('Worker payments'))}</h3><p>${esc(__('Keep wages earned separate from money actually paid.'))}</p></div>
                    <div class="pp-task-links">${link(['PP Wage Settlement', 'Record payment'])}${link(['PP Work Entry', 'Wages earned'])}</div></div>
                ${frappe.user.has_role('System Manager') ? `<div class="pp-task-row"><div><h3>${esc(__('Business reports'))}</h3><p>${esc(__('Review project results, deployment and each worker’s history.'))}</p></div>
                    <div class="pp-task-links"><a href="/desk/query-report/PLUS%20POINT%20Project%20Finances">${esc(__('Project finances'))}</a>
                    <a href="/desk/query-report/PLUS%20POINT%20Worker%20Statement">${esc(__('Worker statement'))}</a></div></div>` : ''}
            </div></div>`;
    }

    function platformHome() {
        return `<div class="pp-task-home"><div class="pp-task-heading"><div><h2>${esc(__('PLUS POINT customers'))}</h2>
            <p>${esc(__('Run your software business: customers, pricing, support and sales finances.'))}</p></div></div>
            <section class="pp-dashboard" aria-label="${esc(__('Software business dashboard'))}"></section>
            <h3 class="pp-tools-heading">${esc(__('Your tools'))}</h3>
            <div class="pp-task-rows">
            ${[
                ['Customer accounts', 'Review new signups and manage subscribers, subscriptions and owner logins.', [['PP Signup Request', 'Signup approvals'], ['PP Tenant', 'Customers'], ['PP Support Request', 'Customer support']]],
                ['Pricing and subscriptions', 'Set monthly prices, trials and customer access.', [['Subscription Plan', 'Pricing plans'], ['Subscription', 'Subscriptions']]],
                ['Software sales', 'Invoice customers for the software and record payments received.', [['Sales Invoice', 'Software invoices'], ['Payment Entry', 'Receipts and payments']]],
                ['Your business finances', 'Record your expenses and review software-business results.', [['Purchase Invoice', 'Business expenses'], ['Company', 'High4Tech company']]],
            ].map(([title, text, links]) => `<div class="pp-task-row"><div><h3>${esc(__(title))}</h3><p>${esc(__(text))}</p></div>
                <div class="pp-task-links">${links.map(link).join('')}</div></div>`).join('')}
            </div><div class="pp-task-links"><a class="pp-guide-link" href="/desk/query-report/Profit%20and%20Loss%20Statement">${esc(__('Financial results'))}</a>
            <a class="pp-guide-link" href="/desk/query-report/Accounts%20Receivable">${esc(__('Outstanding invoices'))}</a></div></div>`;
    }

    function supportRequest(frm, operation) {
        const create = async values => {
            const result = await frappe.call({method:'plus_point.support.request_account_help', type:'POST',
                args:{tenant:frm.doc.name, operation, new_username:values?.new_username || ''}, freeze:true,
                freeze_message:__('Queuing customer support…')});
            frappe.show_alert({message:__('Support request queued.'),indicator:'blue'});
            frappe.set_route('Form','PP Support Request',result.message.name);
        };
        if (operation === 'Change login ID') frappe.prompt([{fieldname:'new_username',fieldtype:'Data',
            label:__('New customer login ID'), reqd:1, description:__('The customer email address stays the same.')}], create, __('Change customer login ID'));
        else frappe.confirm(__('Create a password-reset link for {0}? Existing customer login sessions will be signed out. No email is sent automatically.',[frm.doc.owner_email]), () => create());
    }

    function showSupportResult(frm) {
        frappe.call({method:'plus_point.support.account_help_result', args:{request_name:frm.doc.name}, callback:r => {
            const result=r.message;
            const linkUrl=result.reset_link;
            if (linkUrl) {
                const parsed=new URL(linkUrl);
                if (!['http:','https:'].includes(parsed.protocol)) return;
            }
            frappe.msgprint({title:__('Customer support'), message:`<p>${esc(__(result.message || result.status))}</p>
                ${linkUrl ? `<p><a href="${esc(linkUrl)}" target="_blank" rel="noopener noreferrer">${esc(__('Open customer password reset'))}</a></p>
                <p>${esc(__('One-time reset link. Native password-reset expiry applies. It is displayed here for up to 20 minutes; no email was sent.'))}</p>` : ''}`});
        }});
    }

    function inProductScope(route) {
        const scope=frappe.boot.plus_point?.navigation;
        if (!scope) return true;
        if (['Form','List','Tree'].includes(route[0])) return scope.doctypes.includes(route[1]) ||
            (route[0] === 'Form' && route[1] === 'User' && route[2] === frappe.session.user);
        if (route[0] === 'query-report') return scope.reports.includes(route[1]);
        if (route[0] === 'Workspaces') return route[1] === scope.workspace;
        if ((scope.pages||[]).includes(route[0])) return true;
        if (route[0] === 'print') return scope.doctypes.includes(route[1]);
        return false;
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
        return `<dl class="pp-app-map">${Object.entries(productSides).map(([name, text]) =>
            `<div><dt>${esc(__(name))}</dt><dd>${esc(__(text))}</dd></div>`).join('')}</dl>`;
    }

    function showGuide() {
        const platformGuide = `<h2>${esc(__('Manage the PLUS POINT service'))}</h2><ol class="pp-workflow">
            <li class="pp-workflow-step"><h3>${esc(__('Add a customer business'))}</h3><p>${esc(__('Create its customer organization and owner account. Each business gets its own separate site and workforce records.'))}</p></li>
            <li class="pp-workflow-step"><h3>${esc(__('Choose its subscription'))}</h3><p>${esc(__('Select a monthly plan or trial, set the period and agree worker, user and work-site limits.'))}</p></li>
            <li class="pp-workflow-step"><h3>${esc(__('Manage billing and access'))}</h3><p>${esc(__('Review subscription invoices and received payments. Renew, suspend or reactivate the customer organization as needed. Access updates normally apply within one minute.'))}</p></li>
            <li class="pp-workflow-step"><h3>${esc(__('Help a customer sign in'))}</h3><p>${esc(__('Open the customer account to change its login ID or create a one-time password-reset link. Old passwords are never displayed. Reactivate a suspended subscription before the customer completes the native password-reset form. No email is sent automatically.'))}</p></li>
        </ol>`;
        const dialog = new frappe.ui.Dialog({title: __(platform() ? 'How High4Tech admin works' : 'How PLUS POINT works'), size: 'large',
            fields: [{fieldname: 'guide', fieldtype: 'HTML', options: `<div class="pp-guide-dialog">
                <h2>${esc(__('Two sides of PLUS POINT'))}</h2>${appMap()}
                ${platform() ? platformGuide : `${frappe.user.has_role('System Manager')?`<p><button type="button" class="btn btn-default pp-help-setup">${esc(__('Guided setup'))}</button></p>`:''}<h2>${esc(__('Follow a job from contract to payment'))}</h2>${workflow()}`}
                <p class="pp-guide-note">${esc(__(platform()
                    ? 'Use this site to run the service. Customer businesses manage their labour operations inside their own PLUS POINT workspace.'
                    : 'ERPNext and HRMS power the shared accounting and employee tools inside PLUS POINT. You do not need to switch between separate apps. Contractor dehadi and standard HR payroll remain separate workflows.'))}</p>
            </div>`}], primary_action_label: __('Got it'), primary_action() { dialog.hide(); }});
        dialog.$wrapper.on('click', '.pp-guide-link', () => dialog.hide());
        dialog.$wrapper.on('click', '.pp-help-setup', () => {
            dialog.$wrapper.one('hidden.bs.modal',()=>plus_point.open_setup());
            dialog.hide();
        });
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

    function formGuide(frm) {
        if(!screens[frm.doctype]){showGuide();return;}
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
        if (platform() && !frm.is_new()) {
            if (frm.doctype === 'PP Tenant') {
                frm.add_custom_button(__('Reset customer password'), () => supportRequest(frm,'Reset password'));
                frm.add_custom_button(__('Change customer login ID'), () => supportRequest(frm,'Change login ID'));
            }
            if (frm.doctype === 'PP Support Request') frm.add_custom_button(__('View support result'), () => showSupportResult(frm));
        }
        if (!screens[frm.doctype]) return;
        if (!platform() && !frm.is_new() && frappe.user.has_role('System Manager')) {
            if (frm.doctype === 'Employee') frm.add_custom_button(__('Worker statement'), () =>
                frappe.set_route('query-report', 'PLUS POINT Worker Statement', {employee: frm.doc.name, company: frm.doc.company}));
            if (frm.doctype === 'Project') frm.add_custom_button(__('Project finances'), () =>
                frappe.set_route('query-report', 'PLUS POINT Project Finances', {project: frm.doc.name, company: frm.doc.company}));
        }
        schedule();
    }

    function context(route) {
        if (platform()) return __('High4Tech · PLUS POINT customers, pricing, account support and software-business finances.');
        if (route[0] === 'desktop') return __('Open PLUS POINT to manage your business. High4Tech administration is on a separate site.');
        if (route[0] === 'query-report' && route[1] === 'PLUS POINT Project Finances')
            return __('Project results and workforce deployment. Choose a client or project to narrow the report.');
        if (route[0] === 'query-report' && route[1] === 'PLUS POINT Worker Statement')
            return __('Worker earnings, payments and assignment history. Dates filter this statement’s activity.');
        if (route[0] === 'Form' || route[0] === 'List') {
            return shortPurpose[route[1]] ? __(shortPurpose[route[1]]) : screens[route[1]] ? __(screens[route[1]][1]) : __('Additional ERP tools. Your contractor workflow starts in PLUS POINT.');
        }
        if (route[0] === 'Workspaces' && route[1] === 'PLUS POINT') return __('Your workspace for labour contracts, daily attendance, wages and client billing.');
        return __('Your business tools are part of PLUS POINT. Use Workforce home to return to daily work.');
    }

    function render() {
        if (redirecting) return;
        const route = frappe.get_route();
        if (!Array.isArray(route) || !route.length) return;
        if(!platform()){
            const identity=frappe.boot.plus_point.company_identity;
            const title=plus_point.dashboard_company||identity?.title||__('Your event company');
            const footer=document.querySelector('.body-sidebar .dropdown-navbar-user');
            if(footer&&!footer.dataset.ppCompanyMenu){
                const clone=footer.cloneNode(true);clone.dataset.ppCompanyMenu='1';footer.replaceWith(clone);
                clone.querySelector('.sidebar-user-button')?.setAttribute('aria-label',__('Company menu'));
                new frappe.ui.Dropdown({trigger:$(clone),side:'top',align:'start',options:[{group:'',options:[
                    {name:'company',label:__('Your company'),onclick:()=>{const name=plus_point.dashboard_company||identity?.name;if(name)frappe.set_route('Form','Company',name);else plus_point.open_setup();}},
                    {name:'setup',label:__('Guided company setup'),onclick:()=>plus_point.open_setup()},
                    {name:'logout',label:__('Sign out'),onclick:()=>frappe.app.logout()}]}]});
            }
            const names=document.querySelectorAll('.sidebar-user-button .avatar-name-email span');
            if(names[0]&&names[0].textContent!==title)names[0].textContent=title;
            if(names[1]&&names[1].textContent!==__('Company account'))names[1].textContent=__('Company account');
            const avatar=document.querySelector('.sidebar-user-button>div:first-child');
            if(avatar&&!avatar.querySelector('.pp-company-avatar'))avatar.innerHTML=`<span class="pp-company-avatar" aria-hidden="true">${esc(title.split(/\s+/).slice(0,2).map(s=>s[0]).join(''))}</span>`;
        }
        if (!inProductScope(route)) {
            // Wait for the native departing route to settle before redirecting.
            // An immediate redirect can let Desktop's async show hide the home.
            redirecting = true;
            window.location.replace(home());
            return;
        }
        if(!platform()&&route[0]==='List'&&route[1]==='Company'){const name=frappe.boot.plus_point?.company_identity?.name;if(name)frappe.set_route('Form','Company',name);else plus_point.open_setup();return;}
        const active = frappe.container?.page;
        if (!active || !$(active).is(':visible')) return;
        // A route changes before the next native page finishes loading. Do not
        // inject the home into the departing Desktop or form during that gap.
        if (route[0] === 'Workspaces' && active.id !== 'page-Workspaces') return;
        const main = active.querySelector('.layout-main-section');
        if (!main) return;
        plus_point.enhance_sections?.();
        active.classList.toggle('pp-customer-screen', !platform());
        const serviceItems=!platform()&&route[0]==='List'&&route[1]==='Item'&&frappe.get_list_view('Item')?.get_filter_value('is_stock_item')==0;
        const listConfig = serviceItems?['Billing items','Add billing item']:(platform() ? platformLists : customerLists)[route[1]];
        if (route[0] === 'List' && listConfig) {
            const [title, action] = listConfig;
            const page = active.page;
            if (page?.title !== __(title)) page?.set_title(__(title));
            const listview = frappe.get_list_view(route[1]);
            if (listview?.can_create && page?.btn_primary?.is(':visible') && page.btn_primary.attr('data-label') !== __(action)) {
                page.set_primary_action({label: __(action), short_label: __('Add')}, () => listview.make_new_doc(), 'plus');
                // Native list refresh can replace the handler on the same button.
                page.btn_primary.removeAttr('data-pp-event-action');
            }
            const primary=(key,label,handler)=>{if(page?.btn_primary?.attr('data-pp-event-action')!==key){page.set_primary_action({label:__(label)},handler,'plus');page.btn_primary.attr('data-pp-event-action',key);}};
            if(!platform()&&['Project','PP Event Plan'].includes(route[1]))primary('plan','Plan an event',()=>plus_point.open_event_wizard());
            if(!platform()&&!serviceItems&&['Customer','Vehicle','Item','Warehouse'].includes(route[1]))primary('resource',action,()=>plus_point.open_resource({Customer:'clients',Vehicle:'vehicles',Item:'inventory_items',Warehouse:'warehouses'}[route[1]],()=>listview.refresh()));
            if(!platform()&&route[1]==='PP Assignment')primary('crew','Assign workers',()=>plus_point.assign_workers({},()=>listview.refresh()));
            if(serviceItems)page?.btn_primary?.removeAttr('data-pp-event-action');
            if(!platform()&&route[1]==='Stock Reconciliation')primary('balances','Update warehouse balances',()=>plus_point.open_import(plus_point.dashboard_company,()=>listview.refresh(),'stock_balances'));
        }
        if(route[0]==='List'&&!platform())plus_point.enhance_record_list?.(frappe.get_list_view(route[1]));
        if(serviceItems&&active.page?.btn_secondary?.hasClass('pp-list-import'))active.page.btn_secondary.addClass('hide');
        if(!platform()&&route[0]==='List'&&route[1]==='Employee'&&frappe.get_list_view('Employee')?.can_create&&!active.querySelector('.pp-open-assign-workers'))active.page?.add_inner_button(__('Assign workers'),()=>plus_point.assign_workers({},()=>frappe.get_list_view('Employee').refresh()))?.addClass('pp-open-assign-workers');
        if (route[0] === 'List' && !platform() && !serviceItems && listImports[route[1]] && frappe.user.has_role('System Manager')) {
            const listview = frappe.get_list_view(route[1]);
            const page = active.page;
            // Include populated/filtered lists, including native Employee, which
            // does not use the custom list-title configuration above.
            if (listview?.doctype === route[1] && listview.can_create && page === listview.page && page?.btn_secondary &&
                (!page.btn_secondary.hasClass('pp-list-import') || page.btn_secondary.hasClass('hide') || page.btn_secondary.attr('data-label')!==__('Import'))) {
                page.set_secondary_action({label:__('Import'),short_label:__('Import')},()=>{
                    const company = listview.get_filter_value?.('company');
                    return plus_point.open_import(typeof company==='string'?company:undefined,()=>listview.refresh(),listImports[listview.doctype]);
                },'upload');
                page.btn_secondary.addClass('pp-list-import');
            }
        }
        if(route[0]==='Tree'&&route[1]==='Warehouse'&&!platform()&&frappe.user.has_role('System Manager')){
            const page=active.page;
            if(page?.btn_primary?.attr('data-pp-event-action')!=='warehouse'||page?.btn_primary?.attr('data-label')!==__('Add warehouse')){
                page?.set_primary_action({label:__('Add warehouse')},()=>plus_point.open_resource('warehouses',()=>frappe.views.trees.Warehouse?.tree?.refresh()),'plus');
                page?.btn_primary?.attr('data-pp-event-action','warehouse');
            }
            if(page?.btn_secondary&&!page.btn_secondary.hasClass('pp-list-import')){
                page.set_secondary_action({label:__('Import')},()=>plus_point.open_import(plus_point.dashboard_company,()=>frappe.views.trees.Warehouse?.tree?.refresh(),'warehouses'),'upload');
                page.btn_secondary.addClass('pp-list-import');
            }
        }
        main.querySelector(':scope > .pp-context-bar')?.remove();
        const actions=active.querySelector('.page-actions')||$('.page-head:visible .page-actions').get(0);
        if(actions&&!actions.querySelector('.pp-top-help')){
            const help=document.createElement('button');help.type='button';help.className='btn btn-default btn-sm pp-top-help';help.textContent=__('Help');
            help.onclick=()=>frappe.get_route()[0]==='Form'&&window.cur_frm?formGuide(cur_frm):showGuide();actions.prepend(help);
        }
        const isHome = route[0] === 'Workspaces' && route[1] === (platform() ? 'High4Tech' : 'PLUS POINT');
        let welcome = main.querySelector(':scope > .pp-welcome');
        if (isHome && !welcome) {
            welcome = document.createElement('section'); welcome.className = 'pp-welcome';
            welcome.setAttribute('aria-label', __('Getting started with PLUS POINT'));
            welcome.innerHTML = platform() ? platformHome() : taskHome();
            main.prepend(welcome);
            plus_point.mount_dashboard(welcome.querySelector('.pp-dashboard'));
            plus_point.mount_setup?.(welcome.querySelector('.pp-setup-banner'));
            welcome.querySelector('.pp-mark-attendance')?.addEventListener('click', attendancePicker);
        } else if (!isHome && welcome) welcome.remove();
        // Keep native records available without making thirteen setup links the home screen.
        const editor = main.querySelector('.editor-js-container');
        if (editor) editor.hidden = isHome;
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
        if (platform()) Object.assign(screens, {
            'Sales Invoice':['Software invoices','Bill a PLUS POINT customer for their software subscription. Record the receipt separately when paid.',[]],
            'Payment Entry':['Receipts and payments','Record software-customer receipts and High4Tech business payments. Submit to update your accounts.',[]],
            'Purchase Invoice':['Business expenses','Record the costs of running and selling PLUS POINT, using your High4Tech company accounts.',[]],
            'Customer':['Billing contacts','A business subscribing to PLUS POINT. Link its subscription and application address under Customer accounts.',[]],
            'Company':['High4Tech company','Your software-selling business and its accounting records.',[]],
            'User':['Your admin profile','Your High4Tech login. To help a customer sign in, open their Customer account instead.',[]],
            'PP Support Request':['Customer support','The background worker updates the registered customer owner login. View support result after completion. Password-reset links are available here for 20 minutes; native expiry also applies.', ['tenant','operation','new_username','status']],
            'PP Signup Request':['Signup approvals','Review simulated payments and approve a fresh company workspace. View Company login to provide its private password setup link. No payment is collected or email sent.',[]],
        });
        // Filter native command/search suggestions without changing backend roles
        // or the registries that native route resolution and forms depend on.
        const search = frappe.search?.utils;
        if (search) {
            for (const name of ['get_creatables','get_search_in_list','get_doctypes','get_reports',
                'get_pages','get_dashboards','get_recent_pages','get_frequent_links']) {
                const original = search[name];
                if (original) search[name] = function (...args) {
                    return original.apply(this,args).filter(option => option.route
                        ? inProductScope(option.route)
                        : option.type === 'New' && frappe.boot.plus_point.navigation.doctypes.includes(option.match));
                };
            }
            const workspaces = search.get_workspaces;
            if (workspaces) search.get_workspaces = function (...args) {
                const own = __('Open {0} Workspace',[__(frappe.boot.plus_point.navigation.workspace)]);
                return workspaces.apply(this,args).filter(option => option.value === own);
            };
        }
        // Keep the native dropdown component; replace its cross-app/editor menu
        // with the two actions relevant to this product workspace.
        if (frappe.ui.SidebarHeader) frappe.ui.SidebarHeader.prototype.menu_items = function () {
            return [{group:'',options:[{name:'product-home',label:__('Overview'),href:home()},
                {name:'arrange-sections',label:__('Arrange sections'),onclick:()=>plus_point.arrange_sections()},
                {name:'product-help',label:__('Help'),onclick:showGuide}]}];
        };
        frappe.provide('frappe.listview_settings');
        Object.keys(platform() ? platformLists : customerLists).forEach(doctype => {
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
