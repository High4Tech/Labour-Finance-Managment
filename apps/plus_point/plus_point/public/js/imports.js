/* Files stay in this session; preview and native posting are separate actions. */
(() => {
    frappe.provide('plus_point');
    const esc=value=>frappe.utils.escape_html(String(value ?? ''));
    const kinds={employees:'Employees',work:'Approved daily work',milestones:'Fixed-price milestones',expenses:'Project expenses',invoices:'Client invoices',receipts:'Client receipts',worker_payments:'Worker payments'};
    const help={
        clients:'Add clients using customer_name and customer_type (Company or Individual). Leave customer blank to create one, or use a Customer ID to update it.',
        event_sites:'Use the event project ID, site_name, address and status (Active or Inactive). Leave site blank for a new venue or enter its ID to update it.',
        vehicles:'Use a unique license_plate, make/model, crew_seats (driver excluded), cargo_capacity and cargo_uom (units, kg or m³). fuel_type is Petrol, Diesel, Natural Gas or Electric. Status is Active or Inactive. Existing plates update the vehicle; bookings protect capacity reductions.',
        inventory_items:'Use a unique item_code, item_name, stock_uom (for example Nos) and status (Active or Inactive). This adds/updates the equipment catalog only, not warehouse quantities or finances.',
        warehouses:'Add warehouse_name under your company. Download reference IDs after creation before importing balances.',
        stock_balances:'Set a counted balance per item_code and warehouse, date (YYYY-MM-DD), quantity and valuation_rate per unit in company currency. This sets absolute warehouse quantities using a submitted native stock reconciliation and may change stock book value. It is not a receipt or a quantity to add. Review carefully; reservations still apply.',
        events:'One event and venue per row: client Customer ID, dates, site_name, workers_per_day, wage_rate, Daily/Fixed billing, client_rate (zero for Fixed), fixed_amount for Fixed, and agreement text. This creates a project, internal agreement and plan. It does not allocate crew, approve attendance or bill a client. Add more phases/sites in the saved event plan.',
        employees:'Use one stable external_id per person. Format IDs and phone columns as text in your spreadsheet. Leave employee blank to add a person, or enter an existing Employee ID to update that profile. Required: first_name, gender, date_of_birth, date_of_joining, status (Active or Inactive). Dates use YYYY-MM-DD. Optional blank last_name and cell_number clear those fields on an update. No login is created.',
        work:'Use an existing assignment ID, work_date (YYYY-MM-DD) and units (1, 0.5 or 0). Wages and client charges use that assignment’s agreed rates. Rows become approved earnings, not payments. Import work before its invoices or worker payments.',
        milestones:'Use active Fixed contract_terms, a title, date (YYYY-MM-DD) and amount. Rows become approved client earnings. The fixed contract cap still applies. Import milestones before their invoices.',
        expenses:'Use project, supplier and non-stock item_code IDs, date (YYYY-MM-DD) and the net amount. This posts an unpaid supplier invoice and updates project spending. Tax-bearing invoices need their full breakdown in the native invoice form.',
        invoices:'Use project, customer and non-stock item_code IDs, date (YYYY-MM-DD) and net amount. For PLUS POINT earnings, fill source_type (PP Work Entry or PP Milestone) and source_name to prevent rebilling. source_name accepts import:external_id from an earlier work/milestone import. Blank sources record a legacy invoice and receivable only; they do not create operational earnings. Taxes need the native invoice form.',
        receipts:'Use a submitted invoice ID, date (YYYY-MM-DD), amount and bank_account ledger ID. invoice accepts import:external_id from an earlier invoice import. This records money already received and allocates it to that invoice. It does not contact a bank.',
        worker_payments:'Use project and employee IDs, date (YYYY-MM-DD), amount and bank_account ledger ID. employee accepts import:external_id from an employee import. This records an actual historical payment and settles approved outstanding wages. It does not send money. Import the related work first.',
    };
    Object.assign(kinds,{clients:'Clients',event_sites:'Event sites',events:'Event plans',vehicles:'Vehicles',inventory_items:'Inventory catalog',warehouses:'Warehouses',stock_balances:'Warehouse stock balances'});
    function download(method,args){
        const url='/api/method/plus_point.imports.'+method+'?'+new URLSearchParams(args);
        const anchor=document.createElement('a');anchor.href=url;anchor.download='';document.body.append(anchor);anchor.click();anchor.remove();
    }
    function errorsFile(rows){
        const csv=value=>{const text=String(value??'');return '"'+((/^[=+@-]/.test(text)?"'":'')+text).replaceAll('"','""')+'"';};
        const content=[['row','external_id','error'],...rows.filter(r=>r.error).map(r=>[r.row,r.external_id,r.error])].map(row=>row.map(csv).join(',')).join('\r\n');
        const url=URL.createObjectURL(new Blob(['\ufeff'+content],{type:'text/csv;charset=utf-8'}));
        const anchor=document.createElement('a');anchor.href=url;anchor.download='plus-point-import-errors.csv';anchor.click();URL.revokeObjectURL(url);
    }
    plus_point.open_import=async(defaultCompany,onClose,defaultKind='employees',returnLabel='Return to records')=>{
        let preview=null,file=null,busy=false,finished=false,dialog;
        const reset=()=>{if(busy || !dialog)return;preview=null;dialog.set_value('confirmed',0);dialog.set_df_property('confirmed','hidden',1);dialog.fields_dict.preview.$wrapper.empty();dialog.set_primary_action(__('Review file'),review);};
        const helpText=()=>{
            if(!dialog)return;
            reset();const kind=dialog.get_value('kind');
            dialog.set_df_property('confirmed','label',__(kind==='stock_balances'?'I reviewed these absolute stock counts and unit values and confirm the native stock-value posting.':'I reviewed these records and confirm the listed changes and any described financial postings.'));
            dialog.fields_dict.instructions.$wrapper.html(`<details><summary>${esc(__('How to fill this template'))}</summary><p>${esc(__(help[kind]))}</p><p>${esc(__('Keep external_id stable when re-uploading. Identical financial rows are skipped; changed posted rows require a reviewed correction. Employee profiles can be updated.'))}</p></details>`);
        };
        dialog=new frappe.ui.Dialog({title:__('Import business records'),static:true,size:'extra-large',fields:[
            {fieldtype:'HTML',fieldname:'intro',options:`<p>${esc(__('Download a template, fill it in Excel or Google Sheets, then upload CSV or XLSX. Review every row before saving. Up to 200 rows and 2 MB per file.'))}</p>`},
            {fieldtype:'Link',fieldname:'company',label:__('Your company'),options:'Company',reqd:1,default:defaultCompany,onchange:reset},
            {fieldtype:'Select',fieldname:'kind',label:__('What are you importing?'),options:Object.entries(kinds).map(([value,label])=>({value,label:__(label)})),default:defaultKind,reqd:1,onchange:helpText},
            {fieldtype:'HTML',fieldname:'template_actions',options:`<div class="pp-import-tools"><button class="btn btn-primary pp-download-template" type="button">${esc(__('Download template'))}</button><button class="btn btn-default pp-download-ids" type="button">${esc(__('Download reference IDs'))}</button></div>`},
            {fieldtype:'HTML',fieldname:'instructions'},
            {fieldtype:'HTML',fieldname:'upload',options:`<label class="pp-import-file">${esc(__('Choose CSV or Excel file'))}<input type="file" accept=".csv,.xlsx" aria-label="${esc(__('Import file'))}"></label><p class="text-muted">${esc(__('Google Sheets: File → Download → CSV or Microsoft Excel. Use one sheet, keep the headers, and replace formulas with values. Use company-currency amounts without separators or symbols.'))}</p>`},
            {fieldtype:'HTML',fieldname:'preview'},
            {fieldtype:'Check',fieldname:'confirmed',label:__('I reviewed these records and want to save the employee changes or post these historical finances.'),hidden:1},
        ],primary_action_label:__('Review file'),primary_action:()=>review(),secondary_action_label:__('Close'),secondary_action:()=>{if(!busy)dialog.hide();}});
        function setBusy(value){
            busy=value;dialog.get_primary_btn().prop('disabled',value);dialog.get_secondary_btn().prop('disabled',value);
            dialog.$wrapper.find('input,select,.pp-download-template,.pp-download-ids').prop('disabled',value);
        }
        async function review(){
            if(busy)return;const values=dialog.get_values();if(!values)return;
            if(!file){frappe.msgprint(__('Choose a CSV or XLSX file first.'));return;}
            if(file.size>2*1024*1024){frappe.msgprint(__('Choose a file smaller than 2 MB.'));return;}
            setBusy(true);
            try {
                const content=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});
                preview=(await frappe.call({method:'plus_point.imports.preview',type:'POST',args:{kind:values.kind,company:values.company,filename:file.name,content}})).message;
                const counts=['Create','Update','Skip','Fix'].map(action=>`${preview.rows.filter(r=>r.action===action).length} ${__(action.toLowerCase())}`).join(' · ');
                dialog.fields_dict.preview.$wrapper.html(`<section class="pp-import-preview" aria-live="polite"><h3>${esc(__(preview.valid?'Review before saving':'Fix the file before importing'))}</h3><p>${esc(counts)}.${!['employees','clients','vehicles','inventory_items','warehouses','event_sites','events'].includes(values.kind)?` ${esc(__(values.kind==='stock_balances'?'Counted stock value (not cash or the value change)':'New or updated amount'))}: <strong>${esc(preview.total)} ${esc(preview.currency)}</strong>`:''}</p>
                    ${(preview.budgets||[]).filter(b=>b.enabled).map(b=>`<div class="pp-condition pp-condition-${esc(b.level)}"><div><h4>${esc(b.title)}</h4><p>${esc(b.projected)} / ${esc(b.limit)} ${esc(b.currency)}. ${esc(__(b.blocked?'Spending limit exceeded. Reduce the rows or review the budget.':b.level==='warning'?'This import reaches at least 80% of the spending budget.':'Within the spending budget.'))}</p></div><a href="/desk/project/${encodeURIComponent(b.project)}" target="_blank" rel="noopener noreferrer">${esc(__('Review spending budget'))}</a></div>`).join('')}
                    <div class="pp-import-table"><table><caption>${esc(__('Import row preview'))}</caption><thead><tr>${['Row','Source ID','Action','Record','Amount','Issue'].map(s=>`<th scope="col">${esc(__(s))}</th>`).join('')}</tr></thead><tbody>${preview.rows.map(r=>`<tr class="${r.error?'pp-import-error':''}"><td>${esc(r.row)}</td><td>${esc(r.external_id)}</td><td>${esc(__(r.action))}</td><td>${esc(r.label||r.document||'')}</td><td>${esc(r.amount??'—')}</td><td>${esc(r.error||'')}</td></tr>`).join('')}</tbody></table></div>
                    ${preview.rows.some(r=>r.error)?`<button type="button" class="btn btn-default pp-download-errors">${esc(__('Download errors to fix'))}</button>`:''}
                    <p>${esc(__('Nothing has been saved yet. Final posting checks run again when you import. If any row fails, no rows from this file are saved.'))}</p></section>`);
                dialog.fields_dict.preview.$wrapper.find('.pp-download-errors').on('click',()=>errorsFile(preview.rows));
                if(preview.valid){dialog.set_df_property('confirmed','hidden',0);dialog.set_primary_action(__(values.kind==='employees'?'Import employees':'Import and post records'),apply);}
            }finally{setBusy(false);}
        }
        async function apply(){
            if(busy||!preview?.token)return;
            if(!dialog.get_value('confirmed')){frappe.msgprint(__('Review the rows and tick the confirmation before importing.'));return;}
            setBusy(true);
            try{
                const result=(await frappe.call({method:'plus_point.imports.apply',type:'POST',args:{token:preview.token}})).message;
                preview=null;finished=true;
                dialog.fields_dict.preview.$wrapper.html(`<section class="pp-condition pp-condition-success"><div><h4>${esc(__('Import saved'))}</h4><p>${esc(__('{0} created, {1} updated, {2} skipped. Your dashboard and reports use the saved records.',[result.created,result.updated,result.skipped]))}</p></div><button type="button" class="btn btn-default pp-import-done">${esc(onClose?__(returnLabel):__('View updated dashboard'))}</button></section><details><summary>${esc(__('Saved records'))}</summary><ul>${result.rows.map(r=>`<li>${esc(r.external_id)}: <a href="/desk/${frappe.router.slug(r.doctype)}/${encodeURIComponent(r.document)}" target="_blank" rel="noopener noreferrer">${esc(r.document)}</a></li>`).join('')}</ul></details>`);
                dialog.fields_dict.preview.$wrapper.find('.pp-import-done').on('click',()=>dialog.hide());
                dialog.set_df_property('confirmed','hidden',1);
                dialog.set_primary_action(__('Import another file'),()=>{finished=false;file=null;dialog.fields_dict.upload.$wrapper.find('input').val('');reset();});
                plus_point.refresh_setup_banner?.();
            }catch{
                // Show native row details; force another preview after a stale or
                // failed batch so a retry cannot hide a changed state.
                preview=null;dialog.set_df_property('confirmed','hidden',1);dialog.set_primary_action(__('Review file again'),review);
            }finally{setBusy(false);}
        }
        dialog.$wrapper.on('hidden.bs.modal',()=>{if(onClose)onClose();else if(finished)plus_point.refresh_setup_banner?.();});
        dialog.$wrapper.addClass('pp-import-dialog');
        dialog.show();helpText();
        const upload=dialog.fields_dict.upload.$wrapper;
        upload.find('input').on('change',event=>{file=event.target.files[0];reset();});
        dialog.fields_dict.template_actions.$wrapper.find('.pp-download-template').on('click',()=>{const company=dialog.get_value('company');if(company)download('template',{kind:dialog.get_value('kind'),company});else frappe.msgprint(__('Choose your company first.'));});
        dialog.fields_dict.template_actions.$wrapper.find('.pp-download-ids').on('click',()=>{const company=dialog.get_value('company');if(company)download('references',{company});else frappe.msgprint(__('Choose your company first.'));});
        if(!defaultCompany){const info=(await frappe.call({method:'plus_point.setup_flow.status'})).message;if(info.companies.length===1)dialog.set_value('company',info.companies[0].name);}
    };
})();
