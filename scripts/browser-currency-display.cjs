/* Actual latest-rate conversion, native-theme checks and read-only UI failure fixture. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path');
(async()=>{
 assert(process.env.PP_BROWSER_PASSWORD,'Supply the local test password through PP_BROWSER_PASSWORD');
 const browser=await chromium.launch({headless:true,channel:process.env.PP_BROWSER_CHANNEL||'msedge'});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});page.setDefaultTimeout(25000);
 await page.addLocatorHandler(page.locator('.modal:visible').filter({hasText:'New updates are available'}),async()=>page.keyboard.press('Escape'));
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const call=args=>page.evaluate(async args=>(await frappe.call({method:'plus_point.dashboard.overview',args})).message,args);
 const settled=currency=>page.waitForFunction(currency=>{const root=document.querySelector('.pp-dashboard');return root?.getAttribute('aria-busy')==='false'&&root.querySelector('.pp-dashboard-currency')?.value===currency;},currency);
 const select=async currency=>{await page.getByRole('combobox',{name:'Display currency',exact:true}).selectOption(currency);await settled(currency);};
 const formatted=value=>new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(Number(value));
 try{
  await page.goto('http://demo.localhost:8000/login');
  assert.equal(await page.evaluate(async c=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)})).json()).message,{usr:'example@email.com',pwd:process.env.PP_BROWSER_PASSWORD}),'Logged In');
  await page.goto('http://demo.localhost:8000/desk/plus-point');await page.locator('.pp-dashboard[data-ready=true]').waitFor();
  const base=await call({});assert.equal(base.currency,'PKR');
  assert(await page.locator('.pp-dashboard-metric dd').first().evaluate(n=>Number(getComputedStyle(n).fontWeight)>=700));
  assert.equal(await page.locator('.pp-dashboard').evaluate(n=>n.style.getPropertyValue('--text-color')),'');
  await select('USD');const usd=await call({company:base.company,display_currency:'USD'});
  assert.equal(usd.fx.status,'converted');assert.equal(usd.currency,'USD');
  assert(Math.abs(Number(usd.earned_revenue)-Number(base.earned_revenue)*Number(usd.fx.rate))<=.00501);
  assert((await page.locator('.pp-dashboard-metric dd').nth(3).innerText()).includes(formatted(usd.earned_revenue)));
  assert.equal(usd.workers,base.workers);assert.deepEqual(usd.activity.clients,base.activity.clients);
  assert.equal(await page.locator('.pp-fx-note').getByRole('link',{name:'Rates by ExchangeRate-API',exact:true}).count(),1);
  assert((await page.locator('.pp-fx-note').innerText()).includes('Books remain in PKR'));
  await page.getByRole('button',{name:'Refresh figures',exact:true}).click();await settled('USD');
  await page.screenshot({path:path.join('.local','qa','currency-usd.png')});
  await select('EUR');const eur=await call({company:base.company,display_currency:'EUR'});assert.equal(eur.fx.status,'converted');
  assert((await page.locator('.pp-dashboard-metric dd').nth(3).innerText()).includes(formatted(eur.earned_revenue)));
  await select('PKR');assert((await page.locator('.pp-dashboard-metric dd').nth(3).innerText()).includes(formatted(base.earned_revenue)));
  // Presentation-only error fixture; backend failure handling has separate database checks.
  const rpc='**/api/method/plus_point.dashboard.overview';
  await page.route(rpc,route=>route.fulfill({contentType:'application/json',body:JSON.stringify({message:{...base,fx:{status:'unavailable',requested:'USD',source:'PKR',target:'PKR'}}})}));
  await page.getByRole('combobox',{name:'Display currency',exact:true}).selectOption('USD');
  await page.getByRole('button',{name:'Retry conversion',exact:true}).waitFor();
  assert.equal(await page.getByRole('combobox',{name:'Display currency',exact:true}).inputValue(),'PKR');
  assert((await page.locator('.pp-dashboard-metric dd').nth(3).innerText()).includes(formatted(base.earned_revenue)));
  await page.unroute(rpc);await page.getByRole('button',{name:'Retry conversion',exact:true}).click();await settled('USD');
  for(const width of [1100,768,390,320]){
   await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`page overflow at ${width}`);
  }
  await page.screenshot({path:path.join('.local','qa','currency-mobile.png')});
  await page.emulateMedia({reducedMotion:'reduce'});
  assert(await page.locator('.pp-motion-dashboard').evaluate(n=>n.getAnimations({subtree:true}).every(a=>a.playState!=='running')));
  const original=await call({company:base.company});assert.equal(original.currency,'PKR');assert.equal(original.earned_revenue,base.earned_revenue);
  assert.deepEqual(errors,[]);
  console.log('PASS actual latest USD/EUR conversion, native currency restoration, bold/native-theme UI, unchanged worker data/books, refresh persistence, failure/retry fixture, reduced motion and 1100/768/390/320px');
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
