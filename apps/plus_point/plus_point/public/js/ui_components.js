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
  amount(value){
   const raw=String(value??0),match=raw.match(/^(-?)(\d+)(?:\.(\d+))?$/);if(!match)return '—';
   const whole=new Intl.NumberFormat(undefined,{maximumFractionDigits:0}).format(BigInt(match[1]+match[2]));
   const decimal=new Intl.NumberFormat().formatToParts(1.1).find(p=>p.type==='decimal')?.value||'.';
   return (match[1]&&BigInt(match[2])===0n?'-':'')+whole+(match[3]&&/[1-9]/.test(match[3])?decimal+match[3].slice(0,2):'');
  },
  kpi(label,value,{symbol='money',unit='',note='',href='',tone='neutral'}={}){
   return '<a class="pp-kpi" data-tone="'+esc(tone)+'" href="'+esc(href)+'"><span class="pp-kpi-icon" aria-hidden="true">'+icon(symbol)+'</span><div class="pp-kpi-content"><span class="pp-kpi-label">'+esc(__(label))+'</span><strong class="pp-kpi-value" data-fit-number>'+esc(pp.ui.amount(value))+'</strong>'+(unit?'<span class="pp-kpi-unit">'+esc(unit)+'</span>':'')+'<small>'+esc(__(note))+'</small></div></a>';
  },
  fit_numbers(root){
   const nodes=[...root.querySelectorAll('[data-fit-number]')];nodes.forEach(n=>{n.style.fontSize='32px';n.closest('.pp-kpi')?.classList.remove('is-long');});
   nodes.forEach(n=>{const range=document.createRange();range.selectNodeContents(n);if(32*(n.clientWidth-2)/Math.max(1,range.getBoundingClientRect().width)<20)n.closest('.pp-kpi')?.classList.add('is-long');});
   const sizes=nodes.map(n=>{const range=document.createRange();range.selectNodeContents(n);const width=range.getBoundingClientRect().width;return Math.max(12,Math.min(32,32*(n.clientWidth-2)/Math.max(1,width)));});
   nodes.forEach((n,i)=>n.style.fontSize=sizes[i]+'px');
  },
  analytics_card(title,symbol,body,{actions='',className=''}={}){
   return '<section class="pp-analytics-card '+esc(className)+'">'+pp.ui.heading(title,{symbol,actions})+'<div class="pp-analytics-body">'+body+'</div></section>';
  },
  bind_input(input,df){
   if(input.ppField)return input.ppField;
   const wrapper=input.closest('label')||input.parentElement;wrapper.classList.add('frappe-control');input.type='text';input.setAttribute('aria-label',df.label);
   const control={df,$input:$(input),$wrapper:$(wrapper),set_focus:()=>input.focus()};input.ppField=control;
   pp.enhance_inputs({fields_dict:{[df.fieldname]:control}});return control;
  },
  panel(title,description='',symbol='document'){
   const section=document.createElement('section');section.className='pp-ui-panel pp-builder-card';
   section.innerHTML=pp.ui.heading(title,{description,symbol,className:'pp-ui-panel-heading'})+'<div class="pp-ui-panel-body pp-builder-card-body"></div>';return section;
  },
  badge(label,tone='neutral'){return '<span class="pp-ui-badge" data-tone="'+esc(tone)+'">'+esc(__(label))+'</span>';},
  metric(symbol,value,label,note='',href=''){
   const tag=href?'a':'div';return '<'+tag+(href?' href="'+esc(href)+'"':'')+' class="pp-ui-metric pp-agreement-metric"><span class="pp-agreement-metric-icon" aria-hidden="true">'+(pp.record_profile_ui?.icon(symbol)||icon(symbol))+'</span><div><span>'+esc(__(label))+'</span><strong title="'+esc(value||'—')+'">'+esc(value||'—')+'</strong><small'+(!note?' aria-hidden="true" class="pp-metric-note-empty"':'')+'>'+esc(note||'\u00a0')+'</small></div></'+tag+'>';
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
   const shell=document.createElement('div');shell.className='pp-disclosure-shell';
   const summary=document.createElement('summary'),label=document.createElement('span'),actions=document.createElement('div');label.textContent=__(title);actions.className='pp-disclosure-actions pp-actions';summary.append(label);node.before(shell);shell.append(box,actions);box.append(summary,node);
   // Move the real controls, never clone handlers or maintain a second action state.
   let source,home;
   const sync=()=>{const current=node.querySelector('.pp-resource-heading .pp-actions')||node.querySelector(':scope > header .pp-builder-card-actions,:scope > header .pp-actions')||node.querySelector('[data-add-condition]');if(current&&current!==source){source?.remove();home?.remove();source=current;home=document.createComment('disclosure actions');source.before(home);}actions.hidden=box.open||!source;shell.classList.toggle('has-actions',!!source&&!box.open);if(!source||!home?.isConnected)return;if(box.open)home.after(source);else if(source.parentElement!==actions)actions.replaceChildren(source);};
   box.ppActionsSync=sync;box.addEventListener('toggle',sync);actions.addEventListener('click',event=>{event.stopPropagation();if(event.target.closest('button,a'))box.open=true;});sync();
   return box;
  },
  nativeFilters(scope){
   if(!document.body.classList.contains('pp-customer-app'))return;
   const pages=scope.matches?.('.page-container')?[scope]:scope.closest?.('.page-container')?[scope.closest('.page-container')]:[...scope.querySelectorAll('.page-container')];
   for(const page of pages){
    const bar=page.querySelector('.page-form .filter-section');if(!bar)continue;
    let owner=page.querySelector('.pp-native-filter-tools');
    const controls=[...page.querySelectorAll('.page-form .filter-selector,.page-form .sort-selector')],status=page.querySelector('[data-fieldname=pp_planning_status]');if(status)controls.unshift(status);
    if(!controls.length)continue;
    if(!owner){owner=document.createElement('details');owner.className='pp-native-filter-tools';const summary=document.createElement('summary');summary.innerHTML=icon('filter')+esc(__('Filters'))+icon('down');const content=document.createElement('div');content.className='pp-native-filter-content';owner.append(summary,content);bar.append(owner);}
    for(const node of controls)if(!owner.contains(node)&&!node.contains(owner))owner.querySelector('.pp-native-filter-content').append(node);
   }
  },
  enhance(scope=document){
   if(scope===document){for(const root of [document.querySelector('.page-container:not([style*="display: none"])'),...document.querySelectorAll('.modal.show')])if(root)pp.ui.enhance(root);return;}
   pp.ui.nativeFilters(scope);
   for(const input of scope.querySelectorAll('input[type=checkbox],input[type=radio]'))if(input.closest('.pp-operations,.pp-worker-profile,.pp-crew-picker,.modal')){input.classList.add('pp-figma-check');input.closest('label')?.classList.add('pp-figma-choice-label');}
   for(const source of scope.querySelectorAll('.frappe-control'))if(source.ppFigmaControl)pp.ui.field(source.ppFigmaControl);
   pp.ui.selects(scope);
   for(const dialog of scope.querySelectorAll('.modal-content:not([data-pp-ui])')){
    dialog.dataset.ppUi='true';dialog.classList.add('pp-ui-dialog');
   }
   for(const toast of scope.querySelectorAll('.es-toast')){
    const tone=[...toast.classList].map(v=>tones[v.replace(/^.*--/,'')]).find(Boolean)||toast.querySelector('[data-feedback-tone]')?.dataset.feedbackTone;
    if(tone&&toast.dataset.tone!==tone)toast.dataset.tone=tone;
   }
  }
 };
 // Figma input composition: preserve Frappe's real input and value lifecycle.
 // Only decorate owned customer controls; no shadow form or second value store.
 let fieldSequence=0;
 const asset=(name,className)=>{const node=document.createElement('img');node.src='/assets/plus_point/images/figma/'+name+'.svg';node.alt='';node.setAttribute('aria-hidden','true');if(className)node.className=className;return node;};
 pp.ui.field=control=>{
  if(!document.body.classList.contains('pp-customer-app')||!control?.$wrapper||!control.$input)return;
  const root=control.$wrapper.get(0),input=control.$input.get(0),df=control.df;if(!root||!input)return;
  root.ppFigmaControl=control;root.classList.add('pp-figma-field');
  input.classList.remove('bold');
  // Keep the real hint in its Figma slot, rather than converting it into a label tooltip.
  root.querySelectorAll('.pp-info,.pp-field-tip').forEach(n=>n.remove());
  const label=root.querySelector('.control-label');label?.classList.remove('pp-label-line');
  if(label&&!label.querySelector('.pp-required-mark')){const mark=document.createElement('span');mark.className='pp-required-mark';mark.textContent='*';mark.setAttribute('aria-hidden','true');label.insertBefore(mark,label.querySelector('.pp-control-help'));}if(label)label.querySelector('.pp-required-mark').hidden=!label.classList.contains('reqd');
  const hint=root.querySelector('.help-box');if(hint){hint.hidden=false;hint.classList.remove('pp-supplementary-help','text-extra-muted');if(!hint.id)hint.id='pp-figma-hint-'+(++fieldSequence);const ids=new Set((input.getAttribute('aria-describedby')||'').split(/\s+/).filter(Boolean));ids.add(hint.id);input.setAttribute('aria-describedby',[...ids].join(' '));}
  if(input.tagName==='SELECT'&&!control.ppChoices&&hint?.textContent.trim()&&!root.querySelector('.pp-control-help')){const help=document.createElement('button');help.type='button';help.className='pp-control-help';help.setAttribute('aria-label',__('Help: {0}',[df.label]));help.append(asset('help-circle'));help.onclick=e=>{e.preventDefault();e.stopPropagation();pp.show_info?.(help,hint.textContent.trim());};label?.append(help);}
  if(control.ppChoices||df.fieldtype==='Check'||!input.matches('input.form-control,textarea.form-control'))return;
  let shell=input.closest('.pp-control-shell');
  if(!shell){shell=input.closest('.awesomplete');if(!shell){shell=document.createElement('div');input.before(shell);shell.append(input);}shell.classList.add('pp-control-shell');}
  const leading=df.options==='Email'||['email','personal_email'].includes(df.fieldname)?'mail':df.fieldtype==='Date'?'calendar':['Link','Dynamic Link'].includes(df.fieldtype)?'search':null;
  if(leading&&!shell.querySelector(':scope > .pp-control-leading')){const mark=document.createElement('span');mark.className='pp-control-leading';mark.append(asset(leading));shell.append(mark);shell.classList.add('has-leading');}
  if(df.fieldtype==='Int'&&!shell.querySelector('.pp-number-step')){
   shell.classList.add('pp-number-shell');for(const [direction,name] of [[-1,'minus'],[1,'plus']]){const button=document.createElement('button');button.type='button';button.className='pp-number-step '+(direction<0?'is-minus':'is-plus');button.setAttribute('aria-label',__(direction<0?'Decrease {0}':'Increase {0}',[df.label]));button.append(asset(name));button.onmousedown=e=>e.preventDefault();button.onclick=async()=>{if(input.disabled||input.readOnly||df.read_only)return;const raw=Number(String(input.value||0).replaceAll(',','')),step=Number(df.step)||1,next=raw+direction*step,min=df.min??input.getAttribute('min'),max=df.max??input.getAttribute('max');if(min!=null&&next<Number(min)||max!=null&&next>Number(max))return;await control.set_value(next);input.dispatchEvent(new Event('input',{bubbles:true}));input.focus({preventScroll:true});};shell.append(button);}
  }
  const text=hint?.textContent.trim();let help=root.querySelector('.pp-control-help');
  if(text&&!help){help=document.createElement('button');help.type='button';help.className='pp-control-help';help.setAttribute('aria-label',__('Help: {0}',[df.label]));help.append(asset('help-circle'));help.onclick=e=>{e.preventDefault();e.stopPropagation();pp.show_info?.(help,hint.textContent.trim());};if(input.tagName==='TEXTAREA')label?.append(help);else shell.append(help);}
  if(help){help.hidden=!text;const atLabel=input.tagName==='TEXTAREA'||['Int','Date','Link','Dynamic Link'].includes(df.fieldtype);if(atLabel&&label&&help.parentElement!==label)label.append(help);shell.classList.toggle('has-help',!!text&&!atLabel);}
  if(input.tagName==='TEXTAREA'){shell.classList.add('pp-textarea-shell');if(!input.ppFigmaSized){input.style.height=(df.pp_size==='sm'?108:df.pp_size==='lg'?180:128)+'px';input.ppFigmaSized=true;}if(!shell.querySelector('.pp-resize-handle'))shell.append(asset('resize','pp-resize-handle'));}
  else if(!shell.querySelector('.pp-control-error'))shell.append(asset('alert-circle','pp-control-error'));
 };
 // Figma Select/Menu contract, backed by the original native <select>. One menu,
 // no polling, and no changes to native field parsing, options or permissions.
 let menu,owner,active=0,items=[],search,selectSequence=0,typed='',typedAt=0;
 const closeSelect=(focus=false)=>{const previous=owner;menu?.remove();menu=owner=search=null;items=[];if(previous){previous.button.setAttribute('aria-expanded','false');previous.button.removeAttribute('aria-activedescendant');previous.button.removeAttribute('aria-controls');if(focus&&previous.button.isConnected)previous.button.focus();}};
 const moveSelect=index=>{if(!items.length)return;active=(index+items.length)%items.length;items.forEach((row,i)=>row.node.classList.toggle('is-active',i===active));const row=items[active];(search||owner.button).setAttribute('aria-activedescendant',row.node.id);row.node.scrollIntoView({block:'nearest'});};
 const selectKeys=event=>{if(!owner)return;if(['ArrowDown','ArrowUp','Home','End','Enter','Escape','Tab'].includes(event.key)){if(event.key!=='Tab'){event.preventDefault();event.stopPropagation();}if(event.key==='Escape'||event.key==='Tab')closeSelect(event.key==='Escape');else if(event.key==='Enter')items[active]?.node.click();else moveSelect(event.key==='Home'?0:event.key==='End'?items.length-1:active+(event.key==='ArrowDown'?1:-1));}else if(!search&&event.key.length===1&&!event.ctrlKey&&!event.metaKey&&!event.altKey){event.preventDefault();typed=Date.now()-typedAt>600?event.key:typed+event.key;typedAt=Date.now();const found=items.findIndex(r=>r.option.text.toLocaleLowerCase().startsWith(typed.toLocaleLowerCase()));if(found>=0)moveSelect(found);}};
 const openSelect=component=>{
  closeSelect();if(component.source.disabled)return;owner=component;menu=document.createElement('div');menu.className='pp-select-menu';menu.id='pp-select-menu-'+(++selectSequence);const list=document.createElement('div');list.role='listbox';list.id=menu.id+'-list';list.setAttribute('aria-label',component.button.getAttribute('aria-label'));component.button.setAttribute('aria-controls',list.id);component.button.setAttribute('aria-expanded','true');
  const options=[...component.source.options];
  const draw=term=>{items=[];list.replaceChildren();for(const option of options){if(option.disabled||option.parentElement?.disabled||option.hidden||term&&!option.text.toLocaleLowerCase().includes(term))continue;const row=document.createElement('div');row.role='option';row.id=list.id+'-'+items.length;row.setAttribute('aria-selected',String(option.selected));row.className='pp-select-option';const label=document.createElement('span');label.textContent=option.text||__('Choose…');row.append(label);if(option.selected){const check=document.createElement('span');check.className='pp-select-check';check.setAttribute('aria-hidden','true');check.append(asset('check-menu'));row.append(check);}row.onpointermove=()=>{active=items.findIndex(i=>i.node===row);items.forEach(i=>i.node.classList.toggle('is-active',i.node===row));};row.onmousedown=e=>e.preventDefault();row.onclick=()=>{component.source.value=option.value;component.source.dispatchEvent(new Event('change',{bubbles:true}));component.sync();closeSelect(true);};list.append(row);items.push({node:row,option});}if(!items.length){const empty=document.createElement('p');empty.className='pp-select-empty';empty.textContent=__('No matches. Try another search.');list.append(empty);}moveSelect(Math.max(0,items.findIndex(r=>r.option.selected)));};
  if(options.length>8){search=document.createElement('input');search.type='search';search.className='form-control pp-select-search';search.placeholder=__('Search choices…');search.setAttribute('aria-label',__('Search {0}',[component.button.getAttribute('aria-label')]));search.setAttribute('role','combobox');search.setAttribute('aria-controls',list.id);search.setAttribute('aria-expanded','true');search.oninput=()=>draw(search.value.trim().toLocaleLowerCase());search.onkeydown=selectKeys;menu.append(search);}
  menu.append(list);document.body.append(menu);const bounds=component.button.getBoundingClientRect();component.openBounds={top:bounds.top,left:bounds.left};const width=Math.min(Math.max(bounds.width,240),innerWidth-24);menu.style.width=width+'px';menu.style.left=Math.max(12,Math.min(bounds.left,innerWidth-width-12))+'px';const availableBelow=innerHeight-bounds.bottom-12,availableAbove=bounds.top-12,below=availableBelow>=Math.min(320,availableAbove);menu.style.maxHeight=Math.max(120,Math.min(360,below?availableBelow:availableAbove))+'px';if(below)menu.style.top=bounds.bottom+4+'px';else menu.style.bottom=innerHeight-bounds.top+4+'px';draw('');search?.focus();
 };
 pp.ui.selects=scope=>{
  if(!document.body.classList.contains('pp-customer-app'))return;if(owner&&!owner.source.isConnected)closeSelect();
  for(const source of scope.querySelectorAll('select.form-control:not(.pp-choice-native):not([multiple])')){
   if(source.ppSelect){source.ppSelect.sync();continue;}if(source.hidden||source.closest('.pp-choice-control,[hidden]'))continue;
   const button=document.createElement('button');button.type='button';button.className='pp-select-trigger form-control';button.role='combobox';button.setAttribute('aria-haspopup','listbox');button.setAttribute('aria-expanded','false');const value=document.createElement('span');value.className='pp-select-value';const chevron=asset('chevron-down','pp-select-chevron');button.append(value,chevron);const shell=document.createElement('span');shell.className='pp-select-container';source.before(shell);shell.append(source,button);source.classList.add('pp-select-source');source.setAttribute('aria-hidden','true');source.tabIndex=-1;
   const component={source,button,sync(){const text=source.selectedOptions[0]?.text||__('Choose…');if(value.textContent!==text)value.textContent=text;button.disabled=source.disabled;button.classList.toggle('is-placeholder',!source.value);button.hidden=source.hidden||!!source.ppControl?.df.read_only;if(owner===component&&(button.disabled||button.hidden))closeSelect();const control=source.closest('.frappe-control'),label=source.ppControl?.df.label||source.getAttribute('aria-label')||source.labels?.[0]?.textContent?.trim()||control?.querySelector('.control-label')?.textContent?.trim()||__('Choose an option');button.setAttribute('aria-label',label);button.setAttribute('aria-invalid',source.getAttribute('aria-invalid')||'false');if(source.getAttribute('aria-describedby'))button.setAttribute('aria-describedby',source.getAttribute('aria-describedby'));button.setAttribute('aria-required',String(source.required||control?.classList.contains('reqd')||false));}};source.ppSelect=component;source.addEventListener('change',component.sync);source.addEventListener('focus',()=>button.focus());button.onclick=()=>owner===component?closeSelect():openSelect(component);button.onkeydown=e=>{if(owner===component)selectKeys(e);else if(['ArrowDown','ArrowUp','Enter',' '].includes(e.key)){e.preventDefault();openSelect(component);}};component.sync();
  }
 };
 document.addEventListener('pointerdown',event=>{if(menu&&!menu.contains(event.target)&&!owner.button.contains(event.target))closeSelect();});
 window.addEventListener('resize',()=>closeSelect());document.addEventListener('scroll',event=>{if(menu&&!menu.contains(event.target)){const bounds=owner.button.getBoundingClientRect();if(Math.abs(bounds.top-owner.openBounds.top)>1||Math.abs(bounds.left-owner.openBounds.left)>1)closeSelect();}},true);
 frappe.router.on('change',()=>closeSelect());$(document).on('hide.bs.modal.pp-select',()=>closeSelect());
 pp.ui.close_select=scope=>{if(!scope||scope.contains(owner?.source))closeSelect();};
 pp.ui.sync_select=source=>source?.ppSelect?.sync();
 const start=()=>{if(!frappe.boot?.plus_point||frappe.boot.plus_point.is_platform)return;pp.watch_ui?.('ui-components',pp.ui.enhance);$(document).off('shown.bs.modal.pp-ui-components').on('shown.bs.modal.pp-ui-components','.modal',event=>pp.ui.enhance(event.currentTarget));pp.ui.enhance();};
 if(window.frappe?.app?.sidebar)start();else if(window.jQuery)$(document).on('app_ready.pp-components',start);
})();
