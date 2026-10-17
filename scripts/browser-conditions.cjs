/* Local state UX regression. Temporary demo budget/draft are restored; no costs posted. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const base='http://demo.localhost:8000',out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,...(process.env.PP_BROWSER_CHANNEL?{channel:process.env.PP_BROWSER_CHANNEL}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});page.setDefaultTimeout(30000);
 const failures=[];page.on('pageerror',e=>failures.push(e.message));
 const call=(method,args={})=>page.evaluate(async({method,args})=>(await frappe.call({method,args,type:'POST'})).message,{method,args});
 let project,original,draft;
 const budget=async amount=>call('frappe.client.set_value',{doctype:'Project',name:project,fieldname:{estimated_costing:amount,pp_enforce_spending_budget:1}});
 async function home(){await page.goto(base+'/desk/plus-point',{waitUntil:'domcontentloaded'});await page.locator('.pp-dashboard[data-ready="true"]').waitFor();}
 try{
  await page.goto(base+'/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async credentials=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials)})).json()).message,
   {usr:'Administrator',pwd:settings.PP_ADMIN_PASSWORD}),'Logged In');
  await home();
  const site=(await call('frappe.client.get_list',{doctype:'PP Site',filters:{site_name:'PLUS POINT Demo'},fields:['name','project'],limit_page_length:1}))[0];
  assert(site);project=site.project;
  original=await call('frappe.client.get',{doctype:'Project',name:project});
  assert(!original.pp_enforce_spending_budget,'Refusing to replace a user-enabled budget in the demo');
  const actual=await call('plus_point.budget.project_status',{project});assert(Number(actual.used)>1);
  await budget(Number(actual.used)-1);await home();
  await page.getByText('Spending budget exceeded',{exact:true}).waitFor();
  assert(await page.locator('.pp-budget-row.pp-value-error').count());
  await page.screenshot({path:path.join(out,'spending-overrun.png'),fullPage:true});
  console.log('PASS real overspend state, red figures and review-budget CTA');
  const day=await page.evaluate(()=>frappe.datetime.add_days(frappe.datetime.get_today(),4));
  assert.equal((await call('frappe.client.get_list',{doctype:'PP Daily Register',filters:{site:site.name,work_date:day},fields:['name']})).length,0,'Refusing to change existing attendance');
  draft=(await call('plus_point.api.prepare_daily_register',{site:site.name,work_date:day})).name;
  const document=await call('frappe.client.get',{doctype:'PP Daily Register',name:draft});
  const projected=(await call('plus_point.budget.preview',{document:JSON.stringify(document)}))[0];
  await budget(Number(projected.projected)-1);
  await page.goto(base+'/desk/pp-daily-register/'+encodeURIComponent(draft),{waitUntil:'domcontentloaded'});
  await page.waitForFunction(name=>window.cur_frm?.doc.name===name && document.querySelector('.pp-condition-section'),draft);
  await page.evaluate(async()=>{frappe.validated=true;await cur_frm.script_manager.trigger('before_submit');});
  await page.getByRole('dialog').getByText('Spending approval stopped',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>frappe.validated),false);
  await page.getByRole('dialog').getByRole('button',{name:'Review cost entries',exact:true}).click();
  assert.equal((await call('frappe.client.get',{doctype:'PP Daily Register',name:draft})).docstatus,0);
  await budget(Number(projected.projected)/0.8);
  const warning=page.evaluate(async()=>{frappe.validated=true;await cur_frm.script_manager.trigger('before_submit');});
  await page.getByRole('dialog').getByText('Review spending warning',{exact:true}).waitFor();
  await page.getByRole('dialog').getByRole('button',{name:'Review costs',exact:true}).click();await warning;
  assert.equal(await page.evaluate(()=>frappe.validated),false);
  assert.equal((await call('frappe.client.get',{doctype:'PP Daily Register',name:draft})).docstatus,0);
  console.log('PASS pre-submit stop, warning acknowledgement/cancel and no approved attendance');
  await call('frappe.client.set_value',{doctype:'Project',name:project,fieldname:{estimated_costing:original.estimated_costing||0,pp_enforce_spending_budget:original.pp_enforce_spending_budget||0}});
  const work=(await call('frappe.client.get_list',{doctype:'PP Work Entry',filters:{project,status:'Approved'},fields:['name'],limit_page_length:1}))[0];
  await page.goto(base+'/desk/pp-work-entry/'+encodeURIComponent(work.name),{waitUntil:'domcontentloaded'});
  await page.getByText('Wages approved',{exact:true}).waitFor();
  await page.getByRole('link',{name:'Review worker payments',exact:true}).waitFor();
  console.log('PASS submitted-work success state and next payment action');
  await home();
  const rpc='**/api/method/plus_point.dashboard.overview';
  await page.route(rpc,route=>route.abort('failed'));
  await page.getByRole('button',{name:'Refresh figures',exact:true}).click();
  await page.getByText('Dashboard could not load',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Try again',exact:true}).waitFor();
  assert(await page.getByRole('button',{name:'Mark attendance',exact:true}).isVisible());
  await page.unroute(rpc);await page.getByRole('button',{name:'Try again',exact:true}).click();
  await page.locator('.pp-dashboard[data-ready="true"]').waitFor();
  // Presentation-only empty-state fixture; actual no-company API was checked on QA.
  await page.route(rpc,route=>route.fulfill({contentType:'application/json',body:JSON.stringify({message:{companies:[],company:null,date:day,is_platform:false}})}));
  await page.getByRole('button',{name:'Refresh figures',exact:true}).click();
  await page.getByRole('link',{name:'Create company',exact:true}).waitFor();
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,'conditions-empty-mobile.png'),fullPage:true});
  await page.unroute(rpc);
  console.log('PASS retry/recovery, empty-state CTA and 390px width');
  assert.deepEqual(failures,[]);
 }finally{
  await page.unrouteAll({behavior:'ignoreErrors'});
  await home();
  if(original)await call('frappe.client.set_value',{doctype:'Project',name:project,fieldname:{estimated_costing:original.estimated_costing||0,pp_enforce_spending_budget:original.pp_enforce_spending_budget||0}});
  if(draft)await call('frappe.client.delete',{doctype:'PP Daily Register',name:draft});
  await browser.close();
  console.log('PASS original demo budget restored and temporary draft removed');
 }
})().catch(e=>{console.error(e.message);process.exitCode=1;});
