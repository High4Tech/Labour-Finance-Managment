/* Live, company-scoped overview. No sample figures or browser-side accounting. */
(() => {
    frappe.provide('plus_point');
    const esc = value => frappe.utils.escape_html(String(value ?? ''));
    const number = value => new Intl.NumberFormat(undefined, {maximumFractionDigits: 2}).format(Number(value) || 0);
    const metric = (label, value, note, unit = '', level = '') => `<div class="pp-dashboard-metric pp-value-${level}"><dt>${esc(__(label))}</dt>
        <dd>${esc(number(value))}${unit ? `<small>${esc(unit)}</small>` : ''}</dd><p>${esc(__(note))}</p></div>`;
    const chart = (rows, series) => {
        const maximum = Math.max(1, ...rows.flatMap(row => series.map(([key]) => Math.abs(Number(row[key]) || 0))));
        const signed = rows.some(row => series.some(([key]) => Number(row[key]) < 0));
        return `<div class="pp-dashboard-chart ${signed?'pp-chart-signed':''}" style="--pp-columns:${rows.length}">${rows.map(row => {
            const label = row.month ? new Intl.DateTimeFormat(undefined,{month:'short'}).format(new Date(row.month+'-01T12:00:00'))
                : new Intl.DateTimeFormat(undefined,{weekday:'short'}).format(new Date(row.date+'T12:00:00'));
            return `<div class="pp-chart-column"><div class="pp-chart-bars">${series.map(([key, title], index) => {
                const value = Number(row[key]) || 0;
                return `<div class="pp-chart-track"><span class="pp-chart-bar pp-series-${index} ${value<0?'pp-bar-negative':''}" style="height:${Math.max(0,Math.abs(value)/maximum*(signed?50:100))}%"
                    title="${esc(`${row.month || row.date}: ${__(title)} ${number(value)}`)}"></span></div>`;
            }).join('')}</div><span>${esc(label)}</span><small>${series.map(([key]) => esc(number(row[key]))).join(' / ')}</small></div>`;
        }).join('')}</div><p class="pp-chart-legend">${series.map(([,title],index) => `<span><i class="pp-series-${index}" aria-hidden="true"></i>${esc(__(title))}</span>`).join('')}</p>`;
    };
    function customer(data) {
        return `<dl class="pp-dashboard-metrics">
            ${metric('Active workers',data.workers,'In your selected company')}
            ${metric('Active work sites',data.active_sites,__('Open projects: {0}',[data.open_projects]))}
            ${metric('Wages unpaid',data.wages_unpaid,'Lifetime approved wages less linked payments',data.currency,Number(data.wages_unpaid)>0?'warning':'success')}
            ${metric('Client invoice balance',data.client_balance,'Outstanding on posted project invoices',data.currency,Number(data.client_balance)>0?'warning':'success')}</dl>
            <div class="pp-dashboard-panels"><section class="pp-dashboard-panel"><h3>${esc(__('Attendance this week'))}</h3>
                <p>${esc(__('Approved worker-days over the last 7 days. Two half-days count as one.'))}</p>
                ${chart(data.attendance,[['units','Worker-days']])}
                <p class="pp-dashboard-caption">${esc(__('Today'))}: <strong>${esc(number(data.attendance.at(-1).units))}</strong> ${esc(__('approved worker-days'))}</p></section>
            <section class="pp-dashboard-panel"><h3>${esc(__('Project snapshot'))}</h3><p>${esc(__('Lifetime figures. Projects with unpaid wages appear first.'))}</p>
                ${data.projects.length ? `<div class="pp-dashboard-table-wrap"><table class="pp-dashboard-table"><caption class="sr-only">${esc(__('Project financial snapshot'))}</caption>
                    <thead><tr><th>${esc(__('Project'))}</th><th>${esc(__('Earned'))}</th><th>${esc(__('Wages unpaid'))}</th></tr></thead>
                    <tbody>${data.projects.map(row => `<tr><th scope="row"><a href="/desk/project/${encodeURIComponent(row.name)}">${esc(row.title)}</a></th>
                        <td>${esc(number(row.earned_revenue))}</td><td>${esc(number(row.wages_unpaid))}</td></tr>`).join('')}</tbody></table></div>`
                    : `<p class="pp-dashboard-empty">${esc(__('No billing projects yet. Start with a client, project and billing terms below.'))} <a href="/desk/pp-contract-terms">${esc(__('Set up billing terms'))}</a></p>`}
                <div class="pp-dashboard-total ${Number(data.contribution)<0?'pp-value-error':''}"><span>${esc(__('Operational contribution'))}</span><strong>${esc(number(data.contribution))} ${esc(data.currency)}</strong></div>
                <p class="pp-dashboard-caption">${esc(__('Earned revenue less wages and recorded project costs. Excludes taxes, overhead and unallocated costs.'))}</p>
            </section></div>${budgets(data)}`;
    }
    const stateLabels={error:'Action required',warning:'Warning',success:'Success',empty:'Next step'};
    function conditions(data) {
        const priority={error:0,warning:1,empty:2,success:3};
        const rows=[...(data.conditions || [])].sort((a,b)=>priority[a.level]-priority[b.level]);
        const row=item=>`<div class="pp-condition pp-condition-${esc(item.level)}" role="${item.level==='error'?'alert':'status'}">
            <div><span class="pp-condition-label">${esc(__(stateLabels[item.level]))}</span><h4>${esc(__(item.title))}</h4>
            ${item.amount!==undefined?`<p class="pp-value-${esc(item.level)}"><strong>${esc(number(item.amount))}</strong> / ${esc(number(item.budget_limit))} ${esc(item.currency)} ${esc(__('used'))}</p>`:''}
            <p>${esc(__(item.message))}</p></div>
            <a class="btn btn-default btn-sm pp-condition-cta" href="${esc(item.path)}" ${item.action?`data-pp-action="${esc(item.action)}"`:''}>${esc(__(item.label))}</a></div>`;
        return rows.length ? `<section class="pp-conditions" aria-label="${esc(__('Next actions'))}">${rows.slice(0,2).map(row).join('')}
            ${rows.length>2?`<details><summary>${esc(__('More next actions'))} (${rows.length-2})</summary>${rows.slice(2).map(row).join('')}</details>`:''}</section>`:'';
    }
    function budgets(data) {
        if (!data.budgets?.length) return '';
        return `<section class="pp-dashboard-panel pp-budget-panel"><h3>${esc(__('Spending budgets'))}</h3>
            <p>${esc(__('Approved wages + posted net purchases + sanctioned expense lines. Separate from the client price; excludes taxes, overhead and unallocated costs.'))}</p>
            ${data.budgets.map(row=>`<div class="pp-budget-row pp-value-${esc(row.level)}"><div><strong>${esc(row.title)}</strong>
                <p>${esc(__(!row.enabled?'Spending stop not enabled':row.level==='error'?'Over budget':Number(row.remaining)===0?'Budget fully used':row.level==='warning'?'Approaching budget':'Within budget'))}</p></div>
                <div class="pp-budget-figures"><strong>${esc(number(row.used))}${row.enabled?` / ${esc(number(row.limit))}`:''} ${esc(row.currency)}</strong>
                <p>${row.enabled?`${esc(number(row.remaining))} ${esc(__('remaining'))}`:esc(__('Set a limit before enforcing it'))}</p></div>
                <a class="btn btn-default btn-sm" href="/desk/project/${encodeURIComponent(row.project)}">${esc(__(row.enabled?'Review budget':'Set spending budget'))}</a></div>`).join('')}</section>`;
    }
    function platform(data) {
        const allZero = data.sales.every(row => !Number(row.invoiced) && !Number(row.receipts));
        return `<dl class="pp-dashboard-metrics">
            ${metric('Software customers',data.customers,`${data.active} active · ${data.trials} on trial`)}
            ${metric('Invoiced this month',data.invoiced_month,'Posted software invoices, including tax',data.currency)}
            ${metric('Received this month',data.receipts_month,'Customer receipts, net of refunds',data.currency)}
            ${metric('Unpaid invoices',data.client_balance,'Outstanding across posted invoices',data.currency,Number(data.client_balance)>0?'warning':'success')}</dl>
            <div class="pp-dashboard-panels"><section class="pp-dashboard-panel"><h3>${esc(__('Software sales and receipts'))}</h3>
                <p>${esc(__('Last 6 months through today. A bill and a payment are separate events.'))}</p>
                ${chart(data.sales,[['invoiced','Invoiced'],['receipts','Received']])}
                <p class="pp-dashboard-caption">${esc(__(allZero ? 'No posted sales or customer receipts in this period. Trials do not count as sales.'
                    : 'Amounts include invoice taxes. Receipts include unallocated payments; this chart is not a profit report.'))}</p></section>
            <section class="pp-dashboard-panel"><h3>${esc(__('Customer access'))}</h3>
                <p>${esc(__('Suspended and expired accounts appear first, followed by trials.'))}</p>
                ${data.customers_preview.length ? `<div class="pp-dashboard-table-wrap"><table class="pp-dashboard-table"><caption class="sr-only">${esc(__('Customer account status'))}</caption>
                    <thead><tr><th>${esc(__('Customer'))}</th><th>${esc(__('Access'))}</th><th>${esc(__('Valid until'))}</th></tr></thead>
                    <tbody>${data.customers_preview.map(row => `<tr><th scope="row"><a href="/desk/pp-tenant/${encodeURIComponent(row.name)}">${esc(row.title)}</a></th>
                        <td><span class="pp-account-status ${['Suspended','Expired'].includes(row.status)?'pp-status-alert':''}">${esc(__(row.status))}</span></td>
                        <td>${esc(row.valid_until ? frappe.datetime.str_to_user(row.valid_until) : __('Not set'))}</td></tr>`).join('')}</tbody></table></div>`
                    : `<p class="pp-dashboard-empty">${esc(__('No customers registered for this company. Add a customer and subscription below.'))}</p>`}
                <div class="pp-dashboard-total"><span>${esc(__('Access needs attention'))}</span><strong>${esc(number(data.restricted))}</strong></div>
                <p class="pp-dashboard-caption">${esc(number(data.pending_support))} ${esc(__('queued, processing or failed support requests.'))}</p>
            </section></div>`;
    }
    plus_point.mount_dashboard = function (root) {
        if (!root) return;
        if (!frappe.boot.plus_point?.is_platform && !frappe.user.has_role('System Manager')) {
            root.remove(); return;
        }
        let request = 0;
        async function load(company) {
            const current = ++request;
            root.setAttribute('aria-busy','true');
            root.querySelector('.pp-dashboard-refresh')?.setAttribute('disabled','');
            try {
                const response = await frappe.call({method:'plus_point.dashboard.overview',args:{company:company || undefined},silent:true});
                if (!root.isConnected || current !== request) return;
                const data=response.message;
                root.innerHTML=`<div class="pp-dashboard-toolbar"><div><h3>${esc(__('At a glance'))}</h3>
                    <p>${esc(frappe.datetime.str_to_user(data.date))}${data.currency ? ` · ${esc(__('Amounts in'))} ${esc(data.currency)}` : ''}</p></div>
                    <div class="pp-dashboard-controls"><label>${esc(__('Company'))}<select class="form-control pp-dashboard-company" aria-label="${esc(__('Dashboard company'))}">
                    ${data.companies.map(row=>`<option value="${esc(row.name)}" ${row.name===data.company?'selected':''}>${esc(row.name)}</option>`).join('')}</select></label>
                    <button class="btn btn-default btn-sm pp-dashboard-refresh" type="button">${esc(__('Refresh figures'))}</button></div></div>
                    ${conditions(data)}
                    ${data.company ? (data.is_platform ? platform(data) : customer(data)) : `<div class="pp-condition pp-condition-empty"><div><h4>${esc(__('Set up your company'))}</h4><p>${esc(__('Add your business to start seeing dashboard figures.'))}</p></div><a class="btn btn-default" href="/desk/company" data-pp-action="new:Company">${esc(__('Create company'))}</a></div>`}
                    <p class="pp-dashboard-updated" role="status">${esc(__('Updated just now. Refresh to see the latest records.'))}</p>`;
                root.querySelector('select').addEventListener('change',event=>load(event.target.value));
                root.querySelector('button').addEventListener('click',()=>load(root.querySelector('select').value));
                root.querySelectorAll('[data-pp-action]').forEach(button=>button.addEventListener('click',event=>{
                    const action=button.dataset.ppAction;
                    if (action.startsWith('new:')) {event.preventDefault();frappe.new_doc(action.slice(4));}
                }));
                root.dataset.ready='true';
            } catch {
                if (!root.isConnected || current !== request) return;
                delete root.dataset.ready;
                root.innerHTML=`<div class="pp-condition pp-condition-error" role="alert"><div><h4>${esc(__('Dashboard could not load'))}</h4><p>${esc(__('Check your connection and permissions, then try again. Your work tools are still available below.'))}</p></div>
                    <button type="button" class="btn btn-default pp-dashboard-retry">${esc(__('Try again'))}</button></div>`;
                root.querySelector('button').addEventListener('click',()=>load(company));
            } finally {
                if (current === request) root.setAttribute('aria-busy','false');
            }
        }
        root.innerHTML=`<p role="status">${esc(__('Loading your dashboard…'))}</p>`;
        load();
    };
})();
