/* Section summaries and personal ordering; native record permissions stay unchanged. */
(() => {
    frappe.provide('plus_point');
    const esc=value=>frappe.utils.escape_html(String(value??''));
    let sectionWrapper;
    const num=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(value)||0);
    const orderError=message=>frappe.msgprint({title:__('Order not saved'),message,
        primary_action:{label:__('Close'),action:()=>frappe.hide_msgprint()}});
    const applyNavigation=navigation=>{
        frappe.boot.plus_point.navigation=navigation;frappe.boot.module_sidebars['PLUS POINT'].items=navigation.items;
        frappe.app.sidebar.all_sidebar_items=frappe.boot.module_sidebars;frappe.app.sidebar.refresh();plus_point.enhance_sections();
    };
    plus_point.save_section_order=async order=>{
        const navigation=(await frappe.call({method:'plus_point.navigation.save_section_order',type:'POST',args:{order:JSON.stringify(order)},silent:true})).message;
        applyNavigation(navigation);
        frappe.show_alert({message:__('Section order saved for your login.'),indicator:'green'});
    };
    plus_point.arrange_sections=()=>{
        let order=[...frappe.boot.plus_point.navigation.groups];
        const dialog=new frappe.ui.Dialog({title:__('Arrange sections'),fields:[{fieldtype:'HTML',fieldname:'order'}],
            primary_action_label:__('Save my order'),async primary_action(){
                dialog.disable_primary_action();
                try{
                    await plus_point.save_section_order(order);dialog.hide();
                }catch{orderError(__('Could not save your section order. Keep this dialog open and try Save my order again.'));}
                finally{dialog.enable_primary_action();}
            }});
        const draw=()=>{
            dialog.fields_dict.order.$wrapper.html(`<p>${esc(__('Move the sections you use most to the top. This changes only your sidebar.'))}</p><ol class="pp-section-order">${order.map((label,index)=>`<li><span>${esc(__(label))}</span><button type="button" data-index="${index}" data-move="-1" aria-label="${esc(__('Move {0} up',[__(label)]))}" ${index===0?'disabled':''}>↑</button><button type="button" data-index="${index}" data-move="1" aria-label="${esc(__('Move {0} down',[__(label)]))}" ${index===order.length-1?'disabled':''}>↓</button></li>`).join('')}</ol>`);
            dialog.fields_dict.order.$wrapper.find('[data-move]').on('click',event=>{const i=Number(event.currentTarget.dataset.index),j=i+Number(event.currentTarget.dataset.move);[order[i],order[j]]=[order[j],order[i]];draw();dialog.fields_dict.order.$wrapper.find(`[data-index="${j}"][data-move="${event.currentTarget.dataset.move}"]`).trigger('focus');});
        };
        draw();dialog.show();
    };
    plus_point.enhance_sections=()=>{
        const groups=frappe.boot.plus_point?.navigation.groups||[];
        document.querySelectorAll('.body-sidebar .section-item > .standard-sidebar-item .section-break > .sidebar-item-label').forEach(label=>{
            if(label.dataset.ppHub)return;
            const section=groups.find(name=>label.textContent.trim()===name||label.textContent.trim()===__(name));if(!section)return;
            label.dataset.ppHub=section;label.setAttribute('role','link');label.tabIndex=0;
            const open=event=>{event.preventDefault();event.stopPropagation();if(Date.now()<(plus_point.section_drag_until||0))return;frappe.set_route('pp-section',{section});};
            label.addEventListener('click',open);label.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key))open(event);});
            label.title=__('Open {0} overview',[__(section)]);
            const row=label.closest('.section-item'),header=label.closest('.standard-sidebar-item');
            row.dataset.ppSection=section;header.classList.add('pp-section-drag-header');
            const grip=document.createElement('span');grip.className='pp-section-grip';grip.textContent='⠿';grip.setAttribute('aria-hidden','true');
            grip.title=__('Drag this header to reorder. For keyboard controls, use Sidebar Menu → Arrange sections.');label.before(grip);
            const parent=row.parentElement;
            if(!parent.ppSectionSortable&&typeof Sortable!=='undefined')parent.ppSectionSortable=new Sortable(parent,{
                draggable:'.section-item[data-pp-section]',handle:'.pp-section-drag-header',filter:'.drop-icon',preventOnFilter:false,
                animation:matchMedia('(prefers-reduced-motion: reduce)').matches?0:150,ghostClass:'pp-section-drag-ghost',
                delayOnTouchOnly:true,delay:180,touchStartThreshold:5,
                onStart(){plus_point.section_drag_until=Infinity;},
                async onEnd(event){
                    plus_point.section_drag_until=Date.now()+350;
                    if(event.oldIndex===event.newIndex)return;
                    const original=frappe.boot.plus_point.navigation;
                    const visible=[...parent.children].filter(node=>node.dataset.ppSection).map(node=>node.dataset.ppSection);
                    const shown=new Set(visible);const order=original.groups.map(label=>shown.has(label)?visible.shift():label);
                    parent.ppSectionSortable.option('disabled',true);
                    try{await plus_point.save_section_order(order);}
                    catch{applyNavigation(original);orderError(__('Could not save your section order. The previous order is restored. Try again or use Sidebar Menu → Arrange sections.'));}
                    finally{parent.ppSectionSortable?.option('disabled',false);}
                }
            });
        });
    };
    plus_point.mount_section=async wrapper=>{
        sectionWrapper=wrapper;
        const root=wrapper.pp_section_root;if(!root)return;
        let section=new URL(location.href).searchParams.get('section')||frappe.route_options?.section||frappe.boot.plus_point.navigation.groups[0];
        if(section==='Business reports'&&!frappe.boot.plus_point.is_platform)section='Payments and costs';
        if(wrapper.__pp_section_loading===section)return;
        wrapper.__pp_section_loading=section;
        const sequence=wrapper.__pp_section_seq=(wrapper.__pp_section_seq||0)+1;
        delete root.dataset.ready;delete root.dataset.section;
        wrapper.page.set_title(__(section));root.innerHTML=`<p role="status">${esc(__('Loading section overview…'))}</p>`;
        try{
            const data=(await frappe.call({method:'plus_point.sections.overview',args:{section,company:plus_point.dashboard_company},silent:true})).message;
            if(sequence!==wrapper.__pp_section_seq)return;
            plus_point.dashboard_company=data.company;
            if(!data.company){
                root.innerHTML=`<p>${esc(__('Add your business to see a section overview.'))}</p><a href="/desk/company">${esc(__('Set up company'))}</a>`;
                root.dataset.section=section;root.dataset.ready='true';return;
            }
            const metrics=data.is_platform?[
                ['Software customers',data.customers],['On trial',data.trials],['Invoiced this month',data.invoiced_month,data.currency],['Unpaid invoices',data.client_balance,data.currency]
            ]:section==='Inventory and transport'?[
                ['Equipment types',data.resources.items],['Warehouses',data.resources.warehouses],['Vehicles',data.resources.vehicles],['Upcoming reservations',data.resources.reservations]
            ]:section==='Clients and billing'?[
                ['Client companies',data.activity.client_count],['Open projects',data.open_projects],['Invoiced net',data.invoiced_net,data.currency],['Client balance',data.client_balance,data.currency]
            ]:section==='Payments and costs'?[
                ['Wages unpaid',data.wages_unpaid,data.currency],['Wages paid',data.wages_paid,data.currency],['Client cash received',data.cash_received,data.currency],['Client balance',data.client_balance,data.currency]
            ]:section==='Business reports'?[
                ['Revenue earned',data.earned_revenue,data.currency],['Wages unpaid',data.wages_unpaid,data.currency],['Client balance',data.client_balance,data.currency],['Operational contribution',data.contribution,data.currency]
            ]:[['Active workers',data.workers],['Active work sites',data.active_sites],['Open projects',data.open_projects],['Worker-days today',data.attendance.at(-1).units]];
            root.innerHTML=`<div class="pp-section-intro"><p>${esc(__('Your section at a glance. Choose a work list below to continue.'))}</p>${data.is_platform?`<label>${esc(__('Company'))}<select class="form-control pp-section-company">${data.companies.map(c=>`<option value="${esc(c.name)}" ${c.name===data.company?'selected':''}>${esc(c.company_name||c.name)}</option>`).join('')}</select></label>`:''}</div>
                <dl class="pp-dashboard-metrics">${metrics.map(([label,value,currency])=>`<div class="pp-dashboard-metric"><dt>${esc(__(label))}</dt><dd>${esc(num(value))}${currency?`<small>${esc(currency)}</small>`:''}</dd></div>`).join('')}</dl>
                <section class="pp-section-worklists"><h2>${esc(__('Work lists'))}</h2>${data.links.map(link=>`<a class="pp-section-list" href="${esc(link.path)}"><span>${esc(__(link.title))}</span><strong>${link.count===null?esc(__(link.is_report===false?'Open availability':'Open report')):esc(num(link.count))}</strong><span aria-hidden="true">›</span></a>`).join('')}</section>
                ${data.loans?.enabled?`<section class="pp-finance-loans"><h2>${esc(__('Worker loans'))}</h2><dl class="pp-dashboard-metrics">${[['Money advanced',data.loans.advanced],['Recovered',data.loans.recovered],['Loan balance',data.loans.outstanding],['Unpaid drafts',data.loans.drafts]].map(([title,value])=>`<div class="pp-dashboard-metric"><dt>${esc(__(title))}</dt><dd>${esc(num(value))}<small>${esc(data.loans.currency)}</small></dd></div>`).join('')}</dl><p class="text-muted">${esc(__('Draft loans are unpaid. Only recorded disbursements and posted recoveries affect the loan balance.'))}</p><div class="pp-actions"><button class="btn btn-primary" type="button" data-new-loan>${esc(__('Assign loan'))}</button><a class="btn btn-default" href="/desk/pp-worker-loan/view/list">${esc(__('Manage loans'))}</a></div></section>`:''}
                ${data.related_links?.length?`<section class="pp-section-worklists"><h2>${esc(__('Related costs'))}</h2>${data.related_links.map(link=>`<a class="pp-section-list" href="${esc(link.path)}"><span>${esc(__(link.title))}</span><span aria-hidden="true">›</span></a>`).join('')}</section>`:''}
                ${data.report_links?.length?`<section class="pp-section-worklists"><h2>${esc(__('Reports'))}</h2>${data.report_links.map(link=>`<a class="pp-section-list" href="${esc(link.path)}"><span>${esc(__(link.title))}</span><span aria-hidden="true">›</span></a>`).join('')}</section>`:''}
                <p class="pp-activity-note">${esc(__('Record counts include drafts. Financial totals use approved work and posted records. Shared setup records may cover the whole business.'))}</p>
                <a class="pp-section-back" href="${frappe.boot.plus_point.home}">${esc(__('Back to overview and charts'))}</a>`;
            if(root.querySelector('select'))root.querySelector('select').onchange=event=>{plus_point.dashboard_company=event.target.value;plus_point.mount_section(wrapper);};
            root.querySelector('[data-new-loan]')?.addEventListener('click',()=>plus_point.new_worker_loan(()=>plus_point.mount_section(wrapper)));
            wrapper.page.set_secondary_action(__('Refresh'),()=>plus_point.mount_section(wrapper),'refresh');
            root.dataset.section=section;root.dataset.ready='true';
        }catch{
            root.innerHTML=`<div class="pp-condition pp-condition-error"><div><h3>${esc(__('Section could not load'))}</h3><p>${esc(__('Retry to load the current figures. Your work lists remain in the sidebar.'))}</p></div><button class="btn btn-default">${esc(__('Try again'))}</button></div>`;
            root.querySelector('button').onclick=()=>plus_point.mount_section(wrapper);
        }finally{if(sequence===wrapper.__pp_section_seq)wrapper.__pp_section_loading=null;}
    };
    const watch=()=>frappe.router.on('change',()=>{const wrapper=sectionWrapper;if(frappe.get_route()[0]==='pp-section'){const active=frappe.container?.page;if(active?.pp_section_root)plus_point.mount_section(active);}else if(wrapper?.pp_section_root){wrapper.__pp_section_seq=(wrapper.__pp_section_seq||0)+1;wrapper.__pp_section_loading=null;wrapper.pp_section_root.replaceChildren();delete wrapper.pp_section_root.dataset.ready;}});
    if(frappe.router)watch();else $(document).on('app_ready.pp-sections',watch);
})();
