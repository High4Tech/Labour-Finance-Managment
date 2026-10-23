/* Shared identity capsules, single action dialogs and focused native worker editing. */
(()=>{
 frappe.provide('plus_point');
 const esc=v=>frappe.utils.escape_html(String(v??''));
 plus_point.worker_avatar=(name,image)=>{
  const parts=String(name||'').trim().split(/\s+/),initials=(parts.length>1?parts[0][0]+parts[1][0]:parts[0]?.slice(0,2)||'?').toUpperCase();
  return `<span class="pp-person-avatar" aria-hidden="true">${image?`<img src="${esc(image)}" alt="" loading="lazy" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><span hidden>${esc(initials)}</span>`:esc(initials)}</span>`;
 };
 plus_point.worker_capsule=(name,image)=>`<span class="pp-person-capsule">${plus_point.worker_avatar(name,image)}<span>${esc(name)}</span></span>`;
 let info;
 plus_point.show_info=(button,text)=>{
  const same=info?.button===button;info?.node.remove();if(info)info.button.setAttribute('aria-expanded','false');info=null;if(same)return;
  const node=document.createElement('div');node.className='pp-info-portal';node.role='tooltip';node.textContent=text;document.body.append(node);
  const box=button.getBoundingClientRect(),width=node.getBoundingClientRect().width;
  node.style.left=Math.max(12,Math.min(innerWidth-width-12,box.right-width))+'px';node.style.top=Math.min(box.bottom+8,Math.max(12,innerHeight-node.offsetHeight-12))+'px';button.setAttribute('aria-expanded','true');info={button,node};
 };
 document.addEventListener('click',e=>{if(info&&!info.node.contains(e.target)&&!info.button.contains(e.target)){info.node.remove();info.button.setAttribute('aria-expanded','false');info=null;}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&info){info.node.remove();info.button.setAttribute('aria-expanded','false');info.button.focus();info=null;}});
 let active;
 plus_point.close_action_popup=()=>{if(!active)return Promise.resolve();const previous=active;return new Promise(resolve=>{previous.dialog.$wrapper.one('hidden.bs.modal',resolve);previous.dialog.hide();});};
 plus_point.action_popup=async(target,title)=>{
  if(!target?.isConnected)return;
  const heading=target.querySelector(':scope>h4');if(heading)heading.hidden=true;
  if(active?.target===target){active.dialog.set_title(heading?.textContent||__(title));active.dialog.show();return active.dialog;}
  if(active)await plus_point.close_action_popup();
  const scope=target.closest('.pp-op-content')||target.parentElement,marker=document.createComment('action form');target.before(marker);
  const dialog=new frappe.ui.Dialog({title:heading?.textContent||__(title),size:'extra-large',fields:[{fieldtype:'HTML',fieldname:'content'}]});
  dialog.$wrapper.addClass('pp-action-dialog');dialog.fields_dict.content.$wrapper.append('<div class="pp-modal-feedback pp-op-message" role="status" hidden></div>');dialog.fields_dict.content.$wrapper.append(target);target.hidden=false;
  // Keep controls scoped to their record while the visible content lives in a modal.
  scope.append(dialog.$wrapper.get(0));active={target,dialog};
  dialog.$wrapper.one('hidden.bs.modal',()=>{if(marker.isConnected){marker.replaceWith(target);target.hidden=true;}target.dispatchEvent(new Event('pp:popup-closed'));if(active?.dialog===dialog)active=null;dialog.$wrapper.remove();});
  dialog.show();return dialog;
 };
 frappe.router.on('change',()=>{if(window.cur_frm?.doctype==='Employee'&&!cur_frm.is_dirty()){cur_frm.__pp_worker_edit=false;cur_frm.__pp_worker_groups=null;}plus_point.close_action_popup();if(info){info.node.remove();info=null;}});
 const listDefaults=frappe.views.ListView.prototype.setup_defaults;
 frappe.views.ListView.prototype.setup_defaults=function(...args){const result=listDefaults.apply(this,args);return Promise.resolve(result).then(()=>{if(!frappe.boot.plus_point?.is_platform&&!Array.isArray(this.view_user_settings.filters))this.filters=[];});};

 plus_point.render_worker_editor=async(frm,root,data={})=>{
  const editingName=frm.doc.name;const options=await plus_point.form_rpc('people.work_options',{employee:frm.is_new()?null:frm.doc.name});
  if(!root.isConnected||frm.doc.name!==editingName)return;
  frm.form_wrapper.find('.form-layout,.form-tabs-list,.form-dashboard').hide();frm.remove_custom_button(__('Create User'));frm.enable_save();
  root.innerHTML=`<header class="pp-worker-heading"><div class="pp-person-heading">${plus_point.worker_avatar(frm.doc.employee_name||frm.doc.first_name||__('New worker'),frm.doc.image)}<div><small>${esc(__('Worker profile'))}</small><h2>${esc(frm.doc.employee_name||__('New worker'))}</h2>${frm.doc.pp_reference?`<span class="pp-reference">${esc(frm.doc.pp_reference)}</span>`:''}</div></div>${!frm.is_new()?`<button class="btn btn-default" type="button" data-worker-back>${esc(__('Back to overview'))}</button>`:''}</header><div class="pp-worker-edit-error" role="alert" hidden></div><div class="pp-worker-edit-tabs" role="tablist"></div><div class="pp-worker-edit-body"></div><div class="pp-worker-edit-actions"><button class="btn btn-primary" type="button" data-save-worker-profile>${esc(__('Save worker'))}</button></div>`;
  const df=(type,key,label,more={})=>({fieldtype:type,fieldname:key,label:__(label),...more});
  const layouts=[['Overview',[
   df('Data','first_name','First name',{reqd:1}),df('Data','last_name','Last name'),df('Link','gender','Gender',{options:'Gender',reqd:1}),df('Date','date_of_birth','Date of birth',{reqd:1,max_date:frappe.datetime.get_today()}),df('Column Break','identity_col',''),df('Date','date_of_joining','Joining date',{reqd:1,default:frappe.datetime.get_today()}),df('Select','status','Status',{options:'Active\nInactive\nSuspended\nLeft',reqd:1,default:'Active'}),df('Data','employee_number','Your worker number'),df('HTML','photo_help','',{options:`<p>${esc(__('A worker photo is optional. Add or update it from the saved profile.'))}</p>`})]],
  ['Work details',[df('Select','department','Department',{options:[{value:'',label:''},...options.departments]}),df('Select','designation','Worker category',{options:['',...options.designations]}),df('Column Break','work_col',''),df('Select','reports_to','Reports to',{options:[{value:'',label:''},...options.managers]}),df('Link','employment_type','Employment type',{options:'Employment Type'})]],
  ['Salary and leaves',[df('Select','pp_salary_basis','Salary basis',{options:'Daily\nMonthly',default:'Daily'}),df('Currency','pp_salary_amount','Salary amount',{description:__('Monthly salary uses a 30-day payroll rate for approved attendance. Salary settings do not post unworked wages.')}),df('Float','pp_leaves_per_month','Leave days per month',{default:0}),df('Column Break','salary_col',''),df('Check','pp_loan_allowed','Eligible for loans'),df('Int','pp_loan_wait_months','Loan waiting period (months)',{default:0}),df('Percent','pp_loan_deduction_percent','Monthly loan deduction (%)',{default:10})]],
  ['Contact',[df('Data','cell_number','Phone'),df('Data','personal_email','Email',{options:'Email'}),df('Small Text','current_address','Current address'),df('Column Break','contact_col',''),df('Data','person_to_be_contacted','Emergency contact'),df('Data','emergency_phone_number','Emergency phone'),df('Select','relation','Relationship',{options:['','Parent','Spouse','Sibling','Relative','Friend','Other',...(frm.doc.relation?[frm.doc.relation]:[])]})]]];
  const groups=[],tabs=root.querySelector('.pp-worker-edit-tabs'),body=root.querySelector('.pp-worker-edit-body');
  for(const [index,[title,fields]] of layouts.filter(([title])=>title!=='Salary and leaves'||frm.fields_dict.pp_salary_amount).entries()){
   const tab=document.createElement('button');tab.type='button';tab.role='tab';tab.className='btn btn-default';tab.textContent=__(title);tabs.append(tab);
   const panel=document.createElement('section');panel.role='tabpanel';panel.dataset.workerPanel=title;panel.id='pp-worker-edit-'+index;tab.setAttribute('aria-controls',panel.id);tab.id=panel.id+'-tab';panel.setAttribute('aria-labelledby',tab.id);panel.hidden=index!==0;body.append(panel);
   const group=new frappe.ui.FieldGroup({body:panel,fields:fields.map(f=>({...f,default:frm.doc[f.fieldname]??f.default}))});group.make();plus_point.enhance_selectors(group);for(const c of Object.values(group.fields_dict))c.$input?.attr('aria-label',c.df.label||'');groups.push(group);$(panel).on('input.pp-worker-dirty change.pp-worker-dirty',event=>{if(!event.originalEvent||frm.is_dirty())return;if(group.fields.some(f=>frm.fields_dict[f.fieldname]&&String(group.get_value(f.fieldname)??'')!==String(frm.doc[f.fieldname]??'')))frm.dirty();});
   tab.onclick=()=>{[...tabs.children].forEach(b=>b.setAttribute('aria-selected',String(b===tab)));[...body.children].forEach(p=>p.hidden=p!==panel);};if(index===0)tab.click();
  }
  const work=groups[1],updateRoles=()=>{const current=work.get_value('designation'),roles=options.roles[work.get_value('department')]||options.designations;work.fields_dict.designation.df.options=['',...roles];work.fields_dict.designation.refresh();if(current&&!roles.includes(current))work.set_value('designation','');};
  work.fields_dict.department.df.onchange=updateRoles;
  if(options.roles[frm.doc.department]?.includes(frm.doc.designation))updateRoles();
  frm.__pp_worker_groups=groups;root.dataset.ready='true';
  if(!frm.__pp_worker_save_bridge){const nativeSave=frm.save;frm.__pp_worker_save_bridge=true;frm.save=async function(...args){try{await sync(this);const isNew=this.is_new();const result=await nativeSave.apply(this,args);if(isNew&&!this.is_new())await this.reload_doc();return result;}catch(error){const box=this.__pp_worker?.get(0)?.querySelector('.pp-worker-edit-error');if(box){box.hidden=false;box.textContent=String(error.message||__('Review the worker fields.')).replace(/<[^>]*>/g,'');}return null;}};}

  root.querySelector('[data-worker-back]')?.addEventListener('click',()=>{frm.__pp_worker_groups=null;frm.__pp_worker_edit=false;frm.reload_doc();});
  root.querySelector('[data-save-worker-profile]').onclick=async e=>{const button=e.currentTarget,box=root.querySelector('.pp-worker-edit-error');button.disabled=true;try{await frm.save();}catch(error){box.hidden=false;box.textContent=String(error.message||__('Review the required worker fields.')).replace(/<[^>]*>/g,'');}finally{button.disabled=false;}};
 };
 async function sync(frm){
  if(!frm.__pp_worker_groups)return;
  for(const group of frm.__pp_worker_groups){if(!plus_point.validate_inputs(group))throw Error(__('Review the highlighted fields.'));const values=group.get_values(true)||{};
   for(const df of group.fields)if(df.reqd&&!values[df.fieldname])throw Error(__('{0} is required.',[df.label]));
   for(const [key,value]of Object.entries(values))if(frm.fields_dict[key])await frm.set_value(key,value);
  }
  if(!frm.doc.company)await frm.set_value('company',frappe.boot.plus_point.company_identity.name);
 }
 frappe.ui.form.on('Employee',{validate:sync});
})();
