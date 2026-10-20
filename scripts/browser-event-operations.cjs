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
  await require('./browser-inline-onboarding.cjs').journey({page:qa,data,run,settings,out,errors});
 }catch(e){console.error(e.stack);console.error('Page errors: '+JSON.stringify(errors));await qa.screenshot({path:path.join(out,'event-qa-failure.png'),fullPage:true});await demo.screenshot({path:path.join(out,'event-demo-failure.png'),fullPage:true});throw e;}
 finally{await browser.close();let cleaned;try{cleaned=fixture('end');}catch(e){console.error(String(e.stdout||e.stderr||'').slice(-5000));throw e;}assert(cleaned.restored);console.log('PASS exact isolated QA company and preferences restored');}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
