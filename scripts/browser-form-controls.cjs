/* Complete dropdowns, centered arrows, field restrictions, saved defaults and deletion. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1360,height:1000}}),errors=[];
 page.setDefaultTimeout(30000);page.setDefaultNavigationTimeout(60000);page.on('pageerror',e=>errors.push(e.message));
 const rpc=(method,args={})=>page.evaluate(({method,args})=>plus_point.form_rpc(method,args),{method,args});
 try{
  await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
  await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});await page.locator('.pp-onboarding-shell[data-ready=true]').waitFor({timeout:60000});
  const country=page.locator('.pp-onboarding-shell [data-fieldname=country]'),input=country.locator('input');
  await country.locator('.pp-picker-toggle').click();await country.locator('.pp-picker-status').filter({hasText:/All \d+ choices/}).waitFor();
  const list=await page.evaluate(()=>[...frappe.container.page.pp_setup_form.fields_dict.country.awesomplete.ul.children].map(li=>li.textContent.trim()));
  assert(list.length>200,`Expected complete country list, got ${list.length}`);assert(list.some(v=>v.includes('Zimbabwe')));
  const labels=await page.evaluate(()=>frappe.container.page.pp_setup_form.fields_dict.country.awesomplete._list.map(r=>String(r.label)));
  assert.deepEqual(labels,[...labels].sort((a,b)=>a.localeCompare(b,undefined,{sensitivity:'base',numeric:true})));
  const center=async()=>{const a=await country.locator('.pp-picker-toggle').boundingBox(),b=await input.boundingBox();assert(Math.abs(a.y+a.height/2-b.y-b.height/2)<=1.5);};await center();
  await page.screenshot({path:path.join(out,'complete-country-dropdown.png'),fullPage:true});await input.fill('Zim');await page.waitForFunction(()=>frappe.container.page.pp_setup_form.fields_dict.country.awesomplete.ul.children.length===1);
  await country.getByRole('option').filter({hasText:'Zimbabwe'}).click();assert.equal(await input.inputValue(),'Zimbabwe');
  await page.setViewportSize({width:390,height:844});await center();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.setViewportSize({width:1360,height:1000});
  const currencies=page.locator('.pp-onboarding-shell [data-fieldname=currency]');await currencies.locator('.pp-picker-toggle').click();await currencies.locator('.pp-picker-status').filter({hasText:/All \d+ choices/}).waitFor();assert(await page.evaluate(()=>frappe.container.page.pp_setup_form.fields_dict.currency.awesomplete._list.some(r=>r.value==='SAR')));await currencies.locator('input').press('Escape');
  console.log('PASS complete sorted country/currency choices and centered mobile arrows');
  await rpc('event_setup.control',{action:'skip'});
  const client=await rpc('events.save_resource',{company:data.company,kind:'clients',values:JSON.stringify({customer_name:data.prefix+' Client',customer_type:'Company',contact_name:'Ayesha Malik',email:'ayesha@example.invalid',country:'Pakistan',city:'Karachi',state:'Sindh',address_line1:'12 Venue Road'})});
  const dates=await page.evaluate(()=>({start:frappe.datetime.get_today(),end:frappe.datetime.add_days(frappe.datetime.get_today(),2)}));
  const event=await rpc('events.create_event',{company:data.company,customer:client.name,event_name:data.prefix+' Forms',start_date:dates.start,end_date:dates.end,agreement:'Forms browser QA agreement',billing_model:'Daily',wage_rate:100,client_rate:150,sites:JSON.stringify([{site_name:'Karachi hall',phase:'Event',start_date:dates.start,end_date:dates.end,workers_required:1}])});
  const context=await rpc('form_defaults.context',{project:event.project});
  await page.evaluate(project=>{plus_point.assign_workers({project});},event.project);const crew=page.locator('.pp-crew-dialog:visible');await crew.locator('.pp-crew-picker[data-ready=true]').waitFor();
  await page.waitForFunction(expected=>window.cur_dialog?.get_value('site')===expected.site&&cur_dialog.get_value('contract_terms')===expected.contract_terms&&cur_dialog.get_value('wage_rate')===100,context);
  assert.equal(await page.evaluate(()=>cur_dialog.get_value('end_date')),dates.end);
  const wage=crew.locator('[data-fieldname=wage_rate] input');await wage.fill('1234');await wage.press('a');assert.equal(await wage.inputValue(),'1234');await wage.press('Home');await page.keyboard.insertText('bad');assert.equal(await wage.inputValue(),'1234');
  await wage.fill('120.50');await wage.press('Tab');assert.equal(await page.evaluate(()=>cur_dialog.get_value('wage_rate')),120.5);
  await crew.getByRole('button',{name:'Add worker',exact:true}).click();const first=crew.locator('.pp-crew-new [data-fieldname=first_name] input');await first.fill('Ayesha');await first.press('7');assert.equal(await first.inputValue(),'Ayesha');
  const phone=crew.locator('.pp-crew-new [data-fieldname=cell_number] input');await phone.fill('+92 (300) 123-4567');await phone.press('x');assert.equal(await phone.inputValue(),'+92 (300) 123-4567');
  await crew.locator('.pp-crew-new [data-fieldname=last_name] input').fill('O’Neill');
  // Native date/link controls retain their own parsing and validation.
  await crew.locator('.pp-crew-new [data-fieldname=gender] input').fill('Female');await crew.locator('.pp-crew-new [data-fieldname=gender] input').press('Tab');
  await crew.locator('.pp-crew-new [data-fieldname=date_of_birth] input').fill(await page.evaluate(()=>frappe.datetime.str_to_user('1990-01-01')));await crew.locator('.pp-crew-new [data-fieldname=date_of_birth] input').press('Tab');
  await crew.getByRole('button',{name:'Create and select worker',exact:true}).click();await crew.locator('.pp-crew-tag').filter({hasText:'Ayesha O’Neill'}).waitFor();
  const imported=await page.evaluate(async company=>(await frappe.db.get_list('Employee',{filters:{company,first_name:'Ayesha'},fields:['name','employee_name']}))[0],data.company);
  assert(imported);await page.screenshot({path:path.join(out,'form-input-and-defaults.png'),fullPage:true});await page.evaluate(()=>cur_dialog.hide());await crew.waitFor({state:'hidden'});
  console.log('PASS saved event defaults and restricted numeric/name/phone inputs');
  const allocated=await rpc('crew.assign',{project:event.project,site:context.site,contract_terms:event.contract_terms,start_date:dates.start,end_date:dates.end,wage_rate:100,client_rate:150,employees:[data.worker]});
  const work=await page.evaluate(async assignment=>(await frappe.call({method:'frappe.client.insert',type:'POST',args:{doc:{doctype:'PP Work Entry',assignment,work_date:frappe.datetime.get_today(),units:1,status:'Draft'}}})).message,allocated.assignments[0]);
  await page.evaluate(name=>frappe.set_route('Form','PP Work Entry',name),work.name);await page.getByRole('button',{name:'Delete',exact:true}).waitFor();
  await page.getByRole('button',{name:'Delete',exact:true}).click();let removal=page.locator('.pp-delete-dialog:visible');await removal.waitFor();assert.equal(await page.locator('.modal:visible').count(),1);await removal.getByRole('button',{name:'Cancel',exact:true}).click();await removal.waitFor({state:'hidden'});
  assert(await page.evaluate(name=>frappe.db.exists('PP Work Entry',name),work.name));await page.getByRole('button',{name:'Delete',exact:true}).click();await removal.getByRole('button',{name:'Delete',exact:true}).click();await removal.waitFor({state:'hidden'});
  assert(!(await page.evaluate(name=>frappe.db.exists('PP Work Entry',name),work.name)));
  await page.evaluate(()=>frappe.set_route('List','Employee'));await page.getByRole('button',{name:'Delete selected',exact:true}).waitFor();
  await page.locator(`.list-row-checkbox[data-name="${imported.name}"]`).check();await page.getByRole('button',{name:'Delete selected',exact:true}).click();await removal.getByRole('button',{name:'Delete',exact:true}).click();await removal.waitFor({state:'hidden'});
  assert(!(await page.evaluate(name=>frappe.db.exists('Employee',name),imported.name)));
  await page.evaluate(name=>frappe.set_route('Form','Project',name),event.project);await page.getByRole('button',{name:'Delete',exact:true}).click();await removal.getByRole('button',{name:'Delete',exact:true}).click();await removal.locator('[role=alert]').waitFor();assert.equal(await page.locator('.modal:visible').count(),1);
  assert(await page.evaluate(name=>frappe.db.exists('Project',name),event.project));await page.screenshot({path:path.join(out,'delete-linked-record-inline.png'),fullPage:true});assert.deepEqual(errors,[]);
  await removal.getByRole('button',{name:'Cancel',exact:true}).click();await removal.waitFor({state:'hidden'});
  await page.evaluate(()=>{const dialog=new frappe.ui.Dialog({title:'Counterparty choices QA',fields:[{fieldname:'party_type',fieldtype:'Select',options:'Customer\nSupplier',default:'Customer'},{fieldname:'party_name',fieldtype:'Dynamic Link',options:'party_type',label:'Client'}]});dialog.show();});
  const dynamic=page.locator('.modal:visible [data-fieldname=party_name]');await dynamic.locator('.pp-picker-toggle').click();await dynamic.locator('.pp-picker-status').filter({hasText:/All \d+ choices/}).waitFor();assert(await page.evaluate(name=>cur_dialog.fields_dict.party_name.awesomplete._list.some(r=>r.value===name),client.name));await page.evaluate(()=>cur_dialog.hide());assert.deepEqual(errors,[]);
  console.log('PASS complete A–Z country list beyond 200 entries, live filtering, centered desktop/mobile arrows, numeric/name/phone restrictions, saved project dates/site/agreement/rates, worker creation, confirmed draft work deletion, list worker deletion and inline linked-record protection');
 }catch(error){await page.screenshot({path:path.join(out,'form-controls-failure.png'),fullPage:true});console.error('Page errors: '+JSON.stringify(errors));throw error;}
 finally{await browser.close();assert(fixture('end').restored);console.log('PASS exact nonfinancial QA records and settings restored');}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
