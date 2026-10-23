/* Layout only: retain native report filters, data, sorting, links and exports. */
(() => {
    frappe.provide('plus_point');
    const titles={'PLUS POINT Project Finances':'Project finances','PLUS POINT Worker Statement':'Worker statement'};
    let current,reportName,root,observer,frame,lastWidth;
    const active=()=>current&&frappe.get_route()[0]==='query-report'&&frappe.get_route()[1]===reportName&&current.report_name===reportName;
    plus_point.business_report_options=options=>({
        ...options,inlineFilters:false,cellHeight:44,minimumColumnWidth:40,
        ...(options.columns?{columns:options.columns.map(column=>{
            const key=column.id||column.fieldname;
            const width=key==='project'?300:key==='customer'?240:key==='site'?210:
                Math.max(Number(column.width)||150,Math.min(230,String(column.name||column.label||'').length*7+34));
            return {...column,width};
        })}:{})
    });
    function fit(){
        frame=null;if(!active()||!current.datatable||!root?.isConnected)return;
        const table=current.datatable,count=table.datamanager.getRows().length;
        const available=Math.max(176,innerHeight-table.bodyScrollable.getBoundingClientRect().top-76);
        const height=Math.max(88,Math.min(count*44+24,available,560));
        root.style.setProperty('--pp-report-body-height',height+'px');
        table.viewportHeight=null;table.setDimensions();table.rowmanager.refreshRows();
        table.bodyScrollable.tabIndex=0;
        table.bodyScrollable.setAttribute('aria-label',__('Report results. Scroll horizontally for more columns.'));
        const footer=current.$report_footer?.get(0);
        if(footer&&!current.tree_report&&!footer.querySelector('.pp-report-scroll-hint')){
            const execution=footer.querySelector('.pull-right'),hint=document.createElement('span');
            hint.className='pp-report-scroll-hint';hint.textContent=__('Scroll horizontally to see all columns. Use the filters above to narrow the results.');
            footer.replaceChildren(hint);if(execution)footer.append(execution);
        }
    }
    function schedule(){if(active()&&!frame)frame=requestAnimationFrame(fit);}
    plus_point.mount_business_report=report=>{
        current=report;reportName=report.report_name;
        const next=report.page.wrapper.get(0);
        if(root!==next){observer?.disconnect();root?.classList.remove('pp-business-report','pp-worker-statement');root=next;lastWidth=0;}
        root.classList.add('pp-business-report');root.classList.toggle('pp-worker-statement',reportName==='PLUS POINT Worker Statement');
        report.$report_message?.addClass('pp-report-message');report.page.set_title(__(titles[reportName]));
        for(const control of report.filters||[]){
            const wrapper=control.$wrapper?.get(0);if(!wrapper||wrapper.querySelector('.pp-report-filter-label'))continue;
            const label=document.createElement('label');label.className='pp-report-filter-label';label.textContent=__(control.df.label);
            const input=control.$input?.get(0);
            if(input){input.id=input.id||'pp-report-filter-'+control.df.fieldname;label.htmlFor=input.id;input.setAttribute('aria-label',__(control.df.label));}
            wrapper.prepend(label);
        }
        if(!observer){observer=new ResizeObserver(entries=>{const width=entries[0].contentRect.width;if(Math.abs(width-lastWidth)>1){lastWidth=width;schedule();}});}
        observer.observe(root);schedule();
    };
    plus_point.fit_business_report=()=>{if(frappe.query_report&&titles[frappe.query_report.report_name])plus_point.mount_business_report(frappe.query_report);};
    addEventListener('resize',schedule,{passive:true});
    document.addEventListener('pp:display-currency',()=>{
        if(active()&&reportName==='PLUS POINT Project Finances'){
            const currency=frappe.boot.plus_point.display_currency;
            if(currency&&current.get_filter_value('display_currency')!==currency)current.set_filter_value('display_currency',currency);
        }
    });
    frappe.router.on('change',()=>{
        const route=frappe.get_route();if(route[0]==='query-report'&&titles[route[1]])return;
        observer?.disconnect();observer=null;root?.classList.remove('pp-business-report','pp-worker-statement');root?.style.removeProperty('--pp-report-body-height');
        current=null;reportName=null;root=null;if(frame)cancelAnimationFrame(frame);frame=null;
    });
})();
