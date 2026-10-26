/* Shared record sections and popup editors. Profiles show saved facts; forms stay in dialogs. */
(()=>{
 frappe.provide('plus_point');
 const esc=v=>frappe.utils.escape_html(String(v??'')),rpc=(method,args)=>plus_point.form_rpc('operations.'+method,args);
 const text=html=>{const el=document.createElement('textarea');el.innerHTML=String(html||'').replace(/<br\s*\/?>|<\/(?:p|div|li|h[1-6])>/gi,'\n').replace(/<[^>]*>/g,'');return el.value.trim();};
 const btn=(label,attr)=>'<button type="button" class="btn '+plus_point.action_class(label)+'" '+attr+'>'+esc(__(label))+'</button>';
 plus_point.profile_section=(title,html,action='')=>'<section class="pp-profile-section"><header class="pp-section-heading"><h3>'+esc(__(title))+'</h3>'+action+'</header>'+html+'</section>';
 plus_point.profile_facts=items=>'<dl class="pp-profile-facts">'+items.map(([label,value])=>'<div><dt>'+esc(__(label))+'</dt><dd>'+esc(value||'—')+'</dd></div>').join('')+'</dl>';
 plus_point.profile_dialog=({title,fields,save})=>{
  const d=new frappe.ui.Dialog({title:__(title),size:'large',fields:[...fields,{fieldtype:'HTML',fieldname:'save_feedback',options:'<p role="alert" class="pp-profile-save-error"></p>'}],primary_action_label:__('Save changes'),primary_action:async values=>{if(!plus_point.validate_inputs(d))return;d.disable_primary_action();try{const saved=await save(values,d);if(saved===false)return;d.hide();document.dispatchEvent(new Event('pp:data-changed'));}catch(error){d.fields_dict.save_feedback.$wrapper.find('p').text(error.message);}finally{d.enable_primary_action();}}});
  d.$wrapper.addClass('pp-profile-dialog');d.$wrapper.one('hidden.bs.modal',()=>d.$wrapper.remove());d.show();plus_point.enhance_selectors(d);for(const c of Object.values(d.fields_dict))c.$input?.attr('aria-label',c.df.label||'');return d;
 };
 plus_point.render_agreement_profile=async(area,data,catalogue,refresh,renderMilestones)=>{
  const name=data.name,currency=data.agreement_currency||data.currency,rate=Number(data.agreement_rate)||1,client=data.client||{},venues=Object.fromEntries((data.venues||[]).map(row=>[row.name,row]));
  const conditions=JSON.parse(data.pp_conditions||'[]'),transport=JSON.parse(data.pp_transport_requirements||'[]'),layout=plus_point.agreement_profile_layout(area,data);
  area.querySelector('[data-profile-scope-copy]').textContent=text(data.scope);
  const refreshPanel=async()=>{layout.keepPanel();await refresh();};
  const save=async values=>{const result=await plus_point.propose_agreement_update(name,values);if(result){await refreshPanel();return true;}return false;};
  const f=(fieldtype,fieldname,label,more={})=>({fieldtype,fieldname,label:__(label),...more});
  area.querySelector('[data-profile-details]').onclick=()=>plus_point.profile_dialog({title:'Agreement details',fields:[f('Data','agreement_title','Agreement name',{reqd:1,default:data.agreement_title}),f('Date','effective_start','Agreement starts',{reqd:1,default:data.effective_start}),f('Select','validity_mode','Agreement validity',{options:'Fixed period\nOngoing',default:data.validity_mode||'Fixed period'}),f('Date','effective_end','Agreement ends',{default:data.effective_end})],save});
  area.querySelector('[data-profile-scope]').onclick=()=>plus_point.profile_dialog({title:'Agreement scope',fields:[f('Text Editor','scope','Scope and deliverables',{reqd:1,default:data.scope})],save});
  area.querySelector('[data-profile-client]').onclick=()=>plus_point.profile_dialog({title:'Client details',fields:plus_point.resource_fields('clients').filter(f=>f.fieldname!=='default_currency').map(f=>({...f,default:client[f.fieldname]})),save:values=>save({client:values})});
  area.querySelector('[data-profile-conditions]').onclick=()=>{
   const d=plus_point.profile_dialog({title:'Agreement conditions',fields:[f('HTML','conditions','',{options:'<div class="pp-profile-condition-rows"></div>'+btn('Add condition','data-append-condition')})],save:()=>save({pp_conditions:JSON.stringify([...d.body.querySelectorAll('textarea')].map(t=>t.value.trim()).filter(Boolean))})});
   const holder=d.body.querySelector('.pp-profile-condition-rows');const add=value=>{const row=document.createElement('div');row.className='pp-condition-row';row.innerHTML='<textarea class="form-control" aria-label="'+esc(__('Condition'))+'" rows="2" maxlength="5000"></textarea>'+btn('Remove','data-remove');row.querySelector('textarea').value=value||'';row.querySelector('button').onclick=()=>row.remove();holder.append(row);};conditions.forEach(add);d.body.querySelector('[data-append-condition]').onclick=()=>add('');
  };
  area.querySelector('[data-profile-pricing]').onclick=()=>{
   const d=plus_point.profile_dialog({title:'Agreement pricing',fields:[f('Link','agreement_currency','Agreement currency',{options:'Currency',reqd:1,default:currency}),f('Select','billing_model','Client billing',{options:'Daily\nFixed',default:data.billing_model,reqd:1}),f('Float','fixed_amount','Fixed contract value ('+currency+')',{default:Number(data.fixed_amount||0)/rate,hidden:data.billing_model!=='Fixed'}),f('Check','auto_invoice','Create invoice draft when a milestone is approved',{default:data.auto_invoice})],save:values=>save({...values,fixed_amount:values.billing_model==='Fixed'?values.fixed_amount:0,pp_daily_checkpoints:values.billing_model==='Fixed'?'[]':data.pp_daily_checkpoints||'[]'})});
   d.fields_dict.billing_model.df.onchange=()=>d.set_df_property('fixed_amount','hidden',d.get_value('billing_model')!=='Fixed');d.fields_dict.agreement_currency.df.onchange=()=>d.set_df_property('fixed_amount','label',__('Fixed contract value')+' ('+(d.get_value('agreement_currency')||currency)+')');
  };
  area.querySelector('[data-profile-crew]').onclick=()=>{
   let editor,future=Number(data.pp_future_crew_count)||0;
   const d=plus_point.profile_dialog({title:'Sites and crew',fields:[f('HTML','crew','',{options:'<div class="pp-profile-crew-editor"></div>'})],save:async()=>{await editor.flush();await save({staffing:editor.get_value('staffing'),sites:editor.siteNames(),site_details:editor.siteDetails(),pp_future_crew_count:future});}});
   editor=plus_point.agreement_staffing_editor(d.body.querySelector('.pp-profile-crew-editor'),{rows:(data.staffing||[]).map(r=>({...r,site_name:venues[r.site]?.site_name||r.site,...Object.fromEntries(['country','city','address_line1'].map(k=>[k,venues[r.site]?.[k]||''])),client_rate:Number(r.client_rate)/rate,wage_rate:0})),sites:(data.venues||[]).map(v=>v.site_name),roles:catalogue.designations,currency:()=>currency,model:()=>data.billing_model,dates:()=>({start_date:data.effective_start,end_date:data.effective_end}),agreement:name,customer:()=>data.customer,country:()=>client.country,future:()=>future,setFuture:n=>future=n,capacity:()=>{},copyTransport:()=>{}});
  };
  area.querySelector('[data-profile-vehicles]').onclick=()=>{
   let editor;const d=plus_point.profile_dialog({title:'Vehicle requirements',fields:[f('HTML','vehicles','',{options:'<div class="pp-profile-vehicle-editor"></div>'})],save:()=>save({transport_requirements:editor.get_value()})});
   editor=plus_point.agreement_transport_editor(d.body.querySelector('.pp-profile-vehicle-editor'),{agreement:data.name,rows:transport,sites:()=>(data.venues||[]).map(v=>v.site_name),dates:()=>({start:data.effective_start,end:data.effective_end})});
  };
  const holder=area.querySelector('.pp-profile-milestones');
  if(data.billing_model==='Daily'){
   const daily=plus_point.daily_checkpoints_editor(holder,{rows:JSON.parse(data.pp_daily_checkpoints||'[]'),dates:()=>({start:data.effective_start,end:data.effective_end}),currency:()=>currency,agreement:name});
   holder.addEventListener('pp:flow-change',()=>save({pp_daily_checkpoints:JSON.stringify(daily.get_value())}).catch(error=>{holder.querySelector('.pp-checkpoint-feedback').textContent=error.message;}));
  }else renderMilestones(holder,data,refreshPanel);
  area.querySelector('[data-profile-pdf]')?.addEventListener('click',async()=>plus_point.preview_document(await plus_point.form_rpc('agreement_documents.agreement_pdf',{name})));
  area.querySelector('[data-profile-sign]').onclick=()=>plus_point.open_agreement_signing(name);
  area.querySelectorAll('[data-profile-upload]').forEach(button=>button.onclick=()=>new frappe.ui.FileUploader({doctype:'Contract',docname:data.contract,make_attachments_public:false,allow_multiple:false,on_success:refreshPanel}));
  area.querySelector('[data-profile-event]').onclick=async()=>{if(data.status==='Draft'){frappe.set_route('pp-agreements',{record:name,edit:1});return;}try{await plus_point.open_event_draft(await plus_point.form_rpc('drafts.event_for_agreement',{agreement:name}));}catch(error){frappe.show_alert({message:error.message,indicator:'red'});}};
 };
})();
