/* Presentation only: move the original controls; their validation and save handlers stay intact. */
(()=>{
 frappe.provide('plus_point');
 const esc=v=>frappe.utils.escape_html(String(v??''));
 const descriptions={agreement:['Add client and contact information.','Set dates, name and scope of work.','Configure billing and payment schedule.','Add sites, crew and vehicle requirements.','Review and prepare for signature.'],event:['Set core details, dates, budget and notes.','Review venues, crew categories and staffing.','Reserve vehicles and equipment.','Review the staffing schedule and calendar.']};
 plus_point.flow_builder=(area,{sections,nav,footer,tabs,go})=>{
  const root=area.closest('.pp-operations'),agreement=sections.length===5,type=agreement?'agreement':'event',groups=area.ppBuilderGroups||{},read=area.ppBuilderRead;
  root.classList.add('pp-flow-builder');area.classList.add('pp-builder-content');area.dataset.builder=type;
  nav.setAttribute('aria-orientation','vertical');
  tabs.forEach((tab,i)=>{const help=document.createElement('small');help.id=tab.id+'-help';help.className='pp-builder-step-help';help.textContent=__(descriptions[type][i]||'Review and save.');tab.setAttribute('aria-describedby',help.id);tab.parentElement.append(help);});
  const stage=document.createElement('div');stage.className='pp-builder-stage';nav.after(stage);stage.append(...sections);
  function card(title,description,icon='document'){
   const node=document.createElement('section');node.className='pp-builder-card';node.innerHTML='<header><span class="pp-builder-icon" aria-hidden="true">'+(plus_point.record_profile_ui?.icon(icon)||'')+'</span><div><h3>'+esc(__(title))+'</h3>'+(description?'<p>'+esc(__(description))+'</p>':'')+'</div></header><div class="pp-builder-card-body"></div>';return node;
  }
  function wrap(selector,title,description,icon){const node=area.querySelector(selector);if(!node)return;const box=card(title,description,icon);node.before(box);box.lastElementChild.append(node);return box;}
  function fieldCard(group,keys,title,description,icon){
   if(!group)return;const nodes=keys.map(key=>group.fields_dict[key]?.$wrapper?.[0]).filter(Boolean);if(!nodes.length)return;
   const box=card(title,description,icon);nodes[0].closest('[data-pp-form]').append(box);box.dataset.builderFields=keys.join(',');box.lastElementChild.classList.add('pp-builder-fields');box.lastElementChild.append(...nodes);return box;
  }
  const header=area.querySelector('.pp-op-heading'),actions=header.querySelector('.pp-op-actions,.pp-op-save');
  if(actions){const slot=document.createElement('div');slot.dataset.draftStatusSlot='true';actions.prepend(slot);const draft=area.querySelector('.pp-draft-status');if(draft)slot.append(draft);}
  if(agreement){
   const clientChoice=wrap('.pp-op-client-choice','Select or create client','Choose an existing client or create a new one.','client');
   if(clientChoice&&![...clientChoice.querySelectorAll('.frappe-control')].some(node=>node.style.display!=='none'))clientChoice.hidden=true;
   wrap('.pp-op-client-fields','Contact and address details','Enter the client’s contact information and address.','scope');
   fieldCard(groups.details,['agreement_title'],'Agreement basics','Set a clear name for this agreement.');
   fieldCard(groups.details,['effective_start','effective_end','allow_past_dates'],'Agreement dates','Set the start and end dates for the agreed work.','calendar');
   fieldCard(groups.details,['scope'],'Scope and deliverables','Describe the work included in this agreement.');
   wrap('.pp-agreement-conditions','Conditions','Add specific terms and conditions for this agreement.');
   area.querySelector('.pp-agreement-conditions>h4')?.remove();
   wrap('.pp-op-terms','Billing setup','Configure the agreement currency and client billing settings.','money');
   const daily=wrap('.pp-daily-checkpoints','Payment schedule','Payment periods follow the agreement dates automatically.','calendar');
   const fixed=wrap('.pp-new-milestones','Milestones','Define the agreed payments and when they are due.','calendar');
   const existing=area.querySelector('.pp-op-milestones');if(existing)wrap('.pp-op-milestones','Existing milestones','Review and approve the payments already saved.');
   wrap('.pp-op-capacity','Crew availability','Availability is checked for the selected dates and category.','client');
   wrap('.pp-op-staffing','Sites and crew','Add a site, then define its crew categories and daily requirements.','scope');
   wrap('.pp-agreement-transport','Vehicle requirements','Optional: agree vehicle types and quantities. Assign vehicles in the event.','truck');
   const category=area.querySelector('[data-open-category]'),categoryForm=area.querySelector('.pp-op-category');if(category){const body=area.querySelector('.pp-op-staffing').parentElement;body.append(category,categoryForm);}
   const summary=card('Review summary','Review the entered details before creating your signing link.');summary.classList.add('pp-builder-review');sections.at(-1).prepend(summary);
   wrap('.pp-signing-ready','Send for signature','Create a private signing link, then choose how to share it.','send');area.querySelector('.pp-signing-ready>h4')?.remove();
   const update=()=>{
    if(!read)return;const value=read(),t=value.terms||{},d=value.details||{},c=value.client||{};
    daily.hidden=t.billing_model!=='Daily';fixed.hidden=t.billing_model!=='Fixed'||!!area.querySelector('.pp-new-milestones')?.hidden;if(existing)existing.closest('.pp-builder-card').hidden=t.billing_model!=='Fixed'||existing.hidden;
    const blocks=[['Client details',[c.customer_name||c.client_name||c.name,c.contact_name,c.email,c.city,c.country].filter(Boolean).join(' · '),0],['Agreement details',[d.agreement_title,d.effective_start&&d.effective_start+' – '+d.effective_end].filter(Boolean).join('\n'),1],['Pricing and milestones',[t.billing_model,t.billing_model==='Fixed'?new Intl.NumberFormat().format(Number(t.fixed_amount)||0)+' '+t.agreement_currency:t.agreement_currency,__('{0} payments',[(t.billing_model==='Daily'?value.daily_checkpoints:value.milestones)?.length||0])].filter(Boolean).join('\n'),2],['Sites and crew',[__('{0} sites',[value.sites?.length||0]),__('{0} crew requirements',[value.staffing?.length||0]),__('{0} vehicle requirements',[value.transport?.length||0])].join('\n'),3]];
    summary.lastElementChild.innerHTML='<div class="pp-builder-review-grid">'+blocks.map(([title,text,index])=>'<article><header><h4>'+esc(__(title))+'</h4><button type="button" class="btn btn-default btn-sm" data-review-step="'+index+'">'+esc(__('Edit'))+'<span class="sr-only"> '+esc(__(title))+'</span></button></header><p>'+esc(text||__('Not added yet'))+'</p></article>').join('')+'</div>';
    summary.querySelectorAll('[data-review-step]').forEach(button=>button.onclick=()=>go(Number(button.dataset.reviewStep)));
   };
   area.addEventListener('pp:builder-update',update);update();
  }else{
   const group=groups.project;
   if(group){fieldCard(group,['event_name','contract_terms','start_date','end_date','budget'],'Event basics','These details are used across planning, staffing and reporting.','calendar');fieldCard(group,['enforce_budget'],'Budget control','Choose whether spending above the budget is blocked.','money');fieldCard(group,['notes'],'Event notes','Add information your team needs during the event.');}
   else wrap('.pp-op-new-plan','Event basics','Choose an agreement and name the event. Dates and crew requirements follow the selected agreement.','calendar');
   const board=area.querySelector('.pp-venue-board');if(board){const box=card('Venue and staffing plan','Define venues, select workers and set their event pay.','client');board.before(box);const body=box.lastElementChild;const tools=document.createElement('div');tools.className='pp-actions';for(const sel of ['[data-auto-crew]','[data-add-venue]']){const button=area.querySelector(sel);if(button)tools.append(button);}body.append(tools,board);}
   const reservations=area.querySelector('.pp-op-reservations'),demand=reservations?.previousElementSibling;if(demand?.tagName==='SECTION')demand.classList.add('pp-builder-card');
   wrap('.pp-op-reservations','Transport and equipment','Assign vehicles and reserve warehouse equipment for this event.','truck');
   wrap('.pp-new-plan-review','Venue and staffing plan','Review the crew requirements carried over from the agreement.','client');
   wrap('.pp-new-plan-transport','Vehicle requirements','Review agreed transport before assigning individual vehicles.','truck');
   wrap('.pp-op-timeline','Event timeline','Review staffing coverage and the event schedule.','calendar');
  }
  footer.classList.add('pp-builder-footer');
  const finish=area.querySelector('[data-create-and-sign],[data-create-plan]');if(finish)footer.querySelector('.pp-actions').append(finish);
  const save=area.querySelector('[data-save-project]'),home=document.createComment('event save home');if(save)save.before(home);
  function update(){for(const card of area.querySelectorAll('[data-builder-fields]'))card.hidden=card.dataset.builderFields.split(',').every(key=>groups.project?.fields_dict[key]?.df.hidden);const current=tabs.findIndex(tab=>tab.getAttribute('aria-selected')==='true');if(finish)finish.hidden=current!==tabs.length-1;if(save){const actions=footer.querySelector('.pp-actions');if(current===tabs.length-1){if(save.parentElement!==actions)actions.append(save);}else if(home.nextSibling!==save)home.after(save);}area.dispatchEvent(new Event('pp:builder-update'));}
  area.addEventListener('pp:builder-step',update);update();
  const rail=root.querySelector('.pp-op-activity'),layout=root.querySelector('.pp-op-layout');
  const align=()=>{stage.querySelectorAll('.pp-staffing-calendar').forEach(node=>node.ppCalendarReveal?.());nav.setAttribute('aria-orientation',innerWidth<=767?'horizontal':'vertical');const first=[...stage.querySelectorAll('.pp-builder-card')].find(card=>card.getClientRects().length);rail.style.setProperty('--pp-builder-top',Math.max(0,(first||stage).getBoundingClientRect().top-layout.getBoundingClientRect().top)+'px');};
  const observer=new ResizeObserver(align);observer.observe(header);observer.observe(area);align();
  const cleanup=area.ppFlowCleanup;area.ppFlowCleanup=()=>{cleanup?.();observer.disconnect();};
 };
})();
