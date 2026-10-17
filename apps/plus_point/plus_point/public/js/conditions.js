/* Native form feedback and spending preflight; server checks remain authoritative. */
(() => {
    const esc=value=>frappe.utils.escape_html(String(value ?? ''));
    const supported=['PP Daily Register','PP Work Entry','Purchase Invoice','Expense Claim'];
    const registered=new Set();
    function summary(row) {
        return `<p class="pp-value-${esc(row.level)}">${esc(row.title)}: <strong>${esc(row.projected)}</strong> / ${esc(row.limit)} ${esc(row.currency)}.</p>
            <p>${esc(__('Tracked costs include approved wages, posted net purchases and sanctioned expense lines. Taxes, overhead and unallocated costs are excluded.'))}</p>`;
    }
    function budgetLink(row) {return `/desk/project/${encodeURIComponent(row.project)}`;}
    function state(row) {
        const title=!row.enabled?'No spending stop enabled':row.blocked?'This action would exceed the spending budget':row.level==='error'?'Spending budget exceeded':row.level==='warning'?'Spending is near the limit':'Spending is within budget';
        return `<div class="pp-condition pp-condition-${esc(row.level)}"><div><h4>${esc(__(title))}</h4>
            ${row.enabled?summary(row):`<p>${esc(__('Set a separate spending budget on the project and enable the spending stop. Client billing is unchanged.'))}</p>`}</div>
            <a class="btn btn-default btn-sm" href="${budgetLink(row)}" target="_blank" rel="noopener noreferrer">${esc(__(row.enabled?'Review spending budget':'Set spending budget'))}</a></div>`;
    }
    async function preflight(frm) {
        const response=await frappe.call({method:'plus_point.budget.preview',type:'POST',args:{document:JSON.stringify(frm.doc)}});
        const rows=response.message;
        const blocked=rows.find(row=>row.blocked);
        if (blocked) {
            frappe.validated=false;
            frappe.msgprint({title:__('Spending approval stopped'),indicator:'red',message:summary(blocked)+
                `<p>${esc(__('Nothing has been approved or submitted. Reduce the proposed cost or ask your administrator to review the spending budget.'))}</p>
                <p><a href="${budgetLink(blocked)}" target="_blank" rel="noopener noreferrer">${esc(__('Review spending budget'))}</a></p>`,
                primary_action:{label:__('Review cost entries'),action(){frappe.hide_msgprint();frm.scroll_to_field(frm.doctype==='PP Work Entry'?'units':frm.doctype==='PP Daily Register'?'entries':frm.doctype==='Purchase Invoice'?'items':'expenses');}}});
            return;
        }
        const warnings=rows.filter(row=>row.enabled && row.level==='warning');
        if (warnings.length) await new Promise(resolve=>{
            let finished=false;
            const finish=ok=>{if(finished)return;finished=true;if(!ok)frappe.validated=false;dialog.hide();resolve();};
            const dialog=new frappe.ui.Dialog({title:__('Review spending warning'),fields:[{fieldtype:'HTML',options:
                `<p>${esc(__('This action reaches at least 80% of a spending budget. Review the figures before proceeding.'))}</p>${warnings.map(summary).join('')}`}],
                primary_action_label:__('Confirm within budget'),primary_action:()=>finish(true),
                secondary_action_label:__('Review costs'),secondary_action:()=>finish(false)});
            dialog.onhide=()=>finish(false);dialog.show();
        });
    }
    async function refresh(frm) {
        if (frappe.boot.plus_point?.is_platform || !frappe.user.has_role('System Manager')) return;
        if (![...supported,'Project','PP Contract Terms'].includes(frm.doctype)) return;
        if (!registered.has(frm.doctype)) {
            registered.add(frm.doctype);
            const handlers={};
            if (supported.includes(frm.doctype)) {
                handlers.before_submit=preflight;
                if (frm.doctype==='PP Work Entry') handlers.validate=async current=>{if(current.doc.status==='Approved')await preflight(current);};
            }
            if (frm.doctype==='Project') {
                handlers.estimated_costing=refresh;handlers.pp_enforce_spending_budget=refresh;
            }
            frappe.ui.form.on(frm.doctype,handlers);
        }
        const sequence=frm.__pp_condition_sequence=(frm.__pp_condition_sequence || 0)+1;
        const render=html=>{
            if (sequence!==frm.__pp_condition_sequence) return;
            if (!frm.__pp_condition_body?.get(0)?.isConnected) frm.__pp_condition_body=frm.dashboard.add_section('',null,'pp-condition-section');
            frm.__pp_condition_body.html(html);
            frm.dashboard.show();
        };
        if (frm.doctype==='Project' && frm.is_dirty()) {
            render(`<div class="pp-condition pp-condition-empty"><div><h4>${esc(__('Save your budget settings'))}</h4><p>${esc(__('Use Spending budget for the separate cost limit. Enable Stop spending above budget to warn at 80% and block new spending above 100%.'))}</p></div><button class="btn btn-default pp-save-budget">${esc(__('Save budget settings'))}</button></div>`);
            frm.__pp_condition_body.find('.pp-save-budget').on('click',()=>frm.save());return;
        }
        const project=frm.doctype==='Project'?(!frm.is_new()?frm.doc.name:null):frm.doc.project;
        if (!project) return;
        try {
            const response=await frappe.call({method:'plus_point.budget.project_status',args:{project},silent:true});
            let html=state(response.message);
            if (frm.doc.docstatus===1 || (frm.doctype==='PP Work Entry' && frm.doc.status==='Approved')) {
                const attendance=['PP Daily Register','PP Work Entry'].includes(frm.doctype);
                const next=attendance?`/desk/pp-wage-settlement?project=${encodeURIComponent(project)}`:
                    `/desk/query-report/PLUS%20POINT%20Project%20Finances?company=${encodeURIComponent(response.message.company)}&project=${encodeURIComponent(project)}`;
                html=`<div class="pp-condition pp-condition-success"><div><h4>${esc(__(attendance?'Wages approved':'Expense submitted'))}</h4><p>${esc(__('The saved record is included in project spending. Payments are recorded separately.'))}</p></div><a class="btn btn-default btn-sm" href="${next}">${esc(__(attendance?'Review worker payments':'View project finances'))}</a></div>`+html;
            }
            render(html);
        } catch {
            render(`<div class="pp-condition pp-condition-error"><div><h4>${esc(__('Spending figures could not load'))}</h4><p>${esc(__('Retry the check. Server budget rules still apply when you approve or submit.'))}</p></div><button class="btn btn-default pp-retry-budget">${esc(__('Retry spending check'))}</button></div>`);
            frm.__pp_condition_body.find('.pp-retry-budget').on('click',()=>refresh(frm));
        }
    }
    $(document).on('form-refresh.pp-conditions',(_event,frm)=>refresh(frm));
})();
