/* Agreement > venues/categories > event deployment > billing, composed in place. */
(() => {
 frappe.provide('plus_point');
 const esc=v=>frappe.utils.escape_html(String(v??'')),rpc=(method,args={})=>plus_point.form_rpc('operations.'+method,args);
 const fmt=v=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(v)||0);
 const button=(label,cls='btn-default',attrs='')=>`<button type="button" class="btn ${cls}" ${attrs}>${esc(__(label))}</button>`;
 const plain=html=>{const node=document.createElement('textarea');node.innerHTML=String(html||'').replace(/<[^>]*>/g,'');return node.value;};
 const field=(fieldtype,fieldname,label,extra={})=>({fieldtype,fieldname,label:__(label),...extra});
 const link=(name,label,options,extra={})=>field('Link',name,label,{options,only_select:true,...extra});
 function form(root,fields,values={}){
  const layoutFields=[...fields];if(fields.length>=6&&!fields.some(df=>['Table','Column Break','Section Break'].includes(df.fieldtype)))layoutFields.splice(Math.ceil(fields.length/2),0,field('Column Break','columns',''));
  const group=new frappe.ui.FieldGroup({body:root,fields:layoutFields});group.make();root.pp_form=group;
  for(const [key,value] of Object.entries(values))if(group.fields_dict[key]&&value!=null)group.set_value(key,value);
  plus_point.enhance_selectors?.(group);if(group.fields_dict.country&&group.fields_dict.default_currency)plus_point.bind_country_currency?.(group);
  return group;
 }
 function values(group){
  const result=group.get_values(true)||{};
  for(const df of group.fields){if(df.reqd&&!group.fields_dict[df.fieldname]?.df.hidden&&(result[df.fieldname]==null||result[df.fieldname]===''||(Array.isArray(result[df.fieldname])&&!result[df.fieldname].length)))throw new Error(__('{0} is required.',[df.label]));}
  if(!plus_point.validate_inputs?.(group))throw new Error(__('Review the highlighted fields.'));
  return result;
 }
 const message=(root,text,success=false)=>{const box=root.querySelector('.pp-op-message');if(box){box.className='pp-op-message '+(success?'pp-op-success':'pp-onboarding-errors');box.textContent=text||'';box.hidden=!text;}};
 async function act(root,el,run){el.disabled=true;message(root,'');try{return await run();}catch(error){message(root,error.message);}finally{if(el.isConnected)el.disabled=false;}}
 const section=(title,content)=>`<section class="pp-op-section"><h3>${esc(__(title))}</h3>${content}</section>`;
 const grid=(columns,rows)=>`<div class="pp-op-table-scroll"><table class="pp-register-table"><thead><tr>${columns.map(c=>`<th>${esc(__(c))}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
 const money=(n,currency)=>esc(fmt(n)+' '+currency);
 function requirementsFields(){return [
  field('Data','site_name','Venue name',{reqd:1,in_list_view:1}),link('designation','Worker category','Designation',{reqd:1,in_list_view:1}),
  field('Select','phase','Phase',{options:'Setup\nEvent\nPack-down\nOther',default:'Event'}),
  field('Date','start_date','From',{reqd:1,in_list_view:1}),field('Date','end_date','Through',{reqd:1,in_list_view:1}),
  field('Int','workers_required','Workers / day',{reqd:1,in_list_view:1}),field('Currency','wage_rate','Daily wage',{reqd:1,in_list_view:1}),field('Currency','client_rate','Daily client charge'),
  link('country','Country','Country'),field('Data','city','City'),field('Data','address_line1','Street address'),field('Data','state','State / region'),field('Data','postal_code','Postal code'),field('Data','site','Saved venue ID',{hidden:1})];}

 plus_point.mount_operations=(wrapper,mode)=>{
  const titles={'pp-agreements':'Client agreements','pp-event-plans':'Event plans','pp-client-billing':'Billing and finances'};
  const page=frappe.ui.make_app_page({parent:wrapper,title:__(titles[mode]),single_column:true});
  const root=document.createElement('div');root.className='pp-operations';page.main.get(0).append(root);
  let catalogue,sequence=0,record;
  async function load(){
   const token=++sequence;root.innerHTML=`<p role="status">${esc(__('Loading your records…'))}</p>`;
   try{
    catalogue=await rpc('catalogue');if(token!==sequence)return;
    const params=new URL(location.href).searchParams;record=params.get('record')||frappe.route_options?.record;
    if(params.has('project'))record=(mode==='pp-event-plans'?catalogue.plans:catalogue.agreements).find(r=>r.project===params.get('project'))?.name;
    if(mode==='pp-agreements'&&params.has('client'))record=catalogue.agreements.find(r=>r.customer===params.get('client'))?.name;
    const rows=mode==='pp-event-plans'?catalogue.plans:catalogue.agreements;
    if(record==='new'||mode==='pp-event-plans'&&(params.has('agreement')||params.has('project')&&!record))record=null;else if(!record)record=rows[0]?.name;
    root.innerHTML=`<div class="pp-op-layout"><aside class="pp-op-index"><label>${esc(__('Find '+(mode==='pp-event-plans'?'event':'agreement')))}<input type="search" class="form-control pp-op-search"></label><div class="pp-op-records">${rows.map(row=>`<button type="button" class="pp-op-record ${row.name===record?'is-selected':''}" data-record="${esc(row.name)}"><strong>${esc(row.event_name||row.title)}</strong><span>${esc(row.client||row.start_date||'')}</span><small>${esc(__(row.status||'Event plan'))}</small></button>`).join('')||`<p>${esc(__('No records yet. Start with a client agreement.'))}</p>`}</div></aside><main class="pp-op-main"><div class="pp-op-message" role="status" hidden></div><div class="pp-op-content"></div></main><aside class="pp-op-activity" hidden></aside></div>`;
    root.querySelector('.pp-op-search').oninput=e=>root.querySelectorAll('.pp-op-record').forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(e.target.value.toLowerCase()));
    root.querySelectorAll('[data-record]').forEach(el=>el.onclick=()=>frappe.set_route(mode,{record:el.dataset.record}));
    page.clear_primary_action();page.clear_secondary_action();
    if(mode==='pp-agreements')page.set_primary_action(__('New agreement'),()=>frappe.set_route(mode,{record:'new'}),'add');
    if(mode==='pp-event-plans')page.set_primary_action(__('Plan from agreement'),()=>createEvent(),'add');
    if(mode==='pp-client-billing')page.set_secondary_action(__('Refresh figures'),load,'refresh');
    if(mode==='pp-agreements'){page.set_secondary_action(__('Import clients'),()=>plus_point.open_import(plus_point.dashboard_company,load,'clients'),'upload');await agreementEditor(record);}
    else if(mode==='pp-event-plans'){page.set_secondary_action(__('Import event plans'),()=>plus_point.open_import(plus_point.dashboard_company,load,'events'),'upload');if(record)await eventView(record);else await createEvent();}
    else if(record)await billingView(record);else content().innerHTML=section('Start with an agreement',`<p>${esc(__('Invoices and milestones appear here after you create a client agreement.'))}</p><a class="btn btn-primary" href="/desk/pp-agreements?record=new">${esc(__('Create client agreement'))}</a>`);
    if(record)await activityRail(mode==='pp-event-plans'?'PP Event Plan':'PP Contract Terms',record);
    root.dataset.ready='true';
   }catch(error){root.innerHTML=`<p class="pp-onboarding-errors" role="alert">${esc(error.message)}</p>${button('Try again')}`;root.querySelector('button').onclick=load;}
  }
  const content=()=>root.querySelector('.pp-op-content');
  async function activityRail(doctype,name){
   const rail=root.querySelector('.pp-op-activity');if(!rail)return;
   const data=await rpc('activity',{doctype,name});rail.hidden=false;root.querySelector('.pp-op-layout').classList.add('has-activity');
   rail.innerHTML=`<h3>${esc(__('Comments and activity'))}</h3><label>${esc(__('Add a comment'))}<textarea class="form-control pp-op-comment" rows="3" maxlength="5000"></textarea></label>${button('Post comment','btn-default','data-post-comment')}<div class="pp-op-comment-list">${data.comments.map(r=>`<article><strong>${esc(r.comment_by)}</strong><small>${esc(frappe.datetime.str_to_user(r.creation))}</small><div>${esc(plain(r.content))}</div></article>`).join('')}</div><h4>${esc(__('Activity'))}</h4><p>${esc(__('Last updated by {0}',[data.modified_by]))}<small>${esc(frappe.datetime.str_to_user(data.modified))}</small></p>${data.versions.map(r=>`<p>${esc(__('Record updated by {0}',[r.owner]))}<small>${esc(frappe.datetime.str_to_user(r.creation))}</small></p>`).join('')}<p>${esc(__('Created by {0}',[data.owner]))}<small>${esc(frappe.datetime.str_to_user(data.created))}</small></p>`;
   rail.querySelector('[data-post-comment]').onclick=e=>act(root,e.currentTarget,async()=>{await rpc('add_comment',{doctype,name,content:rail.querySelector('textarea').value});await activityRail(doctype,name);});
  }
  async function agreementEditor(name){
   const data=name?await rpc('agreement',{name}):{},venues=Object.fromEntries((data.venues||[]).map(r=>[r.name,r]));
   const area=content();area.innerHTML=`<header class="pp-op-heading"><div><h2>${esc(data.agreement_title||__('New client agreement'))}</h2><p>${esc(__('Define the client, venues, worker categories and payment milestones here. The event plan uses these details.'))}</p></div></header>
    ${section('Client details',`<div class="pp-op-client-choice"></div><div class="pp-op-client-fields"></div>`)}
    ${section('Agreement and billing',`<div class="pp-op-terms"></div>${name?`<p>${esc(__(data.is_signed?'Signed agreement':'Agreement documents'))}</p>${(data.files||[]).map(r=>`<p><a href="${esc(r.file_url)}" target="_blank" rel="noopener">${esc(r.file_name)}</a></p>`).join('')}${button('Upload agreement document','btn-default','data-upload-agreement')}`:''}`)}
    ${section('Venues and staffing categories',`<p>${esc(__('One row per venue, worker category and date range. Set the daily wage and client charge for each category. Open a row for its address.'))}</p><div class="pp-op-staffing"></div><details><summary>${esc(__("Add a worker category"))}</summary><div class="pp-op-category"></div>${button("Save category","btn-default","data-save-category")}</details>`)}
    <div class="pp-op-save">${button('Save agreement','btn-primary','data-save-agreement')}${name?`<a class="btn btn-default" href="/desk/pp-event-plans?agreement=${encodeURIComponent(name)}">${esc(__('Plan this event'))}</a>`:''}</div>
    ${name?section('Payment milestones',`<p>${esc(__('Add milestones now or later. Approval earns the milestone and can automatically create an invoice draft for review.'))}</p><div class="pp-op-milestones"></div>`):''}`;
   let clientData=data.client||{},newClient=!name&&!catalogue.clients.length;
   const choose=form(area.querySelector('.pp-op-client-choice'),[field('Select','client_mode','Client',{options:'Choose existing client\nAdd new client',default:newClient?'Add new client':'Choose existing client'}),link('customer','Client profile','Customer',{default:data.customer,read_only:!!name})]);
   let clientForm;
   async function drawClient(){
    newClient=choose.get_value('client_mode')==='Add new client';
    choose.fields_dict.customer.$wrapper.toggle(!newClient);if(name){choose.fields_dict.client_mode.$wrapper.hide();newClient=false;}
    if(!newClient&&choose.get_value('customer'))clientData=await plus_point.form_rpc('clients.details',{customer:choose.get_value('customer')});
    clientForm=form(area.querySelector('.pp-op-client-fields'),plus_point.resource_fields('clients').map(df=>({...df,only_select:true})),clientData);
   }
   choose.fields_dict.client_mode.df.onchange=()=>{clientData={};area.querySelector('.pp-op-client-fields').innerHTML='';drawClient();};
   choose.fields_dict.customer.df.onchange=()=>{area.querySelector('.pp-op-client-fields').innerHTML='';drawClient();};
   await drawClient();
   const terms=form(area.querySelector('.pp-op-terms'),[
    field('Data','agreement_title','Agreement name',{reqd:1}),field('Date','effective_start','Agreement starts',{reqd:1,default:frappe.datetime.get_today()}),field('Date','effective_end','Agreement ends',{reqd:1,default:frappe.datetime.get_today()}),
    field('Select','billing_model','Client billing',{options:'Daily\nFixed',default:'Daily',reqd:1}),field('Currency','fixed_amount','Fixed contract value',{default:0}),field('Select','status','Agreement status',{options:'Draft\nActive\nClosed',default:'Active'}),
    field('Text Editor','scope','Agreed scope',{reqd:1}),link('billing_item','Invoice service item','Item',{get_query:()=>({filters:{is_stock_item:0,disabled:0}})}),field('Check','auto_invoice','Create invoice draft when a milestone is approved',{default:1})],data);
   const rows=(data.staffing||[]).map(r=>({...r,site_name:venues[r.site]?.site_name||r.site,...Object.fromEntries(['country','city','address_line1'].map(k=>[k,venues[r.site]?.[k]]))}));
   const staffing=form(area.querySelector('.pp-op-staffing'),[field('Table','staffing','Contracted staffing',{fields:requirementsFields(),in_place_edit:true,data:rows,reqd:1})]);
   const category=form(area.querySelector('.pp-op-category'),[field('Data','title','Category name')]);area.querySelector('[data-save-category]').onclick=e=>act(root,e.currentTarget,async()=>{await rpc('create_category',{title:category.get_value('title')});message(root,__('Category added. Select it in the staffing row.'),true);});
   area.querySelector('[data-save-agreement]').onclick=e=>act(root,e.currentTarget,async()=>{
    const result=values(terms);result.staffing=staffing.get_value('staffing');
    const client=values(clientForm);
    if(newClient)result.client=client;else{result.customer=choose.get_value('customer');if(!result.customer)throw new Error(__('Choose the client.'));result.client=client;}
    const saved=await rpc('save_agreement',{name,values:result});message(root,__('Agreement saved.'),true);frappe.set_route('pp-agreements',{record:saved.name});if(name===saved.name)await load();
   });
   area.querySelector('[data-upload-agreement]')?.addEventListener('click',()=>new frappe.ui.FileUploader({doctype:'Contract',docname:data.contract,make_attachments_public:false,on_success:()=>agreementEditor(name)}));
   if(name)milestones(area.querySelector('.pp-op-milestones'),data,()=>agreementEditor(name));
  }
  async function createEvent(){
   const area=content();if(!area)return;area.innerHTML=section('Plan an event from an agreement',`<p>${esc(__('Select the agreement first. Client, venues, dates, categories and rates are copied into the event plan.'))}</p><div class="pp-op-new-plan"></div>${button('Create event plan','btn-primary','data-create-plan')}`);
   const options=catalogue.agreements.filter(r=>r.status==='Active').map(r=>({label:r.title+' / '+r.client,value:r.name}));
   if(!options.length){area.innerHTML=section('Start with a client agreement',`<p>${esc(__('Create or activate a client agreement with venues and worker categories before planning an event.'))}</p><a class="btn btn-primary" href="/desk/pp-agreements?record=new">${esc(__('Create client agreement'))}</a>`);return;}
   const selected=new URL(location.href).searchParams.get('agreement')||catalogue.agreements.find(r=>r.project===new URL(location.href).searchParams.get('project'))?.name;
   const group=form(area.querySelector('.pp-op-new-plan'),[field('Select','contract_terms','Client agreement',{options,reqd:1,default:selected||options[0]?.value}),field('Data','event_name','Event name',{reqd:1}),field('Small Text','notes','Project notes')]);
   group.fields_dict.contract_terms.df.onchange=()=>{const record=catalogue.agreements.find(r=>r.name===group.get_value('contract_terms'));if(record&&!group.get_value('event_name'))group.set_value('event_name',record.title);};
   if(selected){const item=catalogue.agreements.find(r=>r.name===selected);if(item)group.set_value('event_name',item.title);}
   area.querySelector('[data-create-plan]').onclick=e=>act(root,e.currentTarget,async()=>{const saved=await rpc('create_plan',values(group));frappe.set_route('pp-event-plans',{record:saved.name});});
  }
  async function eventView(name){
   const data=await rpc('plan',{name}),area=content(),sites=Object.fromEntries(data.timeline.sites.map(r=>[r.site,r.title]));
   area.innerHTML=`<header class="pp-op-heading"><div><h2>${esc(data.event_name)}</h2><p>${esc(data.start_date)} – ${esc(data.end_date)}</p><a href="/desk/pp-agreements?record=${encodeURIComponent(data.contract_terms)}">${esc(data.agreement.agreement_title||__('Client agreement'))}</a></div><div class="pp-op-actions">${button('Auto-select available crew','btn-primary','data-auto-crew')}<a class="btn btn-default" href="/desk/pp-client-billing?record=${encodeURIComponent(data.contract_terms)}">${esc(__('Billing and finances'))}</a></div></header>
    ${section('Event information',`<p><strong>${esc(data.agreement.client.title)}</strong></p><p>${esc(data.notes||__('No project notes yet.'))}</p><div class="pp-op-project-fields"></div>${button('Save project information','btn-default','data-save-project')}`)}
    ${section('Sites and worker categories',grid(['Venue','Category','Dates','Workers / day','Wage','Assign'],data.staffing.map(r=>`<tr><th>${esc(sites[r.site]||r.site)}</th><td>${esc(r.designation||__('All crew'))}</td><td>${esc(r.start_date)}<br>${esc(r.end_date)}</td><td>${r.workers_required}<br>${button('Adjust headcount','btn-default',`data-edit-headcount="${esc(r.name)}"`)}</td><td>${money(r.wage_rate||data.wage_rate,catalogue.currency)}</td><td>${button('Choose workers','btn-default',`data-choose-crew="${esc(r.name)}"`)}</td></tr>`)))+`<div class="pp-op-crew-picker"></div><details class="pp-op-extra"><summary>${esc(__('Add an extra worker category or staffing phase'))}</summary><p>${esc(__('Extra allocations are labelled against the agreement baseline. Their wages and daily billing use the agreed allocation rates.'))}</p><div class="pp-op-extra-form"></div>${button('Add requirement','btn-default','data-add-requirement')}</details>`}
    ${section('Crew coverage',`<div class="pp-op-coverage"></div>`)}
    ${section('Assigned workers',data.allocations.length?grid(['Worker','Category','Venue','Dates','Next action'],data.allocations.map(r=>`<tr><th><a href="/desk/employee/${encodeURIComponent(r.employee)}">${esc(r.worker)}</a></th><td>${esc(r.designation||'—')}</td><td>${esc(sites[r.site]||r.site)}</td><td>${esc(r.start_date)} – ${esc(r.end_date||'')}</td><td>${button('Move or unassign','btn-default',`data-move-worker="${esc(r.name)}"`)}</td></tr>`)):`<p>${esc(__('No crew assigned. Choose workers by category or auto-select available crew.'))}</p>`)}
    <div class="pp-op-transfer"></div>${section('Event timeline',`<div class="pp-op-timeline"></div>`)}
    ${section('Transport and equipment',`${button('Assign vehicle','btn-default','data-book-vehicle')}${button('Reserve equipment','btn-default','data-book-equipment')}<div class="pp-op-reservations"></div>`)}
    <div class="pp-op-financial-snapshot"></div>`;
   const projectFields=form(area.querySelector('.pp-op-project-fields'),[field('Small Text','notes','Project notes',{default:data.notes}),field('Currency','budget','Spending budget',{default:data.budget}),field('Check','enforce_budget','Stop spending above budget',{default:data.enforce_budget})]);
   area.querySelector('[data-save-project]').onclick=e=>act(root,e.currentTarget,async()=>{await rpc('save_project',{name,values:values(projectFields)});message(root,__('Project information saved.'),true);});
   // Consecutive rows are grouped below without hiding a change in headcount.
   const grouped=[];for(const row of data.coverage){const previous=grouped.findLast(r=>r.site===row.site&&r.designation===row.designation);if(previous&&previous.required===row.required&&previous.planned===row.planned&&previous.assigned===row.assigned&&frappe.datetime.add_days(previous.through,1)===row.date)previous.through=row.date;else grouped.push({...row,through:row.date});}
   area.querySelector('.pp-op-coverage').innerHTML=grid(['Venue / category','Dates','Agreed','Planned','Assigned','State'],grouped.map(r=>`<tr><th>${esc(r.venue)}<small>${esc(r.designation)}</small></th><td>${esc(r.date)} – ${esc(r.through)}</td><td>${r.required}</td><td>${r.planned}</td><td>${r.assigned}</td><td><span class="pp-op-badge ${r.extra||r.planned_extra?'is-extra':r.missing?'is-warning':'is-good'}">${esc(r.extra?__('Extra above agreement: {0}',[r.extra]):r.planned_extra?__('Planned extra: {0}; missing: {1}',[r.planned_extra,r.missing]):r.missing?__('Missing {0}',[r.missing]):__('Covered'))}</span></td></tr>`));
   plus_point.render_event_timeline(area.querySelector('.pp-op-timeline'),data.timeline);area.querySelector('.pp-op-timeline .pp-panel-heading a')?.remove();
   area.querySelector('[data-auto-crew]').onclick=e=>act(root,e.currentTarget,async()=>{const r=await rpc('auto_assign',{name});await eventView(name);message(root,__('{0} workers assigned.',[r.created]),true);});
   area.querySelectorAll('[data-edit-headcount]').forEach(el=>el.onclick=()=>{const target=area.querySelector('.pp-op-crew-picker'),row=data.staffing.find(r=>r.name===el.dataset.editHeadcount);target.innerHTML=`<h4>${esc(__('Adjust planned headcount'))}</h4><p>${esc(__('The agreed count stays unchanged. Existing allocations and wages stay intact; extras are labelled.'))}</p><div class="pp-op-headcount-form"></div>${button('Save planned headcount','btn-primary','data-save-headcount')}`;const group=form(target.querySelector('div'),[field('Int','workers_required','Workers / day',{reqd:1,default:row.workers_required})]);target.querySelector('button').onclick=e=>act(root,e.currentTarget,async()=>{await rpc('update_headcount',{name,requirement:row.name,...values(group)});await eventView(name);});target.scrollIntoView({block:'center'});});
   area.querySelectorAll('[data-choose-crew]').forEach(el=>el.onclick=()=>chooseCrew(data,el.dataset.chooseCrew));
   area.querySelectorAll('[data-move-worker]').forEach(el=>el.onclick=()=>transferEditor(area.querySelector('.pp-op-transfer'),data.allocations.find(r=>r.name===el.dataset.moveWorker),()=>eventView(name)));
   const extra=form(area.querySelector('.pp-op-extra-form'),[link('site','Event site','PP Site',{get_query:()=>({filters:{project:data.project,is_active:1}}),reqd:1}),link('designation','Worker category','Designation',{reqd:1}),field('Date','start_date','From',{reqd:1,default:data.start_date}),field('Date','end_date','Through',{reqd:1,default:data.end_date}),field('Int','workers_required','Workers / day',{reqd:1,default:1}),field('Currency','wage_rate','Daily wage',{reqd:1,default:data.wage_rate}),field('Currency','client_rate','Daily client charge',{default:data.client_rate}),field('Select','phase','Phase',{options:'Setup\nEvent\nPack-down\nOther',default:'Event'})]);
   area.querySelector('[data-add-requirement]').onclick=e=>act(root,e.currentTarget,async()=>{await rpc('add_requirement',{name,values:values(extra)});await eventView(name);});
   for(const kind of ['vehicle','equipment'])area.querySelector('[data-book-'+kind+']').onclick=()=>plus_point.book_event_resource(kind,data.project,data.staffing[0]?.site,data.start_date,data.end_date,()=>eventView(name));
   area.querySelector('.pp-op-reservations').innerHTML=(data.reservations||[]).map(r=>`<p>${esc(r.title)} · ${esc(r.site)} · ${esc(r.start)} – ${esc(r.end)}</p>`).join('')||`<p>${esc(__('No transport or equipment reserved yet.'))}</p>`;
  }
  async function chooseCrew(data,requirement){
   const rootPicker=content().querySelector('.pp-op-crew-picker'),response=await rpc('available_crew',{name:data.name,requirement}),chosen=new Set();
   rootPicker.innerHTML=`<h4>${esc(__('Choose available workers'))}</h4><input type="search" class="form-control pp-op-crew-search" aria-label="${esc(__('Find worker'))}" placeholder="${esc(__('Find worker'))}"><div class="pp-op-crew-tags"></div><div class="pp-op-crew-options"></div>${button('Assign selected workers','btn-primary','data-assign-selected disabled')}${button('Close','btn-default','data-close-crew')}`;
   const draw=()=>{const query=rootPicker.querySelector('input').value.toLowerCase(),rows=response.rows.filter(r=>r.worker.toLowerCase().includes(query));rootPicker.querySelector('.pp-op-crew-options').innerHTML=rows.map(r=>`<label><input type="checkbox" value="${esc(r.name)}" ${chosen.has(r.name)?'checked':''} ${!r.available?'disabled':''}><span>${esc(r.worker)}<small>${esc(r.available?r.designation:r.reason)}</small></span></label>`).join('')||`<p>${esc(__('No workers in this category. Add a worker profile with this designation, then try again.'))}</p>`;rootPicker.querySelector('.pp-op-crew-tags').innerHTML=[...chosen].map(id=>`<button class="pp-op-tag" type="button" data-remove="${esc(id)}">${esc(response.rows.find(r=>r.name===id)?.worker)} ×</button>`).join('');rootPicker.querySelector('[data-assign-selected]').disabled=!chosen.size;rootPicker.querySelectorAll('[data-remove]').forEach(el=>el.onclick=()=>{chosen.delete(el.dataset.remove);draw();});rootPicker.querySelectorAll('input[type=checkbox]').forEach(el=>el.onchange=()=>{el.checked?chosen.add(el.value):chosen.delete(el.value);draw();});};
   rootPicker.querySelector('.pp-op-crew-search').oninput=draw;rootPicker.querySelector('[data-close-crew]').onclick=()=>rootPicker.innerHTML='';draw();
   rootPicker.querySelector('[data-assign-selected]').onclick=e=>act(root,e.currentTarget,async()=>{await rpc('assign_crew',{name:data.name,requirement,employees:[...chosen]});await eventView(data.name);});rootPicker.scrollIntoView({block:'center',behavior:'smooth'});
  }
  async function transferEditor(area,allocation,after){
   area.innerHTML=section('Move or unassign worker',`<p>${esc(allocation.worker)}. ${esc(__('Past wages stay with the original event. New dates use the destination category rates.'))}</p><div class="pp-op-transfer-fields"></div>${button('Save allocation change','btn-primary','data-save-transfer')}${button('Cancel','btn-default','data-cancel-transfer')}`);
   const group=form(area.querySelector('.pp-op-transfer-fields'),[field('Select','action','Action',{options:'Move to another site or event\nUnassign',default:'Move to another site or event'}),field('Date','effective_date','Effective from',{reqd:1,default:frappe.datetime.get_today()}),link('target_plan','Destination event','PP Event Plan'),link('site','Destination site','PP Site',{get_query:()=>({filters:{project:group.__project,is_active:1}})}),field('Date','end_date','Through date')]);
   group.fields_dict.target_plan.df.onchange=async()=>{const target=await rpc('plan',{name:group.get_value('target_plan')});group.__project=target.project;group.set_value('site','');group.set_value('end_date',target.end_date);};
   group.fields_dict.action.df.onchange=()=>['target_plan','site','end_date'].forEach(key=>group.fields_dict[key].$wrapper.toggle(group.get_value('action')!=='Unassign'));
   area.querySelector('[data-save-transfer]').onclick=e=>act(root,e.currentTarget,async()=>{const v=values(group);if(v.action==='Unassign')v.target_plan=null;else if(!v.target_plan||!v.site||!v.end_date)throw new Error(__('Choose the destination event, site and through date before moving this worker.'));delete v.action;await rpc('move_worker',{assignment:allocation.name,...v});await after();message(root,__('Worker allocation updated. Recorded wages were preserved.'),true);});area.querySelector('[data-cancel-transfer]').onclick=()=>area.innerHTML='';area.scrollIntoView({block:'center'});
  }
  function milestones(area,data,after){
   area.innerHTML=`${data.billing_model!=='Fixed'?`<p>${esc(__('This agreement bills approved worker-days. Payment milestones apply to fixed-price agreements.'))}</p>`:grid(['Milestone','Due','Amount','Status','Invoice'],(data.milestones||[]).map(r=>`<tr><th>${esc(r.milestone_title)}</th><td>${esc(r.due_date||'—')}</td><td>${money(r.amount,data.currency)}</td><td>${esc(r.status)} ${r.status==='Planned'?button('Edit / approve','btn-default',`data-edit-milestone="${esc(r.name)}"`):''}</td><td>${r.sales_invoice?`<a href="/desk/pp-client-billing?record=${encodeURIComponent(data.name)}&invoice=${encodeURIComponent(r.sales_invoice)}">${esc(r.sales_invoice)}</a>`:'—'}</td></tr>`))}${data.billing_model==='Fixed'?button('Add milestone','btn-default','data-add-milestone'):''}<div class="pp-op-milestone-editor"></div>`;
   function editor(row={}){
    const target=area.querySelector('.pp-op-milestone-editor');target.innerHTML=`<div class="pp-op-milestone-fields"></div>${button('Save milestone','btn-primary','data-save-milestone')}${button('Cancel','btn-default','data-cancel-milestone')}`;
    const group=form(target.querySelector('div'),[field('Data','milestone_title','Milestone',{reqd:1}),field('Date','due_date','Due date',{default:frappe.datetime.get_today()}),field('Currency','amount','Amount',{reqd:1}),field('Select','status','Status',{options:'Planned\nApproved',default:'Planned',reqd:1})],row);
    target.querySelector('[data-save-milestone]').onclick=e=>act(root,e.currentTarget,async()=>{await rpc('save_milestone',{contract_terms:data.name,name:row.name,values:values(group)});await after();message(root,__('Milestone saved. Approved milestones follow the agreement invoice setting.'),true);});target.querySelector('[data-cancel-milestone]').onclick=()=>target.innerHTML='';
   }
   area.querySelector('[data-add-milestone]')?.addEventListener('click',()=>editor());area.querySelectorAll('[data-edit-milestone]').forEach(el=>el.onclick=()=>editor(data.milestones.find(r=>r.name===el.dataset.editMilestone)));
  }
  async function billingView(name){
   const data=await rpc('billing',{contract_terms:name}),area=content(),agreement=data.agreement,totals=data.totals;
   area.innerHTML=`<header class="pp-op-heading"><div><h2>${esc(agreement.agreement_title||agreement.client.title)}</h2><p>${esc(agreement.client.title)} · ${esc(agreement.billing_model)} ${esc(__('billing'))}</p></div><a class="btn btn-default" href="/desk/pp-agreements?record=${encodeURIComponent(name)}">${esc(__('Review agreement'))}</a></header>
    <div class="pp-op-metrics">${[['Earned revenue',totals.earned_revenue],['Wages earned',totals.labour_cost],['Other costs',totals.other_project_costs],['Operational contribution',totals.operational_profit],['Client outstanding',totals.client_outstanding_gross],['Cash received',totals.cash_collected_gross],['Wages paid',totals.wages_paid],['Wages outstanding',totals.wages_outstanding]].map(([label,n])=>`<article><span>${esc(__(label))}</span><strong>${money(n,agreement.currency)}</strong></article>`).join('')}</div>
    ${section('Payment milestones','<div class="pp-op-billing-milestones"></div>')}
    ${section('Client invoices',`<p>${esc(__('Milestone approval creates invoice drafts when enabled in the agreement. Review and submit drafts before they are posted. Approved source values remain protected. Extra charges can be entered separately.'))}</p><div class="pp-op-actions">${button('Generate from approved work','btn-primary','data-generate-invoice')}${button('Add extra invoice','btn-default','data-extra-invoice')}</div>${grid(['Invoice','Date','Amount','Outstanding','Status','Next action'],data.invoices.map(r=>`<tr><th>${esc(r.name)}</th><td>${esc(r.posting_date)}</td><td>${money(r.grand_total,r.currency)}</td><td>${money(r.outstanding_amount,r.currency)}</td><td>${esc(r.status)}</td><td>${button('Review invoice','btn-default',`data-review-invoice="${esc(r.name)}"`)}</td></tr>`))}<div class="pp-op-invoice-editor"></div>`)}
    ${section('Costs and payments',`<p>${esc(__('Project costs and worker payments stay linked to the same event and appear in its totals.'))}</p><div class="pp-op-actions"><a class="btn btn-default" href="/desk/purchase-invoice?project=${encodeURIComponent(agreement.project)}">${esc(__('Project expenses'))}</a><a class="btn btn-default" href="/desk/pp-wage-settlement?project=${encodeURIComponent(agreement.project)}">${esc(__('Worker payments'))}</a><a class="btn btn-default" href="/desk/payment-entry?project=${encodeURIComponent(agreement.project)}">${esc(__('Client receipts'))}</a><a class="btn btn-default" href="/desk/query-report/PLUS%20POINT%20Project%20Finances?project=${encodeURIComponent(agreement.project)}">${esc(__('Detailed finances'))}</a></div>`)} `;
   milestones(area.querySelector('.pp-op-billing-milestones'),agreement,()=>billingView(name));
   area.querySelector('[data-generate-invoice]').onclick=e=>act(root,e.currentTarget,async()=>{
    const options=await plus_point.form_rpc('billing.invoice_options',{contract_terms:name}),target=area.querySelector('.pp-op-invoice-editor');target.innerHTML=`<h4>${esc(__('Generate from approved work'))}</h4><div class="pp-op-generate-fields"></div>${button('Create invoice draft','btn-primary','data-create-billing-draft')}`;
    const group=form(target.querySelector('div'),[link('item_code','Invoice service item','Item',{reqd:1,default:agreement.billing_item,get_query:()=>({filters:{is_stock_item:0,disabled:0}})}),link('invoice_currency','Invoice currency','Currency',{reqd:1,default:options.currency}),field('Float','exchange_rate','Exchange rate (accounting currency per invoice unit)',{reqd:1,default:options.currency===options.base_currency?1:0}),field('Date','from_date','From date (optional)'),field('Date','to_date','Through date (optional)')]);
    const quote=async()=>{try{const result=await plus_point.form_rpc('billing.quote',{company:options.company,currency:group.get_value('invoice_currency')});await group.set_value('exchange_rate',Number(result.rate));}catch(error){group.set_value('exchange_rate',0);message(root,error.message);}};group.fields_dict.invoice_currency.df.onchange=quote;if(options.currency!==options.base_currency)await quote();
    target.querySelector('button').onclick=e=>act(root,e.currentTarget,async()=>{const result=await plus_point.form_rpc('billing.create_invoice',{contract_terms:name,...values(group)});await billingView(name);await invoiceEditor(result.name,data);});target.scrollIntoView({block:'center'});
   });
   area.querySelectorAll('[data-review-invoice]').forEach(el=>el.onclick=()=>invoiceEditor(el.dataset.reviewInvoice,data));
   area.querySelector('[data-extra-invoice]').onclick=()=>{
    const target=area.querySelector('.pp-op-invoice-editor');target.innerHTML=`<h4>${esc(__('Extra client charge'))}</h4><div class="pp-op-extra-invoice-fields"></div>${button('Create invoice draft','btn-primary','data-save-extra-invoice')}`;
    const group=form(target.querySelector('div'),[link('item_code','Service item','Item',{reqd:1,default:agreement.billing_item,get_query:()=>({filters:{is_stock_item:0,disabled:0}})}),field('Small Text','description','Charge description',{reqd:1}),field('Currency','amount','Amount',{reqd:1})]);target.querySelector('button').onclick=e=>act(root,e.currentTarget,async()=>{const result=await rpc('extra_invoice',{contract_terms:name,...values(group)});await billingView(name);await invoiceEditor(result.name,data);});
   };
   const requested=new URL(location.href).searchParams.get('invoice');if(requested&&data.invoices.some(r=>r.name===requested))await invoiceEditor(requested,data);
  }
  async function invoiceEditor(name,data){
   const invoice=await rpc('invoice',{name}),target=content().querySelector('.pp-op-invoice-editor');
   target.innerHTML=`<h4>${esc(name)}</h4><p>${esc(invoice.docstatus?__('Posted invoice. Saved amounts retain their audit history.'):__('Edit the draft below. Approved work and milestone amounts are locked; descriptions and extra charges can be edited.'))}</p><div class="pp-op-invoice-fields"></div><div class="pp-op-actions">${!invoice.docstatus?button('Save invoice draft','btn-default','data-save-invoice')+button('Submit invoice','btn-primary','data-post-invoice'):''}<a class="btn btn-default" target="_blank" rel="noopener" href="/api/method/plus_point.operations.download_invoice?name=${encodeURIComponent(name)}">${esc(__('Download PDF'))}</a>${button('Email invoice','btn-default','data-email-invoice')}</div><div class="pp-op-email-info" role="status"></div>`;
   const fields=[link('currency','Invoice currency','Currency',{reqd:1,read_only:!!invoice.docstatus}),field('Float','exchange_rate','Exchange rate (accounting currency per invoice unit)',{reqd:1,read_only:!!invoice.docstatus}),field('Date','due_date','Due date',{read_only:!!invoice.docstatus}),field('Small Text','remarks','Invoice notes',{read_only:!!invoice.docstatus})];
   invoice.items.forEach((r,index)=>{fields.push(field('Small Text','description_'+index,'Line '+(index+1)+' description',{default:r.description,read_only:!!invoice.docstatus}));fields.push(field('Currency','rate_'+index,'Rate',{default:r.rate,read_only:!!invoice.docstatus||r.locked}));});
   const group=form(target.querySelector('.pp-op-invoice-fields'),fields,invoice);
   const convert=()=>{const rate=Number(group.get_value('exchange_rate'));if(!(rate>0))return;invoice.items.forEach((r,i)=>group.set_value('rate_'+i,Number(r.rate)*Number(invoice.exchange_rate)/rate));};
   group.fields_dict.exchange_rate.df.onchange=convert;
   group.fields_dict.currency.df.onchange=async()=>{group.set_value('exchange_rate',0);try{const result=await plus_point.form_rpc('billing.quote',{company:data.agreement.client_company||frappe.boot.plus_point.company_identity.name,currency:group.get_value('currency')});await group.set_value('exchange_rate',Number(result.rate));}catch(error){message(root,error.message);}};
   const saveDraft=async()=>{const v=values(group);v.items=invoice.items.map((r,i)=>({name:r.name,description:v['description_'+i],rate:v['rate_'+i]}));await rpc('update_invoice',{name,values:v});};
   target.querySelector('[data-save-invoice]')?.addEventListener('click',e=>act(root,e.currentTarget,async()=>{await saveDraft();message(root,__('Invoice draft saved.'),true);}));
   target.querySelector('[data-post-invoice]')?.addEventListener('click',()=>frappe.confirm(__('Submit this reviewed invoice and post it to the client account?'),()=>act(root,target.querySelector('[data-post-invoice]'),async()=>{await saveDraft();await rpc('post_invoice',{name});await billingView(data.agreement.name);await invoiceEditor(name,data);})));
   target.querySelector('[data-email-invoice]').onclick=e=>act(root,e.currentTarget,async()=>{const options=await rpc('email_options',{name});if(!options.configured){target.querySelector('.pp-op-email-info').innerHTML=`<p>${esc(__('Connect an outgoing email account before sending invoices. The PDF is available to download.'))}</p><a class="btn btn-default" href="/desk/email-account">${esc(__('Configure outgoing email'))}</a>`;return;}const holder=target.querySelector('.pp-op-email-info');holder.innerHTML=`<h4>${esc(__('Email invoice PDF'))}</h4><div class="pp-op-mail-fields"></div>${button('Send invoice email','btn-primary','data-send-invoice')}`;const mail=form(holder.querySelector('div'),[field('Data','recipient','Client email',{reqd:1,options:'Email',default:options.recipient}),field('Data','subject','Subject',{reqd:1,default:__('Invoice {0}',[name])}),field('Small Text','body','Message',{default:__('Please find your invoice attached.')})]);holder.querySelector('button').onclick=e=>act(root,e.currentTarget,async()=>{if(!invoice.docstatus)await saveDraft();await rpc('email_invoice',{name,...values(mail)});holder.innerHTML=`<p>${esc(__('Invoice email queued with the PDF attached. Check the email queue for delivery status.'))}</p>`;});});
   target.scrollIntoView({block:'start'});
  }
  wrapper.pp_operations_load=load;load();
 };

 // Keep the familiar native comment editor and its listeners; change its position.
 function rail(frm){
  if(frm.is_new())return;
  const page=frm.page.wrapper,side=page.find('.layout-side-section').first(),footer=frm.footer?.wrapper;
  if(!side.length||!footer?.length)return;
  let container=side.parent('.pp-record-rail');
  if(!container.length){container=$('<aside class="pp-record-rail"></aside>').insertBefore(side);container.append(side);}
  page.addClass('pp-has-record-rail');
  if(!container.children('.pp-record-activity').length)container.append('<section class="pp-record-activity"><h3>'+esc(__('Comments and activity'))+'</h3></section>');
  const target=container.children('.pp-record-activity');if(footer.parent().get(0)!==target.get(0))footer.appendTo(target);
  plus_point.refresh_record_rail=()=>rail(frm);

 }
 $(document).on('form-refresh.pp-record-rail',(_e,frm)=>{if(!frappe.boot.plus_point?.is_platform){for(const df of frm.meta.fields)if(df.fieldtype==='Link'&&df.options==='Company'){frm.set_df_property(df.fieldname,'hidden',1);if(frm.is_new()&&!frm.doc[df.fieldname])frm.set_value(df.fieldname,frappe.boot.plus_point?.company_identity?.name);}}setTimeout(()=>rail(frm),150);});
 let workerRefresh=0;
 async function workerList(){
  const route=frappe.get_route();if(route[0]!=='List'||route[1]!=='Employee'||frappe.boot.plus_point?.is_platform)return;
  const view=window.cur_list;if(!view||Date.now()-workerRefresh<3000)return;workerRefresh=Date.now();
  try{const states=await rpc('worker_states');view.__pp_states=states;view.settings.get_indicator=doc=>{if(doc.status&&doc.status!=='Active')return [__(doc.status),'grey',''];const state=states[doc.name]||'Available';return [__(state),state==='Available'?'green':state==='Assigned'?'orange':'blue',''];};view.render_list?.();}catch{workerRefresh=0;}
 }
 const ready=()=>{
  let timer;new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(()=>{if(window.cur_frm&&frappe.get_route()[0]==='Form')rail(cur_frm);workerList();},200);}).observe(document.body,{childList:true,subtree:true});
  plus_point.open_event_wizard=()=>frappe.set_route('pp-event-plans',{record:'new'});if(!frappe.boot.plus_point?.is_platform)plus_point.assign_workers=(defaults={})=>frappe.set_route('pp-event-plans',defaults.project?{project:defaults.project}:{});
 };
 if(frappe.boot)ready();else $(document).on('app_ready.pp-operations',ready);
})();
