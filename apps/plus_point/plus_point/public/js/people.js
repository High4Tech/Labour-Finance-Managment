/* Shared identity capsules, single action dialogs and focused native worker editing. */
(()=>{
 frappe.provide('plus_point');
 plus_point.bind_category_choice=group=>{const c=group.fields_dict?.designation;if(!c||c.df.fieldtype!=='Select'||c.df.read_only||c.ppCategory)return;c.ppCategory=true;const options=Array.isArray(c.df.options)?c.df.options:String(c.df.options||'').split('\n');c.df.options=[...options.filter(v=>v!=='__new__'),{label:__('New category…'),value:'__new__'}];c.refresh();const extra=frappe.ui.form.make_control({parent:c.$wrapper.parent(),df:{fieldtype:'Data',fieldname:'new_category',label:__('New category name')},render_input:true});extra.$wrapper.insertAfter(c.$wrapper).hide();extra.$input.attr('aria-label',__('New category name'));group.ppNewCategory=extra;plus_point.enhance_inputs?.({fields_dict:{new_category:extra}});const old=c.df.onchange;c.df.onchange=async(...args)=>{extra.$wrapper.toggle(c.get_value()==='__new__');if(c.get_value()==='__new__'){extra.$input.trigger('focus');return;}await old?.(...args);};};
 plus_point.resolve_category=async group=>{if(group.fields_dict?.designation?.get_value()!=='__new__')return;const title=String(group.ppNewCategory?.get_value()||'').trim();if(!title){plus_point.field_error(group.ppNewCategory,__('Enter the new category name.'));throw Error(__('Enter the new category name.'));}const saved=await plus_point.form_rpc('operations.create_category',{title});group.ppCreatedCategories=[...new Set([...(group.ppCreatedCategories||[]),saved.name])];const c=group.fields_dict.designation;c.df.options=[...c.df.options.filter(v=>(typeof v==='object'?v.value:v)!=='__new__'),saved.name,{label:__('New category…'),value:'__new__'}];c.refresh();await group.set_value('designation',saved.name);group.ppNewCategory.$wrapper.hide();return saved.name;};
 const esc=v=>frappe.utils.escape_html(String(v??''));
 plus_point.worker_avatar=(name,image)=>{
  const parts=String(name||'').trim().split(/\s+/),initials=(parts.length>1?parts[0][0]+parts.at(-1)[0]:parts[0]?.slice(0,2)||'?').toUpperCase();
  return `<span class="pp-person-avatar" aria-hidden="true">${image?`<img src="${esc(image)}" alt="" loading="lazy" onerror="this.hidden=true;this.nextElementSibling.hidden=false"><span hidden>${esc(initials)}</span>`:esc(initials)}</span>`;
 };
 plus_point.worker_capsule=(name,image)=>`<span class="pp-person-capsule">${plus_point.worker_avatar(name,image)}<span>${esc(name)}</span></span>`;
 let info;
 plus_point.show_info=(button,text)=>{
  const same=info?.button===button;info?.node.remove();if(info)info.button.setAttribute('aria-expanded','false');info=null;if(same)return;
  const fieldHelp=button.classList.contains('pp-control-help'),node=document.createElement('div');node.className='pp-info-portal'+(fieldHelp?' pp-field-tooltip':'');node.role='tooltip';node.textContent=text;document.body.append(node);if(!fieldHelp)plus_point.freddy_feedback?.(node,{tone:'guide',animate:false});
  const box=button.getBoundingClientRect(),width=node.getBoundingClientRect().width;
  node.style.left=Math.max(12,Math.min(innerWidth-width-12,fieldHelp?box.left+box.width/2-width/2:box.right-width))+'px';const above=box.top-node.offsetHeight-8;node.style.top=(fieldHelp&&above>=12?above:Math.min(box.bottom+8,Math.max(12,innerHeight-node.offsetHeight-12)))+'px';button.setAttribute('aria-expanded','true');info={button,node};
 };
 document.addEventListener('click',e=>{if(info&&!info.node.contains(e.target)&&!info.button.contains(e.target)){info.node.remove();info.button.setAttribute('aria-expanded','false');info=null;}});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&info){e.preventDefault();e.stopImmediatePropagation();info.node.remove();info.button.setAttribute('aria-expanded','false');info.button.focus();info=null;}},true);
 let active;
 plus_point.close_action_popup=()=>{if(!active)return Promise.resolve();const previous=active;return new Promise(resolve=>{previous.dialog.$wrapper.one('hidden.bs.modal',resolve);plus_point.close_dialog(previous.dialog);});};
 plus_point.action_popup=async(target,title,{size='extra-large'}={})=>{
  if(!target?.isConnected)return;
  const heading=target.querySelector(':scope>h4');if(heading)heading.hidden=true;
  if(active?.target===target&&!active.closing){active.dialog.set_title(heading?.textContent||__(title));active.dialog.show();return active.dialog;}
  if(active)await plus_point.close_action_popup();
  const scope=target.closest('.pp-op-content')||target.closest('.modal')?.parentElement||target.parentElement,marker=document.createComment('action form');target.before(marker);
  const dialog=new frappe.ui.Dialog({title:heading?.textContent||__(title),size,fields:[{fieldtype:'HTML',fieldname:'content'}]});
  dialog.$wrapper.addClass('pp-action-dialog');dialog.fields_dict.content.$wrapper.append('<div class="pp-modal-feedback pp-op-message" role="status" hidden></div>');dialog.fields_dict.content.$wrapper.append(target);target.hidden=false;
  // Keep controls scoped to their record while the visible content lives in a modal.
  scope.append(dialog.$wrapper.get(0));active={target,dialog};dialog.$wrapper.one('hide.bs.modal',()=>{if(active?.dialog===dialog)active.closing=true;});
  dialog.$wrapper.one('hidden.bs.modal',()=>{if(marker.isConnected){marker.replaceWith(target);target.hidden=true;}target.dispatchEvent(new Event('pp:popup-closed'));if(active?.dialog===dialog)active=null;dialog.$wrapper.remove();});
  dialog.show();return dialog;
 };
 frappe.router.on('change',()=>{plus_point.close_action_popup();if(info){info.node.remove();info=null;}});
 const listDefaults=frappe.views.ListView.prototype.setup_defaults;
 frappe.views.ListView.prototype.setup_defaults=function(...args){const result=listDefaults.apply(this,args);return Promise.resolve(result).then(()=>{if(!frappe.boot.plus_point?.is_platform&&!Array.isArray(this.view_user_settings.filters))this.filters=[];});};

})();
