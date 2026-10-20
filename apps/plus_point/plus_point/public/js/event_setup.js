/* Inline company onboarding. One workspace, resumable steps and a visible skip action. */
(()=>{
 frappe.provide('plus_point');const esc=v=>frappe.utils.escape_html(String(v??''));
 const rpc=async(method,args={})=>{
  const response=await fetch('/api/method/'+method,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':frappe.csrf_token},body:JSON.stringify(args)});
  const data=await response.json();if(!response.ok||data.exc_type){const error=new Error(__('Could not save this step. Check your details and try again.'));error.responseJSON=data;throw error;}return data.message;
 };
 plus_point.setup_rpc=rpc;
 const api=(method,args={})=>rpc('plus_point.event_setup.'+method,args);
 const steps=['company','client','event','terms','workers','plan','vehicle','inventory','allocate','done'];
 const field=(type,name,label,extra={})=>({fieldtype:type,fieldname:name,label:__(label),...(type==='Link'?{only_select:1}:{}),...extra});
 const choose=(name,label,choices,defaultValue)=>field('Select',name,label,{options:choices.join('\n'),default:defaultValue||choices[0]});
 const existing=(name,label,doctype,filters,value)=>field('Link',name,label,{options:doctype,only_select:1,default:value,get_query:()=>({filters})});
 const when=(fields,condition,required=true)=>fields.map(f=>({...f,depends_on:f.depends_on||condition,mandatory_depends_on:required&&f.reqd?condition:f.mandatory_depends_on,reqd:0}));
 let checked=false;
 function lock(on){document.body.classList.toggle('pp-onboarding-active',on);document.querySelectorAll('.body-sidebar a[href]').forEach(a=>{
  const disabled=on&&!a.getAttribute('href').includes('pp-onboarding');
  if(disabled){if(a.dataset.ppOnboardingInert===undefined){a.dataset.ppOnboardingInert=a.inert?'1':'0';a.dataset.ppOnboardingDisabled=a.getAttribute('aria-disabled')||'';}a.inert=true;a.setAttribute('aria-disabled','true');}
  else if(a.dataset.ppOnboardingInert!==undefined){a.inert=a.dataset.ppOnboardingInert==='1';if(a.dataset.ppOnboardingDisabled)a.setAttribute('aria-disabled',a.dataset.ppOnboardingDisabled);else a.removeAttribute('aria-disabled');delete a.dataset.ppOnboardingInert;delete a.dataset.ppOnboardingDisabled;}
 });}
 const copy={company:['Your event company','One subscription, one business workspace. Clients and events belong inside this business.'],client:['Who is the client?','Save the client’s contact and billing address, or use a client already saved in this workspace.'],event:['The event and its first venue','Include setup through pack-down in the date range. More venues and phases go into the next planning step.'],terms:['The client agreement','Save the agreed scope and daily or fixed client billing. This is an internal contract record, not an online signature.'],workers:['Add your event crew','Choose or add one worker, then import more if needed. No staff login is created.'],plan:['Plan each venue day','For each site and phase, enter dates and the number of workers needed every day. Planned work is separate from attendance.'],vehicle:['How will crew or inventory travel?','Assign a vehicle to this event site for crew OR inventory. Capacity is checked, without mapping individual inventory items to cars.'],inventory:['Equipment for the event','Add the equipment you own and its warehouse quantity, then choose how much this event needs. Existing items use their recorded stock.'],allocate:['Review and allocate the crew','The planner picks available active workers for complete phases and checks their existing date commitments again when you save.'],done:['Your first event is ready','The client agreement, event timeline and resource choices are saved. On each actual work date, review and submit attendance before wages are earned.']};
 function fields(s,companies,info){const company=s.company,profile=companies.find(c=>c.name===company)||companies[0],country=profile?.country||frappe.sys_defaults.country||'Pakistan';
  switch(s.step){
   case 'company':return [
    field('Data','company','',{default:profile?.name,hidden:1}),
    field('Data','company_name','Business name',{reqd:1,default:profile?.company_name||frappe.boot.plus_point?.signup_company_name||'',read_only:!!profile}),
    field('Link','country','Country',{options:'Country',default:country,reqd:1}),
    field('Data','currency','Accounting currency',{default:profile?.default_currency||'',read_only:1,description:__(info.currency_locked?'You can correct the country. Existing agreements or accounting entries keep their original accounting currency; changing the country does not convert those amounts.':'Set automatically from the country you choose.')}),
   ];
   case 'client':return [choose('mode','Client',['Add client','Choose existing client'],s.customer?'Choose existing client':'Add client'),
    {...existing('customer','Client','Customer',{},s.customer),depends_on:'eval:doc.mode==="Choose existing client"',mandatory_depends_on:'eval:doc.mode==="Choose existing client"'},
    field('HTML','client_summary','',{depends_on:'eval:doc.mode==="Choose existing client"'}),
    field('Check','edit_client','Edit this client’s details',{default:s.customer?1:0,depends_on:'eval:doc.mode==="Choose existing client"'}),
    ...when(plus_point.resource_fields('clients',country),'eval:doc.mode==="Add client" || doc.edit_client')];
   case 'event':return [choose('mode','Event project',['Create event project','Choose existing event project'],s.project?'Choose existing event project':undefined),
    {...existing('project','Event project','Project',{company,customer:s.customer},s.project),depends_on:'eval:doc.mode==="Choose existing event project"',mandatory_depends_on:'eval:doc.mode==="Choose existing event project"'},
    ...when([field('Data','event_name','Event name',{reqd:1,default:s.event_name})],'eval:doc.mode==="Create event project"'),
    field('Date','start_date','First setup day',{reqd:1,default:s.start_date||frappe.datetime.get_today()}),field('Date','end_date','Last pack-down day',{reqd:1,default:s.end_date||frappe.datetime.get_today()}),
    choose('venue_mode','Venue',['Add event site','Choose existing site'],s.site?'Choose existing site':undefined),
    {...existing('site','Event site','PP Site',{project:s.project,is_active:1},s.site),depends_on:'eval:doc.venue_mode==="Choose existing site"',mandatory_depends_on:'eval:doc.venue_mode==="Choose existing site"'},
    field('Check','edit_site','Edit this venue’s address',{default:s.site?1:0,depends_on:'eval:doc.venue_mode==="Choose existing site"'}),
    ...when([field('Data','site_name','Venue name',{reqd:1}),field('Link','country','Venue country',{options:'Country',default:country,reqd:1}),field('Data','state','State / region'),field('Data','city','City',{reqd:1}),field('Data','address_line1','Street address',{reqd:1}),field('Data','address_line2','Building / additional directions'),field('Data','postal_code','Postal code'),
     field('HTML','map_picker','',{options:'<button type="button" class="btn btn-default pp-choose-map">'+esc(__('Choose from map'))+'</button><div class="pp-location-map" hidden></div><p class="pp-map-status" role="status"></p>'}),
     field('Data','latitude','Latitude (optional)'),field('Data','longitude','Longitude (optional)')],'eval:doc.venue_mode==="Add event site" || doc.edit_site')];
   case 'terms':return [choose('mode','Agreement',['Add client agreement','Use existing billing terms'],s.contract_terms?'Use existing billing terms':undefined),{...existing('contract_terms','Billing terms','PP Contract Terms',{project:s.project,status:'Active'},s.contract_terms),depends_on:'eval:doc.mode==="Use existing billing terms"',mandatory_depends_on:'eval:doc.mode==="Use existing billing terms"'},field('Check','edit_terms','Edit this agreement',{default:s.contract_terms?1:0,depends_on:'eval:doc.mode==="Use existing billing terms"'}),...when([choose('billing_model','How is the client billed?',['Daily','Fixed']),field('Currency','fixed_amount','Agreed fixed client price',{depends_on:'eval:(doc.mode==="Add client agreement" || doc.edit_terms) && doc.billing_model==="Fixed"'}),field('Small Text','agreement','What has the client agreed to?',{reqd:1})],'eval:doc.mode==="Add client agreement" || doc.edit_terms')];
   case 'workers':return [choose('mode','Crew',['Add a worker','Choose existing worker'],s.employee?'Choose existing worker':undefined),{...existing('employee','Worker','Employee',{company,status:'Active'},s.employee),depends_on:'eval:doc.mode==="Choose existing worker"',mandatory_depends_on:'eval:doc.mode==="Choose existing worker"'},...when([field('Data','first_name','First name',{reqd:1}),field('Data','last_name','Last name'),field('Link','gender','Gender',{options:'Gender',reqd:1}),field('Date','date_of_birth','Date of birth',{reqd:1}),field('Date','date_of_joining','Joining date',{reqd:1,default:frappe.datetime.get_today()}),field('Data','cell_number','Phone')],'eval:doc.mode==="Add a worker"')];
   case 'plan':return [field('Check','use_existing_plan','Use this project’s saved event plan if one exists',{default:s.plan?1:0,hidden:!s.plan}),...when([field('Currency','wage_rate','Daily wage for planned crew',{reqd:1}),field('Currency','client_rate','Daily client rate per worker',{reqd:s.billing_model==='Daily'?1:0,default:0}),field('Table','staffing','Venue phases',{reqd:1,in_place_edit:true,data:[{site:s.site,phase:'Event',start_date:s.start_date,end_date:s.end_date,workers_required:1}],fields:[{...existing('site','Event site','PP Site',{project:s.project},s.site),in_list_view:1,reqd:0},field('Data','site_name','New venue (if needed)',{in_list_view:1}),{...choose('phase','Phase',['Setup','Event','Pack-down','Other']),in_list_view:1},{...field('Date','start_date','From',{reqd:1}),in_list_view:1},{...field('Date','end_date','Through',{reqd:1}),in_list_view:1},field('Int','workers_required','Workers / day',{reqd:1,in_list_view:1})]})],'eval:!doc.use_existing_plan')];
   case 'vehicle':return [field('Check','no_vehicle','This event does not need transport',{default:0}),
    {...choose('purpose','Transport purpose',['Crew','Inventory']),depends_on:'eval:!doc.no_vehicle'},
    {...choose('mode','Vehicle',['Add vehicle','Choose existing vehicle'],s.vehicle?'Choose existing vehicle':'Add vehicle'),depends_on:'eval:!doc.no_vehicle'},
    ...when([{...existing('vehicle','Vehicle','Vehicle',{company,pp_event_enabled:1},s.vehicle),reqd:1}],'eval:!doc.no_vehicle && doc.mode==="Choose existing vehicle"'),
    ...when(plus_point.resource_fields('vehicles').filter(f=>!['status','purpose','crew_seats','cargo_capacity','cargo_uom'].includes(f.fieldname)),'eval:!doc.no_vehicle && doc.mode==="Add vehicle"'),
    ...when([field('Int','crew_seats','Crew passenger seats (driver excluded)',{reqd:1})],'eval:!doc.no_vehicle && doc.mode==="Add vehicle" && doc.purpose==="Crew"'),
    ...when([field('Float','cargo_capacity','Inventory load capacity',{reqd:1}),choose('cargo_uom','Load unit',['units','kg','m³'])],'eval:!doc.no_vehicle && doc.mode==="Add vehicle" && doc.purpose==="Inventory"'),
    field('Int','crew_count','Crew passengers for this event (driver excluded)',{default:1,depends_on:'eval:!doc.no_vehicle && doc.purpose==="Crew"'}),
    field('Float','cargo_load','Inventory load for this event',{depends_on:'eval:!doc.no_vehicle && doc.purpose==="Inventory"'})];
   case 'inventory':return [
    field('Check','no_equipment','This event does not need warehouse equipment',{default:0}),
    {...choose('mode','Equipment',['Choose existing item','Add inventory item'],s.item?'Choose existing item':'Add inventory item'),depends_on:'eval:!doc.no_equipment'},
    ...when([{...existing('item','Inventory item','Item',{is_stock_item:1,disabled:0},s.item),reqd:1}],'eval:!doc.no_equipment && doc.mode==="Choose existing item"'),
    ...when(plus_point.resource_fields('inventory_items').filter(f=>f.fieldname!=='status').map(f=>f.fieldname==='stock_uom'?{...f,description:__('Use Nos for individual pieces, or choose the unit you actually count.')} :f),'eval:!doc.no_equipment && doc.mode==="Add inventory item"'),
    {...choose('warehouse_mode','Warehouse',['Choose existing warehouse','Add warehouse'],s.warehouse?'Choose existing warehouse':'Add warehouse'),depends_on:'eval:!doc.no_equipment'},
    ...when([{...existing('warehouse','Warehouse','Warehouse',{company,is_group:0,disabled:0},s.warehouse),reqd:1}],'eval:!doc.no_equipment && doc.warehouse_mode==="Choose existing warehouse"'),
    ...when([field('Data','warehouse_name','Warehouse name',{reqd:1})],'eval:!doc.no_equipment && doc.warehouse_mode==="Add warehouse"'),
    field('Check','set_stock_balance','Update this item’s recorded warehouse quantity',{depends_on:'eval:!doc.no_equipment && doc.mode==="Choose existing item"',description:__('Only update this if you have counted your stock. This replaces the recorded quantity; it does not add to it.')}),
    ...when([
     field('Section Break','starting_stock_section','Warehouse quantity'),
     field('HTML','stock_warning','',{options:'<p>'+esc(__('Enter the total quantity you currently own in this warehouse. Saving records its inventory value and reserves the event quantity. No payment is made.'))+'</p>'}),
     field('Float','stock_quantity','Quantity you own in this warehouse',{reqd:1}),
     field('Currency','valuation_rate','Estimated value per unit (optional)',{default:0,description:__('Enter a unit value to track inventory value, or leave 0 to record quantity only. This does not charge the client.')}),
     field('Check','confirm_stock_balance','I confirm this warehouse quantity and value are correct',{reqd:1})
    ],'eval:!doc.no_equipment && (doc.mode==="Add inventory item" || doc.set_stock_balance)'),
    field('Section Break','event_quantity_section','Event reservation',{depends_on:'eval:!doc.no_equipment'}),
    field('Float','quantity','Quantity needed for this event',{depends_on:'eval:!doc.no_equipment',mandatory_depends_on:'eval:!doc.no_equipment'}),
    field('HTML','inventory_feedback','',{depends_on:'eval:!doc.no_equipment'})
   ];
   case 'allocate':return [field('HTML','crew_preview','',{options:'<p>'+esc(__('Checking available crew…'))+'</p>'})];
   default:return [field('HTML','done','',{options:`<p><strong>${esc(s.event_name||'')}</strong> · ${esc(s.start_date)} – ${esc(s.end_date)}</p><p>${esc(__('Open the event plan to review each venue day, assigned vehicles and reserved equipment. Plan and reservation records create no wages; approved attendance does.'))}</p>`})];
  }
 }
 function errorText(error){
  try{const messages=error?.responseJSON?._server_messages||error?._server_messages;if(messages)return JSON.parse(messages).map(v=>{try{return JSON.parse(v).message;}catch{return v;}}).join(' ' ).replace(/<[^>]*>/g,'');}catch{}
  return error?.message||__('Could not save this step. Check the highlighted fields and try again.');
 }
 async function show(wrapper,info){
  const s=info.state,index=steps.indexOf(s.step),[title,description]=copy[s.step],root=wrapper.pp_onboarding_root;
  root.dataset.ready='false';
  wrapper.pp_setup_info=info;wrapper.pp_maps?.forEach(m=>m.remove());wrapper.pp_maps=[];
  if(info.companies[0])frappe.boot.plus_point.company_country=info.companies[0].country;
  root.innerHTML=`<header class="pp-onboarding-header"><div><p>${esc(__('Your business setup'))}</p><h2>${esc(__(title))}</h2><p>${esc(__(description))}</p></div><button type="button" class="btn btn-default pp-skip-onboarding">${esc(__(s.step==='done'?'Return to overview':'Skip onboarding'))}</button></header>
   <div class="pp-onboarding-layout"><nav aria-label="${esc(__('Onboarding steps'))}"><ol>${steps.slice(0,-1).map((step,i)=>`<li ${s.step===step?'aria-current="step"':''} class="${i<info.furthest?'is-complete':''}"><button type="button" class="pp-onboarding-step" data-step="${step}" ${i>info.furthest?'disabled':''} ${s.step===step?'aria-current="step"':''}><span>${i<info.furthest?'✓':i+1}</span><span>${esc(__(copy[step][0]))}</span></button></li>`).join('')}</ol><p>${esc(__('Choose any completed step to review or edit it. Progress saves after each step.'))}</p></nav><section class="pp-onboarding-panel"><div class="pp-onboarding-errors" role="alert" tabindex="-1" hidden></div><div class="pp-onboarding-fields"></div><footer><button type="button" class="btn btn-default pp-onboarding-back" ${index===0||s.step==='done'?'hidden':''}>${esc(__('Back'))}</button><button type="button" class="btn btn-primary pp-onboarding-save">${esc(__(s.step==='done'?'Open my event plan':s.step==='allocate'?'Allocate crew & finish setup':'Save and continue'))}</button></footer></section></div>`;
  const definitions=fields(s,info.companies,info),form=new frappe.ui.FieldGroup({fields:definitions,no_submit_on_enter:true,body:$(root.querySelector('.pp-onboarding-fields'))});
  // Native FieldGroup resolves visibility, but only Dialog/Form implements
  // conditional required/read-only properties. Apply those to this inline form.
  form.set_dependant_property=function(condition,name,property){this.set_df_property(name,property,this.evaluate_depends_on_value(condition)?1:0);};
  form.make();wrapper.pp_setup_form=form;plus_point.enhance_selectors(form);
  await form.set_values(Object.fromEntries(definitions.filter(f=>f.default!==undefined).map(f=>[f.fieldname,f.default])));
  if(info.values)await form.set_values(info.values);
  if(wrapper.pp_onboarding_drafts?.[s.step])await form.set_values(wrapper.pp_onboarding_drafts[s.step]);
  if(['workers','allocate'].includes(s.step)){
   const button=$('<button type="button" class="btn btn-default pp-inline-import-workers"></button>').text(__('Import workers from a template'));
   button.on('click',()=>{wrapper.pp_onboarding_drafts||={};wrapper.pp_onboarding_drafts[s.step]=form.get_values(true)||{};plus_point.open_import(s.company,()=>plus_point.load_onboarding(wrapper),'employees','Continue onboarding');});$(root.querySelector('.pp-onboarding-fields')).append(button);
  }
  const errorBox=root.querySelector('.pp-onboarding-errors'),save=root.querySelector('.pp-onboarding-save');
  const error=message=>{errorBox.textContent=message;errorBox.hidden=false;errorBox.focus();};
  const actions=[...root.querySelectorAll('.pp-onboarding-save,.pp-onboarding-back,.pp-skip-onboarding,.pp-onboarding-step')],fieldArea=root.querySelector('.pp-onboarding-fields'),saveLabel=save.textContent;
  const disabledBefore=new Map();
  const busy=on=>{actions.forEach(b=>{if(on){disabledBefore.set(b,b.disabled);b.disabled=true;}else b.disabled=disabledBefore.get(b)??b.disabled;});if(!on)disabledBefore.clear();fieldArea.inert=on;save.textContent=on?__('Saving…'):saveLabel;if(wrapper.pp_setup_form===form)root.setAttribute('aria-busy',String(on));};
  lock(info.required);root.dataset.step=s.step;
  const current=()=>form.get_values(true)||{};
  const change=(name,fn)=>{const control=form.fields_dict[name];if(!control)return;const original=control.df.onchange;control.df.onchange=()=>{original?.call(control);fn();};};
  root.querySelector('.pp-skip-onboarding').onclick=async()=>{if(s.step==='done'){lock(false);frappe.set_route('/desk/plus-point');return;}busy(true);try{wrapper.pp_onboarding_drafts||={};wrapper.pp_onboarding_drafts[s.step]=current();await api('control',{action:'skip'});lock(false);frappe.set_route('/desk/plus-point');}catch(e){error(errorText(e));}finally{busy(false);}};
  root.querySelector('.pp-onboarding-back').onclick=async()=>{busy(true);try{wrapper.pp_onboarding_drafts||={};wrapper.pp_onboarding_drafts[s.step]=current();await api('control',{action:'back'});await plus_point.load_onboarding(wrapper);}catch(e){error(errorText(e));}finally{busy(false);}};
  root.querySelectorAll('.pp-onboarding-step').forEach(button=>button.onclick=async()=>{
   if(button.dataset.step===s.step)return;busy(true);
   try{wrapper.pp_onboarding_drafts||={};wrapper.pp_onboarding_drafts[s.step]=current();await api('control',{action:'go',step:button.dataset.step});await plus_point.load_onboarding(wrapper);}catch(e){error(errorText(e));}finally{busy(false);}
  });
  save.onclick=async()=>{
   errorBox.hidden=true;const values=current();
   const missing=Object.values(form.fields_dict).filter(f=>f.df.reqd&&!f.df.hidden&&f.$wrapper?.is(':visible')&&(f.get_value?.()===undefined||f.get_value?.()===null||f.get_value?.()===''||f.df.fieldtype==='Check'&&!f.get_value()));
   if(missing.length){error(__('Complete: {0}',[missing.map(f=>__(f.df.label)).join(', ')]));missing[0].set_focus?.();return;}
   if(s.step==='inventory'&&!values.no_equipment&&(values.mode==='Add inventory item'||values.set_stock_balance)&&Number(values.stock_quantity)<Number(values.quantity)){inventoryFeedback();form.fields_dict.stock_quantity.set_focus();return;}
   busy(true);try{
    if(s.step==='done'){lock(false);frappe.set_route('Form','PP Event Plan',s.plan);return;}
    if(values.mode==='Add client')delete values.customer;if(values.mode==='Create event project')delete values.project;
    if(values.venue_mode==='Add event site')delete values.site;if(values.mode==='Add client agreement')delete values.contract_terms;
    if(values.mode==='Add a worker')delete values.employee;if(values.mode==='Add vehicle')delete values.vehicle;
    if(values.mode==='Add inventory item')delete values.item;if(values.warehouse_mode==='Add warehouse')delete values.warehouse;
    await api('advance',{step:s.step,values:JSON.stringify(values)});if(wrapper.pp_onboarding_drafts)delete wrapper.pp_onboarding_drafts[s.step];
    await plus_point.load_onboarding(wrapper);
   }catch(e){error(errorText(e));}finally{busy(false);}
  };
  function inventoryFeedback(){
   if(s.step!=='inventory')return;const v=current(),target=form.fields_dict.inventory_feedback.$wrapper;
   if(v.no_equipment){target.empty();return;}
   if(v.mode!=='Add inventory item'&&!v.set_stock_balance){target.html('<p>'+esc(__('Uses saved warehouse stock. Update the count only if you have counted it again.'))+'</p>');return;}
   const owned=Number(v.stock_quantity||0),needed=Number(v.quantity||0),short=needed>owned;
   const text=needed<=0?__('Enter how many you own and how many this event needs.'):short?__('You own {0}, but this event needs {1}. Check the warehouse count or reduce the event quantity.',[owned,needed]):v.mode==='Add inventory item'?__('Warehouse: {0} · For this event: {1} · Remaining: {2}',[owned,needed,owned-needed]):__('Warehouse count: {0} · This event: {1}. Other reservations are checked when you save.',[owned,needed]);
   target.html(`<p class="pp-setup-stock-${short?'short':'ready'}" role="${short?'alert':'status'}">${esc(text)}</p>`);
  }
  if(s.step==='inventory'){for(const name of ['mode','no_equipment','set_stock_balance','stock_quantity','quantity'])change(name,inventoryFeedback);inventoryFeedback();}
  if(s.step==='company'){
   let seq=0;const currency=async()=>{const own=++seq;try{const data=await rpc('plus_point.locations.country_defaults',{country:form.get_value('country')});if(own===seq)await form.set_value('currency',data.currency);}catch(e){if(own===seq)error(errorText(e));}};
   if(!info.currency_locked){change('country',currency);await currency();}
  }
  if(s.step==='client'){
   let seq=0;const summary=async(fill=true)=>{const id=++seq,name=form.get_value('customer'),box=form.fields_dict.client_summary.$wrapper;box.empty();if(!name)return;try{const data=await rpc('plus_point.clients.details',{customer:name});if(id!==seq)return;if(fill)await form.set_values(Object.fromEntries(['customer_name','customer_type','contact_name','email','phone','country','state','city','address_line1','address_line2','postal_code'].map(k=>[k,data[k]||''])));box.html(`<div class="pp-client-summary"><strong>${esc(data.title)}</strong><p>${esc([data.contact_name,data.email,data.phone].filter(Boolean).join(' · ')||__('No contact saved yet'))}</p><p>${esc(data.address||__('No billing address saved yet'))}</p></div>`);}catch(e){if(id===seq)error(errorText(e));}};change('customer',summary);await summary(!wrapper.pp_onboarding_drafts?.[s.step]);
  }
  if(s.step==='terms'){
   const fill=async()=>{const name=form.get_value('contract_terms');if(!name)return;try{const terms=await rpc('frappe.client.get',{doctype:'PP Contract Terms',name});const contract=await rpc('frappe.client.get',{doctype:'Contract',name:terms.contract});if(name!==form.get_value('contract_terms'))return;await form.set_values({billing_model:terms.billing_model,fixed_amount:terms.fixed_amount,agreement:contract.contract_terms});}catch(e){error(errorText(e));}};change('contract_terms',fill);
  }
  if(s.step==='event'){
   const fill=async()=>{const name=form.get_value('site');if(!name)return;try{const site=await rpc('frappe.client.get',{doctype:'PP Site',name});if(name!==form.get_value('site'))return;await form.set_values(Object.fromEntries(['site_name','country','state','city','address_line1','address_line2','postal_code','latitude','longitude'].map(k=>[k,site[k]??''])));}catch(e){error(errorText(e));}};change('site',fill);
   const holder=form.fields_dict.map_picker.$wrapper;
   holder.find('.pp-choose-map').on('click',async()=>{const el=holder.find('.pp-location-map').get(0),status=holder.find('.pp-map-status');el.hidden=false;
    if(el.pp_map){el.pp_map.invalidateSize();return;}
    try{await Promise.all([frappe.require('leaflet.bundle.js'),frappe.require('leaflet.bundle.css')]);
     const centers={'Saudi Arabia':[24.5,44],'Pakistan':[30.3,69.3],'United Arab Emirates':[24.2,54.4],'United States':[39,-98],'United Kingdom':[54,-2],'India':[22,79]};
     const value=current(),hasPoint=value.latitude!==undefined&&value.longitude!==undefined&&value.latitude!==''&&value.longitude!=='';
     const map=L.map(el,{scrollWheelZoom:false,fadeAnimation:false}).setView(hasPoint?[Number(value.latitude),Number(value.longitude)]:centers[value.country]||[20,0],hasPoint?13:4);el.pp_map=map;wrapper.pp_maps.push(map);
     L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a>'}).on('loading',()=>{el.dataset.tilesReady='false';}).on('load',()=>{el.dataset.tilesReady='true';}).on('tileerror',()=>status.text(__('Map tiles could not load. Enter the address and coordinates manually, or try again when connected.'))).addTo(map);
     let marker,placing=false;
     const markerAt=(lat,lon)=>{if(marker)marker.setLatLng([lat,lon]);else marker=L.marker([lat,lon],{draggable:true}).addTo(map).on('dragend',e=>{const p=e.target.getLatLng();place(p.lat,p.lng);});};
     const place=async(lat,lon)=>{markerAt(lat,lon);placing=true;try{await form.set_values({latitude:lat.toFixed(6),longitude:lon.toFixed(6)});}finally{placing=false;}status.text(__('Map point selected. Keep the country, city and street address accurate.'));};
     const syncCoordinates=()=>{if(placing)return;const v=current();if(v.latitude==null||v.longitude==null||v.latitude===''||v.longitude==='')return;const lat=Number(v.latitude),lon=Number(v.longitude);if(!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)return;markerAt(lat,lon);map.setView([lat,lon],Math.max(13,map.getZoom()),{animate:false});};
     change('latitude',syncCoordinates);change('longitude',syncCoordinates);
     if(hasPoint)await place(Number(value.latitude),Number(value.longitude));map.on('click',e=>place(e.latlng.lat,e.latlng.lng));status.text(__('Pan and zoom, then click to place the venue pin. You can also type coordinates below.'));map.invalidateSize();
    }catch{status.text(__('The map could not load. You can still enter the address and coordinates below.'));}
   });
  }
  if(s.step==='allocate'){
   save.disabled=true;try{const result=await rpc('plus_point.events.preview_crew',{plan:s.plan});form.fields_dict.crew_preview.$wrapper.html(result.shortages.length?`<p>${esc(__('More workers are needed. Go Back to change the plan or import crew, then retry.'))}</p><ul>${result.shortages.map(r=>`<li>${esc(r.site)}: ${esc(r.missing)} ${esc(__('workers missing'))}</li>`).join('')}</ul>`:`<p>${esc(__('Every phase can be covered. Save to create assignments; this still does not approve attendance.'))}</p>`);save.disabled=!!result.shortages.length;}catch(e){error(errorText(e));}
  }
  root.dataset.ready='true';root.setAttribute('aria-busy','false');
 }
 plus_point.load_onboarding=async wrapper=>{wrapper.pp_onboarding_root.dataset.ready='false';try{const info=await api('status');await show(wrapper,info);}catch(e){wrapper.pp_onboarding_root.innerHTML=`<div class="pp-onboarding-errors" role="alert">${esc(errorText(e))}</div><button type="button" class="btn btn-default pp-setup-retry">${esc(__('Retry onboarding'))}</button><button type="button" class="btn btn-default pp-setup-skip-error">${esc(__('Skip onboarding'))}</button>`;wrapper.pp_onboarding_root.querySelector('.pp-setup-retry').onclick=()=>plus_point.load_onboarding(wrapper);wrapper.pp_onboarding_root.querySelector('.pp-setup-skip-error').onclick=async()=>{try{await api('control',{action:'skip'});lock(false);frappe.set_route('/desk/plus-point');}catch(err){wrapper.pp_onboarding_root.querySelector('[role=alert]').textContent=errorText(err);}};}};
 plus_point.open_setup=()=>frappe.set_route('pp-onboarding');
 plus_point.mount_setup=async root=>{if(!root)return;root.replaceChildren();try{const info=await api('status');if(info.required){frappe.set_route('pp-onboarding');return;}if(info.state.skipped){root.innerHTML=`<div class="pp-setup-resume"><span>${esc(__('Onboarding paused. Your saved steps are kept.'))}</span><button type="button" class="btn btn-default">${esc(__('Resume onboarding'))}</button></div>`;root.querySelector('button').onclick=plus_point.open_setup;}}catch{}};
 const start=()=>{if(checked||frappe.boot.plus_point?.is_platform)return;checked=true;api('status').then(info=>{if(info.required)frappe.set_route('pp-onboarding');}).catch(()=>{});};
 frappe.router.on('change',()=>{if(frappe.get_route()[0]!=='pp-onboarding')lock(false);});
 $(document).on('app_ready.pp-event-setup',start);if(frappe.app?.sidebar)start();
})();
