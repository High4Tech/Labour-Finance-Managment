/* Read-only layout/lifecycle regression. Draft writes stay in browser fixtures. */
const fs=require('fs'),assert=require('node:assert/strict'),{chromium}=require('playwright');
(async()=>{
 const out='.local/qa/react-layout';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:2550,height:1300}}),checks=[],errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
 const check=async(name,run)=>{try{checks.push({name,passed:true,details:await run()});}catch(e){checks.push({name,passed:false,error:e.message});await page.screenshot({path:out+'/failure-'+checks.length+'.png'});await page.keyboard.press('Escape').catch(()=>{});}fs.writeFileSync(out+'/report.json',JSON.stringify({checks,errors},null,2));};
 const route=(...args)=>page.evaluate(args=>frappe.set_route(...args),args),origin='http://high4tech-events-fd166a217c.localhost:8000';
 const fillWidth=selector=>page.locator(selector).evaluate(el=>{const r=el.getBoundingClientRect(),main=el.closest('.layout-main');const m=main?.getBoundingClientRect();return {left:r.left,width:r.width,mainLeft:m?.left,mainWidth:m?.width};});
 try{
  await page.goto(origin+'/login');await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim());
  await page.goto(origin+'/desk/pp-contract-terms',{waitUntil:'commit',timeout:90000});await page.waitForSelector('.pp-r-planning tbody a',{timeout:60000}).catch(async e=>{await page.screenshot({path:out+'/first-route-failure.png'});const detail=await page.evaluate(()=>({route:window.frappe?.get_route?.(),title:document.title,roots:window.plus_point?.react_ui?.stats,visible:document.body.innerText.slice(0,500)}));throw Error(e.message+' '+JSON.stringify(detail));});
  await check('All five migrated lists use full native main width at first ready frame',async()=>{
   const result=[];for(const [doctype,selector] of [['PP Contract Terms','.pp-r-planning'],['PP Event Plan','.pp-r-planning'],['Customer','[data-pp-react-root=clients]'],['Employee','[data-pp-react-root=workers]'],['PP Wage Settlement','[data-pp-react-root=payments]']]){
    await route('List',doctype);await page.waitForSelector(selector+' table');const first=await fillWidth(selector);await page.waitForTimeout(300);const later=await fillWidth(selector);assert(first.mainWidth&&first.width>=first.mainWidth-2,JSON.stringify({doctype,first}));assert.equal(first.left,later.left);assert.equal(first.width,later.width);result.push({doctype,...first});
   }return result;
  });
  await check('Paid and unapproved payment rows remain selectable for review, not payable',async()=>{
   const table=page.locator('[data-rows]');assert.equal(await table.locator('tbody input:disabled').count(),0);await table.locator('thead input').check();const boxes=await table.locator('input').evaluateAll(nodes=>nodes.map(el=>({w:el.getBoundingClientRect().width,h:el.getBoundingClientRect().height,checked:el.checked})));assert(boxes.every(b=>b.w===20&&b.h===20&&b.checked));assert(await table.locator('thead input').evaluate(el=>el.classList.contains('pp-figma-check')&&getComputedStyle(el).backgroundColor!=='rgb(0, 0, 0)')); await page.screenshot({path:out+'/payment-selection.png'});
   const data=await page.evaluate(()=>plus_point.form_rpc('wage_payments.overview',{}));if(!data.rows.some(r=>Number(r.outstanding)>0))assert(await page.getByRole('button',{name:'Record selected payments',exact:true}).isDisabled());assert(await page.getByText('Paid balances and work awaiting approval are excluded from payment.',{exact:true}).isVisible());await page.getByRole('button',{name:'Clear selection',exact:true}).click();
  });
  await check('Agreement creator fills the same width and footer from its first frame',async()=>{
   await route('pp-agreements',{record:'new'});await page.waitForSelector('.pp-r-builder .pp-r-step');const r=await fillWidth('.pp-r-builder');assert(r.mainWidth&&r.width>=r.mainWidth-2,JSON.stringify(r));const footer=await page.locator('.pp-r-builder-footer').boundingBox();assert(Math.abs(footer.x-r.left)<2&&Math.abs(footer.width-r.width)<2);await page.screenshot({path:out+'/builder-wide.png'});
  });
  let release,held=new Promise(resolve=>release=resolve);
  await page.route('**/api/method/plus_point.dashboard.overview',async r=>{await held;await r.continue();});
  await check('React owns a single aligned dashboard skeleton without native blocks underneath',async()=>{
   await route('Workspaces','PLUS POINT');await page.waitForSelector('[data-pp-react-root=dashboard] .pp-overview-loading');const skeleton=page.locator('.pp-overview-loading');assert.equal(await skeleton.count(),1);assert.equal(await page.locator('.pp-overview-skeleton:visible,.list-skeleton:visible').count(),0);assert.equal(await page.evaluate(()=>plus_point.react_ui.stats.activeRoots),1);
   const dims=await skeleton.evaluate(el=>{const primary=el.querySelector('.pp-overview-primary').getBoundingClientRect(),activity=el.querySelector('.pp-overview-activity').getBoundingClientRect(),metrics=[...el.querySelectorAll('.pp-kpi-grid>i')].map(n=>n.getBoundingClientRect().width);return {primary:primary.x,activity:activity.x,metrics,scroll:document.documentElement.scrollWidth,width:innerWidth};});assert(dims.activity>dims.primary);assert(Math.max(...dims.metrics)-Math.min(...dims.metrics)<2);assert(dims.scroll<=dims.width+1);await page.screenshot({path:out+'/dashboard-skeleton.png'});
  });release();await page.waitForSelector('.pp-overview-metric');await page.unroute('**/api/method/plus_point.dashboard.overview',{behavior:'wait'});
  await check('Currency refresh keeps the React root and input mounted, with no idle reload',async()=>{
   await page.waitForSelector('[data-overview-workers] tbody tr');await page.evaluate(()=>window.qaDashboard={input:document.querySelector('.pp-overview-search input'),mounts:plus_point.react_ui.stats.mounts});const before=requests.filter(u=>u.includes('dashboard.overview')).length,response=page.waitForResponse(r=>r.url().includes('dashboard_view.view')&&r.ok());await page.evaluate(()=>document.dispatchEvent(new Event('pp:display-currency')));await response;await page.waitForFunction(()=>document.querySelector('.pp-overview')?.getAttribute('aria-busy')==='false');assert(await page.evaluate(()=>qaDashboard.input===document.querySelector('.pp-overview-search input')&&qaDashboard.mounts===plus_point.react_ui.stats.mounts));assert.equal(requests.filter(u=>u.includes('dashboard.overview')).length-before,1);const after=requests.length;await page.waitForTimeout(1800);assert.equal(requests.slice(after).filter(u=>u.includes('/api/method/plus_point.')).length,0);
  });
  checks.push({name:'No unhandled browser errors',passed:errors.length===0,details:errors});
 }finally{fs.writeFileSync(out+'/report.json',JSON.stringify({checks,errors},null,2));await browser.close();}
 console.log(JSON.stringify({passed:checks.filter(c=>c.passed).length,failed:checks.filter(c=>!c.passed),errors},null,2));if(checks.some(c=>!c.passed))process.exitCode=1;
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
