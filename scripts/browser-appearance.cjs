/* Saved native themes and shared CTA geometry, without business-data changes. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));let original;
 const mode=()=>page.evaluate(()=>document.documentElement.getAttribute('data-theme-mode'));
 const choose=async label=>{await page.getByRole('button',{name:/^Appearance:/}).click();await page.getByRole('menuitem',{name:label,exact:true}).click();await page.waitForFunction(label=>document.querySelector('.pp-theme-value')?.textContent===label,label);};
 const geometry=async(selector,height)=>{
  const rows=await page.locator(selector).evaluateAll(nodes=>nodes.filter(el=>el.getBoundingClientRect().width&&el.getBoundingClientRect().height&&getComputedStyle(el).visibility!=='hidden').map(el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return {label:el.textContent.trim()||el.getAttribute('aria-label')||el.title,height:r.height,width:r.width,x:r.x,y:r.y,icon:el.matches('.icon-btn,[data-icon-button=true]'),radius:s.borderRadius};}));
  assert(rows.length>1,JSON.stringify(rows));for(const r of rows){assert(Math.abs(r.height-height)<1,JSON.stringify(r));if(r.icon)assert(Math.abs(r.width-height)<1,JSON.stringify(r));assert.equal(r.radius,'8px');}return rows;
 };
 const noOverflow=async()=>assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 try{
  await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
  await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});
  await page.getByRole('button',{name:/^Appearance:/}).waitFor();original=await mode();
  await page.locator('.pp-onboarding-shell[data-ready=true]').waitFor({timeout:60000});
  await page.getByRole('button',{name:'Skip onboarding',exact:true}).click();await page.locator('.pp-dashboard[data-ready=true]').waitFor();
  await choose('Light');await page.waitForFunction(()=>document.documentElement.dataset.theme==='light');
  await geometry('.pp-dashboard .btn',36);await page.screenshot({path:path.join(out,'appearance-light-dashboard.png'),fullPage:true});
  await choose('Dark');await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
  await page.waitForFunction(()=>{const el=document.querySelector('.pp-dashboard-metric:nth-child(2)');return el&&Number(getComputedStyle(el).backgroundColor.match(/\d+/)?.[0])<90;});
  await geometry('.pp-dashboard .btn',36);await page.screenshot({path:path.join(out,'appearance-dark-dashboard.png'),fullPage:true});
  // The root's effective theme, saved preference and reload must agree.
  await page.reload({waitUntil:'domcontentloaded'});await page.getByRole('button',{name:'Appearance: Dark',exact:true}).waitFor();assert.equal(await mode(),'dark');
  await page.evaluate(()=>frappe.set_route('List','PP Event Plan'));await page.getByRole('button',{name:'Plan an event',exact:true}).waitFor();
  const toolbar=await geometry('.page-head:visible .page-actions :is(.btn,.es-button)',36);
  for(const row of toolbar)assert(Math.abs(row.y-toolbar[0].y)<2,JSON.stringify(toolbar));
  await page.screenshot({path:path.join(out,'appearance-dark-event-toolbar.png'),fullPage:true});
  await page.getByRole('button',{name:'Import',exact:true}).click();const dialog=page.locator('.pp-import-dialog:visible');await dialog.waitFor();
  await geometry('.pp-import-dialog:visible :is(.modal-footer,.pp-import-tools) :is(.btn,.es-button)',36);
  // Invalid rows retain readable state colors in dark mode.
  const header=['external_id','event_name','customer','start_date','end_date','site_name','workers_per_day','billing_model','fixed_amount','wage_rate','client_rate','agreement'];
  const bad='appearance-bad,Event,Missing Client,2026-12-01,2026-12-02,Hall,2,unsupported,0,100,150,Agreement';
  await dialog.locator('input[type=file]').setInputFiles({name:'invalid.csv',mimeType:'text/csv',buffer:Buffer.from(header.join(',')+'\n'+bad)});await dialog.getByRole('button',{name:'Review file',exact:true}).click();
  await dialog.getByText('Fix the file before importing',{exact:true}).waitFor();
  const status=await dialog.locator('.pp-import-error td:last-child').evaluate(el=>({color:getComputedStyle(el).color,text:el.textContent}));assert.match(status.text,/unsupported/);assert.equal(status.color,'rgb(255, 170, 170)');
  await page.screenshot({path:path.join(out,'appearance-dark-import.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});await geometry('.pp-import-dialog:visible :is(.modal-footer,.pp-import-tools) :is(.btn,.es-button)',44);await noOverflow();
  const action=dialog.getByRole('button',{name:'Review file',exact:true});assert(await action.evaluate(el=>el.getBoundingClientRect().bottom<=innerHeight));
  await page.screenshot({path:path.join(out,'appearance-dark-import-mobile.png'),fullPage:true});
  await dialog.getByRole('button',{name:'Close',exact:true}).click();await dialog.waitFor({state:'hidden'});
  await geometry('.page-head:visible .page-actions :is(.btn,.es-button)',44);await noOverflow();
  const mobileHeader=await page.locator('.page-head:visible').boundingBox();
  for(const row of await geometry('.page-head:visible .page-actions :is(.btn,.es-button)',44)){
   assert(row.y>=mobileHeader.y,JSON.stringify(row));assert(row.y+row.height<=mobileHeader.y+mobileHeader.height+1,JSON.stringify({row,mobileHeader}));
   assert(row.x>=0&&row.x+row.width<=390,JSON.stringify(row));
  }
  await page.getByRole('button',{name:'Import',exact:true}).click();await dialog.waitFor();await dialog.getByRole('button',{name:'Close',exact:true}).click();await dialog.waitFor({state:'hidden'});
  await page.screenshot({path:path.join(out,'appearance-dark-toolbar-mobile.png'),fullPage:true});
  await page.setViewportSize({width:1440,height:1000});
  await page.evaluate(name=>frappe.set_route('Form','Employee',name),data.worker);await page.getByRole('button',{name:'Delete',exact:true}).waitFor();
  await geometry('.page-head:visible .page-actions :is(.btn,.es-button)',36);
  await page.getByRole('button',{name:'Delete',exact:true}).click();const removal=page.locator('.pp-delete-dialog:visible');await removal.waitFor();
  await geometry('.pp-delete-dialog:visible .modal-footer :is(.btn,.es-button)',36);await removal.getByRole('button',{name:'Cancel',exact:true}).click();await removal.waitFor({state:'hidden'});
  await page.emulateMedia({colorScheme:'light'});await choose('System');await page.waitForFunction(()=>document.documentElement.dataset.theme==='light');
  await page.emulateMedia({colorScheme:'dark'});await page.waitForFunction(()=>document.documentElement.dataset.theme==='dark');assert.equal(await mode(),'automatic');
  // Failed saves leave the selected preference unchanged and allow retry.
  await page.route('**/api/method/frappe.core.doctype.user.user.switch_theme',route=>route.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await page.evaluate(()=>plus_point.set_theme('light'));assert.equal(await mode(),'automatic');assert.equal(await page.getByRole('button',{name:'Appearance: System',exact:true}).isDisabled(),false);
  assert.equal(await page.locator('.modal:visible').count(),0,'Appearance errors should not open another dialog');
  await page.unroute('**/api/method/frappe.core.doctype.user.user.switch_theme');
  assert.deepEqual(errors,[]);
  const admin=await browser.newPage({viewport:{width:1440,height:1000}});let adminOriginal;
  try{
   await admin.goto('http://platform.localhost:8000/login',{waitUntil:'domcontentloaded'});
   assert.equal(await admin.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
   await admin.goto('http://platform.localhost:8000/desk/high4tech',{waitUntil:'domcontentloaded'});
   await admin.getByRole('button',{name:/^Appearance:/}).waitFor();adminOriginal=await admin.evaluate(()=>document.documentElement.dataset.themeMode);
   await admin.evaluate(()=>plus_point.set_theme('dark'));await admin.waitForFunction(()=>document.documentElement.dataset.theme==='dark');
   assert.equal(await admin.locator('.pp-theme-toggle').count(),1);
   await admin.locator('.pp-dashboard[data-ready=true]').waitFor();
   await admin.waitForFunction(()=>{const el=document.querySelector('.pp-dashboard');return el&&Number(getComputedStyle(el).backgroundColor.match(/\d+/)?.[0])<90;});
   const heights=await admin.locator('.pp-dashboard .btn').evaluateAll(nodes=>nodes.filter(el=>el.getBoundingClientRect().width).map(el=>el.getBoundingClientRect().height));
   assert(heights.length);assert(heights.every(height=>Math.abs(height-36)<1));
   await admin.screenshot({path:path.join(out,'appearance-high4tech-dark.png'),fullPage:true});
  }finally{if(adminOriginal)await admin.evaluate(async value=>{await frappe.xcall('frappe.core.doctype.user.user.switch_theme',{theme:{light:'Light',dark:'Dark',automatic:'Automatic'}[value]});},adminOriginal);await admin.close();}
  console.log('PASS High4Tech appearance control, dark dashboard and shared 36px actions; original admin preference restored');
  console.log('PASS native saved Light/Dark/System themes, reload persistence, live system-theme changes, retry after save failure, aligned 36px list/form/dialog CTAs, 44px mobile actions, readable error states, mobile fit and no business records changed');
 }catch(error){await page.screenshot({path:path.join(out,'appearance-failure.png'),fullPage:true});console.error('PAGE ERRORS',errors);throw error;}
 finally{
  let restoreError;
  try{if(original){await page.unroute('**/api/method/frappe.core.doctype.user.user.switch_theme').catch(()=>{});await page.evaluate(async value=>{await frappe.xcall('frappe.core.doctype.user.user.switch_theme',{theme:{light:'Light',dark:'Dark',automatic:'Automatic'}[value]});},original);}}
  catch(error){restoreError=error;}
  finally{await browser.close();assert(fixture('end').restored);}
  if(restoreError)throw new Error('Could not restore the original theme: '+restoreError.message);
  console.log('PASS original appearance preference and disposable workspace restored');
 }
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
