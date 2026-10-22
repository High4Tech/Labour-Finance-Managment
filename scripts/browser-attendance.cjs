/* Actual customer-side roster, attendance approval, finances and worker dashboard. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.attendance_browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];let originalTheme;
 page.setDefaultTimeout(30000);page.on('pageerror',error=>errors.push(error.message));
 const rpc=(method,args={})=>page.evaluate(({method,args})=>plus_point.form_rpc(method,args),{method,args});
 const native=(method,args={})=>page.evaluate(async({method,args})=>(await frappe.call({method,type:'POST',args})).message,{method,args});
 const summary=project=>rpc('api.project_summary',{project});
 const waitSave=async(button,approve)=>{const response=page.waitForResponse(r=>r.url().endsWith('/plus_point.attendance.save_marks')&&JSON.parse(r.request().postData()||'{}').approve===(approve?1:0));await button.click();const result=await(await response).json();assert(!result.exc_type,JSON.stringify(result));return result.message;};
 try{
  await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
  await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});await page.locator('.pp-onboarding-shell[data-ready=true]').waitFor({timeout:60000});
  originalTheme=await page.evaluate(()=>document.documentElement.dataset.themeMode);
  await page.getByRole('button',{name:'Skip onboarding',exact:true}).click();await page.locator('.pp-dashboard[data-ready=true]').waitFor();
  const client=await rpc('events.save_resource',{company:data.company,kind:'clients',values:{customer_name:data.prefix+' Client',customer_type:'Company',contact_name:'Ayesha Malik',email:'crew@example.invalid',country:'Pakistan',city:'Karachi',address_line1:'12 Venue Road'}});
  const day=await page.evaluate(()=>frappe.datetime.get_today()),end=await page.evaluate(()=>frappe.datetime.add_days(frappe.datetime.get_today(),1));
  const event=await rpc('events.create_event',{company:data.company,customer:client.name,event_name:data.prefix+' Festival',start_date:day,end_date:end,agreement:'Disposable browser staffing agreement',billing_model:'Daily',wage_rate:1000,client_rate:1500,sites:[{site_name:'Main stage',phase:'Event',start_date:day,end_date:end,workers_required:3},{site_name:'Backstage',phase:'Event',start_date:day,end_date:end,workers_required:1}]});
  const plan=await native('frappe.client.get',{doctype:'PP Event Plan',name:event.plan});const site=plan.staffing.find(r=>r.workers_required===3).site;
  const people=[data.worker];
  for(const first_name of ['Ayesha Attendance Browser','Bilal Attendance Browser']){
   const worker=await native('frappe.client.insert',{doc:{doctype:'Employee',first_name,gender:'Male',date_of_birth:'1990-01-01',date_of_joining:'2020-01-01',company:data.company,status:'Active',create_user_automatically:0}});people.push(worker.name);
  }
  await rpc('crew.assign',{project:event.project,site,contract_terms:event.contract_terms,start_date:day,end_date:end,wage_rate:1000,client_rate:1500,employees:people});
  const initial=await native('frappe.client.get_list',{doctype:'PP Daily Register',filters:{project:event.project,site,work_date:day},fields:['name']});assert.equal(initial.length,1,'Allocations should generate today’s roster automatically');
  assert.equal((await summary(event.project)).labour_cost,'0.00');
  await page.evaluate(()=>plus_point.open_attendance_picker());const picker=page.locator('.modal:visible');await picker.getByRole('button',{name:'Open register',exact:true}).waitFor();
  await page.waitForFunction(()=>window.cur_dialog?.display);await page.evaluate(async values=>{await cur_dialog.set_value('project',values.project);await cur_dialog.set_value('site',values.site);}, {project:event.project,site});
  await picker.getByRole('button',{name:'Open register',exact:true}).click();const register=page.locator('.pp-register[data-ready=true]');await register.waitFor();
  assert.equal(await register.locator('tbody tr').count(),3);assert.equal(await page.evaluate(()=>cur_frm.doc.name),initial[0].name);
  assert(await register.getByRole('button',{name:'Approve attendance',exact:true}).isDisabled());
  assert.equal(await register.getByText('Not marked',{exact:true}).count(),4);
  for(const [index,state] of ['Present','Half day','Absent'].entries())await register.locator(`tr:has(a[href$="/${people[index]}"])`).getByRole('button',{name:state,exact:true}).click();
  assert(await register.getByRole('button',{name:'Approve attendance',exact:true}).isEnabled());
  await waitSave(register.getByRole('button',{name:'Save draft',exact:true}),false);assert.equal((await summary(event.project)).labour_cost,'0.00');
  await page.waitForFunction(()=>cur_frm.doc.entries.every(r=>r.attendance_status!=='Not marked'));
  await native('frappe.client.set_value',{doctype:'Project',name:event.project,fieldname:{estimated_costing:500,pp_enforce_spending_budget:1}});
  await register.getByRole('button',{name:'Approve attendance',exact:true}).click();await register.locator('.pp-register-error').filter({hasText:'Spending budget exceeded'}).waitFor();
  assert.equal((await summary(event.project)).labour_cost,'0.00');
  await page.screenshot({path:path.join(out,'attendance-budget-stop.png'),fullPage:true});
  await native('frappe.client.set_value',{doctype:'Project',name:event.project,fieldname:{estimated_costing:5000,pp_enforce_spending_budget:1}});
  await waitSave(register.getByRole('button',{name:'Approve attendance',exact:true}),true);
  await page.waitForFunction(()=>cur_frm.doc.docstatus===1);await register.getByText('Approved attendance',{exact:false}).waitFor();
  const totals=await summary(event.project);assert.equal(totals.labour_cost,'1500.00');assert.equal(totals.earned_revenue,'2250.00');
  assert.equal((await rpc('attendance.prepare',{site,project:event.project,work_date:day})).name,initial[0].name);
  const work=await native('frappe.client.get_list',{doctype:'PP Work Entry',filters:{project:event.project},fields:['name','units']});assert.equal(work.length,3);assert.deepEqual(work.map(r=>Number(r.units)).sort(),[0,.5,1]);
  await page.screenshot({path:path.join(out,'attendance-approved-desktop.png'),fullPage:true});
  await page.evaluate(name=>frappe.set_route('Form','Employee',name),people[0]);const profile=page.locator('.pp-worker-profile[data-ready=true]');await profile.waitFor();
  assert.equal(await profile.locator('.pp-worker-metrics article').first().locator('strong').innerText(),'1');
  assert.match(await profile.locator('.pp-worker-finances').innerText(),/1,000 PKR/);
  assert.equal(await profile.locator('.pp-worker-day').count(),91);assert.equal(await profile.locator('.pp-day-present[data-date]').count(),1);
  assert.equal(await page.locator('.form-layout:visible').count(),0,'Worker should open on overview, not the long HR form');
  await profile.getByRole('button',{name:'Edit profile',exact:true}).click();await page.locator('.form-layout:visible').waitFor();
  await profile.getByRole('button',{name:'Back to overview',exact:true}).click();assert.equal(await page.locator('.form-layout:visible').count(),0);
  await profile.locator('.pp-worker-period').selectOption('366');await page.waitForFunction(()=>document.querySelectorAll('.pp-worker-day').length===366);
  const focus=profile.locator('.pp-worker-day').last();await focus.focus();await focus.press('ArrowLeft');assert.equal(await page.locator('.pp-worker-day[tabindex="0"]').count(),1);
  await page.screenshot({path:path.join(out,'worker-overview-desktop.png'),fullPage:true});
  await page.evaluate(()=>plus_point.set_theme('dark'));await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.waitForTimeout(350);assert.equal(await page.locator('.page-container:visible .layout-side-section:visible').count(),0,'Native form sidebar should not overlay worker overview');await page.screenshot({path:path.join(out,'worker-overview-mobile-dark.png'),fullPage:true});
  await page.evaluate(name=>frappe.set_route('Form','PP Daily Register',name),initial[0].name);await register.waitFor();assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,'attendance-approved-mobile-dark.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('PASS event/site picker, automatic saved roster, unmarked defaults, three attendance states, draft/approval separation, budget stop, exact wages/revenue, duplicate protection, worker overview/edit/history/year calendar, keyboard navigation and mobile dark-mode fit');
 }catch(error){await page.screenshot({path:path.join(out,'attendance-failure.png'),fullPage:true});console.error('PAGE ERRORS',errors);throw error;}
 finally{
  try{if(originalTheme)await page.evaluate(async value=>{await frappe.xcall('frappe.core.doctype.user.user.switch_theme',{theme:{light:'Light',dark:'Dark',automatic:'Automatic'}[value]});},originalTheme);}
  finally{await browser.close();assert(fixture('end').restored);console.log('PASS exact unbilled QA work/registers, crew, event/client and original workspace/appearance restored');}
 }
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
