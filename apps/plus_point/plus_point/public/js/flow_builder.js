/* Presentation only: move the original controls; their validation and save handlers stay intact. */
(()=>{
 frappe.provide('plus_point');
 const esc=v=>frappe.utils.escape_html(String(v??''));

 plus_point.flow_builder=(area,{sections,nav,footer,tabs,go})=>{
  const descriptions={agreement:['Select a client, name the agreement and describe the work.','Set pricing and payment terms. Add commitments only if agreed.','Review the summary and create your agreement.'],event:['Choose the client, agreement and work dates.','Confirm crew and add optional resources.','Review coverage and save the event.']};
  const root=area.closest('.pp-operations'),agreement=area.dataset.flowKind==='agreement',type=agreement?'agreement':'event',groups=area.ppBuilderGroups||{},read=area.ppBuilderRead;
  root.classList.add('pp-flow-builder');area.classList.add('pp-builder-content');area.dataset.builder=type;
  nav.setAttribute('aria-orientation','vertical');
  tabs.forEach((tab,i)=>{const help=document.createElement('small');help.id=tab.id+'-help';help.className='pp-builder-step-help';help.textContent=__(descriptions[type][i]||'Review and save.');tab.setAttribute('aria-describedby',help.id);tab.parentElement.append(help);});
  const stage=document.createElement('div');stage.className='pp-builder-stage';nav.after(stage);stage.append(...sections);
  function card(title,description,icon='document'){
   return plus_point.ui.panel(title,description,icon);
  }
  function wrap(selector,title,description,icon){const node=area.querySelector(selector);if(!node)return;const box=card(title,description,icon);node.before(box);box.lastElementChild.append(node);
   const sync=()=>{const inner=node.querySelector(':scope > .pp-section-heading,:scope > .pp-resource-heading');if(!inner)return;const header=box.querySelector(':scope > header');let actions=header.querySelector('[data-card-actions]')||box.closest('.pp-disclosure-shell')?.querySelector(':scope>.pp-disclosure-actions [data-card-actions]');if(!actions){actions=document.createElement('div');actions.className='pp-actions pp-builder-card-actions';actions.dataset.cardActions='true';header.append(actions);}actions.replaceChildren(...inner.querySelectorAll('button,a.btn'));inner.remove();const note=node.querySelector(':scope > p:not([role])');if(note){header.querySelector('p').textContent=node.dataset.cardSummary||__(description);note.remove();}};
   node.addEventListener('pp:component-render',sync);sync();return box;}

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
   fieldCard(groups.details,['validity_mode','effective_start','effective_end','allow_past_dates'],'Agreement dates','Set the start and end dates for the agreed work.','calendar');
   fieldCard(groups.details,['scope'],'Scope and deliverables','Describe the work included in this agreement.');
   const conditionsCard=wrap('.pp-agreement-conditions','Conditions','Add specific terms and conditions for this agreement.');if(conditionsCard)sections[1].append(conditionsCard);
   area.querySelector('.pp-agreement-conditions>h4')?.remove();
   wrap('.pp-op-terms','Billing setup','Configure the agreement currency and client billing settings.','money');
   const daily=wrap('.pp-daily-checkpoints','Payment schedule','Payment periods follow the agreement dates automatically.','calendar');
   const fixed=wrap('.pp-new-milestones','Milestones','Define the agreed payments and when they are due.','calendar');
   const existing=area.querySelector('.pp-op-milestones');if(existing)wrap('.pp-op-milestones','Existing milestones','Review and approve the payments already saved.');
   wrap('.pp-op-resource-policy','Resource commitment','Choose quantities now, a rate card, or confirm requirements per event.','client');
   const sitesCard=wrap('.pp-op-staffing','Sites and crew','Add a site, then define its crew categories and daily requirements.','scope');
   const capacity=area.querySelector('.pp-op-capacity');if(sitesCard&&capacity)sitesCard.lastElementChild.prepend(capacity);
   wrap('.pp-agreement-transport','Vehicle requirements','Optional: agree vehicle types and quantities. Assign vehicles in the event.','truck');
   const siteAdd=area.querySelector('[data-add-staffing]');if(sitesCard&&siteAdd){const tools=document.createElement('div');tools.className='pp-actions pp-builder-card-actions';tools.append(siteAdd);sitesCard.querySelector('header').append(tools);}
   const summary=card('Review summary','Review the entered details before creating your signing link.');summary.classList.add('pp-builder-review');sections.at(-1).prepend(summary);
   wrap('.pp-signing-ready,.pp-agreement-sharing','Creation checklist','Review the details and choose whether to email the client.','send');area.querySelector('.pp-signing-ready>h4')?.remove();
   let lastReview='';const update=()=>{
    if(!read)return;const t=groups.terms?plus_point.draft_form(groups.terms):(read().terms||{});
    daily.hidden=t.billing_model!=='Daily';fixed.hidden=t.billing_model!=='Fixed'||!!area.querySelector('.pp-new-milestones')?.hidden;if(existing)existing.closest('.pp-builder-card').hidden=t.billing_model!=='Fixed'||existing.hidden;
    if(summary.closest('[hidden]'))return;const value=read(),d=value.details||{},c=value.client||{};
    const blocks=[['Client details',[c.customer_name||c.client_name||c.name,c.contact_name,c.email,c.city,c.country].filter(Boolean).join(' · '),0],['Agreement details',[d.agreement_title,d.effective_start&&d.effective_start+' – '+d.effective_end].filter(Boolean).join('\n'),1],['Pricing and milestones',[t.billing_model,t.billing_model==='Fixed'?new Intl.NumberFormat().format(Number(t.fixed_amount)||0)+' '+t.agreement_currency:t.agreement_currency,__('{0} payments',[(t.billing_model==='Daily'?value.daily_checkpoints:value.milestones)?.length||0])].filter(Boolean).join('\n'),3],['Sites and crew',[__('{0} sites',[value.sites?.length||0]),__('{0} crew requirements',[value.staffing?.length||0]),__('{0} vehicle requirements',[value.transport?.length||0])].join('\n'),2]];
    blocks.sort((a,b)=>a[2]-b[2]);const review=JSON.stringify(blocks);if(review===lastReview)return;lastReview=review;
    summary.lastElementChild.innerHTML='<div class="pp-builder-review-grid">'+blocks.map(([title,text,index])=>'<article><header><h4>'+esc(__(title))+'</h4><button type="button" class="btn btn-default btn-sm" data-review-step="'+index+'">'+esc(__('Edit'))+'<span class="sr-only"> '+esc(__(title))+'</span></button></header><p>'+esc(text||__('Not added yet'))+'</p></article>').join('')+'</div>';
    summary.querySelectorAll('[data-review-step]').forEach(button=>button.onclick=async()=>{const index=Number(button.dataset.reviewStep);await go(index);const target=area.querySelector(['.pp-op-client-fields','.pp-op-details','.pp-op-staffing','.pp-op-terms'][index]);for(let parent=target?.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;if(index===0)area.querySelector('.pp-client-compact button')?.click();target?.scrollIntoView({block:'start',behavior:'instant'});});
   };
   area.addEventListener('pp:builder-update',update);update();
  }else{
   const group=groups.project;
   if(group){fieldCard(group,['event_path','customer','event_name','contract_terms','start_date','end_date','billing_model','fixed_amount','commercial_status','commercial_source','budget'],'Event basics','These details are used across planning, staffing and reporting.','calendar');fieldCard(group,['enforce_budget'],'Budget control','Choose whether spending above the budget is blocked.','money');fieldCard(group,['notes'],'Event notes','Add information your team needs during the event.');}
   else wrap('.pp-op-new-plan','Event basics','Choose an agreement and name the event. Dates and crew requirements follow the selected agreement.','calendar');
   const board=area.querySelector('.pp-venue-board');if(board){const box=card('Venue and staffing plan','Define venues, select workers and set their event pay.','client');board.before(box);const body=box.lastElementChild;const tools=document.createElement('div');tools.className='pp-actions';for(const sel of ['[data-add-venue]','[data-auto-crew]']){const button=area.querySelector(sel);if(button){if(sel==='[data-add-venue]'){button.classList.remove('btn-default');button.classList.add('btn-primary');}tools.append(button);}}tools.classList.add('pp-builder-card-actions');box.querySelector('header').append(tools);body.append(board);}
   const reservations=area.querySelector('.pp-op-reservations'),demand=reservations?.previousElementSibling;if(demand?.tagName==='SECTION')demand.classList.add('pp-builder-card');
   wrap('.pp-op-reservations','Transport and equipment','Assign vehicles and reserve warehouse equipment for this event.','truck');
   wrap('.pp-new-plan-review','Venue and staffing plan','Review the crew requirements carried over from the agreement.','client');
   wrap('.pp-new-plan-transport','Vehicle requirements','Review agreed transport before assigning individual vehicles.','truck');
   wrap('.pp-op-timeline','Staffing schedule','See coverage by date. Select crew to assign workers or open attendance.','calendar');
   const review=card('Review event','Check the dates, coverage and resources before saving.','calendar');sections.at(-1).prepend(review);let last='';
   const refreshReview=()=>{if(review.closest('[hidden]'))return;const data=area.ppBuilderEvent?.();if(!data)return;const missing=data.coverage.reduce((sum,row)=>sum+Number(row.missing||0),0),required=data.coverage.reduce((sum,row)=>sum+Number(row.required||0),0),currency=data.agreement.agreement_currency||data.agreement.currency,value=JSON.stringify([data.event_name,data.start_date,data.end_date,missing,required,data.reservations,data.budget,data.agreement.commercial_status]);if(value===last)return;last=value;
   review.lastElementChild.innerHTML=plus_point.profile_facts([['Event',data.event_name],['Client',data.agreement.client.title||data.agreement.client.customer_name],['Dates',data.start_date+' – '+data.end_date],['Client billing',data.agreement.billing_model],...(Number(data.budget)>0?[['Spending budget',new Intl.NumberFormat().format(Number(data.budget)/(Number(data.agreement.agreement_rate)||1))+' '+currency]]:[])])+'<p>'+esc(required?__(missing?'{0} of {1} worker-days covered':'All {1} worker-days covered',[Math.max(0,required-missing),required]):__('No crew requirement'))+'</p>'+(data.reservations.length?'<ul>'+data.reservations.map(row=>'<li>'+esc(row.title)+' · '+esc(row.start)+' – '+esc(row.end)+'</li>').join('')+'</ul>':'')+(data.agreement.event_basis&&data.agreement.commercial_status==='Pending'?'<p>'+esc(__('Commercial confirmation is needed before invoicing.'))+'</p>':'')+'<button type="button" class="btn btn-default" data-review-crew>'+esc(__(missing?'Assign workers':'Review crew and resources'))+'</button>';review.querySelector('[data-review-crew]').onclick=()=>go(1);};area.addEventListener('pp:builder-update',refreshReview);

  }
  function compactClient(){
   const holder=area.querySelector('.pp-op-client-fields');if(!holder)return;
   holder.parentElement.querySelector('.pp-client-compact')?.remove();
   if(holder.dataset.existingClient!=='true')return;
   const fields=[...holder.querySelectorAll('.frappe-control')],missing=fields.filter(node=>{const field=node.pp_control||holder.pp_form?.fields_dict?.[node.dataset.fieldname];return field?.df.reqd&&!field.get_value();});
   if(missing.length)return;
   const summary=document.createElement('div');summary.className='pp-client-compact';const p=document.createElement('p'),data=read?.().client||{};p.textContent=[data.customer_name,data.contact_name,data.email,data.city,data.country].filter(Boolean).join(' · ');const edit=document.createElement('button');edit.type='button';edit.className='btn btn-default';edit.textContent=__('Edit client details');edit.onclick=()=>{holder.hidden=false;summary.remove();};summary.append(p,edit);holder.before(summary);holder.hidden=true;
  }
  area.addEventListener('pp:client-loaded',compactClient);if(agreement)compactClient();
  const optional=(selector,title,open=false)=>plus_point.ui.optional(area.querySelector(selector)?.closest('.pp-builder-card'),title,{open});
  if(agreement){
   for(const [selector,title] of [['.pp-agreement-conditions','Conditions'],['.pp-op-staffing','Sites and crew'],['.pp-agreement-transport','Vehicle requirements']])optional(selector,title,!!area.querySelector(selector)?.querySelector('tbody tr:not(.pp-table-empty)'));
   const scope=groups.details?.fields_dict.scope,toolbar=scope?.$wrapper?.[0]?.querySelector('.ql-toolbar');if(toolbar){toolbar.hidden=false;const shell=toolbar.parentElement;shell.classList.add('pp-rich-editor');}
  }else{
   optional('.pp-op-reservations','Vehicles and equipment',!!area.querySelector('.pp-op-reservations tbody tr:not(.pp-table-empty)'));
   optional('[data-builder-fields=enforce_budget]','Spending controls',!!groups.project?.get_value('enforce_budget'));
   optional('[data-builder-fields=notes]','Event notes',!!groups.project?.get_value('notes'));
  }
  // Empty native layout scaffolding remains after its fields move into owned panels.
  for(const section of area.querySelectorAll('[data-pp-form] .form-section'))if(!section.querySelector('.frappe-control:not([data-fieldtype="Section Break"]):not([data-fieldtype="Column Break"]),input,textarea,button,table,[contenteditable]'))section.remove();
  footer.classList.add('pp-builder-footer');
  const duplicate=agreement&&area.querySelector('[data-create-and-sign]');if(duplicate)duplicate.remove();const finish=agreement?null:area.querySelector('[data-create-plan]');if(finish)footer.querySelector('.pp-actions').append(finish);
  const save=area.querySelector('[data-save-project]'),home=document.createComment('event save home');if(save)save.before(home);
  let lastStep=-1;function update(){for(const card of area.querySelectorAll('[data-builder-fields]'))card.hidden=card.dataset.builderFields.split(',').every(key=>groups.project?.fields_dict[key]?.df.hidden);const current=tabs.findIndex(tab=>tab.getAttribute('aria-selected')==='true');if(current!==lastStep){lastStep=current;root.dataset.finalStep=String(current===tabs.length-1);if(agreement){const next=footer.querySelector('[data-flow-next]');next.hidden=false;next.disabled=current===tabs.length-1;next.classList.toggle('btn-primary',!next.disabled);next.classList.toggle('btn-default',next.disabled);}if(finish)finish.hidden=current!==tabs.length-1;if(save){save.hidden=current!==tabs.length-1;const actions=footer.querySelector('.pp-actions');if(current===tabs.length-1){if(save.parentElement!==actions)actions.append(save);}else if(home.nextSibling!==save)home.after(save);}}area.dispatchEvent(new Event('pp:builder-update'));}
  area.addEventListener('pp:builder-step',update);area.addEventListener('pp:builder-state',update);update();
  const rail=root.querySelector('.pp-op-activity'),layout=root.querySelector('.pp-op-layout');
  const align=()=>{stage.querySelectorAll('.pp-staffing-calendar').forEach(node=>node.ppCalendarReveal?.());const orientation=innerWidth<=767?'horizontal':'vertical';if(nav.getAttribute('aria-orientation')!==orientation)nav.setAttribute('aria-orientation',orientation);const first=[...stage.querySelectorAll('.pp-builder-card')].find(card=>card.getClientRects().length);const top=Math.max(0,(first||stage).getBoundingClientRect().top-layout.getBoundingClientRect().top)+'px';if(rail.style.getPropertyValue('--pp-builder-top')!==top)rail.style.setProperty('--pp-builder-top',top);};
  const observer=new ResizeObserver(align);observer.observe(header);observer.observe(area);align();
  const cleanup=area.ppFlowCleanup;area.ppFlowCleanup=()=>{cleanup?.();observer.disconnect();area.removeEventListener('pp:client-loaded',compactClient);};
 };
})();
