/* Event customer UI and a complete isolated company journey. Exact QA fixtures restored. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex');
 const fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}).trim());
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:process.env.PP_BROWSER_CHANNEL||'msedge'});
 const demo=await browser.newPage({viewport:{width:1440,height:1000}}),qa=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 for(const p of [demo,qa]){p.setDefaultTimeout(30000);p.setDefaultNavigationTimeout(60000);p.on('pageerror',e=>errors.push(e.message));await p.addLocatorHandler(p.locator('.modal:visible').filter({hasText:'New updates are available'}),()=>p.keyboard.press('Escape'));}
 const login=async(p,site,user,password)=>{await p.goto(`http://${site}:8000/login`,{waitUntil:'commit'});assert.equal(await p.evaluate(async c=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)})).json()).message,{usr:user,pwd:password}),'Logged In');await p.goto(`http://${site}:8000/desk/plus-point`,{waitUntil:'commit'});await p.locator('.pp-dashboard[data-ready=true]').waitFor({timeout:60000});};
 const modal=p=>p.locator('.modal:visible').last();
 const values=async(p,v)=>{await p.waitForFunction(()=>window.cur_dialog?.display&&cur_dialog.$wrapper.is(':visible'));await p.evaluate(async v=>{for(const [key,value] of Object.entries(v)){if(Array.isArray(value)&&cur_dialog.fields_dict[key]?.grid){cur_dialog.fields_dict[key].df.data=value;cur_dialog.fields_dict[key].grid.refresh();}else await cur_dialog.set_value(key,value);}},v);};
 const step=async title=>{await modal(qa).getByText(title,{exact:true}).waitFor();await qa.waitForFunction(()=>window.cur_dialog?.display&&cur_dialog.$wrapper.is(':visible'));console.log('STEP '+title);};
 const save=()=>modal(qa).getByRole('button',{name:'Save and continue',exact:true}).click();
 const rpc=(p,method,args={})=>p.evaluate(async({method,args})=>(await frappe.call({method,type:'POST',args})).message,{method,args});
 try{
  if(!process.env.PP_EVENT_GUIDE_ONLY){
  await login(demo,'demo.localhost','example@email.com',process.env.PP_BROWSER_PASSWORD||'user123');
  assert.equal(await demo.locator('.pp-event-setup-dialog:visible').count(),0);
  assert.match(await demo.locator('.body-sidebar .avatar-name-email').innerText(),/PLUS POINT Demo/);
  assert(!/Ahmad|Ahmed/.test(await demo.locator('.body-sidebar .avatar-name-email').innerText()));
  assert.equal(await demo.locator('.pp-context-bar:visible').count(),0);await demo.locator('.pp-top-help:visible').waitFor();
  await demo.getByRole('heading',{name:'Upcoming events',exact:true}).waitFor();
  await demo.locator('.sidebar-user-button').click();await demo.getByText('Guided company setup',{exact:true}).waitFor();await demo.locator('.sidebar-user-button').click();
  await demo.screenshot({path:path.join(out,'event-overview.png'),fullPage:true});
  const plan=(await rpc(demo,'plus_point.events.plans_for',{company:'PLUS POINT Demo'})).find(x=>x.event_name==='Lumen wedding showcase (Demo)');assert(plan);
  await demo.evaluate(name=>frappe.set_route('Form','PP Event Plan',name),plan.name);
  await demo.locator('.pp-event-map').waitFor();const timeline=await rpc(demo,'plus_point.events.timeline',{plan:plan.name});
  assert.equal(await demo.locator('.pp-event-day').count(),timeline.duration*timeline.sites.length);
  assert.equal(await demo.locator('.pp-heatmap-weekday').count(),7*timeline.sites.length);
  assert.equal(timeline.vehicle_bookings,2);assert.equal(timeline.equipment_bookings,1);
  await demo.screenshot({path:path.join(out,'event-timeline.png'),fullPage:true});
  for(const width of [390,320]){await demo.setViewportSize({width,height:844});assert(await demo.evaluate(()=>[...document.querySelectorAll('.pp-event-day')].every(b=>{const c=b.getBoundingClientRect(),m=b.closest('.pp-event-map').getBoundingClientRect();return c.top>=m.top&&c.bottom<=m.bottom+1&&c.left>=m.left&&c.right<=m.right+1;})));assert(await demo.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Event timeline must scroll within its panel');}
  await demo.setViewportSize({width:1440,height:1000});
  await demo.evaluate(()=>frappe.set_route('pp-inventory'));await demo.locator('[data-ready=true].pp-section-home').waitFor();
  assert.match(await demo.locator('.pp-inventory-table').innerText(),/Banquet chair/);assert.match(await demo.locator('.pp-inventory-table').innerText(),/60/);
  await demo.screenshot({path:path.join(out,'event-warehouse.png'),fullPage:true});
  await demo.locator('.body-sidebar').getByRole('link',{name:'Inventory and transport',exact:true}).click();
  await demo.locator('.pp-section-home[data-ready=true][data-section="Inventory and transport"]').waitFor();
  const resources=(await rpc(demo,'plus_point.sections.overview',{section:'Inventory and transport',company:'PLUS POINT Demo'})).resources;
  assert.match(await demo.locator('.pp-section-home[data-section="Inventory and transport"] .pp-dashboard-metrics').innerText(),/Equipment types/);
  assert.deepEqual((await demo.locator('.pp-section-home[data-section="Inventory and transport"] .pp-dashboard-metric dd').allTextContents()).map(Number),[resources.items,resources.warehouses,resources.vehicles,resources.reservations]);
  await demo.screenshot({path:path.join(out,'event-resource-overview.png'),fullPage:true});
  for(const [doctype,kind] of [['Customer','clients'],['Vehicle','vehicles'],['Item','inventory_items'],['Warehouse','warehouses'],['Stock Reconciliation','stock_balances'],['PP Site','event_sites'],['PP Event Plan','events']]){
   await demo.evaluate(doctype=>frappe.set_route(doctype==='Warehouse'?'Tree':'List',doctype,...(doctype==='Item'?[{is_stock_item:1}]:[])),doctype);
   console.log('TEMPLATE '+kind);
   await demo.locator('.page-head:visible').getByRole('button',{name:'Import',exact:true}).click();
   await demo.locator('.pp-import-dialog:visible').waitFor();await values(demo,{company:'PLUS POINT Demo'});
   assert.equal(await modal(demo).locator('[data-fieldname=kind] select').inputValue(),kind);
   const download=demo.waitForEvent('download');await modal(demo).getByRole('button',{name:'Download template',exact:true}).click();
   const file=await download;assert.equal(file.suggestedFilename(),`plus-point-${kind}.csv`);assert(fs.readFileSync(await file.path(),'utf8').replace(/^\ufeff/,'').startsWith('external_id,'));
   await modal(demo).getByRole('button',{name:'Close',exact:true}).click();
  }
  console.log('PASS event overview, company identity, top Help, native stock availability, seven import templates and bounded mobile event calendar');
  }
  await login(qa,'qa.localhost','Administrator',settings.PP_ADMIN_PASSWORD);
  await step('Your event company');assert(await qa.locator('#body').evaluate(el=>el.inert));
  await values(qa,{mode:'Choose existing company',company:data.company});await save();
  await step('Who is the client?');await values(qa,{mode:'Add client',customer_name:data.prefix+' Client'});await save();
  await step('The event and its first venue');const dates=await qa.evaluate(()=>({start:frappe.datetime.add_days(frappe.datetime.get_today(),2),end:frappe.datetime.add_days(frappe.datetime.get_today(),4)}));
  await values(qa,{mode:'Create event project',event_name:data.prefix+' Event',venue_mode:'Add event site',site_name:'Main ballroom QA',start_date:dates.start,end_date:dates.end});await save();
  await step('The client agreement');await values(qa,{mode:'Add client agreement',billing_model:'Daily',agreement:'Temporary event setup and staffing QA'});await save();
  await step('Add your event crew');await qa.reload({waitUntil:'commit'});await step('Add your event crew');assert(await qa.locator('#body').evaluate(el=>el.inert));
  await values(qa,{mode:'Choose existing worker',employee:data.worker});await save();
  await step('Plan each venue day');await values(qa,{wage_rate:2000,client_rate:3000});await save();
  await step('How will crew or inventory travel?');await values(qa,{mode:'Add vehicle',license_plate:'QA-'+run,make:'Toyota',model:'Crew van QA',crew_seats:4,cargo_capacity:0,purpose:'Crew',crew_count:1});
  await qa.setViewportSize({width:390,height:844});assert(await modal(qa).evaluate(el=>el.scrollWidth<=innerWidth));await qa.screenshot({path:path.join(out,'event-setup-mobile.png'),fullPage:true});await save();
  await step('Equipment for the event');
  const inventoryDialog=modal(qa);
  assert.equal(await inventoryDialog.locator('[data-fieldname=stock_uom] input').inputValue(),'Nos');
  assert(await inventoryDialog.locator('[data-fieldname=stock_quantity] input').isVisible());
  assert.equal(await inventoryDialog.locator('input[data-fieldname=set_stock_balance]').isVisible(),false);
  await values(qa,{item_code:'QA-UNSAVED-'+run,item_name:'Palm decoration QA',warehouse_mode:'Add warehouse',warehouse_name:'QA unsaved equipment',stock_quantity:1,quantity:2,valuation_rate:100,confirm_stock_balance:1});
  await inventoryDialog.getByText('You entered 1 in the warehouse, but this event needs 2. Increase the warehouse quantity only if you own that stock, or reduce the event quantity.',{exact:true}).waitFor();
  await save();assert.equal(await qa.locator('.modal:visible').count(),1);
  assert.equal((await rpc(qa,'plus_point.event_setup.status')).state.step,'inventory');
  assert.equal((await rpc(qa,'frappe.client.get_list',{doctype:'Item',filters:{item_code:'QA-UNSAVED-'+run},fields:['name']})).length,0);
  await values(qa,{stock_quantity:5});await inventoryDialog.getByText('Warehouse: 5 · For this event: 2 · Remaining: 3',{exact:true}).waitFor();
  await qa.setViewportSize({width:390,height:844});assert(await inventoryDialog.evaluate(el=>el.scrollWidth<=innerWidth));
  await qa.screenshot({path:path.join(out,'event-starting-stock.png'),fullPage:true});
  await values(qa,{mode:'Choose existing item'});assert.equal(await inventoryDialog.locator('[data-fieldname=stock_quantity] input').isVisible(),false);
  await values(qa,{set_stock_balance:1});assert(await inventoryDialog.locator('[data-fieldname=stock_quantity] input').isVisible());
  await values(qa,{no_equipment:1});await save();
  console.log('PASS visible new-item warehouse count, Nos default, inline shortage prevents writes, coverage summary, existing-item count opt-in and mobile layout');
  await step('Review and allocate the crew');await modal(qa).getByText('Every phase can be covered. Save to create assignments; this still does not approve attendance.',{exact:true}).waitFor();
  await modal(qa).getByRole('button',{name:'Allocate crew & finish setup',exact:true}).click();await step('Your first event is ready');
  await modal(qa).getByRole('button',{name:'Open my event plan',exact:true}).click();await qa.locator('.pp-event-map').waitFor();assert.equal(await qa.locator('#body').evaluate(el=>el.inert),false);
  const final=(await rpc(qa,'plus_point.event_setup.status')).state;assert.equal(final.step,'done');assert.equal((await rpc(qa,'frappe.client.get_list',{doctype:'PP Work Entry',filters:{project:final.project},fields:['name']})).length,0);
  assert.equal((await rpc(qa,'plus_point.events.timeline',{plan:final.plan})).duration,3);
  await qa.reload({waitUntil:'commit'});await qa.locator('.pp-event-map').waitFor();assert.equal(await qa.locator('.pp-event-setup-dialog:visible').count(),0);
  await qa.setViewportSize({width:1440,height:1000});await qa.evaluate(()=>frappe.set_route('List','PP Event Plan'));
  await qa.waitForFunction(()=>window.cur_list?.doctype==='PP Event Plan'&&cur_list.page?.btn_primary?.is(':visible'));
  // Native refresh recreates the action on its existing button. The wizard must survive.
  await qa.evaluate(()=>cur_list.page.set_primary_action({label:__('Add PP Event Plan')},()=>cur_list.make_new_doc(),'plus'));
  await qa.locator('.page-head:visible').getByRole('button',{name:'Plan an event',exact:true}).click();await step('Your client and event');
  await values(qa,{company:data.company,customer:final.customer,event_name:data.prefix+' Wizard',start_date:dates.start,end_date:dates.end});await modal(qa).getByRole('button',{name:'Continue',exact:true}).click();await step('Client agreement');
  await values(qa,{agreement:'Temporary QA wizard agreement',wage_rate:2000,client_rate:3000});await modal(qa).getByRole('button',{name:'Continue',exact:true}).click();await step('Event sites and daily staffing');
  await values(qa,{sites:[{site_name:'Garden marquee QA',phase:'Event',start_date:dates.start,end_date:dates.end,workers_required:1}]});await modal(qa).getByRole('button',{name:'Continue',exact:true}).click();await step('Review the event plan');
  await modal(qa).getByRole('button',{name:'Back',exact:true}).click();await step('Event sites and daily staffing');await modal(qa).getByRole('button',{name:'Continue',exact:true}).click();await step('Review the event plan');assert.match(await modal(qa).innerText(),/Garden marquee QA/);
  await modal(qa).getByRole('button',{name:'Create event plan',exact:true}).click();await qa.locator('.pp-event-map').waitFor();
  assert.deepEqual(errors,[]);console.log('PASS required guided steps, disabled background, reload/resume, real vehicle, crew allocation, no earned work, wizard forward/back and atomic save');
 }catch(e){console.error(e.stack);console.error('Page errors: '+JSON.stringify(errors));await qa.screenshot({path:path.join(out,'event-qa-failure.png'),fullPage:true});await demo.screenshot({path:path.join(out,'event-demo-failure.png'),fullPage:true});throw e;}
 finally{await browser.close();let cleaned;try{cleaned=fixture('end');}catch(e){console.error(String(e.stdout||e.stderr||'').slice(-5000));throw e;}assert(cleaned.restored);console.log('PASS exact isolated QA company and preferences restored');}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
