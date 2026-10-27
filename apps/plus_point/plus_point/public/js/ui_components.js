/* Shared presentation primitives. Native fields, Dialog and server permissions own behavior. */
(()=>{
 window.plus_point ||= {};
 const pp=plus_point,esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const symbols={success:'check',error:'close',warning:'warning',info:'info',neutral:'settings',loading:'refresh'};
 const icon=name=>pp.icon?.(name)||'<svg width=24 height=24 viewBox="0 0 24 24" aria-hidden="true"><use href="/assets/plus_point/images/tabler.svg#'+name+'"></use></svg>';
 const tones={green:'success',red:'error',orange:'warning',yellow:'warning',blue:'info'};
 pp.ui={
  heading(title,{description='',symbol='',actions='',className=''}={}){
   return '<header class="pp-ui-section-heading pp-section-heading '+esc(className)+'"><div class="pp-ui-heading-title pp-agreement-card-title">'+(symbol?'<span class="pp-ui-heading-icon pp-agreement-icon" aria-hidden="true">'+icon(symbol)+'</span>':'')+'<div><h3>'+esc(__(title))+'</h3>'+(description?'<p>'+esc(__(description))+'</p>':'')+'</div></div>'+actions+'</header>';
  },
  panel(title,description='',symbol='document'){
   const section=document.createElement('section');section.className='pp-ui-panel pp-builder-card';
   section.innerHTML=pp.ui.heading(title,{description,symbol,className:'pp-ui-panel-heading'})+'<div class="pp-ui-panel-body pp-builder-card-body"></div>';return section;
  },
  badge(label,tone='neutral'){return '<span class="pp-ui-badge" data-tone="'+esc(tone)+'">'+esc(__(label))+'</span>';},
  metric(symbol,value,label,note='',href=''){
   const tag=href?'a':'div';return '<'+tag+(href?' href="'+esc(href)+'"':'')+' class="pp-ui-metric pp-agreement-metric"><span class="pp-agreement-metric-icon" aria-hidden="true">'+(pp.record_profile_ui?.icon(symbol)||icon(symbol))+'</span><div><span>'+esc(__(label))+'</span><strong>'+esc(value||'—')+'</strong>'+(note?'<small>'+esc(note)+'</small>':'')+'</div></'+tag+'>';
  },
  feedback(node,{message,tone='info',rich=false}={}){
   if(!node)return;tone=tones[tone]||tone;const text=String(message??node.textContent).trim();
   if(!text){node.replaceChildren();node.classList.remove('pp-ui-feedback');return;}
   if(node.dataset.uiMessage===text&&node.dataset.tone===tone&&node.classList.contains('pp-ui-feedback')&&node.querySelector(':scope > .pp-ui-feedback-icon'))return;
   const content=document.createElement('div');content.className='pp-ui-feedback-content';
   if(rich){while(node.firstChild)content.append(node.firstChild);}else content.textContent=text;
   const mark=document.createElement('span');mark.className='pp-ui-feedback-icon';mark.setAttribute('aria-hidden','true');mark.innerHTML=icon(symbols[tone]||'info');
   node.replaceChildren(mark,content);node.classList.add('pp-ui-feedback');node.classList.remove('pp-freddy-host');node.dataset.tone=tone;node.dataset.uiMessage=text;
  },
  optional(node,title,{open=false}={}){
   if(!node||node.closest('.pp-ui-disclosure'))return;
   const box=document.createElement('details');box.className='pp-ui-disclosure';box.open=open;
   const summary=document.createElement('summary');summary.textContent=__(title);node.before(box);box.append(summary,node);return box;
  },
  nativeFilters(scope){
   if(!document.body.classList.contains('pp-customer-app'))return;
   for(const bar of scope.querySelectorAll('.page-form .filter-section')){
    if(bar.querySelector('.pp-native-filter-tools'))continue;
    const controls=[...bar.children].filter(node=>node.matches('.filter-selector,.sort-selector'));
    if(!controls.length)continue;
    const details=document.createElement('details');details.className='pp-native-filter-tools';
    const summary=document.createElement('summary');summary.innerHTML=esc(__('More filters'))+icon('down');
    const content=document.createElement('div');content.className='pp-native-filter-content';details.append(summary,content);controls[0].before(details);content.append(...controls);
   }
  },
  enhance(scope=document){
   if(scope===document){for(const root of [document.querySelector('.page-container:not([style*="display: none"])'),...document.querySelectorAll('.modal.show')])if(root)pp.ui.enhance(root);return;}
   pp.ui.nativeFilters(scope);
   for(const dialog of scope.querySelectorAll('.modal-content:not([data-pp-ui])')){
    dialog.dataset.ppUi='true';dialog.classList.add('pp-ui-dialog');
   }
   for(const toast of scope.querySelectorAll('.es-toast')){
    const tone=[...toast.classList].map(v=>tones[v.replace(/^.*--/,'')]).find(Boolean)||toast.querySelector('[data-feedback-tone]')?.dataset.feedbackTone;
    if(tone&&toast.dataset.tone!==tone)toast.dataset.tone=tone;
   }
  }
 };
 const start=()=>{if(!frappe.boot?.plus_point||frappe.boot.plus_point.is_platform)return;pp.watch_ui?.('ui-components',pp.ui.enhance);pp.ui.enhance();};
 if(window.frappe?.app?.sidebar)start();else if(window.jQuery)$(document).on('app_ready.pp-components',start);
})();
