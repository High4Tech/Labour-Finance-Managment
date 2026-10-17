/* Read-only verification of the two focused product interfaces. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..');
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/)
  .filter(line=>line.includes('=')&&!line.startsWith('#')).map(line=>{const i=line.indexOf('=');return[line.slice(0,i),line.slice(i+1)];}));
 const site=process.env.PP_BROWSER_SITE||'demo.localhost',platform=site==='platform.localhost';
 assert(site.endsWith('.localhost'));
 const base=`http://${site}:${settings.FRAPPE_PORT||8000}`;
 const browser=await chromium.launch({headless:true,...(process.env.PP_BROWSER_CHANNEL?{channel:process.env.PP_BROWSER_CHANNEL}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(30000);
 const failures=[];page.on('pageerror',e=>failures.push(e.stack || e.message));
 page.on('response',r=>{if(r.status()>=400)failures.push(`HTTP ${r.status()}: ${r.url()}`);});
 const out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const homeTitle=platform?'PLUS POINT customers':'Workforce overview';
 try{
  await page.goto(base+'/login',{waitUntil:'domcontentloaded'});
  const login=await page.evaluate(async credentials=>(await(await fetch('/api/method/login',{method:'POST',
   headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials)})).json()).message,
   {usr:process.env.PP_BROWSER_USER||'Administrator',pwd:process.env.PP_BROWSER_PASSWORD||settings.PP_ADMIN_PASSWORD});
  assert.equal(login,'Logged In');
  await page.goto(base+'/desk',{waitUntil:'domcontentloaded'});
  await page.locator('.pp-task-home').getByText(homeTitle,{exact:true}).waitFor();
  await page.locator('.pp-dashboard[data-ready="true"]').waitFor();
  assert.equal(await page.locator('.pp-dashboard-metric').count(),4);
  assert.equal(await page.locator('.pp-dashboard-panel').count(),2);
  assert(await page.locator('.pp-dashboard').evaluate(node=>node.getBoundingClientRect().top < document.querySelector('.pp-task-rows').getBoundingClientRect().top));
  await page.locator('.pp-dashboard').getByRole('button',{name:'Refresh figures',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.pp-dashboard')?.getAttribute('aria-busy')==='false');
  assert.equal(await page.locator('.pp-dashboard[data-ready="true"]').count(),1);
  assert.deepEqual(await page.evaluate(()=>Object.keys(frappe.boot.module_sidebars)),['PLUS POINT']);
  const sidebar=await page.locator('.body-sidebar').innerText();
  const search=await page.evaluate(()=>({
   unrelated:frappe.search.utils.get_workspaces('Manufacturing'),
   records:frappe.search.utils.get_doctypes('BOM'),
   own:frappe.search.utils.get_workspaces(frappe.boot.plus_point.navigation.workspace)
  }));
  assert.equal(search.unrelated.length,0);assert.equal(search.records.length,0);assert(search.own.length);
  for(const label of ['Manufacturing','Payroll','Frappe HR','Framework','ERPNext'])assert(!sidebar.includes(label),label);
  if(platform){
   for(const label of ['Customer accounts','Customer support','Pricing plans','Subscriptions','Software invoices','Financial results','Outstanding invoices'])assert(sidebar.includes(label),label);
   for(const label of ['Assign workers','Attendance','Wages earned','PP Assignment'])assert(!sidebar.includes(label),label);
   await page.getByRole('link',{name:'Customers',exact:true}).click();
   await page.getByRole('button',{name:'Add customer',exact:true}).waitFor();
   const tenant=await page.evaluate(async()=>{const rows=await frappe.db.get_list('PP Tenant',{fields:['name'],limit:1});return rows[0].name;});
   await page.goto(base+'/desk/pp-tenant/'+encodeURIComponent(tenant),{waitUntil:'domcontentloaded'});
   await page.getByRole('button',{name:'Reset customer password',exact:true}).waitFor();
   await page.getByRole('button',{name:'Change customer login ID',exact:true}).waitFor();
   await page.getByRole('link',{name:'Platform home',exact:true}).click();
   for(const [label,report] of [['Financial results','Profit and Loss Statement'],['Outstanding invoices','Accounts Receivable']]){
    await page.locator('.pp-task-home').getByRole('link',{name:label,exact:true}).click();
    await page.waitForFunction(report=>frappe.query_report?.report_name===report &&
     frappe.query_report.get_filter_value('company') && Array.isArray(frappe.query_report.data),report);
    await page.getByRole('link',{name:'Platform home',exact:true}).click();
    await page.locator('.pp-task-home').getByText(homeTitle,{exact:true}).waitFor();
   }
  }else{
   assert(sidebar.includes('Attendance')&&sidebar.includes('Workers')&&sidebar.includes('Project finances')&&sidebar.includes('Worker statement'));
   assert(!sidebar.includes('Subscriptions')&&!sidebar.includes('Customer support'));
   assert.equal(await page.getByRole('link',{name:'HR tools',exact:true}).count(),0);
   await page.getByRole('button',{name:'Mark attendance',exact:true}).click();
   await page.getByRole('dialog').getByRole('button',{name:'Review attendance',exact:true}).waitFor();
   await page.getByRole('dialog').getByRole('button',{name:'Close',exact:true}).click();
   await page.getByRole('dialog').waitFor({state:'hidden'});
  }
  await page.locator('.pp-task-home').getByText(homeTitle,{exact:true}).waitFor();
  await page.locator('.body-sidebar .sidebar-header').click();
  for(const label of ['Apps','Modules','All apps','Edit Sidebar'])
   assert.equal(await page.getByText(label,{exact:true}).filter({visible:true}).count(),0,label);
  await page.keyboard.press('Escape');
  await page.goto(base+(platform?'/desk/pp-assignment':'/desk/manufacturing'),{waitUntil:'domcontentloaded'});
  await page.locator('.pp-task-home').getByText(homeTitle,{exact:true}).waitFor();
  await page.locator('.pp-dashboard[data-ready="true"]').waitFor();
  await page.screenshot({path:path.join(out,platform?'focused-platform.png':'focused-customer.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,platform?'focused-platform-mobile.png':'focused-customer-mobile.png'),fullPage:true});
  assert.deepEqual(failures,[]);
  console.log(`PASS ${platform?'High4Tech':'PLUS POINT'} focused sidebar/home, no extra app/module menu, unrelated route return, 390px layout and zero browser/server errors`);
 }catch(error){await page.screenshot({path:path.join(out,'product-scope-failure.png'),fullPage:true});console.error('Browser failures:',failures);console.error((await page.locator('body').innerText()).slice(-2200));
  console.error(await page.evaluate(()=>({route:frappe.get_route(),active:frappe.container?.page?.id,
   ancestors:[...document.querySelectorAll('.pp-task-home')].map(node=>{const rows=[];for(let el=node;el;el=el.parentElement)rows.push([el.tagName,el.id,el.className,getComputedStyle(el).display,el.hidden]);return rows;})})));
  throw error;}
 finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
