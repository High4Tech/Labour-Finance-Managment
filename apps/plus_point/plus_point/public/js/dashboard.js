/* Live, company-scoped overview. No sample figures or browser-side accounting. */
(() => {
    frappe.provide('plus_point');
    const esc = value => frappe.utils.escape_html(String(value ?? ''));
    const number = value => new Intl.NumberFormat(undefined, {maximumFractionDigits: 2}).format(Number(value) || 0);
    const sign=(data,key)=>data.source_signs?.[key]??Math.sign(Number(data[key])||0);
    function exchangeNote(data){
        const fx=data.fx;
        if(fx?.status==='unavailable')return `<div class="pp-fx-note pp-fx-error" role="status"><p>${esc(__('{0} conversion is unavailable. Showing original {1} amounts.',[fx.requested,data.currency]))}</p><button type="button" class="btn btn-default btn-sm pp-retry-fx">${esc(__('Retry conversion'))}</button></div>`;
        if(fx?.status!=='converted')return '';
        const quote=new Intl.NumberFormat(undefined,{maximumFractionDigits:6}).format(Number(fx.source_per_target));
        const updated=new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short',timeZone:'UTC'}).format(new Date(fx.as_of));
        return `<div class="pp-fx-note" role="status"><p><strong>1 ${esc(fx.target)} = ${esc(quote)} ${esc(fx.source)}</strong> · ${esc(__('Rate updated'))} ${esc(updated)} UTC<br>${esc(__('Latest daily rate. Books remain in {0}.',[fx.source]))} <a href="https://www.exchangerate-api.com" target="_blank" rel="noopener noreferrer">${esc(__('Rates by ExchangeRate-API'))}</a></p></div>`;
    }
    const metric = (label, value, note, unit = '', level = '') => `<div class="pp-dashboard-metric pp-value-${level}"><dt>${esc(__(label))}</dt>
        <dd>${esc(number(value))}${unit ? `<small>${esc(unit)}</small>` : ''}</dd><p>${esc(__(note))}</p></div>`;
    const chart = (rows, series) => {
        const maximum = Math.max(1, ...rows.flatMap(row => series.map(([key]) => Math.abs(Number(row[key]) || 0))));
        const signed = rows.some(row => series.some(([key]) => Number(row[key]) < 0));
        return `<div class="pp-dashboard-chart ${signed?'pp-chart-signed':''} ${rows.length>14?'pp-chart-dense':''}" style="--pp-columns:${rows.length}">${rows.map((row,index) => {
            const stride=Math.ceil(rows.length/7);
            const label = row.month ? new Intl.DateTimeFormat(undefined,{month:'short'}).format(new Date(row.month+'-01T12:00:00'))
                : index%stride===0 ? new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric'}).format(new Date(row.date+'T12:00:00')) : '';
            return `<div class="pp-chart-column"><div class="pp-chart-bars">${series.map(([key, title], index) => {
                const value = Number(row[key]) || 0;
                return `<div class="pp-chart-track"><span class="pp-chart-bar pp-series-${index} ${value<0?'pp-bar-negative':''}" style="height:${Math.max(0,Math.abs(value)/maximum*(signed?50:100))}%"
                    title="${esc(`${row.month || row.date}: ${__(title)} ${number(value)}`)}"></span></div>`;
            }).join('')}</div><span>${esc(label)}</span><small>${series.map(([key]) => esc(number(row[key]))).join(' / ')}</small></div>`;
        }).join('')}</div><p class="pp-chart-legend">${series.map(([,title],index) => `<span><i class="pp-series-${index}" aria-hidden="true"></i>${esc(__(title))}</span>`).join('')}</p>`;
    };
    function customer(data,range=14) {
        const days=(data.activity?.daily || data.attendance).slice(-range);
        const financial=[['Revenue earned',data.earned_revenue,'revenue','earned_revenue'],['Wages earned',data.wages_earned,'wages','wages_earned'],['Other project costs',data.other_costs,'costs','other_costs'],['Operational contribution',data.contribution,'contribution','contribution']];
        const maximum=Math.max(1,...financial.map(([,value])=>Math.abs(Number(value)||0)));
        return `<dl class="pp-dashboard-metrics pp-workforce-metrics">
            ${metric('Worker-days today',data.attendance.at(-1).units,'Approved work only')}
            ${metric('Active workers',data.workers,'In your selected company')}
            ${metric('Active work sites',data.active_sites,__('Open projects: {0}',[data.open_projects]))}
            ${metric('Revenue earned',data.earned_revenue,'Lifetime approved work and milestones',data.currency)}
            ${metric('Wages unpaid',data.wages_unpaid,'Lifetime approved wages less linked payments',data.currency,sign(data,'wages_unpaid')>0?'warning':'success')}
            ${metric('Client invoice balance',data.client_balance,'Outstanding on posted project invoices',data.currency,sign(data,'client_balance')>0?'warning':'success')}</dl>
            ${conditions(data)}
            ${plus_point.event_summary_markup?.(data.event_plans)||''}
            <div class="pp-dashboard-panels"><section class="pp-dashboard-panel pp-work-trend"><header class="pp-panel-heading"><h3>${esc(__('Work delivered'))}</h3><div class="pp-chart-range" aria-label="${esc(__('Activity period'))}">${[7,14,30,91].map(n=>`<button type="button" data-range="${n}" aria-pressed="${n===range}">${n}${esc(__('d'))}</button>`).join('')}</div></header>
                <p>${esc(__('Approved worker-days. Two half-days count as one; drafts are excluded.'))}</p>
                ${chart(days,[['units','Worker-days']])}
                <p class="pp-dashboard-caption"><strong>${esc(number(days.reduce((n,row)=>n+Number(row.units),0)))}</strong> ${esc(__('worker-days in this period'))}</p></section>
            <section class="pp-dashboard-panel pp-finance-chart"><h3>${esc(__('Revenue and project costs'))}</h3><p>${esc(__('Lifetime amounts in'))} ${esc(data.currency)}. ${esc(__('Earnings and cash received are separate.'))}</p>
                <div class="pp-finance-bars">${financial.map(([label,value,key,field])=>`<div class="pp-finance-bar ${sign(data,field)<0?'pp-value-error':''}"><span>${esc(__(label))}</span><strong>${esc(number(value))}</strong><div><i class="pp-finance-${key}" style="width:${Math.abs(Number(value)||0)/maximum*100}%"></i></div></div>`).join('')}</div><p class="pp-dashboard-caption">${esc(__('Client cash received'))}: <strong>${esc(number(data.cash_received))} ${esc(data.currency)}</strong>. ${esc(__('Contribution excludes taxes, overhead and unallocated costs.'))}</p></section></div>
            ${plus_point.dashboard_workflow?.()||''}
            <section class="pp-activity-panel"><header class="pp-panel-heading"><div><h3>${esc(__('Client company activity'))}</h3><p>${esc(__('Last 91 days. See when and how much work was approved for each client.'))}</p></div><a href="/desk/customer">${esc(__('All clients'))}</a></header>${plus_point.activity_markup(data.activity,data.company)}</section>
            <section class="pp-dashboard-panel pp-dashboard-projects"><h3>${esc(__('Project snapshot'))}</h3><p>${esc(__('Lifetime figures. Projects with unpaid wages appear first.'))}</p>
                ${data.projects.length ? `<div class="pp-dashboard-table-wrap"><table class="pp-dashboard-table"><caption class="sr-only">${esc(__('Project financial snapshot'))}</caption>
                    <thead><tr><th>${esc(__('Project'))}</th><th>${esc(__('Earned'))}</th><th>${esc(__('Wages unpaid'))}</th></tr></thead>
                    <tbody>${data.projects.map(row => `<tr><th scope="row"><a href="/desk/project/${encodeURIComponent(row.name)}">${esc(row.title)}</a></th>
                        <td>${esc(number(row.earned_revenue))}</td><td>${esc(number(row.wages_unpaid))}</td></tr>`).join('')}</tbody></table></div>`
                    : `<p class="pp-dashboard-empty">${esc(__('No billing projects yet. Start with a client, project and billing terms below.'))} <a href="/desk/pp-contract-terms">${esc(__('Set up billing terms'))}</a></p>`}
                <div class="pp-dashboard-total ${sign(data,'contribution')<0?'pp-value-error':''}"><span>${esc(__('Operational contribution'))}</span><strong>${esc(number(data.contribution))} ${esc(data.currency)}</strong></div>
                <p class="pp-dashboard-caption">${esc(__('Earned revenue less wages and recorded project costs. Excludes taxes, overhead and unallocated costs.'))}</p>
            </section><details class="pp-budget-disclosure"><summary>${esc(__('Spending budgets'))}</summary>${budgets(data)}</details>`;
    }
    const stateLabels={error:'Action required',warning:'Warning',success:'Success',empty:'Next step'};
    function conditions(data) {
        const priority={error:0,warning:1,empty:2,success:3};
        const rows=[...(data.conditions || [])].sort((a,b)=>priority[a.level]-priority[b.level]);
        const unread=(data.notifications||[]).filter(row=>!row.read).length;
        const row=item=>`<div class="pp-condition pp-ticket pp-condition-${esc(item.level)}" role="${item.level==='error'?'alert':'status'}">
            <div><span class="pp-condition-label">${esc(__(stateLabels[item.level]))}</span><h4>${esc(__(item.title))}</h4>
            ${item.amount!==undefined?`<p class="pp-value-${esc(item.level)}"><strong>${esc(number(item.amount))}</strong> / ${esc(number(item.budget_limit))} ${esc(item.currency)} ${esc(__('used'))}</p>`:''}
            <p>${esc(__(item.message))}</p></div>
            <a class="btn btn-default btn-sm pp-condition-cta" href="${esc(item.path)}" ${item.action?`data-pp-action="${esc(item.action)}"`:''}>${esc(__(item.label))}</a></div>`;
        return rows.length ? `<section class="pp-conditions pp-action-inbox" aria-label="${esc(__('Action inbox'))}" tabindex="-1"><header class="pp-panel-heading"><div><h3>${esc(__('Action inbox'))} <span class="pp-count">${rows.length}</span></h3><p>${unread?esc(__('{0} unread updates',[unread])):esc(__('You have reviewed the latest updates. Actions remain until the underlying record is resolved.'))}</p></div>${unread?`<button type="button" class="btn btn-default btn-sm pp-mark-updates">${esc(__('Mark updates read'))}</button>`:''}</header>${rows.slice(0,2).map(row).join('')}
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
            ${metric('Unpaid invoices',data.client_balance,'Outstanding across posted invoices',data.currency,sign(data,'client_balance')>0?'warning':'success')}</dl>
            ${conditions(data)}
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
        async function load(company,displayCurrency=plus_point.dashboard_currency) {
            const current = ++request;
            root.setAttribute('aria-busy','true');
            root.querySelector('.pp-dashboard-refresh')?.setAttribute('disabled','');
            const updating=root.querySelector('.pp-dashboard-updated');
            if(updating)updating.textContent=__('Updating figures and exchange rate…');
            try {
                const response = await frappe.call({method:'plus_point.dashboard.overview',args:{company:company || undefined,display_currency:displayCurrency || undefined},silent:true});
                if (!root.isConnected || current !== request) return;
                const data=response.message;plus_point.dashboard_company=data.company;
                plus_point.dashboard_currency=data.currency;
                root.classList.toggle('pp-motion-dashboard',!data.is_platform);
                const draw=()=>{
                root.innerHTML=`<div class="pp-dashboard-toolbar"><div><h3>${esc(__('At a glance'))}</h3>
                    <p>${esc(frappe.datetime.str_to_user(data.date))}${data.currency ? ` · ${esc(__('Amounts in'))} ${esc(data.currency)}` : ''}</p></div>
                    <div class="pp-dashboard-controls"><label>${esc(__('Company'))}<select class="form-control pp-dashboard-company" aria-label="${esc(__('Dashboard company'))}">
                    ${data.companies.map(row=>`<option value="${esc(row.name)}" ${row.name===data.company?'selected':''}>${esc(row.company_name||row.name)}</option>`).join('')}</select></label>
                    <label>${esc(__('Display currency'))}<select class="form-control pp-dashboard-currency" aria-label="${esc(__('Display currency'))}" ${!data.company?'disabled':''}>${(data.currency_options||[data.currency].filter(Boolean)).map(code=>`<option value="${esc(code)}" ${code===data.currency?'selected':''}>${esc(code)}</option>`).join('')}</select></label>
                    <button class="btn btn-default btn-sm pp-open-updates" type="button" aria-label="${esc(__('Notifications'))}">${esc(__('Updates'))} <span class="pp-count">${(data.notifications||[]).filter(row=>!row.read).length}</span></button>
                    <button class="btn btn-default btn-sm pp-dashboard-refresh" type="button">${esc(__('Refresh figures'))}</button></div></div>
                    ${exchangeNote(data)}
                    ${data.company ? (data.is_platform ? platform(data) : customer(data,Number(root.dataset.range)||14)) : `<div class="pp-condition pp-condition-empty"><div><h4>${esc(__('Set up your company'))}</h4><p>${esc(__('Add your business to start seeing dashboard figures.'))}</p></div><a class="btn btn-default" href="/desk/company" data-pp-action="new:Company">${esc(__('Create company'))}</a></div>`}
                    <p class="pp-dashboard-updated" role="status">${esc(__('Updated just now. Refresh to see the latest records.'))}</p>`;
                root.querySelector('.pp-dashboard-company').addEventListener('change',event=>load(event.target.value));
                root.querySelector('.pp-dashboard-currency').addEventListener('change',event=>load(data.company,event.target.value));
                root.querySelector('.pp-dashboard-refresh').addEventListener('click',()=>load(root.querySelector('.pp-dashboard-company').value));
                root.querySelector('.pp-retry-fx')?.addEventListener('click',()=>load(data.company,data.fx.requested));
                root.querySelector('.pp-open-updates').addEventListener('click',()=>{const inbox=root.querySelector('.pp-action-inbox');inbox?.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});inbox?.focus({preventScroll:true});});
                root.querySelector('.pp-mark-updates')?.addEventListener('click',async event=>{event.target.disabled=true;try{await frappe.call({method:'plus_point.dashboard.mark_updates_read',type:'POST',args:{company:data.company}});data.notifications.forEach(row=>row.read=true);draw();}finally{event.target.disabled=false;}});
                root.querySelectorAll('[data-range]').forEach(button=>button.addEventListener('click',()=>{root.dataset.range=button.dataset.range;draw();}));
                plus_point.bind_activity(root);
                root.querySelector('.pp-new-event')?.addEventListener('click',()=>plus_point.open_event_wizard());
                plus_point.present_dashboard?.(root);
                root.querySelectorAll('[data-pp-action]').forEach(button=>button.addEventListener('click',event=>{
                    const action=button.dataset.ppAction;
                    if (action.startsWith('new:')) {event.preventDefault();frappe.new_doc(action.slice(4));}
                }));
                root.dataset.ready='true';
                };draw();
            } catch {
                if (!root.isConnected || current !== request) return;
                delete root.dataset.ready;
                root.innerHTML=`<div class="pp-condition pp-condition-error" role="alert"><div><h4>${esc(__('Dashboard could not load'))}</h4><p>${esc(__('Check your connection and permissions, then try again. Your work tools are still available below.'))}</p></div>
                    <button type="button" class="btn btn-default pp-dashboard-retry">${esc(__('Try again'))}</button></div>`;
                root.querySelector('button').addEventListener('click',()=>load(company,displayCurrency));
            } finally {
                if (current === request) root.setAttribute('aria-busy','false');
            }
        }
        root.innerHTML=`<p role="status">${esc(__('Loading your dashboard…'))}</p>`;
        load(plus_point.dashboard_company);
    };
})();
