/* Freddy is local, contextual feedback, not a floating chat service. */
(()=>{
 window.plus_point ||= {};
 if(plus_point.freddy_installed)return;plus_point.freddy_installed=true;
 const pp=plus_point,translate=text=>typeof window.__==='function'?__(text):text;
 const plain=value=>{const text=document.createElement('textarea');text.innerHTML=String(value??'').replace(/<br\s*\/?>|<\/(?:p|li|div)>/gi,' ').replace(/<[^>]*>/g,'');return text.value.replace(/\s+/g,' ').trim();};
 const poses={error:'confused',warning:'surprised',info:'curious',guide:'listening',loading:'thinking',success:'happy',empty:'curious'};
 const read=node=>{if(!node.children.length)return node.textContent;const clone=node.cloneNode(true);clone.querySelectorAll('.pp-dismiss-message,.close,[aria-hidden=true]').forEach(child=>child.remove());clone.querySelectorAll('p,div,li,strong,h1,h2,h3,h4,td,th,br').forEach(child=>child.append(document.createTextNode(' ')));return clone.textContent;};
 const states=new WeakMap(),motion=matchMedia('(prefers-reduced-motion: reduce)');
 let active,lastAction,started=false,lastAutomatic=0,sequence=0,importantHost=null,paused=false;
 const stats=pp.freddy_stats={rendered:0,animations:0,activeAnimations:0,suppressed:0};
 const enabled=()=>document.body?.dataset.ppFreddy==='true'||!!window.frappe?.boot?.plus_point&&!frappe.boot.plus_point.is_platform;
 function sentence(message,tone='info'){
  const text=plain(message),lower=text.toLowerCase();if(!text)return '';
  if(tone==='warning')return translate('Let’s check this before you continue: ')+text;
  if(tone==='error'||tone==='warning'){
   if(/email.*(?:such as|format|valid|incomplete)|include.*@|missing.*@/i.test(text))return translate('That email address looks incomplete; enter an address such as name@example.com.');
   if(/7.?15 digits|phone.*(?:invalid|digits|number.*valid)/i.test(text))return translate('That phone number needs 7–15 digits; check the number and country code.');
   if(/whole numbers only/i.test(text))return translate('I can only use whole numbers here; remove letters and decimal places.');
   if(/use numbers only/i.test(text))return translate('I can only use numbers here; remove letters and other characters.');
   if(/^Enter a number from |^Enter .+ or (?:more|less)\./i.test(text))return translate('This value is outside the allowed range; ')+text[0].toLowerCase()+text.slice(1);
   if(/end date.*(?:before|after|precede)|start date.*(?:after|end)|dates.*wrong order/i.test(text))return translate('These dates are in the wrong order; choose an end date on or after the start date.');
   if(/not enough crew|crew.*shortfall|reduce the number.*hiring/i.test(text))return translate('There aren’t enough crew for these dates; reduce the count, add crew in this category or confirm additional hiring.');
   if(/failed to fetch|networkerror|network request|couldn.t reach|connection.*retry/i.test(text))return translate('I couldn’t reach the app; check your connection and try this action again.');
   if(/session.*expired|csrf|not logged in/i.test(text))return translate('Your sign-in session needs refreshing; sign in again, then retry this action.');
   if(/link.*(?:expired|revoked|invalid|no longer|not valid)|signing.*not found/i.test(text))return translate('This signing link can’t be used; ask the event company for a new link.');
   if(/not permitted|permission denied|insufficient permission|not have permission/i.test(text))return translate('I can’t make this change with your current access; ask your company administrator for permission.');
   if(/^Enter .+\.$/.test(text))return translate('I need this detail to continue; ')+text[0].toLowerCase()+text.slice(1);
   if(/^Use |^Choose |^Select |^Add |^Review |^Keep |^Wait |^Enable /i.test(text))return translate('Let’s fix this: ')+text[0].toLowerCase()+text.slice(1);
   return translate('I couldn’t finish this step: ')+text.replace(/[.!]$/,'')+translate('; review these details and try again.');
  }
  if(tone==='loading')return /loading/i.test(lower)?translate('I’m getting these details ready; you can continue when they appear.'):text;
  if(tone==='success')return translate('All set: ')+text;
  if(tone==='empty')return translate('Let’s get started: ')+text;
  return translate('I can help here: ')+text;
 }
 pp.freddy_sentence=sentence;
 function stop(){if(!active)return;clearTimeout(active.timer);active.controller?.destroy();active.host?.remove();if(active.image?.isConnected)active.image.hidden=false;active=null;stats.activeAnimations=0;}
 function animate(widget,automatic=false){
  if(!widget?.isConnected||widget.parentElement!==importantHost||paused||document.hidden||motion.matches)return;
  if(!pp.freddy_runtime){pp.load_feature?.('freddy_runtime')?.then(()=>animate(widget,automatic)).catch(()=>{});return;}
  if(active?.host&&widget.contains(active.host))return;
  if(automatic)lastAutomatic=Date.now();stop();
  const image=widget.querySelector('.pp-freddy__image'),slot=widget.querySelector('.pp-freddy__avatar');if(!image||!slot||!slot.getClientRects().length)return;
  const host=document.createElement('span');host.className='pp-freddy__motion';host.setAttribute('aria-hidden','true');slot.append(host);image.hidden=true;
  try{const controller=pp.freddy_runtime.create(host,{animation:widget.dataset.expression,autoplay:true,loop:false,size:'100%'});active={host,image,controller,timer:setTimeout(stop,4500)};stats.animations++;stats.activeAnimations=1;}catch{host.remove();image.hidden=false;}
 }
 pp.stop_freddy=stop;
 function toneOf(node,text){
  if(node.dataset.feedbackTone)return node.dataset.feedbackTone;
  if(node.matches('.frappe-confirm-message'))return 'warning';
  if(node.closest('.pp-import-error')||node.matches('.msgprint')&&node.closest('.modal-content')?.querySelector('.indicator.red'))return 'error';
  if(node.matches('.pp-loading-state')||/^loading|^saving|^uploading|^preparing/i.test(text))return 'loading';
  if(node.matches('.pp-empty-state,.pp-activity-empty'))return 'empty';
  if(node.matches('.pp-op-success')||/^(?:all set|saved|draft saved|agreement signed|signed by|.*(?:saved successfully|imported successfully))|link copied|email queued/i.test(text))return 'success';
  if(node.matches('.pp-info-portal,.tooltip-inner,.pp-freddy-guidance,.pp-upload-guidance,.driver-popover-description,.pp-guide-note,.pp-signing-ready>p'))return 'guide';
  if(node.matches('[role=alert],.pp-onboarding-errors,.pp-profile-save-error,.pp-upload-error,.pp-import-feedback,.pp-input-hint,.error')||/could not|couldn.t|failed|not enough|invalid|review the highlighted|not set up|not configured/i.test(text))return 'error';
  return 'info';
 }
 const preserved='button,a,input,select,textarea,table,ul,ol,details';
 pp.freddy_feedback=(node,{message,tone,solution,rich=false,animate:play=true}={})=>{
  if(!node||!enabled()||node.matches('.pp-loading-state'))return;const previous=states.get(node);
  if(pp.ui&&!node.matches('.pp-freddy-important')){const text=message??read(node);if(node.matches('.pp-flow-position,.pp-draft-status>span,.pp-input-hint,.pp-date-error,.pp-freddy-validation')||node.closest('.frappe-control')){if(message!=null)node.textContent=message;return;}pp.ui.feedback(node,{message:text,tone:tone||toneOf(node,plain(text)),rich});return;}
  const important=node.matches('.pp-op-message,.pp-onboarding-errors,.pp-freddy-important,.pp-freddy-action-feedback,.frappe-confirm-message,.msgprint,#agreement-status');
  if(!important){if(message!=null&&node.textContent!==String(message))node.textContent=message;return;}
  if(importantHost&&importantHost!==node){const state=states.get(importantHost);if(state){const widget=importantHost.querySelector(':scope > .pp-freddy'),details=widget?.querySelector('.pp-freddy__details');if(widget){const controls=[...widget.querySelectorAll(':scope > .pp-dismiss-message,:scope > .close')];widget.replaceWith(...(details?[...details.childNodes]:[document.createTextNode(state.original)]),...controls);}importantHost.classList.remove('pp-freddy-host');states.delete(importantHost);}stop();}importantHost=node;
  if(message!=null&&previous&&plain(message)===previous.original&&(!tone||tone===previous.tone)&&node.querySelector(':scope > .pp-freddy'))return;
  if(message==null&&previous&&node.querySelector(':scope > .pp-freddy')&&node.textContent===previous.rendered&&(!tone||tone===previous.tone))return;
  const existing=node.querySelector(':scope > .pp-freddy');
  if(existing){if(active&&existing.contains(active.host))stop();const details=existing.querySelector('.pp-freddy__details'),speech=existing.querySelector('.pp-freddy__speech'),close=[...existing.querySelectorAll(':scope > .pp-dismiss-message,:scope > .close')];existing.replaceWith(...(details?[...details.childNodes]:[document.createTextNode(speech?.textContent===previous?.spoken?previous.original:speech?.textContent||'')]),...close);}
  const original=message??read(node),text=plain(original);tone=tone||toneOf(node,text);
  if(!text){node.classList.remove('pp-freddy-host');states.delete(node);return;}
  const compact=node.matches('.pp-input-hint')||!!node.closest('.frappe-control,td'),widget=document.createElement(node.matches('P,SPAN')?'span':'div');
  widget.className='pp-freddy'+(compact?' pp-freddy--compact':'');widget.dataset.tone=tone;widget.dataset.expression=tone==='error'&&/connection|reach the app|network|failed to fetch/i.test(text)?'sad':poses[tone]||'curious';
  const avatar=document.createElement('span');avatar.className='pp-freddy__avatar';avatar.setAttribute('aria-hidden','true');
  const image=document.createElement('img');image.className='pp-freddy__image';image.src='/assets/plus_point/images/freddy/'+widget.dataset.expression+'.svg?v=20261027';image.alt='';image.width=64;image.height=64;image.decoding='async';avatar.append(image);
  const speech=document.createElement(node.matches('P,SPAN')?'span':'div');speech.className='pp-freddy__speech';
  const dismiss=[...node.querySelectorAll(':scope > .pp-dismiss-message,:scope > .close')];dismiss.forEach(el=>el.remove());
  if(rich&&node.children.length){const intro=document.createElement('span');intro.className='pp-freddy__intro';intro.textContent=tone==='error'?translate('I found something to review; follow the details below to resolve it.'):translate('I’ve kept the details below so you can review the next step.');speech.append(intro);const details=document.createElement('div');details.className='pp-freddy__details';while(node.firstChild)details.append(node.firstChild);speech.append(details);}
  else{let copy=sentence(text,tone);if(tone==='empty'){const title=node.querySelector('strong')?.textContent.trim(),description=node.querySelector('p')?.textContent.trim(),match=title?.match(/^No (.+?) yet[.!]?$/i);if(match&&description)copy=translate('I don’t have any ')+match[1]+translate(' to show yet; ')+description[0].toLowerCase()+description.slice(1);}speech.textContent=copy+(solution?' '+plain(solution):'');}
  widget.append(avatar,speech,...dismiss);node.replaceChildren(widget);node.classList.add('pp-freddy-host');
  states.set(node,{rendered:node.textContent,spoken:speech.textContent,tone,original:text});stats.rendered++;
  if(play)requestAnimationFrame(()=>animate(widget,true));
 };
 const selector=['.pp-freddy-important','.pp-freddy-action-feedback','.pp-input-hint','.pp-op-message','.pp-onboarding-errors','.pp-import-feedback','.pp-upload-error','.pp-import-error td:last-child','.pp-profile-save-error','.pp-checkpoint-feedback','.pp-sign-feedback','.pp-worker-edit-error','.pp-stock-feedback','.pp-empty-state','.pp-loading-state','.pp-activity-empty','.pp-info-portal','.pp-tooltip .tooltip-inner','.pp-freddy-guidance','.pp-upload-guidance','.pp-guide-note','.driver-popover-description','.pp-draft-status>span','.pp-signing-ready>p','.pp-flow-position','.msgprint','.frappe-confirm-message','.es-toast__message','#alert-container .alert-message','#agreement-status','[data-freddy-feedback]','[role=alert]'].join(',');
 function enhance(scope=document){
  if(!enabled())return;if(active&&(!active.host.isConnected||!active.host.closest('.pp-freddy__avatar')?.getClientRects().length))stop();
  const candidates=[...scope.querySelectorAll(selector)].filter(node=>!node.closest('.pp-freddy')&&!node.closest('[hidden],[inert],pre,code')&&node.getClientRects().length&&plain(node.textContent));
  const nodes=candidates.filter(node=>node.matches('.pp-op-message,.pp-onboarding-errors,.pp-freddy-important,.pp-freddy-action-feedback,.frappe-confirm-message,.msgprint,#agreement-status')).sort((a,b)=>Number(!!b.closest('.modal'))-Number(!!a.closest('.modal'))||Number(b.getAttribute('role')==='alert')-Number(a.getAttribute('role')==='alert')).slice(0,1);
  // Keep a pathological error list from creating unbounded work in a single pass.
  let changed=0;for(const node of nodes){
   if(node.querySelector('.pp-freddy')&&!node.querySelector(':scope > .pp-freddy'))continue;
   if(node.matches('.pp-op-message')&&/^review the highlighted fields[.!]?$/i.test(plain(read(node)))&&node.closest('.pp-operations')?.querySelector('[aria-invalid=true]')){node.hidden=true;continue;}
   const state=states.get(node);if(state&&node.querySelector(':scope > .pp-freddy')&&node.textContent===state.rendered)continue;
   if(changed++>=80)break;
   const rich=node.matches('.msgprint,.pp-activity-empty')||[...node.querySelectorAll(preserved)].some(child=>!child.matches('.pp-dismiss-message,.close'));
   pp.freddy_feedback(node,{rich});
  }
 }
 pp.enhance_feedback=enhance;
 function anchorError(message,tone){
  const action=lastAction?.node;if(!action?.isConnected||Date.now()-lastAction.at>15000)return false;
  const scope=action.closest('.modal-content')?.querySelector('.modal-body')||action.closest('.pp-op-content,.pp-worker-profile,.layout-main-section');if(!scope)return false;
  let node=scope.querySelector(':scope > .pp-freddy-action-feedback');if(!node){node=document.createElement('div');node.className='pp-freddy-action-feedback';node.role='alert';scope.prepend(node);}node.textContent=plain(message);node.hidden=false;pp.freddy_feedback(node,{tone});return true;
 }
 function start(){
  if(started||!enabled())return;started=true;
  if(window.frappe?.show_alert){const original=frappe.show_alert;frappe.show_alert=function(message,seconds,actions){const result=original.apply(this,arguments),indicator=String(message?.indicator||'blue').toLowerCase(),tone=({red:'error',orange:'warning',yellow:'warning',green:'success'})[indicator]||'info',content=typeof message==='string'?message:message?.message,node=result?.find?.('.es-toast__message').get(0);if(node){node.dataset.feedbackTone=tone;pp.freddy_feedback(node,{tone,rich:!!node.querySelector(preserved)});}const simple=typeof content==='string'&&!/<[a-z]/i.test(content)&&!message?.body&&!message?.subtitle&&!Object.keys(actions||{}).length;if(simple&&['error','warning'].includes(tone)&&anchorError(content,tone))result?.hide?.();return result;};if(frappe.toast===original)frappe.toast=frappe.show_alert;}
  if(window.frappe?.msgprint){const original=frappe.msgprint;frappe.msgprint=function(message){const result=original.apply(this,arguments),node=frappe.msg_dialog?.msg_area?.get(0);if(node&&message&&!Array.isArray(message))node.dataset.feedbackTone=typeof message==='object'&&(message.indicator==='red'||message.raise_exception||/error|failed/i.test(message.title||''))?'error':'info';return result;};if(window.msgprint===original)window.msgprint=frappe.msgprint;}
  if(pp.watch_ui)pp.watch_ui('freddy-feedback',enhance);
  else{let timer;const observer=new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(()=>{observer.disconnect();enhance();observer.observe(document.body,{childList:true,subtree:true});},120);});observer.observe(document.body,{childList:true,subtree:true});}
  enhance();
 }
 document.addEventListener('pointerdown',event=>{const node=event.target.closest('button,a,input,[role=button]');if(node)lastAction={node,at:Date.now()};},true);
 document.addEventListener('pointerover',event=>{const widget=event.target.closest('.pp-freddy');if(widget&&!widget.contains(event.relatedTarget))animate(widget);});
 document.addEventListener('focusin',event=>{const widget=event.target.closest('.pp-freddy')||event.target.closest('.frappe-control')?.querySelector('.pp-freddy');if(widget)animate(widget);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else if(importantHost?.getClientRects().length)animate(importantHost.querySelector(':scope > .pp-freddy'));});window.addEventListener('pagehide',stop);motion.addEventListener('change',()=>{if(motion.matches)stop();});
 if(window.frappe?.router)frappe.router.on('change',()=>{stop();lastAction=null;document.querySelectorAll('.pp-freddy-action-feedback').forEach(node=>node.remove());importantHost=null;sequence++;});
 // Signing-page native constraints still block submission; Freddy replaces only the browser's error bubble.
 document.addEventListener('invalid',event=>{if(document.body.dataset.ppFreddy!=='true')return;event.preventDefault();const input=event.target,label=input.closest('label'),name=label?.firstChild?.textContent.trim()||input.name;let node=document.getElementById(input.dataset.freddyValidation||'');if(!node){node=document.createElement('span');node.className='pp-freddy-validation';node.role='alert';node.id='freddy-validation-'+(++sequence);(label||input).after(node);input.dataset.freddyValidation=node.id;}node.textContent=input.type==='checkbox'?translate('You haven’t accepted the terms; select this box only if you agree.'):input.validity.valueMissing?translate('Enter ')+name+'.':input.type==='email'&&input.validity.typeMismatch?translate('Enter an email such as name@example.com.'):input.validationMessage;pp.freddy_feedback(node,{tone:'error'});input.setAttribute('aria-invalid','true');input.setAttribute('aria-describedby',[...new Set([...(input.getAttribute('aria-describedby')||'').split(' '),node.id])].filter(Boolean).join(' '));if(!document.querySelector('#agreement-sign [aria-invalid=true]:focus'))input.focus();},true);
 document.addEventListener('input',event=>{if(document.body.dataset.ppFreddy!=='true'||!event.target.validity?.valid)return;const input=event.target,node=document.getElementById(input.dataset.freddyValidation||'');if(node){node.remove();input.removeAttribute('aria-invalid');const ids=(input.getAttribute('aria-describedby')||'').split(' ').filter(id=>id!==node.id);if(ids.length)input.setAttribute('aria-describedby',ids.join(' '));else input.removeAttribute('aria-describedby');delete input.dataset.freddyValidation;}});
 if(window.frappe?.app?.sidebar||document.body?.dataset.ppFreddy==='true')start();else if(window.jQuery)$(document).on('app_ready.pp-freddy',start);else document.addEventListener('DOMContentLoaded',start);
})();
