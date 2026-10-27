/* Presentation only. No records, timers, counters or business actions are changed. */
(() => {
    frappe.provide('plus_point');
    const esc=value=>frappe.utils.escape_html(String(value));
    let revealObserver,flowObserver,activeFlow;
    const cleanup=()=>{revealObserver?.disconnect();flowObserver?.disconnect();activeFlow?.classList.remove('pp-flow-in-view');revealObserver=flowObserver=activeFlow=null;};
    const watch=()=>frappe.router.on('change',cleanup);
    if(frappe.router)watch();else $(document).on('app_ready.pp-dashboard-motion',watch);
    window.addEventListener('pagehide',cleanup);

    plus_point.dashboard_workflow=()=>`<section class="pp-workflow-card">
        <p class="sr-only">${esc(__('Attendance is approved before it contributes to worker earnings and client billing.'))}</p>
        <svg class="pp-workflow-graphic" viewBox="0 0 462 164" aria-hidden="true" focusable="false">
            <g class="pp-flow-connectors"><path d="M116 78H156"/><path d="M288 78C313 78 313 39 338 39"/><path d="M288 78C313 78 313 123 338 123"/></g>
            <g class="pp-flow-signals"><path pathLength="100" d="M116 78H156"/><path pathLength="100" d="M288 78C313 78 313 39 338 39"/><path pathLength="100" d="M288 78C313 78 313 123 338 123"/></g>
            <g class="pp-flow-node pp-flow-source"><rect x="8" y="59" width="108" height="38" rx="9"/><circle cx="22" cy="78" r="3"/><text x="33" y="82">${esc(__('Attendance'))}</text></g>
            <g class="pp-flow-node"><rect x="156" y="59" width="132" height="38" rx="9"/><text x="171" y="82">${esc(__('Approved work'))}</text></g>
            <g class="pp-flow-node"><rect x="338" y="20" width="116" height="38" rx="9"/><text x="350" y="43">${esc(__('Worker earnings'))}</text></g>
            <g class="pp-flow-node"><rect x="338" y="104" width="116" height="38" rx="9"/><text x="355" y="127">${esc(__('Client billing'))}</text></g>
        </svg>
        <div class="pp-workflow-compact" aria-hidden="true"><span class="pp-compact-node pp-compact-source">${esc(__('Attendance'))}</span><i class="pp-compact-line"></i>
            <span class="pp-compact-node">${esc(__('Approved work'))}</span><i class="pp-compact-line"></i>
            <div class="pp-compact-branches"><span class="pp-compact-node">${esc(__('Worker earnings'))}</span><span class="pp-compact-node">${esc(__('Client billing'))}</span></div></div></section>`;

    plus_point.present_dashboard=root=>{
        cleanup();
        if(!root.classList.contains('pp-motion-dashboard'))return;
        const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
        const flow=activeFlow=root.querySelector('.pp-workflow-card');
        if(flow&&!reduced&&'IntersectionObserver' in window){
            flowObserver=new IntersectionObserver(entries=>entries.forEach(entry=>entry.target.classList.toggle('pp-flow-in-view',entry.isIntersecting)));
            flowObserver.observe(flow);
        }
        root.dataset.presentationReady='true';
    };
})();
