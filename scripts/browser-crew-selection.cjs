/* The same crew checklist must work from ordinary event and assignment screens. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.setDefaultTimeout(30000);page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
  await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});await page.locator('.pp-onboarding-shell[data-ready=true]').waitFor({timeout:60000});
  const rpc=(method,args={})=>page.evaluate(async({method,args})=>(await frappe.call({method,args,type:'POST'})).message,{method,args});
  await rpc('plus_point.event_setup.control',{action:'skip'});
  const client=await rpc('plus_point.events.save_resource',{company:data.company,kind:'clients',values:JSON.stringify({customer_name:data.prefix+' Client',customer_type:'Company',contact_name:'Ayesha QA',email:'crew@example.invalid',country:'Pakistan',city:'Karachi',address_line1:'12 Venue Road'})});
  const dates=await page.evaluate(()=>({start:frappe.datetime.add_days(frappe.datetime.get_today(),5),end:frappe.datetime.add_days(frappe.datetime.get_today(),7)}));
  const create=label=>rpc('plus_point.events.create_event',{company:data.company,customer:client.name,event_name:data.prefix+' '+label,start_date:dates.start,end_date:dates.end,agreement:'Crew browser QA agreement',billing_model:'Daily',wage_rate:100,client_rate:150,sites:JSON.stringify([{site_name:label+' hall QA',phase:'Event',start_date:dates.start,end_date:dates.end,workers_required:label==='First'?2:1}])});
  const ayesha=await rpc('plus_point.crew.add_worker',{company:data.company,values:JSON.stringify({first_name:'Ayesha QA',last_name:'Crew',gender:'Female',date_of_birth:'1990-01-01',date_of_joining:'2020-01-01'})});
  const haris=await rpc('plus_point.crew.add_worker',{company:data.company,values:JSON.stringify({first_name:'Haris QA',last_name:'Crew',gender:'Male',date_of_birth:'1990-01-01',date_of_joining:'2020-01-01'})});
  const first=await create('First');await page.evaluate(name=>frappe.set_route('Form','PP Event Plan',name),first.plan);await page.waitForFunction(name=>window.cur_frm?.doc.name===name&&!cur_frm.is_dirty(),first.plan);
  await page.getByRole('button',{name:'Choose crew',exact:true}).click();const dialog=page.locator('.pp-crew-dialog:visible');await dialog.locator('.pp-crew-picker[data-ready=true]').waitFor();
  assert.equal(await dialog.locator('.pp-crew-row').count(),3);
  await dialog.getByRole('checkbox',{name:'Select Sana Browser QA',exact:true}).check();await dialog.getByRole('checkbox',{name:'Select Ayesha QA Crew',exact:true}).check();assert.equal(await dialog.locator('.pp-crew-tag').count(),2);
  await dialog.getByRole('button',{name:'Import workers',exact:true}).click();const importDialog=page.locator('.pp-import-dialog:visible');await importDialog.waitFor();await dialog.waitFor({state:'hidden'});assert.equal(await page.locator('.modal:visible').count(),1);
  await importDialog.getByRole('button',{name:'Close',exact:true}).click();await importDialog.waitFor({state:'hidden'});await dialog.locator('.pp-crew-picker[data-ready=true]').waitFor();assert.equal(await dialog.locator('.pp-crew-tag').count(),2);
  const allocate=dialog.getByRole('button',{name:'Allocate selected crew',exact:true});await page.waitForFunction(()=>window.cur_dialog?.get_primary_btn&&!cur_dialog.get_primary_btn().prop('disabled'));
  await page.screenshot({path:path.join(out,'crew-plan-picker.png'),fullPage:true});await allocate.click();await dialog.waitFor({state:'hidden'});
  const assigned=await rpc('frappe.client.get_list',{doctype:'PP Assignment',filters:{pp_event_plan:first.plan},fields:['employee']});assert.deepEqual(new Set(assigned.map(r=>r.employee)),new Set([data.worker,ayesha.name]));
  const second=await create('Second'),site=(await rpc('frappe.client.get_list',{doctype:'PP Site',filters:{project:second.project},fields:['name']}))[0].name;
  await page.evaluate(()=>frappe.set_route('List','PP Assignment'));await page.getByRole('button',{name:'Assign workers',exact:true}).waitFor();await page.getByRole('button',{name:'Assign workers',exact:true}).click();
  await page.waitForFunction(()=>window.cur_dialog?.display&&cur_dialog.fields_dict.project);
  await page.evaluate(async v=>{for(const [key,value] of Object.entries(v))await cur_dialog.set_value(key,value);},{project:second.project,site,contract_terms:second.contract_terms,start_date:dates.start,end_date:dates.end,wage_rate:100,client_rate:150});
  const bulk=page.locator('.pp-crew-dialog:visible');await bulk.locator('.pp-crew-picker[data-ready=true]').waitFor();
  assert.equal(await bulk.locator('.pp-crew-row').count(),1);assert.match(await bulk.locator('.pp-crew-excluded').innerText(),/2 workers excluded/);
  await bulk.getByRole('checkbox',{name:'Select Haris QA Crew',exact:true}).check();await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,'crew-assignment-mobile.png'),fullPage:true});await bulk.getByRole('button',{name:'Assign selected workers',exact:true}).click();await bulk.waitFor({state:'hidden'});
  const manual=await rpc('frappe.client.get_list',{doctype:'PP Assignment',filters:{project:second.project},fields:['employee']});assert.deepEqual(manual.map(r=>r.employee),[haris.name]);
  assert.equal((await rpc('frappe.client.get_list',{doctype:'PP Work Entry',filters:{project:['in',[first.project,second.project]]},fields:['name']})).length,0);assert.deepEqual(errors,[]);
  console.log('PASS normal event-plan multi-selection, preserved tags after import, exact chosen-worker allocation, normal Assign workers list action, overlapping-project exclusions, mobile bulk assignment and no earned attendance');
 }catch(error){await page.screenshot({path:path.join(out,'crew-selection-failure.png'),fullPage:true});throw error;}
 finally{await browser.close();assert(fixture('end').restored);console.log('PASS exact crew, clients, projects and workspace settings restored');}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
