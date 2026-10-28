/* Visual contract against the actual Figma nodes; native controls, no record writes. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),{chromium}=require('playwright');
(async()=>{
 const phase=process.argv[2]||'after',out=path.resolve('.local/qa/figma-parity');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1600,height:1200},deviceScaleFactor:2});page.setDefaultTimeout(90000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
 await page.goto('http://high4tech-events-fd166a217c.localhost:8000/login');await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim());
 await page.goto('http://high4tech-events-fd166a217c.localhost:8000/desk/plus-point',{waitUntil:'commit'});await page.locator('.pp-dashboard[data-ready=true]').waitFor();
 await page.evaluate(()=>{
  window.parityDialog=new frappe.ui.Dialog({title:'Figma component verification',size:'large',fields:[
   {fieldname:'email',label:'Email',fieldtype:'Data',options:'Email',reqd:1,description:'This is a hint text to help user.',default:'olivia@untitledui.com'},
   {fieldname:'details',label:'Description',fieldtype:'Small Text',reqd:1,description:'This is a hint text to help user.',default:'A little about the company and the team that you’ll be working with.'},
   {fieldname:'member',label:'Team member',fieldtype:'Select',options:'Phoenix Baker\nOlivia Rhye\nLana Steiner\nDemi Wilkinson\nCandice Wu\nNatali Craig',default:'Olivia Rhye',reqd:1,description:'This is a hint text to help user.'},
   {fieldname:'customer_type',label:'Client type',fieldtype:'Select',options:'Company\nIndividual',default:'Company'},
   {fieldname:'phase',label:'Phase',fieldtype:'Select',options:'Setup\nEvent\nPack-down\nOther',default:'Event'},
   {fieldname:'consent',label:'Remember me',fieldtype:'Check',description:'Save my login details for next time.'},
   {fieldname:'quantity',label:'Workers per day',fieldtype:'Int',min:1,default:1},
   {fieldname:'start_date',label:'Date',fieldtype:'Date',default:frappe.datetime.get_today()}
  ]});parityDialog.show();plus_point.enhance_selectors(parityDialog);
 });
 const modal=page.locator('.modal.show').last();await modal.waitFor();await page.waitForTimeout(700);
 // A component's responsive width is supplied by its form column. Match the 320px Figma instance.
 await page.evaluate(()=>{for(const f of Object.values(parityDialog.fields_dict))f.$wrapper?.css({width:'320px',maxWidth:'100%'});});
 const field=n=>modal.locator('.frappe-control[data-fieldname='+n+']');
 await modal.screenshot({path:path.join(out,phase+'-dialog.png')});
 const geometry=()=>page.evaluate(()=>Object.fromEntries(Object.entries(parityDialog.fields_dict).filter(([,c])=>c.$wrapper).map(([key,c])=>{const input=c.$input?.get(0),visible=input?.ppSelect?.button||input,label=c.$wrapper.find('.control-label').get(0),s=visible&&getComputedStyle(visible);return [key,{html:c.$wrapper.get(0).outerHTML,style:s&&Object.fromEntries(['height','fontFamily','fontSize','fontWeight','lineHeight','borderColor','borderRadius','padding','backgroundImage'].map(k=>[k,s[k]])),label:label&&{rect:label.getBoundingClientRect().toJSON(),style:getComputedStyle(label).display},rect:visible?.getBoundingClientRect().toJSON()}];})));
 await modal.locator('.btn-modal-close').focus();await page.waitForTimeout(150);const before=await geometry();fs.writeFileSync(path.join(out,phase+'-geometry.json'),JSON.stringify({fields:before,errors},null,2));for(const name of ['email','details','member','customer_type','phase','consent'])await field(name).screenshot({path:path.join(out,phase+'-'+name+'.png')});
 fs.writeFileSync(path.join(out,phase+'-choices.json'),JSON.stringify(await field('customer_type').locator('input:visible').evaluateAll(nodes=>nodes.map(n=>({html:n.outerHTML,styles:[null,':before',':after'].map(p=>Object.fromEntries(['content','appearance','width','height','borderRadius','borderWidth','position','background','margin','transform'].map(k=>[k,getComputedStyle(n,p)[k]])))}))),null,2));
 await field('email').locator('input').focus();await field('email').screenshot({path:path.join(out,phase+'-email-focused.png')});
 await field('email').locator('input').fill('invalid');await field('email').screenshot({path:path.join(out,phase+'-email-error.png')});await field('member').locator('.pp-select-trigger').click();await page.locator('.pp-select-menu').screenshot({path:path.join(out,phase+'-menu.png')});await page.keyboard.press('Escape');
 if(phase!=='before'){
  assert.equal(before.email.style.height,'40px');assert.equal(before.email.style.fontWeight,'400');assert.equal(before.email.style.borderColor,'rgb(203, 213, 225)');assert.equal(before.member.style.height,'40px');assert.equal(before.details.style.height,'128px');
  assert.equal(await field('email').locator('.pp-control-leading img').count(),1);assert.equal(await field('email').locator('.pp-control-help img').count(),1);
  assert.equal(await field('email').locator('input').getAttribute('aria-invalid'),'true');assert(await field('email').locator('.pp-input-hint').isVisible());
  await field('quantity').getByRole('button',{name:'Increase Workers per day',exact:true}).click();assert.equal(await page.evaluate(()=>parityDialog.get_value('quantity')),2);await field('quantity').getByRole('button',{name:'Decrease Workers per day',exact:true}).click();assert.equal(await page.evaluate(()=>parityDialog.get_value('quantity')),1);await field('quantity').getByRole('button',{name:'Decrease Workers per day',exact:true}).click();assert.equal(await page.evaluate(()=>parityDialog.get_value('quantity')),1);
  for(const name of ['quantity','start_date'])await field(name).screenshot({path:path.join(out,'after-'+name+'.png')});
  const assets=await modal.locator('img[src*="/images/figma/"]').evaluateAll(nodes=>nodes.map(n=>({name:n.src.split('/').at(-1),loaded:n.complete&&n.naturalWidth>0,width:n.width,height:n.height,naturalWidth:n.naturalWidth,naturalHeight:n.naturalHeight})));assert(assets.every(n=>n.loaded&&n.width===n.naturalWidth&&n.height===n.naturalHeight),JSON.stringify(assets));fs.writeFileSync(path.join(out,'assets.json'),JSON.stringify(assets,null,2));
  await field('email').locator('input').fill('olivia@untitledui.com');assert(await field('email').locator('.help-box').isVisible());await field('member').locator('.pp-select-trigger').click();await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');assert.equal(await field('member').locator('select').inputValue(),'Lana Steiner');
  await field('email').getByRole('button',{name:'Help: Email',exact:true}).click();const tooltip=page.locator('.pp-field-tooltip');assert(await tooltip.isVisible());assert.equal(await tooltip.evaluate(n=>getComputedStyle(n).backgroundColor),'rgb(0, 31, 51)');await tooltip.screenshot({path:path.join(out,'after-help.png')});await page.keyboard.press('Escape');assert.equal(await tooltip.count(),0);
  await modal.getByRole('radio',{name:'Individual',exact:true}).check();assert.equal(await page.evaluate(()=>parityDialog.get_value('customer_type')),'Individual');await modal.getByRole('checkbox',{name:'Setup',exact:true}).check();assert.equal(await page.evaluate(()=>parityDialog.get_value('phase')),'Setup, Event');
  await page.evaluate(()=>parityDialog.set_df_property('customer_type','read_only',1));assert(await modal.getByRole('radio',{name:'Individual',exact:true}).isDisabled());await page.evaluate(()=>parityDialog.set_df_property('customer_type','read_only',0));assert(await modal.getByRole('radio',{name:'Individual',exact:true}).isEnabled());
  await page.evaluate(()=>parityDialog.fields_dict.email.$input.prop('disabled',true));await field('email').screenshot({path:path.join(out,'after-email-disabled.png')});await page.evaluate(()=>parityDialog.fields_dict.email.$input.prop('disabled',false));
  await page.addScriptTag({path:path.resolve('.local/a11y/node_modules/axe-core/axe.min.js')});const accessibility=[];
  for(const width of [390,768,1600])for(const theme of ['light','dark']){await page.setViewportSize({width,height:1200});await page.evaluate(t=>document.documentElement.dataset.theme=t,theme);const v=await page.evaluate(async()=>{const r=await axe.run(document.querySelector('.modal.show'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.html)}));});accessibility.push({width,theme,violations:v});await modal.screenshot({path:path.join(out,`after-${width}-${theme}.png`)});assert.deepEqual(v,[],JSON.stringify({width,theme,v}));}
  fs.writeFileSync(path.join(out,'accessibility.json'),JSON.stringify(accessibility,null,2));
 }
 fs.writeFileSync(path.join(out,phase+'-geometry.json'),JSON.stringify({fields:before,errors},null,2));assert.deepEqual(errors,[]);console.log(JSON.stringify({phase,fields:8,errors}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});



