/* One saved step at a time; skipping releases the rest of Desk immediately. */
(() => {
    frappe.provide('plus_point');
    const esc=value=>frappe.utils.escape_html(String(value ?? ''));
    const call=(method,args={})=>frappe.call({method:'plus_point.setup_flow.'+method,args,type:'POST'}).then(r=>r.message);
    let opening=false, autoChecked=false;
    const choice=(fieldname,label,options,defaultValue)=>({fieldtype:'Select',fieldname,label:__(label),options:options.join('\n'),default:defaultValue || options[0]});
    const input=(fieldtype,fieldname,label,extra={})=>({fieldtype,fieldname,label:__(label),...extra});
    function fields(saved, companies) {
        const company=saved.company;
        switch(saved.step) {
        case 'company': return [choice('mode','Your business',companies.length?['Use an existing company','Create a company']:['Create a company']),
            input('Link','company','Company',{options:'Company',default:companies.length===1?companies[0].name:undefined,depends_on:'eval:doc.mode==="Use an existing company"',mandatory_depends_on:'eval:doc.mode==="Use an existing company"'}),
            ...[input('Data','company_name','Business name'),input('Data','abbr','Short company code',{description:__('A short unique code, for example PP.')}),input('Link','country','Country',{options:'Country',default:'Pakistan'}),input('Link','currency','Accounting currency',{options:'Currency',default:'PKR'})].map(f=>({...f,depends_on:'eval:doc.mode==="Create a company"',mandatory_depends_on:'eval:doc.mode==="Create a company"'}))];
        case 'worker': return [choice('mode','Worker',['Add a worker','Choose an existing worker']),
            input('Link','employee','Existing worker',{options:'Employee',get_query:()=>({filters:{company,status:'Active'}}),depends_on:'eval:doc.mode==="Choose an existing worker"',mandatory_depends_on:'eval:doc.mode==="Choose an existing worker"'}),
            ...[input('Data','first_name','First name',{reqd:1}),input('Data','last_name','Last name'),input('Link','gender','Gender',{options:'Gender',reqd:1}),input('Date','date_of_birth','Date of birth',{reqd:1}),input('Date','date_of_joining','Joining date',{default:frappe.datetime.get_today(),reqd:1}),input('Data','cell_number','Phone number')].map(f=>{const required=f.reqd;delete f.reqd;return {...f,depends_on:'eval:doc.mode==="Add a worker"',mandatory_depends_on:required?'eval:doc.mode==="Add a worker"':undefined};})];
        case 'site': return [choice('mode','Work location',['Add a site','Choose an existing site']),
            input('Link','site','Existing site',{options:'PP Site',get_query:()=>({query:'plus_point.setup_flow.site_query',filters:{company}}),depends_on:'eval:doc.mode==="Choose an existing site"',mandatory_depends_on:'eval:doc.mode==="Choose an existing site"'}),
            input('Data','site_name','Site name',{depends_on:'eval:doc.mode==="Add a site"',mandatory_depends_on:'eval:doc.mode==="Add a site"'}),
            input('Small Text','address','Site address',{depends_on:'eval:doc.mode==="Add a site"'}),
            {...choice('job_mode','Client job',['Use an existing project','Create a project']),depends_on:'eval:doc.mode==="Add a site"'},
            input('Link','project','Project',{options:'Project',get_query:()=>({filters:{company}}),depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Use an existing project"',mandatory_depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Use an existing project"'}),
            input('Data','project_name','New project name',{depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Create a project"',mandatory_depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Create a project"'}),
            {...choice('client_mode','Client',['Use an existing client','Add a client']),depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Create a project"'},
            input('Link','customer','Client',{options:'Customer',depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Create a project" && doc.client_mode==="Use an existing client"',mandatory_depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Create a project" && doc.client_mode==="Use an existing client"'}),
            input('Data','customer_name','New client name',{depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Create a project" && doc.client_mode==="Add a client"',mandatory_depends_on:'eval:doc.mode==="Add a site" && doc.job_mode==="Create a project" && doc.client_mode==="Add a client"'})];
        case 'terms': return [choice('mode','Client billing',['Use existing billing terms','Add billing terms']),
            input('Link','contract_terms','Billing terms',{options:'PP Contract Terms',get_query:()=>({filters:{project:saved.project,status:'Active'}}),depends_on:'eval:doc.mode==="Use existing billing terms"',mandatory_depends_on:'eval:doc.mode==="Use existing billing terms"'}),
            ...[{...choice('billing_model','How do you bill this client?',['Daily','Fixed'])},input('Currency','fixed_amount','Total fixed client price',{depends_on:'eval:doc.mode==="Add billing terms" && doc.billing_model==="Fixed"',mandatory_depends_on:'eval:doc.mode==="Add billing terms" && doc.billing_model==="Fixed"'}),input('Date','effective_start','Agreement starts',{default:frappe.datetime.get_today(),reqd:1}),input('Small Text','agreement','What has the client agreed to?',{reqd:1,description:__('Record the actual agreed work and billing arrangement. This creates your internal contract record.')})].map(f=>{const required=f.reqd;delete f.reqd;return {...f,depends_on:f.depends_on || 'eval:doc.mode==="Add billing terms"',mandatory_depends_on:f.mandatory_depends_on || (required?'eval:doc.mode==="Add billing terms"':undefined)};})];
        case 'assignment': return [input('HTML','review','',{options:`<p>${esc(__('Worker'))}: <strong>${esc(saved.worker_label || saved.employee)}</strong><br>${esc(__('Work site'))}: <strong>${esc(saved.site_label || saved.site)}</strong></p>`}),
            input('Date','start_date','First work day',{reqd:1,default:frappe.datetime.get_today()}),input('Date','end_date','Last work day (optional)'),
            input('Currency','wage_rate','Worker wage per full day',{reqd:1,description:__('A half-day earns half this wage. This does not record attendance or payment.')}),
            input('Currency','client_rate','Client charge per worker-day',{default:0,description:__('Daily billing: enter the agreed client rate. Fixed billing: use 0; client revenue comes from milestones.')})];
        default:return [];
        }
    }
    const copy={
        company:['Choose your business','Keep each company’s workers and accounts together. We only need this once.'],
        worker:['Add your first worker','Start with one person. You can import the rest from a spreadsheet at any time. A worker profile does not create a login.'],
        site:['Where will they work?','Choose a location and the client job it belongs to. Add a new job here if you are starting from scratch.'],
        terms:['Set the client agreement','Your worker’s wage and what you charge the client are separate. Choose the billing agreement for this job.'],
        assignment:['Assign the worker to the site','Set the dates and daily rates. You will review attendance before any wages are approved.'],
        import:['Bring your existing records','Your first worker and assignment are saved. Import your other employees or historical finances now, or do it later.'],
        done:['You’re ready to record work','Your worker, work site and assignment are saved. Next, mark attendance and review the draft before approving earnings.'],
    };
    function focusBackground(block) {
        document.body.classList.toggle('pp-setup-active',block);
        document.querySelectorAll('#body, .body-sidebar').forEach(el=>{
            if(block){el.dataset.ppWasInert=el.inert?'1':'0';el.inert=true;}
            else {el.inert=el.dataset.ppWasInert==='1';delete el.dataset.ppWasInert;}
        });
    }
    function show(saved,companies) {
        const [title,description]=copy[saved.step];
        const index=['company','worker','site','terms','assignment','import','done'].indexOf(saved.step);
        const progress=`<div class="pp-setup-progress" aria-label="${esc(__('Setup progress'))}"><span>${esc(saved.step==='done'?__('Setup complete'):__('Step {0} of 6',[index+1]))}</span><progress max="6" value="${Math.min(index,6)}"></progress></div><p>${esc(__(description))}</p>`;
        let busy=false,leaving=false,afterHide;
        const dialog=new frappe.ui.Dialog({title:__(title),static:true,size:'large',
            fields:[{fieldtype:'HTML',fieldname:'intro',options:progress},...fields(saved,companies),
                ...(saved.step==='import'?[{fieldtype:'HTML',fieldname:'import_actions',options:`<button type="button" class="btn btn-default pp-setup-import">${esc(__('Import employees or finances'))}</button>`}]:[])],
            primary_action_label:__(saved.step==='done'?'Open my dashboard':saved.step==='import'?'Finish setup':'Save and continue'),
            async primary_action(values){
                if(busy)return;busy=true;dialog.disable_primary_action();
                try {
                    if(saved.step==='done'){leaving=true;dialog.hide();plus_point.refresh_setup_banner?.();return;}
                    // Hidden alternatives never carry a stale selection into a save.
                    if(values.mode==='Create a company')delete values.company;
                    if(values.mode==='Add a worker')delete values.employee;
                    if(values.mode==='Add a site')delete values.site;
                    if(values.job_mode==='Create a project')delete values.project;
                    if(values.client_mode==='Add a client')delete values.customer;
                    if(values.mode==='Add billing terms')delete values.contract_terms;
                    if(values.billing_model==='Daily')values.fixed_amount=0;
                    const next=await call('advance',{step:saved.step,values:JSON.stringify(values)});
                    leaving=true;afterHide=()=>show(next,companies);dialog.hide();
                } finally {busy=false;dialog.enable_primary_action();}
            },secondary_action_label:__('Skip setup and explore'),async secondary_action(){
                if(busy)return;busy=true;
                try{await call('control',{action:'skip'});leaving=true;dialog.hide();plus_point.refresh_setup_banner?.();}
                finally{busy=false;}
            }});
        dialog.$wrapper.addClass('pp-setup-dialog');
        dialog.onhide=()=>{focusBackground(false);if(!leaving)call('control',{action:'skip'});afterHide?.();};
        dialog.show();focusBackground(true);
        dialog.fields_dict.import_actions?.$wrapper.find('.pp-setup-import').on('click',()=>{
            leaving=true;afterHide=()=>plus_point.open_import(saved.company,()=>show(saved,companies));dialog.hide();
        });
    }
    plus_point.open_setup=async()=>{
        if(opening)return;opening=true;
        try {const info=await call('status');const saved=await call('control',{action:'resume'});show(saved,info.companies);}
        finally{opening=false;}
    };
    plus_point.mount_setup=async root=>{
        if(!root || frappe.boot.plus_point?.is_platform || !frappe.user.has_role('System Manager'))return;
        const update=async()=>{
            root.replaceChildren();
            try {
                const info=await call('status');
                if(!root.isConnected || !info.auto_start)return;
                root.innerHTML=`<div><strong>${esc(__('Finish setting up your business'))}</strong><p>${esc(__('Add your first worker, work site and assignment. You can skip and explore anytime.'))}</p></div><button class="btn btn-default pp-open-setup">${esc(__('Continue setup'))}</button>`;
                root.querySelector('.pp-open-setup').onclick=plus_point.open_setup;
                if(!autoChecked){autoChecked=true;show(info.state,info.companies);}
            }catch { /* Help remains available for a deliberate setup retry. */ }
        };
        plus_point.refresh_setup_banner=()=>{plus_point.mount_dashboard?.(root.parentElement.querySelector('.pp-dashboard'));return update();};
        await update();
    };
})();
