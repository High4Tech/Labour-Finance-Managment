/* Figma 23:16918 / 23:16717. One company shell; native permissions and menus stay native. */
(()=>{
 frappe.provide('plus_point');const pp=plus_point,esc=v=>frappe.utils.escape_html(String(v??'')),base='/assets/plus_point/images/dashboard/';
 const icon=n=>'<img class="pp-shell-icon" alt="" aria-hidden="true" src="'+base+n+'.svg">';
 const text=(node,value)=>{if(node&&node.textContent!==value)node.textContent=value;};
 let header,context={},companyMenu,mobileOpen=false,mobilePrevious,backdrop,mainWasInert=false,notificationPopover,attention;
 const dismissed=new Set();
 function searchPopover(){
  if(frappe.boot?.plus_point?.is_platform)return;
  const modal=document.querySelector('#navbar-search')?.closest('.modal');if(!modal||getComputedStyle(modal).display==='none')return;
  const anchor=document.querySelector('.navbar-modal-search-mobile'),r=anchor?.getBoundingClientRect(),width=Math.min(460,innerWidth-24),left=Math.max(12,Math.min(r?.left||12,innerWidth-width-12)),top=Math.min((r?.bottom||60)+8,innerHeight-180);
  modal.classList.add('pp-search-popover');modal.setAttribute('aria-label',__('Search'));modal.style.setProperty('--pp-search-left',left+'px');modal.style.setProperty('--pp-search-top',top+'px');modal.style.setProperty('--pp-search-width',width+'px');document.body.classList.add('pp-search-open');
 }
 $(document).on('shown.bs.modal.pp-shell-search',searchPopover).on('hidden.bs.modal.pp-shell-search',()=>document.body.classList.remove('pp-search-open'));
 document.addEventListener('pointerdown',e=>{if(!document.body.classList.contains('pp-search-open')||e.target.closest('.pp-search-popover .modal-content,.navbar-modal-search-mobile'))return;document.querySelector('.pp-search-popover .btn-modal-close')?.click();});
 function notifications(){
  const native=frappe.app?.sidebar?.notifications,bell=header?.querySelector('.pp-shell-notifications');if(!native?.panel?.$panel?.[0]||!bell||notificationPopover)return;
  native.panel.hide();native.as_popover=true;
  const content=native.panel.$panel[0];content.classList.add('pp-notification-content');
  notificationPopover=new frappe.ui.Popover({trigger:$(bell),content:()=>{content.style.display='block';return content;},css_class:'notifications-popover pp-header-notifications',side:'bottom',align:'end',on_open:()=>native.on_open()});native.popover=notificationPopover;
  const close=content.querySelector('.panel-close');close?.addEventListener('click',e=>{e.stopImmediatePropagation();native.close_panel();},true);
 }
 function setAttention(rows){
  const active=rows.filter(r=>['error','warning','empty'].includes(r.level)&&!dismissed.has(r.title+'|'+r.path)).slice(0,3);
  if(!attention){attention=document.createElement('aside');attention.className='pp-attention-stack';attention.setAttribute('aria-label',__('Needs your attention'));document.body.append(attention);}
  attention.innerHTML=active.map((r,i)=>'<article class="pp-attention-toast" data-tone="'+esc(r.level)+'"><span class="pp-attention-icon" aria-hidden="true">'+pp.icon(r.level==='error'?'warning':r.level==='warning'?'warning':'info')+'</span><div><strong>'+esc(__(r.title))+'</strong><p>'+esc(__(r.message))+'</p><a class="btn btn-default" href="'+esc(r.path)+'">'+esc(__(r.label))+'</a></div><button type="button" class="btn btn-default pp-attention-dismiss" data-dismiss-attention="'+i+'" aria-label="'+esc(__('Dismiss {0}',[r.title]))+'">'+pp.icon('close')+'</button></article>').join('');
  attention.hidden=!active.length;attention.querySelectorAll('article').forEach((article,i)=>{const row=active[i];if(row.action?.startsWith('new:'))article.querySelector('a').onclick=e=>{e.preventDefault();frappe.new_doc(row.action.slice(4));};});attention.querySelectorAll('[data-dismiss-attention]').forEach(b=>b.onclick=()=>{const row=active[Number(b.dataset.dismissAttention)];dismissed.add(row.title+'|'+row.path);b.closest('article').remove();attention.hidden=!attention.children.length;});
 }
 function mobileNavigation(open){
  open=!!open&&matchMedia('(max-width:767px)').matches;if(open===mobileOpen)return;
  const sidebar=frappe.app?.sidebar,node=document.querySelector('.body-sidebar'),main=document.querySelector('.main-section');if(!sidebar||!node)return;
  mobileOpen=open;document.body.classList.toggle('pp-mobile-navigation-open',open);
  if(open){if(main){mainWasInert=main.inert;main.inert=true;}mobilePrevious=sidebar.sidebar_expanded;sidebar.sidebar_expanded=true;sidebar.apply_expanded_state();node.inert=false;
   if(!backdrop){backdrop=document.createElement('button');backdrop.type='button';backdrop.className='pp-shell-nav-backdrop';backdrop.setAttribute('aria-label',__('Close navigation'));backdrop.onclick=()=>mobileNavigation(false);document.body.append(backdrop);}
   if(!node.querySelector('.pp-shell-nav-close')){const close=document.createElement('button');close.type='button';close.className='btn btn-default pp-shell-nav-close';close.setAttribute('aria-label',__('Close navigation'));close.innerHTML=pp.icon('close');close.onclick=()=>mobileNavigation(false);node.prepend(close);}
   node.querySelector('.pp-shell-nav-close').focus();
  }else{if(main)main.inert=mainWasInert;sidebar.sidebar_expanded=mobilePrevious;sidebar.apply_expanded_state();header?.querySelector('.pp-shell-mobile-nav')?.focus();}
  if(backdrop)backdrop.hidden=!open;
  header?.querySelector('.pp-shell-mobile-nav')?.setAttribute('aria-expanded',String(open));
 }
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&mobileOpen){e.preventDefault();mobileNavigation(false);}});
 $(document).on('show.bs.modal.pp-shell',()=>mobileNavigation(false));
 frappe.router.on('change',()=>mobileNavigation(false));
 matchMedia('(max-width:767px)').addEventListener('change',()=>mobileNavigation(false));
 const initials=name=>String(name||'').split(/\s+/).filter(Boolean).slice(0,2).map(w=>w[0]).join('').toUpperCase();
 function pageTitle(){
  const r=frappe.get_route()||[],aliases={'pp-agreements':'Agreements','pp-event-plans':'Jobs & Events','pp-client-billing':'Billing and invoices','pp-daily-register':'Attendance','pp-onboarding':'Company setup','pp-section':new URL(location.href).searchParams.get('section')};
  if(r[0]==='Workspaces')return __('Overview');
  if(r[0]==='pp-inventory')return __(({vehicles:'Vehicles',equipment:'Inventory & equipment',warehouses:'Warehouses'})[new URL(location.href).searchParams.get('view')]||'Warehouses');
  const items=frappe.boot.plus_point.navigation?.items||[],item=items.find(i=>i.link_to===r[1]||i.link_to===r[0]);
  return __(aliases[r[0]]||item?.label||r[1]||r[0]||'Overview');
 }
 function help(){
  if(!frappe.boot.plus_point.is_platform){pp.load_feature('app_help').then(()=>pp.app_help.open()).catch(()=>frappe.show_alert({message:__('Help could not load. Please try again.'),indicator:'red'}));return;}
  const local=[...document.querySelectorAll('.pp-top-help')].find(b=>b.closest('.page-container')?.style.display!=='none');
  if(local){local.click();return;}
  frappe.msgprint({title:__('Help and support'),message:'<p>'+__('Use the information icons beside fields for help. Contact your software provider for account or billing support.')+'</p><p class="pp-icon-credit">Icons by <a href="https://github.com/tabler/tabler-icons" target="_blank" rel="noopener">Tabler</a> · Theme icons by <a href="https://github.com/basmilius/meteocons" target="_blank" rel="noopener">Meteocons</a> · MIT.</p>'});
 }
 function mount(body){
  companyMenu?.destroy?.();
  header=document.createElement('header');header.className='pp-global-bar pp-app-header';header.setAttribute('aria-label',__('Company and page controls'));
  header.innerHTML='<div class="pp-shell-breadcrumb"><button type="button" class="pp-shell-company" aria-label="'+esc(__('Company menu'))+'"><span class="pp-shell-company-avatar" aria-hidden="true"></span><strong></strong>'+icon('chevronselectorvertical')+'</button>'+icon('chevronright')+'<span class="pp-shell-page" aria-current="page"></span></div><div class="pp-shell-controls"><label class="pp-shell-currency"><span class="sr-only">'+esc(__('Display currency'))+'</span><select class="form-control pp-app-currency" aria-label="'+esc(__('Display currency'))+'"></select></label><span class="pp-shell-appearance"></span><button type="button" class="btn btn-default pp-global-help pp-shell-icon-button" aria-label="'+esc(__('Help and support'))+'" title="'+esc(__('Help and support'))+'">'+icon('openfalsesupportingtextfalsetooltiptopnoarrow')+'</button><button type="button" class="btn btn-default pp-shell-notifications pp-shell-icon-button" aria-label="'+esc(__('Notifications'))+'" title="'+esc(__('Notifications'))+'">'+icon('bell01')+'<span class="pp-shell-notification-count" hidden></span></button><a class="btn btn-primary pp-shell-upgrade" aria-label="'+esc(__("Upgrade now"))+'" title="'+esc(__("Upgrade now"))+'" href="/plans" target="_blank" rel="noopener">'+icon('zap')+'<span>'+esc(__('Upgrade now'))+'</span></a></div>';
  header.querySelector('.pp-shell-breadcrumb').insertAdjacentHTML('afterbegin','<button type="button" class="btn btn-default pp-shell-mobile-nav" aria-label="'+esc(__('Open navigation'))+'">'+pp.icon('list')+'</button>');
  header.querySelector('.pp-shell-mobile-nav').setAttribute('aria-expanded','false');
  header.querySelector('.pp-shell-mobile-nav').onclick=e=>{e.stopPropagation();mobileNavigation(!mobileOpen);};
  body.prepend(header);
  companyMenu=new frappe.ui.Dropdown({trigger:$(header.querySelector('.pp-shell-company')),side:'bottom',align:'start',options:[{group:__('Company'),options:[{name:'shell-company',label:__('Your company'),onclick:()=>{const name=pp.dashboard_company||frappe.boot.plus_point.company_identity?.name;if(name)frappe.set_route('Form','Company',name);else pp.open_setup();}}]}]});
  header.querySelector('.pp-global-help').onclick=help;
  header.querySelector('.pp-app-currency').onchange=async e=>{const select=e.target,previous=frappe.boot.plus_point.display_currency||context.currency;select.disabled=true;try{await pp.form_rpc('workflows.display_currency',{currency:select.value});frappe.boot.plus_point.display_currency=select.value;context.currency=select.value;document.dispatchEvent(new Event('pp:display-currency'));}catch(error){select.value=previous;frappe.show_alert({message:__('Could not change currency. Please try again.'),indicator:'red'});}finally{select.disabled=false;}};
 }
 function account(){
  const account=document.querySelector('.body-sidebar .sidebar-user-button');if(!account)return;
  const user=frappe.user_info(frappe.session.user)||{},name=user.fullname||frappe.boot.user.first_name||frappe.session.user,email=user.email||frappe.boot.user.email||'';
  const names=account.querySelectorAll('.avatar-name-email span');text(names[0],name);text(names[1],email);
  for(const [key,value] of [['role','button'],['tabindex','0'],['aria-label',__('Account menu for {0}',[name])]])if(account.getAttribute(key)!==value)account.setAttribute(key,value);
  if(!account.dataset.ppShellKeys){account.dataset.ppShellKeys='true';account.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();account.click();}});}
  const avatar=account.firstElementChild,key=String(user.image||'')+'|'+name;
  if(avatar&&avatar.dataset.ppAccount!==key){avatar.dataset.ppAccount=key;avatar.innerHTML='<span class="pp-shell-user-avatar">'+(user.image?'<img alt="" src="'+esc(user.image)+'">':esc(initials(name)))+'<span class="pp-shell-signed-in" aria-hidden="true"></span></span>';}
  if(!account.querySelector('.pp-shell-account-chevron'))account.insertAdjacentHTML('beforeend','<span class="pp-shell-account-chevron">'+icon('chevronselectorvertical')+'</span>');
 }
 function update(data){
  if(frappe.boot?.plus_point?.is_platform)return;
  if(data)Object.assign(context,data);
  const body=document.getElementById('body');if(!body)return;
  if(!header?.isConnected)mount(body);
  const identity=context.companies?.find(c=>c.name===context.company)?.company_name||frappe.boot.plus_point.company_identity?.title||__('Your company');
  text(header.querySelector('.pp-shell-company strong'),identity);text(header.querySelector('.pp-shell-company-avatar'),initials(identity));text(header.querySelector('.pp-shell-page'),pageTitle());
  const currency=frappe.boot.plus_point.display_currency||context.currency||frappe.boot.plus_point.company_currency||'USD',options=context.currency_options||frappe.boot.plus_point.currency_options||[currency],select=header.querySelector('.pp-app-currency'),key=options.join('|');
  if(select.dataset.options!==key){select.innerHTML=options.map(c=>'<option value="'+esc(c)+'">'+esc(c)+'</option>').join('');select.dataset.options=key;}if(select.value!==currency)select.value=currency;
  const theme=document.querySelector('.pp-theme-toggle');if(theme&&!header.contains(theme))header.querySelector('.pp-shell-appearance').append(theme);
  const count=Math.max(0,Number(document.querySelector('.sidebar-notification .notification-count')?.textContent)||0),badge=header.querySelector('.pp-shell-notification-count'),bell=header.querySelector('.pp-shell-notifications');text(badge,String(count));if(badge.hidden!==(count===0))badge.hidden=count===0;
  const label=count?__('Notifications: {0} unread',[count]):__('Notifications');if(bell.getAttribute('aria-label')!==label)bell.setAttribute('aria-label',label);
  account();
  notifications();
 }
 pp.app_shell={update,account,setContext:data=>update(data),setAttention,clearAttention(){attention?.remove();attention=null;}};
})();
