/* Public signup rejection and personal drag ordering; no disposable tenant is provisioned. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
(async()=>{
 assert(process.env.PP_BROWSER_PASSWORD&&process.env.PP_PLATFORM_PASSWORD,'Supply local dummy passwords through environment variables');
 const run=crypto.randomBytes(6).toString('hex'),root=process.cwd();let reference;
 const bench=(site,method,args)=>execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site',site,'execute',method,'--kwargs',JSON.stringify(args)],{cwd:root,encoding:'utf8'}).trim();
 const prefs=action=>JSON.parse(bench('demo.localhost','plus_point.testing.dashboard_browser_preferences',{action,run_id:run}));
 prefs('begin');
 const browser=await chromium.launch({headless:true,channel:process.env.PP_BROWSER_CHANNEL||'msedge'});
 const customer=await browser.newPage({viewport:{width:1440,height:1000}}),publicPage=await browser.newPage({viewport:{width:1280,height:1000}}),admin=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];
 for(const page of [customer,publicPage,admin]){page.setDefaultTimeout(25000);page.on('pageerror',e=>errors.push(e.message));await page.addLocatorHandler(page.locator('.modal:visible').filter({hasText:'New updates are available'}),async()=>page.keyboard.press('Escape'));}
 const login=async(page,site,password,home)=>{
  await page.goto(`http://${site}:8000/login`,{waitUntil:'domcontentloaded'});await page.locator('#login_email').waitFor();
  assert.equal(await page.evaluate(async c=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)})).json()).message,{usr:'example@email.com',pwd:password}),'Logged In');
  await page.goto(`http://${site}:8000/desk/${home}`,{waitUntil:'domcontentloaded'});await page.locator('.pp-dashboard[data-ready=true]').waitFor();
 };
 const rpc=(page,method,args={})=>page.evaluate(async({method,args})=>(await frappe.call({method,args,type:'POST'})).message,{method,args});
 const headers=page=>page.locator('.body-sidebar [data-pp-section] > .pp-section-drag-header');
 async function collapse(page){const open=page.locator('.body-sidebar [data-pp-section] > .pp-section-drag-header .drop-icon[data-state=opened]');while(await open.count())await open.first().click();}
 try{
  await publicPage.goto('http://demo.localhost:8000/login',{waitUntil:'domcontentloaded'});
  await publicPage.getByRole('link',{name:'New to PLUS POINT? See plans & sign up',exact:true}).click();
  await publicPage.waitForURL('http://platform.localhost:8000/plans');
  await publicPage.getByRole('button',{name:'Choose this plan',exact:true}).first().waitFor();
  await publicPage.screenshot({path:'.local/qa/signup-plans.png',fullPage:true});
  await publicPage.getByRole('button',{name:'Choose this plan',exact:true}).first().click();
  await publicPage.getByLabel('Your name',{exact:true}).fill('Ayesha Malik (QA)');
  await publicPage.getByLabel('Business name',{exact:true}).fill('QA Signup Browser');
  await publicPage.getByLabel('Email',{exact:true}).fill(run+'@signup-test.example');
  const created=publicPage.waitForResponse(r=>r.url().endsWith('/plus_point.signup.register'));
  await publicPage.getByRole('button',{name:'Continue to demo payment',exact:true}).click();
  const result=await(await created).json();reference=result.message?.reference;assert(reference,'Signup request persisted');
  await publicPage.getByRole('button',{name:'Simulate payment & request approval',exact:true}).click();
  await publicPage.getByRole('heading',{name:'Waiting for High4Tech approval',exact:true}).waitFor();
  await publicPage.reload({waitUntil:'domcontentloaded'});await publicPage.getByRole('heading',{name:'Waiting for High4Tech approval',exact:true}).waitFor();
  await login(admin,'platform.localhost',process.env.PP_PLATFORM_PASSWORD,'high4tech');
  assert((await rpc(admin,'plus_point.dashboard.overview')).conditions.some(r=>r.title==='Demo signups await approval'));
  await admin.locator('.body-sidebar').getByRole('link',{name:'Signup approvals',exact:true}).click();
  await admin.getByRole('link',{name:'QA Signup Browser',exact:true}).click();
  await admin.getByRole('button',{name:'Reject signup',exact:true}).click();
  await publicPage.getByRole('button',{name:'Check approval status',exact:true}).click();
  await publicPage.getByRole('heading',{name:'Signup not approved',exact:true}).waitFor();
  await publicPage.screenshot({path:'.local/qa/signup-approved.png',fullPage:true});
  await publicPage.setViewportSize({width:390,height:844});assert(await publicPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  console.log('PASS login signup CTA, native-plan pricing, guest registration, demo payment, reload/resume, High4Tech rejection form, token-protected status and mobile');
  await login(customer,'demo.localhost',process.env.PP_BROWSER_PASSWORD,'plus-point');await collapse(customer);
  const initial=await customer.evaluate(()=>frappe.boot.plus_point.navigation.groups);
  const source=initial[1],target=initial[0];
  await customer.locator(`[data-pp-section="${source}"] > .pp-section-drag-header`).dragTo(customer.locator(`[data-pp-section="${target}"] > .pp-section-drag-header`),{targetPosition:{x:70,y:3}});
  await customer.waitForFunction(label=>frappe.boot.plus_point.navigation.groups[0]===label,source);
  await customer.reload({waitUntil:'domcontentloaded'});await customer.locator('.pp-dashboard[data-ready=true]').waitFor();
  assert.equal((await headers(customer).allTextContents())[0].replace('⠿','').trim(),source);
  await collapse(customer);const before=await customer.evaluate(()=>frappe.boot.plus_point.navigation.groups);
  await customer.route('**/api/method/plus_point.navigation.save_section_order',route=>route.fulfill({status:503,contentType:'application/json',body:'{"exc_type":"ValidationError"}'}));
  await customer.locator(`[data-pp-section="${before[1]}"] > .pp-section-drag-header`).dragTo(customer.locator(`[data-pp-section="${before[0]}"] > .pp-section-drag-header`),{targetPosition:{x:70,y:3}});
  await customer.getByText('Could not save your section order. The previous order is restored. Try again or use Sidebar Menu → Arrange sections.',{exact:true}).waitFor();
  assert.deepEqual(await customer.evaluate(()=>frappe.boot.plus_point.navigation.groups),before);
  await customer.locator('.modal:visible .modal-footer').getByRole('button',{name:'Close',exact:true}).click();
  await customer.locator('.modal:visible').waitFor({state:'hidden'});
  await customer.unroute('**/api/method/plus_point.navigation.save_section_order');
  await customer.getByRole('button',{name:'Sidebar Menu',exact:true}).click();await customer.getByText('Arrange sections',{exact:true}).click();
  const move=customer.getByRole('button',{name:`Move ${before[1]} up`,exact:true});await move.focus();await customer.keyboard.press('Enter');
  await customer.getByRole('button',{name:'Save my order',exact:true}).click();await customer.waitForFunction(label=>frappe.boot.plus_point.navigation.groups[0]===label,before[1]);
  await customer.screenshot({path:'.local/qa/sidebar-drag.png'});
  assert.deepEqual(errors,[]);
  console.log('PASS actual header drag, per-login saved/reloaded order, failed-save rollback and keyboard alternative');
 }finally{
  await browser.close();assert(prefs('end').restored);console.log('PASS original personal preferences restored');
  if(reference)console.log(bench('platform.localhost','plus_point.signup.cleanup_browser_request',{reference}));
 }
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
