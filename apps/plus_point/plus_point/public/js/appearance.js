/* One saved Desk preference for PLUS POINT and High4Tech; no second theme state. */
(() => {
    frappe.provide('plus_point');
    const modes = {light:__('Light'), dark:__('Dark'), automatic:__('System')};
    const root = document.documentElement;
    let started = false, pending = false, scheduled = false;
    const mode = () => root.getAttribute('data-theme-mode') || 'light';
    const icon = dark => `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${dark?'<path d="M20.5 13.2A8.6 8.6 0 0 1 10.8 3.5a8.6 8.6 0 1 0 9.7 9.7Z"/>':'<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.4 1.4m11.2 11.2L19 19M5 19l1.4-1.4M17.6 6.4 19 5"/>'}</svg>`;

    plus_point.set_theme = async next => {
        if (!Object.hasOwn(modes,next) || pending || next === mode()) return;
        pending = true; render();
        try {
            const response=await fetch('/api/method/frappe.core.doctype.user.user.switch_theme',{
                method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':frappe.csrf_token},
                body:JSON.stringify({theme:{light:'Light',dark:'Dark',automatic:'Automatic'}[next]})
            });
            const result=await response.json();
            if(!response.ok||result.exc_type)throw new Error('appearance-save');
            root.setAttribute('data-theme-mode',next);
            frappe.ui.set_theme();
        } catch {
            frappe.show_alert({message:__('Could not save appearance. Please try again.'),indicator:'red'},5);
        } finally { pending = false; render(); }
    };

    function render() {
        if (!frappe.boot?.plus_point) return;
        document.body.classList.add('pp-ui');
        const footer = document.querySelector('.body-sidebar-bottom');
        if (!footer) return;
        let button = document.querySelector('.pp-theme-toggle');
        if (!button) {
            button = document.createElement('button');
            button.type = 'button'; button.className = 'btn btn-default pp-theme-toggle';
            const graphic=document.createElement('span');graphic.className='pp-theme-symbol';
            const label=document.createElement('span');label.textContent=__('Appearance');
            const value=document.createElement('span');value.className='pp-theme-value';
            button.append(graphic,label,value);footer.prepend(button);
            new frappe.ui.Dropdown({trigger:$(button),side:'top',align:'start',options:[{group:__('Appearance'),options:
                Object.entries(modes).map(([name,label])=>({name:'pp-theme-'+name,label,onclick:()=>plus_point.set_theme(name)}))
            }]});
        }
        const current=modes[mode()] || modes.light;
        const label=__('Appearance: {0}',[current]);
        if (button.getAttribute('aria-label')!==label)button.setAttribute('aria-label',label);
        const value=button.querySelector('.pp-theme-value');
        if (value.textContent!==current)value.textContent=current;
        const symbol=button.querySelector('.pp-theme-symbol'),dark=root.getAttribute('data-theme')==='dark';
        if (symbol.dataset.theme!==String(dark)) { symbol.innerHTML=icon(dark);symbol.dataset.theme=String(dark); }
        button.disabled=pending;
        if (button.getAttribute('aria-busy')!==String(pending))button.setAttribute('aria-busy',String(pending));
    }
    function schedule() {
        if (scheduled)return;
        scheduled=true;requestAnimationFrame(()=>{scheduled=false;render();});
    }
    function start() {
        if(started || !frappe.boot?.plus_point)return;
        started=true;render();
        new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
        new MutationObserver(schedule).observe(root,{attributes:true,attributeFilter:['data-theme','data-theme-mode']});
        frappe.router.on('change',schedule);
    }
    $(document).on('app_ready.pp-appearance',start);
    if(frappe.app?.sidebar)start();
})();
