/* Keyboard-accessible 91-day client activity. Values come from approved work only. */
(() => {
    frappe.provide('plus_point');
    const esc=value=>frappe.utils.escape_html(String(value??''));
    const num=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(value)||0);
    const level=value=>value<=0?0:value<=1?1:value<=3?2:value<=6?3:4;
    function calendar(days,client,company){
        if(!days.length)return '';
        const date=value=>new Date(value+'T12:00:00');
        const offset=(date(days[0].date).getDay()+6)%7;
        const weeks=Math.ceil((offset+days.length)/7);
        const firstYear=days[0].date.slice(0,4),lastYear=days.at(-1).date.slice(0,4);
        const year=firstYear===lastYear?firstYear:`${firstYear.slice(2)}–${lastYear.slice(2)}`;
        const months=[];
        // A week's Thursday determines its month, keeping boundary labels apart.
        for(let week=0;week<weeks;week++){
            const day=days[Math.max(0,Math.min(days.length-1,week*7+3-offset))];
            const key=day.date.slice(0,7);
            if(months.at(-1)?.key!==key)months.push({key,week,date:day.date});
        }
        const monthLabels=months.filter((month,index)=>index!==0||months.length===1||months[1].week>=2).map((month,index,visible)=>{
            const start=Math.min(month.week,Math.max(0,weeks-2));
            const next=visible[index+1]?Math.min(visible[index+1].week,Math.max(0,weeks-2)):weeks;
            const span=Math.max(1,next-start);
            const label=new Intl.DateTimeFormat(undefined,{month:'short'}).format(date(month.date));
            const title=new Intl.DateTimeFormat(undefined,{month:'long',year:'numeric'}).format(date(month.date));
            return `<span class="pp-heatmap-month" data-month="${esc(month.key)}" style="grid-column:${start+2}/span ${span}" title="${esc(title)}">${esc(label)}</span>`;
        }).join('');
        return `<div class="pp-heatmap-scroll"><div class="pp-heatmap" role="group" aria-label="${esc(__('{0}: approved daily worker-days, Monday to Sunday',[client.title]))}" data-customer="${esc(client.name)}" data-company="${esc(company)}" style="--pp-weeks:${weeks};--pp-calendar-width:${34+weeks*16}px">
            <span class="pp-heatmap-year" title="${esc(firstYear===lastYear?firstYear:firstYear+'–'+lastYear)}">${esc(year)}</span>${monthLabels}
            ${['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map((day,index)=>`<span class="pp-heatmap-weekday" style="grid-row:${index+2}" aria-hidden="true">${esc(__(day))}</span>`).join('')}
            ${days.map((day,index)=>{const position=offset+index,label=`${day.date}: ${num(day.units)} ${__('worker-days')}, ${day.entries} ${__('approved entries')}`;return `<button type="button" class="pp-day pp-heat-${level(Number(day.units))}" data-day="${day.date}" style="grid-column:${Math.floor(position/7)+2};grid-row:${position%7+2}" tabindex="${index===days.length-1?'0':'-1'}" title="${esc(label)}" aria-label="${esc(label)}"></button>`;}).join('')}</div></div>`;
    }
    plus_point.activity_markup=(activity,company)=>{
        if(!activity?.clients?.length)return `<div class="pp-activity-empty"><p>${esc(__('No client work recorded yet. Add a client project and approve its attendance to build this history.'))}</p><a href="/desk/customer">${esc(__('View clients'))}</a></div>`;
        return `<div class="pp-client-activity-grid">${activity.clients.map(client=>{
            return `<article class="pp-client-activity"><header><div><a href="/desk/customer/${encodeURIComponent(client.name)}">${esc(client.title)}</a><p>${esc(__('{0} projects · {1} days with work',[client.projects,client.active_days]))}</p></div><strong>${esc(num(client.units))}<small>${esc(__('worker-days'))}</small></strong></header>
                ${calendar(client.days,client,company)}
                <footer><span>${esc(activity.start)} – ${esc(activity.end)}</span><span>${esc(__('Less'))} ${[0,1,2,3,4].map(n=>`<i class="pp-heat-${n}" aria-hidden="true"></i>`).join('')} ${esc(__('More'))}</span></footer>
                <p class="pp-activity-note">${esc(__('Longest run: {0} calendar days. Select a day for workers, sites and quantities.',[client.longest_streak]))}</p></article>`;
        }).join('')}</div><p class="pp-activity-note">${esc(__('Approved worker-days, not login activity. Two half-days equal one worker-day; an empty square does not prove absence. Colour bands: 0, up to 1, up to 3, up to 6, more than 6 worker-days.'))}${activity.client_count>activity.clients.length?` ${esc(__('Showing {0} of {1} clients. Open any client to see its own activity.',[activity.clients.length,activity.client_count]))}`:''}</p>`;
    };
    async function openDay(button){
        const map=button.closest('.pp-heatmap');button.disabled=true;
        try{
            const data=(await frappe.call({method:'plus_point.activity.day_detail',args:{company:map.dataset.company,customer:map.dataset.customer,day:button.dataset.day}})).message;
            frappe.msgprint({title:__('Work on {0}',[data.date]),wide:true,message:`<p>${esc(num(data.worker_days))} ${esc(__('approved worker-days'))}</p>${data.rows.length?`<div class="pp-dashboard-table-wrap"><table class="pp-dashboard-table"><thead><tr>${['Worker','Site','Worker-days'].map(t=>`<th>${esc(__(t))}</th>`).join('')}</tr></thead><tbody>${data.rows.map(row=>`<tr><th><a href="/desk/pp-work-entry/${encodeURIComponent(row.name)}">${esc(row.worker)}</a></th><td>${esc(row.site_title)}</td><td>${esc(num(row.units))}</td></tr>`).join('')}</tbody></table></div>`:`<p>${esc(__('No approved work entries for this date. Drafts are excluded.'))}</p><a href="/desk/pp-daily-register?work_date=${encodeURIComponent(data.date)}">${esc(__('Review attendance'))}</a>`}`});
        }finally{button.disabled=false;}
    }
    plus_point.bind_activity=root=>{
        root.querySelectorAll('.pp-heatmap').forEach(map=>{
            const buttons=[...map.querySelectorAll('.pp-day')];
            buttons.forEach((button,index)=>{
                button.addEventListener('click',()=>openDay(button));
                button.addEventListener('keydown',event=>{
                    const move={ArrowLeft:-7,ArrowRight:7,ArrowUp:-1,ArrowDown:1};
                    if(!(event.key in move))return;
                    event.preventDefault();const next=buttons[Math.max(0,Math.min(buttons.length-1,index+move[event.key]))];
                    buttons.forEach(b=>b.tabIndex=-1);next.tabIndex=0;next.focus();
                });
            });
        });
    };
    $(document).on('form-refresh.pp-client-activity',async(_event,frm)=>{
        if(!['Customer','Company'].includes(frm.doctype)||frappe.boot.plus_point?.is_platform||!frappe.user.has_role('System Manager'))return;
        if(frm.is_new()){frm.__pp_activity_body?.remove();return;}
        const name=frm.doc.name,seq=frm.__pp_activity_seq=(frm.__pp_activity_seq||0)+1;
        if(!frm.__pp_activity_body?.get(0)?.isConnected)frm.__pp_activity_body=$('<section class="pp-client-activity-section" aria-label="'+esc(__('Client work activity'))+'"></section>').prependTo(frm.form_wrapper);
        frm.__pp_activity_body.html(`<p role="status">${esc(__('Loading work activity…'))}</p>`);
        try{
            const legal=frm.doctype==='Company';
            const data=(await frappe.call({method:legal?'plus_point.dashboard.overview':'plus_point.activity.customer_summary',args:legal?{company:name}:{customer:name,company:plus_point.dashboard_company},silent:true})).message;
            if(seq!==frm.__pp_activity_seq||frm.doc.name!==name)return;
            frm.__pp_activity_body.html(`<h3>${esc(__('Work activity'))}</h3><p class="pp-activity-note">${esc(data.company||'')}</p>${plus_point.activity_markup(legal?data.activity:data,data.company)}`);
            plus_point.bind_activity(frm.__pp_activity_body.get(0));
        }catch {
            if(seq!==frm.__pp_activity_seq||frm.doc.name!==name)return;
            frm.__pp_activity_body.html(`<p>${esc(__('Work activity could not load.'))}</p><button type="button" class="btn btn-default">${esc(__('Try again'))}</button>`);
            frm.__pp_activity_body.find('button').on('click',()=>$(document).trigger('form-refresh',[frm]));
        }
    });
})();
