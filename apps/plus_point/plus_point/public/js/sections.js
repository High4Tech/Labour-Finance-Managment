/* Section summaries and personal ordering; native record permissions stay unchanged. */
(() => {
    frappe.provide('plus_point');
    const esc=value=>frappe.utils.escape_html(String(value??''));
    const num=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(value)||0);
    plus_point.arrange_sections=()=>{
        let order=[...frappe.boot.plus_point.navigation.groups];
        const dialog=new frappe.ui.Dialog({title:__('Arrange sections'),fields:[{fieldtype:'HTML',fieldname:'order'}],
            primary_action_label:__('Save my order'),async primary_action(){
                dialog.disable_primary_action();
                try{
                    const navigation=(await frappe.call({method:'plus_point.navigation.save_section_order',type:'POST',args:{order:JSON.stringify(order)}})).message;
                    frappe.boot.plus_point.navigation=navigation;frappe.boot.module_sidebars['PLUS POINT'].items=navigation.items;
                    frappe.app.sidebar.all_sidebar_items=frappe.boot.module_sidebars;frappe.app.sidebar.refresh();plus_point.enhance_sections();
                    dialog.hide();frappe.show_alert({message:__('Section order saved for your login.'),indicator:'green'});
                }finally{dialog.enable_primary_action();}
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
            const open=event=>{event.preventDefault();event.stopPropagation();frappe.set_route('pp-section',{section});};
            label.addEventListener('click',open);label.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key))open(event);});
            label.title=__('Open {0} overview',[__(section)]);
        });
    };
    plus_point.mount_section=async wrapper=>{
        const root=wrapper.pp_section_root;if(!root)return;
        const section=new URL(location.href).searchParams.get('section')||frappe.route_options?.section||frappe.boot.plus_point.navigation.groups[0];
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
            ]:section==='Clients and billing'?[
                ['Client companies',data.activity.client_count],['Open projects',data.open_projects],['Invoiced net',data.invoiced_net,data.currency],['Client balance',data.client_balance,data.currency]
            ]:section==='Payments and costs'?[
                ['Wages unpaid',data.wages_unpaid,data.currency],['Wages paid',data.wages_paid,data.currency],['Client cash received',data.cash_received,data.currency],['Client balance',data.client_balance,data.currency]
            ]:section==='Business reports'?[
                ['Revenue earned',data.earned_revenue,data.currency],['Wages unpaid',data.wages_unpaid,data.currency],['Client balance',data.client_balance,data.currency],['Operational contribution',data.contribution,data.currency]
            ]:[['Active workers',data.workers],['Active work sites',data.active_sites],['Open projects',data.open_projects],['Worker-days today',data.attendance.at(-1).units]];
            root.innerHTML=`<div class="pp-section-intro"><p>${esc(__('Your section at a glance. Choose a work list below to continue.'))}</p><label>${esc(__('Company'))}<select class="form-control pp-section-company">${data.companies.map(c=>`<option value="${esc(c.name)}" ${c.name===data.company?'selected':''}>${esc(c.company_name||c.name)}</option>`).join('')}</select></label></div>
                <dl class="pp-dashboard-metrics">${metrics.map(([label,value,currency])=>`<div class="pp-dashboard-metric"><dt>${esc(__(label))}</dt><dd>${esc(num(value))}${currency?`<small>${esc(currency)}</small>`:''}</dd></div>`).join('')}</dl>
                <section class="pp-section-worklists"><h2>${esc(__('Work lists'))}</h2>${data.links.map(link=>`<a class="pp-section-list" href="${esc(link.path)}"><span>${esc(__(link.title))}</span><strong>${link.count===null?esc(__('Open report')):esc(num(link.count))}</strong><span aria-hidden="true">›</span></a>`).join('')}</section>
                <p class="pp-activity-note">${esc(__('Record counts include drafts. Financial totals use approved work and posted records. Shared setup records may cover the whole business.'))}</p>
                <a class="pp-section-back" href="${frappe.boot.plus_point.home}">${esc(__('Back to overview and charts'))}</a>`;
            root.querySelector('select').onchange=event=>{plus_point.dashboard_company=event.target.value;plus_point.mount_section(wrapper);};
            root.dataset.section=section;root.dataset.ready='true';
        }catch{
            root.innerHTML=`<div class="pp-condition pp-condition-error"><div><h3>${esc(__('Section could not load'))}</h3><p>${esc(__('Retry to load the current figures. Your work lists remain in the sidebar.'))}</p></div><button class="btn btn-default">${esc(__('Try again'))}</button></div>`;
            root.querySelector('button').onclick=()=>plus_point.mount_section(wrapper);
        }
    };
    const watch=()=>frappe.router.on('change',()=>{if(frappe.get_route()[0]==='pp-section'){const wrapper=frappe.container?.page;if(wrapper?.pp_section_root)plus_point.mount_section(wrapper);}});
    if(frappe.router)watch();else $(document).on('app_ready.pp-sections',watch);
})();
