/* Native finance lists, shared worker dialogs and one on-demand loan summary. */
(() => {
    frappe.provide('plus_point');
    const esc=value=>frappe.utils.escape_html(String(value??''));
    const rpc=(method,args={})=>plus_point.form_rpc('finance_hub.'+method,args);
    const number=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(value)||0);
    const money=(value,currency)=>esc(number(value)+' '+currency);
    const refreshList=()=>window.cur_list?.refresh();
    const hub=()=>frappe.set_route('pp-section',{section:'Finance'});
    let activeLoanForm;

    plus_point.new_worker_loan=async after=>{
        await plus_point.close_action_popup?.();
        return plus_point.worker_loan(null,after||refreshList);
    };

    const nativeTypes=['PP Wage Settlement','PP Worker Loan','Payment Entry','Purchase Invoice','Expense Claim','PP Loan Recovery'];
    function enhanceLists(){
        const route=frappe.get_route(),list=window.cur_list;
        if(frappe.boot.plus_point?.is_platform||route?.[0]!=='List'||!nativeTypes.includes(route[1])||
            list?.doctype!==route[1]||!list.page?.main||!list.list_view_settings||!Array.isArray(list.data))return;
        if(!list.__pp_finance_links){
            list.__pp_finance_links=true;
            list.page.add_inner_button(__('Payments overview'),hub);
            if(['Purchase Invoice','Expense Claim'].includes(list.doctype)){
                list.page.add_inner_button(__(list.doctype==='Purchase Invoice'?'Worker reimbursements':'Supplier expenses'),
                    ()=>frappe.set_route('List',list.doctype==='Purchase Invoice'?'Expense Claim':'Purchase Invoice','List'));
            }
            if(list.doctype==='PP Wage Settlement')list.page.add_inner_button(__('Worker statements'),()=>frappe.set_route('query-report','PLUS POINT Worker Statement'));
            if(list.doctype==='PP Worker Loan')list.page.add_inner_button(__('Recovery history'),()=>frappe.set_route('List','PP Loan Recovery','List'));
        }
        if(list.doctype!=='PP Worker Loan')return;
        if(!list.__pp_loan_create){list.__pp_loan_create=true;list.make_new_doc=()=>plus_point.new_worker_loan(()=>list.refresh());}
        if(list.can_create&&list.page.btn_primary?.text().trim()!==__('Assign loan')){
            list.page.set_primary_action(__('Assign loan'),()=>list.make_new_doc(),'plus');
            list.page.btn_primary.attr('data-pp-event-action','loan');
        }
        if(!list.__pp_loan_setup){
            list.__pp_loan_setup=true;
            list.settings.has_indicator_for_draft=true;
            list.settings.has_indicator_for_cancelled=true;
            list.settings.get_indicator=doc=>{
                const status=doc.loan_status||(doc.docstatus===2?'Cancelled':doc.docstatus===0?'Draft · unpaid':'Disbursed');
                return [__(status),status==='Active'?'orange':status==='Repaid'?'green':'grey',''];
            };
            list.meta.title_field='employee';
            for(const df of list.meta.fields)df.in_list_view=Number(['amount','loan_date','deduction_percent'].includes(df.fieldname));
            list.settings.formatters={...list.settings.formatters,employee:(value,df,doc)=>esc(doc.worker_name||value)};
            list.setup_columns().then(()=>{list.render_header(true);list.render_list();});
        }
        const rows=list.data;
        if(rows.length&&list.__pp_loan_rows!==rows&&!list.__pp_loan_busy){
            list.__pp_loan_rows=rows;list.__pp_loan_busy=true;
            rpc('loan_states',{names:rows.slice(0,200).map(r=>r.name)}).then(states=>{
                const byName=new Map(states.map(r=>[r.name,r]));
                for(const row of rows)Object.assign(row,byName.get(row.name)||{});
                if(cur_list===list&&frappe.get_route()[0]==='List'&&frappe.get_route()[1]===list.doctype)list.render_list();
            }).catch(()=>frappe.show_alert({message:__('Loan balances could not load. Refresh to try again.'),indicator:'orange'}))
                .finally(()=>{list.__pp_loan_busy=false;});
        }
        list.$result?.find('.list-row-container').each((_i,row)=>{
            const link=row.querySelector('a[data-name]'),name=link?.dataset.name,doc=rows.find(r=>r.name===name);
            if(!doc?.loan_status||row.querySelector('.pp-loan-list-balance'))return;
            if(link&&!link.dataset.ppLoanName){
                link.dataset.ppLoanName='true';
                link.textContent=doc.worker_name;
                const reference=document.createElement('small');reference.className='pp-reference';reference.textContent=doc.name;link.after(reference);
                if(plus_point.worker_avatar){link.insertAdjacentHTML('afterbegin',plus_point.worker_avatar(doc.worker_name,doc.image));link.classList.add('pp-worker-list-name');}
            }
            const right=row.querySelector('.list-row .level-right,.list-row .list-row-right');
            if(!right)return;
            const balance=document.createElement('span');balance.className='pp-loan-list-balance';
            balance.textContent=doc.docstatus===0?__('Payment not recorded'):doc.docstatus===2?__('Cancelled'):__('Balance: {0}',[number(doc.outstanding)+' '+doc.currency]);
            right.prepend(balance);
        });
    }

    async function loanSummary(frm,month){
        activeLoanForm=frm;
        const name=frm.doc.name,token=frm.__pp_loan_seq=(frm.__pp_loan_seq||0)+1;
        if(!frm.__pp_loan_root?.isConnected){frm.__pp_loan_root=document.createElement('section');frm.__pp_loan_root.className='pp-loan-summary';frm.form_wrapper.prepend(frm.__pp_loan_root);}
        const root=frm.__pp_loan_root;delete root.dataset.ready;root.innerHTML=`<p role="status">${esc(__('Loading loan balance…'))}</p>`;
        try{
            const data=await rpc('loan_detail',{name,month});
            if(token!==frm.__pp_loan_seq||!root.isConnected||frm.doc.name!==name||frappe.get_route()[0]!=='Form'||frappe.get_route()[2]!==name)return;
            const state=data.benefits,loan=data.loan,currency=data.currency,worker={doc:data.worker};
            const reload=async()=>{await frm.reload_doc();};
            const status=frm.doc.docstatus===2?'Cancelled':frm.doc.docstatus===0?'Draft · unpaid':Number(loan?.outstanding)>0?'Active':'Repaid';
            root.innerHTML=`<div class="pp-resource-heading"><div><p class="text-muted">${esc(__('Worker loan'))} · ${esc(__(status))}</p><h2>${esc(data.worker.employee_name)}</h2></div><div class="pp-actions"><button type="button" class="btn btn-default" data-worker>${esc(__('Worker profile'))}</button><button type="button" class="btn btn-default" data-loans>${esc(__('All loans'))}</button></div></div>
                <dl class="pp-dashboard-metrics">${[['Loan amount',frm.doc.amount],['Recovered',loan?.recovered||0],['Loan balance',loan?.outstanding||0]].map(([title,value])=>`<div class="pp-dashboard-metric"><dt>${esc(__(title))}</dt><dd>${money(value,currency)}</dd></div>`).join('')}</dl>
                <div class="pp-actions">${frm.doc.docstatus===0?`<button class="btn btn-primary" type="button" data-disburse>${esc(__('Record disbursement'))}</button>`:''}${Number(loan?.proposed_deduction)>0?`<button class="btn btn-primary" type="button" data-recover>${esc(__('Post monthly deduction'))}</button>`:''}</div>
                <p class="text-muted">${esc(__(frm.doc.docstatus===0?'This loan is unpaid. Record the matching employee advance payment before disbursing it. Wages are unchanged.':'Loan recoveries reduce outstanding wages only when the deduction is posted.'))}</p>
                <div class="pp-finance-month"><h3>${esc(__('Monthly wage deduction'))}</h3><label>${esc(__('Month'))}<input type="month" class="form-control" value="${esc(state.month.slice(0,7))}" aria-label="${esc(__('Deduction month'))}"></label></div>
                <dl class="pp-dashboard-metrics">${[['Wages outstanding',state.monthly_outstanding],['Proposed deductions · all loans',state.proposed_deduction],['Wages after proposed deductions',state.monthly_after_deduction]].map(([title,value])=>`<div class="pp-dashboard-metric"><dt>${esc(__(title))}</dt><dd>${money(value,currency)}</dd></div>`).join('')}</dl>
                <p class="text-muted">${esc(__('Outstanding wages already include posted recoveries. Proposed deductions are limited by approved earnings, unpaid wages and each loan’s balance.'))}</p>
                <h3>${esc(__('Recovery history'))}</h3>${data.recoveries.length?`<div class="pp-section-worklists">${data.recoveries.map(r=>`<a class="pp-section-list" href="/desk/pp-loan-recovery/${encodeURIComponent(r.name)}"><span>${esc(String(r.month).slice(0,7))} · ${esc(__(r.docstatus===1?'Posted':r.docstatus===2?'Cancelled':'Draft'))}</span><strong>${money(r.amount,currency)}</strong></a>`).join('')}</div>`:`<p class="text-muted">${esc(__('No deductions recorded for this loan.'))}</p>`}`;
            root.querySelector('[data-worker]').onclick=()=>frappe.set_route('Form','Employee',data.worker.name);
            root.querySelector('[data-loans]').onclick=()=>frappe.set_route('List','PP Worker Loan','List');
            root.querySelector('input[type=month]').onchange=event=>{if(/^\d{4}-\d{2}$/.test(event.target.value))loanSummary(frm,event.target.value+'-01');};
            root.querySelector('[data-disburse]')?.addEventListener('click',()=>plus_point.worker_disburse(worker,{...frm.doc},reload));
            root.querySelector('[data-recover]')?.addEventListener('click',()=>plus_point.worker_recovery(worker,loan,state.month,reload));
            root.dataset.ready='true';
        }catch(error){if(token===frm.__pp_loan_seq){root.innerHTML=`<p role="alert">${esc(error.message)}</p><button class="btn btn-default" type="button">${esc(__('Try again'))}</button>`;root.querySelector('button').onclick=()=>loanSummary(frm,month);}}
    }
    $(document).on('form-refresh.pp-finance',(_event,frm)=>{
        if(frappe.boot.plus_point?.is_platform||frm.doctype!=='PP Worker Loan'||frm.is_new())return;
        frm.set_df_property('company','hidden',1);
        loanSummary(frm);
    });
    frappe.router.on('change',()=>{
        const frm=activeLoanForm;
        if(frm?.__pp_loan_root&&(frappe.get_route()[0]!=='Form'||frappe.get_route()[1]!=='PP Worker Loan'||frappe.get_route()[2]!==frm.doc.name)){
            frm.__pp_loan_seq=(frm.__pp_loan_seq||0)+1;frm.__pp_loan_root.remove();frm.__pp_loan_root=null;activeLoanForm=null;
        }
    });
    plus_point.watch_ui('finance-native-lists',enhanceLists);
})();
