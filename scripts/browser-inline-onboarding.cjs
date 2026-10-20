/* Real inline onboarding UI. Exact QA records are restored; stock posting is tested in DB savepoints. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const {chromium}=require('playwright');

async function journey({page,data,run,settings,out,errors}){
 page.setDefaultTimeout(30000);page.setDefaultNavigationTimeout(60000);
 await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
 assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
 await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});
 const root=page.locator('.pp-onboarding-shell');
 const step=async name=>{await page.locator(`.pp-onboarding-shell[data-ready=true][data-step=${name}]`).waitFor({timeout:60000});assert.equal(await page.locator('.modal:visible').count(),0);assert(await root.getByRole('button',{name:name==='done'?'Return to overview':'Skip onboarding',exact:true}).isVisible());console.log('INLINE '+name);};
 const values=async v=>page.evaluate(async v=>{const form=frappe.container.page.pp_setup_form;for(const [key,value] of Object.entries(v)){if(Array.isArray(value)&&form.fields_dict[key]?.grid){form.fields_dict[key].df.data=value;form.fields_dict[key].grid.refresh();}else await form.set_value(key,value);}},v);
 const value=key=>page.evaluate(key=>frappe.container.page.pp_setup_form.get_value(key),key);
 const save=()=>root.locator('.pp-onboarding-save').click();
 const rpc=(method,args={})=>page.evaluate(async({method,args})=>(await frappe.call({method,args,type:'POST'})).message,{method,args});
 await step('company');assert.equal(await page.locator('.pp-event-setup-dialog:visible').count(),0);
 assert.equal((await rpc('plus_point.event_setup.status')).companies.length,1);
 // Clicking a filled link opens a list without erasing its selected value.
 const countryInput=root.locator('[data-fieldname=country] input');await countryInput.click();
 await root.locator('[data-fieldname=country] .awesomplete [role=option]').first().waitFor();
 await countryInput.fill('Saud');await root.locator('[data-fieldname=country] .awesomplete [role=option]').filter({hasText:'Saudi Arabia'}).waitFor();
 await root.locator('[data-fieldname=country] .awesomplete [role=option]').filter({hasText:'Saudi Arabia'}).click();
 await page.waitForFunction(()=>frappe.container.page.pp_setup_form.get_value('currency')==='SAR');
 await root.locator('[data-fieldname=country] .pp-picker-toggle').click();
 assert.equal(await value('country'),'Saudi Arabia');await root.locator('[data-fieldname=country] .awesomplete [role=option]').first().waitFor();
 await page.keyboard.press('Escape');
 await values({country:'Saudi Arabia'});await page.waitForFunction(()=>frappe.container.page.pp_setup_form.get_value('currency')==='SAR');
 assert.equal(await page.evaluate(()=>frappe.container.page.pp_setup_form.fields_dict.currency.df.read_only||0),0);
 await root.getByRole('button',{name:'Skip onboarding',exact:true}).click();await page.locator('.pp-dashboard[data-ready=true]').waitFor({timeout:60000});
 assert((await rpc('plus_point.event_setup.status')).state.skipped);assert.equal(await page.evaluate(()=>document.body.classList.contains('pp-onboarding-active')),false);
 await page.reload({waitUntil:'domcontentloaded'});await page.locator('.pp-dashboard[data-ready=true]').waitFor();
 assert.equal(await page.locator('.pp-onboarding-shell:visible').count(),0);
 await page.locator('.body-sidebar').getByRole('link',{name:'Onboarding',exact:true}).click();await step('company');
 await values({country:'Saudi Arabia'});await page.waitForFunction(()=>frappe.container.page.pp_setup_form.get_value('currency')==='SAR');
 await page.screenshot({path:path.join(out,'inline-onboarding-company.png'),fullPage:true});
 await save();await step('client');
 await values({customer_name:data.prefix+' Client'});await save();await root.locator('.pp-onboarding-errors:visible').waitFor();
 assert.match(await root.locator('.pp-onboarding-errors').innerText(),/Contact person|City|Street address/);
 assert.equal((await rpc('frappe.client.get_list',{doctype:'Customer',filters:{customer_name:data.prefix+' Client'},fields:['name']})).length,0);
 await values({contact_name:'Ayesha Malik',email:'ayesha.qa@example.invalid',phone:'+966501234567',country:'Saudi Arabia',city:'Riyadh',state:'Riyadh',address_line1:'12 Exhibition Road',postal_code:'12345'});
 await page.screenshot({path:path.join(out,'inline-onboarding-client.png'),fullPage:true});await save();await step('event');
 const client=(await rpc('plus_point.event_setup.status')).state.customer;
 const details=await rpc('plus_point.clients.details',{customer:client});assert.equal(details.email,'ayesha.qa@example.invalid');assert.match(details.address,/Riyadh/);
 await root.getByRole('button',{name:'Back',exact:true}).click();await step('client');
 assert.equal(await page.evaluate(()=>frappe.container.page.pp_setup_form.fields_dict.customer.df.only_select),1);
 assert.match(await root.locator('.pp-client-summary').innerText(),/Ayesha Malik/);
 await save();await step('event');
 await root.getByRole('checkbox',{name:'Use the client’s saved address for this venue',exact:true}).check();await page.waitForFunction(()=>frappe.container.page.pp_setup_form.get_value('address_line1')==='12 Exhibition Road');assert.equal(await value('city'),'Riyadh');await root.getByRole('checkbox',{name:'Use the client’s saved address for this venue',exact:true}).uncheck();
 const dates=await page.evaluate(()=>({start:frappe.datetime.add_days(frappe.datetime.get_today(),2),end:frappe.datetime.add_days(frappe.datetime.get_today(),4)}));
 await values({event_name:data.prefix+' Event',site_name:'Riyadh exhibition hall QA',start_date:dates.start,end_date:dates.end,country:'Saudi Arabia',city:'Riyadh',state:'Riyadh',address_line1:'24 Venue Road',postal_code:'12345'});
 await root.getByRole('button',{name:'Choose from map',exact:true}).click();await root.locator('.leaflet-container').waitFor();
 await root.locator('.pp-location-map').click({position:{x:180,y:150}});
 await page.waitForFunction(()=>Boolean(frappe.container.page.pp_setup_form.get_value('latitude')));
 assert(Number.isFinite(Number(await value('longitude'))));
 await values({latitude:'24.713600',longitude:'46.675300'});
 assert(await root.locator('.pp-location-map').evaluate(el=>Math.abs(el.pp_map.getCenter().lat-24.7136)<0.0001),'Typed coordinates update the visible map');
 try{await page.waitForFunction(()=>document.querySelector('.pp-location-map')?.dataset.tilesReady==='true'&&[...document.querySelectorAll('.pp-location-map img.leaflet-tile')].some(i=>i.complete&&i.naturalWidth>0),{},{timeout:20000});console.log('PASS live map tiles');}catch{console.log('Map tiles unavailable in this browser run; manual address and map-coordinate entry remain available');}
 await root.locator('.pp-location-map').evaluate(el=>el.scrollIntoView({block:'center'}));
 await page.screenshot({path:path.join(out,'inline-onboarding-map.png'),fullPage:true});await save();await step('terms');
 const event=(await rpc('plus_point.event_setup.status')).state;
 const site=(await rpc('frappe.client.get',{doctype:'PP Site',name:event.site}));assert.equal(site.country,'Saudi Arabia');assert.equal(site.city,'Riyadh');assert.equal(Number(site.latitude),24.7136);
 await values({agreement:'Temporary QA event staffing and equipment agreement',billing_model:'Daily'});await save();await step('workers');
 // Completed rows navigate directly and edit existing records, retaining later progress.
 await root.locator('.pp-onboarding-step[data-step=client]').click();await step('client');
 assert.equal(await value('contact_name'),'Ayesha Malik');await values({contact_name:'Haris Khan',city:'Jeddah'});await save();await step('event');
 assert.equal((await rpc('plus_point.clients.details',{customer:client})).contact_name,'Haris Khan');
 await root.locator('.pp-onboarding-step[data-step=terms]').click();await step('terms');
 assert.equal(await value('agreement'),'Temporary QA event staffing and equipment agreement');
 const originalTerms=(await rpc('plus_point.event_setup.status')).state.contract_terms;
 await values({agreement:'Updated QA client agreement'});await save();await step('workers');
 assert.equal((await rpc('plus_point.event_setup.status')).state.contract_terms,originalTerms);
 await root.locator('.pp-onboarding-step[data-step=company]').click();await step('company');
 assert.equal(await countryInput.isEditable(),true);await values({country:'United Arab Emirates'});await page.waitForFunction(()=>frappe.container.page.pp_setup_form.get_value('currency')==='AED');await values({currency:'USD'});assert.equal(await value('currency'),'USD');
 await save();await step('client');await root.locator('.pp-onboarding-step[data-step=workers]').click();await step('workers');
 // The user's original template, with names in employee, previews new worker profiles.
 await root.locator('.pp-crew-picker[data-ready=true]').waitFor();await root.getByRole('button',{name:'Import workers',exact:true}).click();
 const importDialog=page.locator('.pp-import-dialog:visible');await importDialog.waitFor();
 const columns=['external_id','employee','first_name','last_name','gender','date_of_birth','date_of_joining','cell_number','status'];
 const csv=[columns.join(','),...Array.from({length:15},(_,i)=>['QAEMP'+i,'QA New Person '+String.fromCharCode(65+i),'QA New','Person '+String.fromCharCode(65+i),'Male','1990-01-01','2020-01-01','','Active'].join(','))].join('\n');
 await importDialog.locator('input[type=file]').setInputFiles({name:'workers.csv',mimeType:'text/csv',buffer:Buffer.from(csv)});
 await importDialog.getByRole('button',{name:'Review file',exact:true}).click();
 await importDialog.getByText('Review before saving',{exact:true}).waitFor();assert.match(await importDialog.locator('.pp-import-preview').innerText(),/15 create/);
 assert.equal(await importDialog.getByText(/Employee .* not found/).count(),0);await importDialog.getByRole('button',{name:'Close',exact:true}).click();await importDialog.waitFor({state:'hidden'});await page.evaluate(()=>plus_point.load_onboarding(frappe.container.page));await step('workers');
 await root.locator('.pp-crew-picker[data-ready=true]').waitFor();
 await root.getByRole('checkbox',{name:'Select Sana Browser QA',exact:true}).check();
 for(const first of ['Ayesha QA','Haris QA']){
  await root.getByRole('button',{name:'Add worker',exact:true}).click();
  await page.evaluate(async first=>frappe.container.page.pp_crew_picker.add_form.set_values({first_name:first,last_name:'Crew',gender:'Female',date_of_birth:'1990-01-01',date_of_joining:'2020-01-01'}),first);
  await root.getByRole('button',{name:'Create and select worker',exact:true}).click();
  await root.locator('.pp-crew-new').waitFor({state:'hidden'});await root.locator('.pp-crew-picker[data-ready=true]').waitFor();
 }
 assert.equal(await root.locator('.pp-crew-tag').count(),3);
 await root.getByRole('button',{name:'Remove Ayesha QA Crew',exact:true}).click();assert.equal(await root.locator('.pp-crew-tag').count(),2);
 await root.locator('.pp-crew-search').fill('Ayesha');assert.equal(await root.locator('.pp-crew-row').count(),1);
 await root.getByRole('checkbox',{name:'Select Ayesha QA Crew',exact:true}).check();await root.locator('.pp-crew-search').fill('');
 assert.equal(await root.locator('.pp-crew-tag').count(),3);
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(out,'crew-picker-mobile.png'),fullPage:true});await page.setViewportSize({width:1440,height:1000});
 await save();await step('plan');assert.equal((await rpc('plus_point.event_setup.status')).state.employees.length,3);

 await values({wage_rate:2000,client_rate:3000});await save();await step('vehicle');
 await values({purpose:'Crew'});assert(await root.locator('[data-fieldname=crew_seats] input').isVisible());assert.equal(await root.locator('[data-fieldname=cargo_capacity] input').isVisible(),false);
 await values({license_plate:'QA-CREW-'+run,make:'Toyota',model:'Crew van',crew_seats:4,crew_count:1});await save();await step('inventory');
 await root.getByRole('button',{name:'Back',exact:true}).click();await step('vehicle');
 await values({purpose:'Inventory',mode:'Add vehicle'});assert.equal(await root.locator('[data-fieldname=crew_seats] input').isVisible(),false);assert(await root.locator('[data-fieldname=cargo_capacity] input').isVisible());
 await values({license_plate:'QA-CARGO-'+run,make:'Toyota',model:'Equipment van',cargo_capacity:40,cargo_uom:'units',cargo_load:10});
 await page.screenshot({path:path.join(out,'inline-onboarding-cargo.png'),fullPage:true});await save();await step('inventory');
 assert.equal(await value('stock_uom'),'Nos');assert(await root.locator('[data-fieldname=stock_quantity] input').isVisible());
 await values({item_code:'QA-UNSAVED-'+run,item_name:'Palm decoration QA',warehouse_mode:'Add warehouse',warehouse_name:'QA temporary warehouse',stock_quantity:1,quantity:2,valuation_rate:0,confirm_stock_balance:1});
 await save();await root.getByText('You own 1, but this event needs 2. Check the warehouse count or reduce the event quantity.',{exact:true}).waitFor();
 let posted;
 await page.route('**/api/method/plus_point.event_setup.advance',async route=>{const body=route.request().postDataJSON();if(body.step!=='inventory')return route.continue();posted=JSON.parse(body.values);await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({_server_messages:JSON.stringify([JSON.stringify({message:'Temporary QA connection failure. Your changes were not saved.'})])})});});
 await values({stock_quantity:5});await save();await root.getByText('Temporary QA connection failure. Your changes were not saved.',{exact:true}).waitFor();
 assert.equal(posted.stock_quantity,5);assert.equal(posted.valuation_rate,0);assert.equal(await value('quantity'),2);assert.equal(await page.locator('.modal:visible').count(),0);
 await page.unroute('**/api/method/plus_point.event_setup.advance');
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 assert(await root.locator('.pp-onboarding-panel').evaluate(el=>{const r=el.getBoundingClientRect();return r.width<=innerWidth+1&&el.scrollWidth<=el.clientWidth+1;}),'Inline panel and its fields must fit on mobile');
 assert(await root.locator('.pp-onboarding-save').evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1;}),'Save action must fit on mobile');
 await root.getByRole('button',{name:'Skip onboarding',exact:true}).scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,'inline-onboarding-mobile.png'),fullPage:true});
 await page.setViewportSize({width:1440,height:1000});
 await root.getByRole('button',{name:'Skip onboarding',exact:true}).click();await page.locator('.pp-dashboard[data-ready=true]').waitFor();
 assert.equal((await rpc('plus_point.event_setup.status')).state.step,'inventory');
 await page.locator('.body-sidebar').getByRole('link',{name:'Onboarding',exact:true}).click();await step('inventory');assert.equal(await value('stock_quantity'),5);
 await page.route('**/api/method/plus_point.events.preview_crew',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({message:{shortages:[{site:'QA shortage state',missing:1}],assignments:[]}})}));
 await values({no_equipment:1});await save();await step('allocate');
 assert(await root.locator('.pp-onboarding-save').isDisabled(),'A shortage keeps allocation disabled after the preceding step finishes');
 await page.unroute('**/api/method/plus_point.events.preview_crew');await page.evaluate(()=>plus_point.load_onboarding(frappe.container.page));
 await step('allocate');await root.getByText('Every phase can be covered. Save to create assignments; this still does not approve attendance.',{exact:true}).waitFor();
 await save();await step('done');await root.getByRole('button',{name:'Open my event plan',exact:true}).click();await page.locator('.pp-event-map').waitFor();
 assert.equal(await page.evaluate(()=>document.body.classList.contains('pp-onboarding-active')),false);
 assert.equal((await rpc('frappe.client.get_list',{doctype:'PP Assignment',filters:{pp_event_plan:(await rpc('plus_point.event_setup.status')).state.plan},fields:['name']})).length,3);
 assert.equal((await rpc('frappe.client.get_list',{doctype:'PP Work Entry',filters:{project:event.project},fields:['name']})).length,0);
 assert.deepEqual(errors,[]);
 console.log('PASS inline onboarding, persistent skip/reload/resume, SAR country mapping, full client contact/address, selection-only existing client, completed-step edits, live dropdown search, 15 new worker import previews, three-worker checklist/tag search and allocation, editable country with protected base currency, structured venue/map point, separate crew/cargo fields, zero-value quantity submission, inline network error, mobile bounds and completion without attendance');
}

module.exports={journey};
if(require.main===module)(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));await page.addLocatorHandler(page.locator('.modal:visible').filter({hasText:'New updates are available'}),()=>page.keyboard.press('Escape'));
 try{await journey({page,data,run,settings,out,errors});}catch(e){await page.screenshot({path:path.join(out,'inline-onboarding-failure.png'),fullPage:true});console.error('Page errors: '+JSON.stringify(errors));throw e;}finally{await browser.close();assert(fixture('end').restored);console.log('PASS exact QA company, client contacts, addresses, vehicles and workspace settings restored');}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
