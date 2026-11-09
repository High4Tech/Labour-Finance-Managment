/* React company finance owners with authorized native list adapters. */
(() => {
    frappe.provide('plus_point');
    $(document).on('form-refresh.pp-react-finance',(_event,frm)=>{
        if(frappe.boot.plus_point?.is_platform||!['Payment Entry','Sales Invoice','Purchase Invoice','Expense Claim','PP Wage Settlement'].includes(frm.doctype))return;
        if(sessionStorage.getItem('pp:finance:advanced-form')===frm.doctype){frm.add_custom_button(__('Back to company form'),()=>{sessionStorage.removeItem('pp:finance:advanced-form');plus_point.load_feature('react_ui').then(()=>plus_point.react_finance_record_mount(frm));});return;}
        plus_point.load_feature('react_ui').then(()=>plus_point.react_finance_record_mount(frm)).catch(console.error);
    });
    const esc=value=>frappe.utils.escape_html(String(value??''));
    const rpc=(method,args={})=>plus_point.form_rpc('finance_hub.'+method,args);
    const number=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(value)||0);
    const money=(value,currency)=>esc(number(value)+' '+currency);
    const refreshList=()=>window.cur_list?.refresh();
    const hub=()=>frappe.set_route('pp-section',{section:'Finance'});

    plus_point.new_worker_loan=async after=>{
        await plus_point.close_action_popup?.();
        await plus_point.load_feature('react_ui');return plus_point.react_new_loan(after||refreshList);
    };

    const nativeTypes=['PP Wage Settlement','PP Worker Loan','Payment Entry','Sales Invoice','Purchase Invoice','Expense Claim','PP Loan Recovery'];
    function enhanceLists(){
        const route=frappe.get_route(),list=window.cur_list;
        if(frappe.boot.plus_point?.is_platform||route?.[0]!=='List'||!nativeTypes.includes(route[1])||
            list?.doctype!==route[1]||['PP Worker Loan','PP Loan Recovery'].includes(list?.doctype)&&!sessionStorage.getItem('pp:loans:advanced')||list.__pp_react_shared_list||!list.page?.main||!list.list_view_settings||!Array.isArray(list.data))return;
        if(['Payment Entry','Sales Invoice','Purchase Invoice','Expense Claim'].includes(list.doctype)&&sessionStorage.getItem('pp:finance:advanced')!==list.doctype)return;
        if(sessionStorage.getItem('pp:finance:advanced')===list.doctype&&!list.__pp_react_return){list.__pp_react_return=true;list.page.add_inner_button(__('Back to company list'),()=>{sessionStorage.removeItem('pp:finance:advanced');location.reload();});}
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
        if(list.doctype==='PP Wage Settlement'&&!plus_point.use_native_payments()&&!list.__pp_wages&&!list.__pp_wages_loading){list.__pp_wages_loading=true;plus_point.load_feature('react_ui').then(()=>{if(window.cur_list===list)plus_point.react_payments_mount(list);}).catch(()=>frappe.show_alert({message:__('Payment balances could not load. Refresh to retry.'),indicator:'red'})).finally(()=>{list.__pp_wages_loading=false;});}
        if(list.doctype==='PP Wage Settlement'&&plus_point.use_native_payments()&&!list.__pp_simple_return){list.__pp_simple_return=true;list.page.add_inner_button(__('Back to payment balances'),()=>{sessionStorage.removeItem('pp:payments:advanced');location.assign(location.pathname);});}
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
            list.settings.add_fields=[...new Set([...(list.settings.add_fields||[]),'currency'])];
            list.settings.formatters={...list.settings.formatters,employee:(value,df,doc)=>esc(doc.worker_name||value),amount:(value,df,doc)=>money(value,doc.currency||frappe.boot.plus_point?.company_identity?.default_currency||frappe.defaults.get_default('currency'))};
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

    $(document).on('form-refresh.pp-finance',(_event,frm)=>{
        if(frappe.boot.plus_point?.is_platform||!['PP Worker Loan','PP Loan Recovery'].includes(frm.doctype))return;
        if(frm.is_new()){frappe.set_route('List','PP Worker Loan');plus_point.new_worker_loan();return;}
        plus_point.load_feature('react_ui').then(()=>plus_point.react_loan_profile(frm)).catch(console.error);
    });
    plus_point.watch_ui('finance-native-lists',enhanceLists);
})();
