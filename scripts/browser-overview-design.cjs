/* Read-only Figma overview regression audit. No company records are saved/deleted. */
const fs=require('fs'),assert=require('node:assert/strict'),{chromium}=require('playwright');
const site=process.env.PP_AUDIT_SITE||'http://high4tech-events-fd166a217c.localhost:8000';
const out='.local/qa/overview-design',checks=[],errors=[];
fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 page.on('pageerror',e=>errors.push(e.message));
 async function check(name,fn){try{const details=await fn();checks.push({name,passed:true,details});}catch(e){checks.push({name,passed:false,error:e.message});await page.locator('.modal:visible .btn-modal-close').last().click({timeout:1000}).catch(()=>{});}}
 async function settled(){await page.waitForFunction(()=>{const r=document.querySelector('.pp-overview');return r?.dataset.analyticsReady==='true'&&!r.hasAttribute('aria-busy');},{},{timeout:90000});await page.waitForTimeout(450);}
 try{
  await page.route('**/api/method/frappe.utils.change_log.show_update_popup*',r=>r.fulfill({contentType:'application/json',body:'{"message":null}'}));
  await page.goto(site+'/login');
  const password=fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim();
  await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),password);
  const started=Date.now();await page.goto(site+'/desk/plus-point');await settled();
  checks.push({name:'Overview ready',passed:true,details:{milliseconds:Date.now()-started}});
  const originalMode=await page.evaluate(()=>document.documentElement.dataset.themeMode);
  await check('Native balances, four ECharts instances, locally stored Figma assets',async()=>{
   const result=await page.evaluate(()=>({stats:plus_point.charts.stats,metrics:[...document.querySelectorAll('.pp-overview-metric strong')].map(n=>n.textContent),logo:document.querySelector('.pp-brand-wordmark').getAttribute('src'),charts:[...document.querySelectorAll('.pp-overview [data-chart-engine]')].map(n=>({svg:!!n.querySelector('svg'),width:n.clientWidth})),resources:performance.getEntriesByType('resource').filter(r=>/echarts|dashboard_overview|three|event_world/.test(r.name)).map(r=>({name:r.name.split('/').pop(),bytes:r.encodedBodySize,duration:r.duration}))}));
   assert.equal(result.stats.active,4);assert(result.charts.every(r=>r.svg&&r.width>0));assert(result.logo.includes('/images/dashboard/'));assert(!result.resources.some(r=>/three|event_world/.test(r.name)));return result;
  });
  await check('Status filter, search, empty results and pagination',async()=>{
   await page.locator('[data-overview-filters]').click();await page.locator('[name=overview-worker-status][value=Assigned]').check();await settled();
   assert(await page.locator('[data-overview-workers] tbody').innerText().then(t=>t.includes('Assigned')));
   await page.locator('[data-overview-reset]').click();await settled();await page.keyboard.press('Escape');
   const input=page.locator('.pp-overview-search input');await input.fill('no-such-worker-unique-9217');await page.waitForTimeout(550);await settled();assert(await page.locator('[data-overview-workers]').innerText().then(t=>t.includes('No workers match')));
   await input.fill('');await page.waitForTimeout(550);await settled();await page.locator('[data-worker-page="2"]').first().click();await settled();assert.equal(await page.locator('.pp-overview-pagination [aria-current=page]').innerText(),'2');
   await page.locator('[data-worker-page="1"]').first().click();await settled();await page.locator('[data-workers-all]').check();assert.equal(await page.locator('[data-worker-check]:checked').count(),5);
   await input.fill('Adeel');await page.waitForTimeout(550);await settled();assert.equal(await page.locator('[data-worker-check]:checked').count(),0);await input.fill('');await page.waitForTimeout(550);await settled();
  });
  await check('Date validation stays in the dialog; date periods update the chart',async()=>{
   await page.locator('[data-overview-range]').click();const dialog=page.locator('.modal:visible').last();await dialog.locator('[data-fieldname=start] input').fill('2026-11-01');await dialog.locator('[data-fieldname=end] input').fill('2026-10-01');await dialog.locator('.btn-modal-primary').click();assert(await dialog.isVisible());assert.match(await dialog.innerText(),/end date on or after/);await dialog.locator('.btn-modal-close').first().click();
   await page.locator('[data-attendance-period="7"]').click();await settled();assert.equal(await page.evaluate(()=>plus_point.charts.get(document.querySelector('[data-chart=attendance]')).instance.getOption().xAxis[0].data.length),7);
   await page.locator('[data-attendance-period="30"]').click();await settled();
  });
  await check('Real activity expansion and notification count',async()=>{
   await page.locator('[data-overview-all-activity]').click();const dialog=page.locator('.modal:visible').last();await dialog.locator('a').first().waitFor();assert(await dialog.locator('a').count()>=await page.locator('[data-overview-feed] a').count());await dialog.locator('.btn-modal-close').first().click();
   return {count:await page.locator('.pp-shell-notification-count').textContent().catch(()=> '0')};
  });
  await check('Theme control has a visible menu',async()=>{await page.locator('.pp-app-header .pp-theme-toggle').click();assert(await page.getByText('Dark',{exact:true}).filter({visible:true}).count()>0);await page.keyboard.press('Escape');});
  await page.addScriptTag({path:'.local/a11y/node_modules/axe-core/axe.min.js'});
  for(const theme of ['light','dark']){
   await page.evaluate(t=>{document.documentElement.dataset.theme=t;document.dispatchEvent(new Event('pp:theme-changed'));},theme);await page.waitForTimeout(450);
   for(const width of [320,390,768,1024,1440,1920]){
    await page.setViewportSize({width,height:1100});await page.waitForTimeout(400);
    await check(theme+' layout '+width,async()=>{
     const v=await page.evaluate(()=>({document:document.documentElement.scrollWidth,viewport:innerWidth,root:document.querySelector('.pp-overview').getBoundingClientRect().toJSON(),feedDisplay:getComputedStyle(document.querySelector('.pp-overview-feed-item')).display,feedHeight:document.querySelector('.pp-overview-feed-item').getBoundingClientRect().height,numbers:[...document.querySelectorAll('.pp-overview-metric strong')].map(n=>({width:n.clientWidth,content:n.scrollWidth})),active:plus_point.charts.stats.active}));assert(v.document<=v.viewport+1,'Document horizontal overflow: '+JSON.stringify(v));assert(v.numbers.every(r=>r.content<=r.width+1));assert.equal(v.active,4);assert.equal(v.feedDisplay,'flex');assert(v.feedHeight<=80);return v;
    });
    if([390,1440].includes(width)){await page.evaluate(()=>{window.scrollTo(0,0);document.querySelectorAll('*').forEach(n=>{if(n.scrollTop)n.scrollTop=0;});});await page.mouse.move(0,0);await page.screenshot({path:out+'/'+theme+'-'+width+'.png',fullPage:true});await check(theme+' WCAG AA '+width,async()=>{const audit=await page.evaluate(()=>axe.run('.pp-overview',{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}}));const violations=audit.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));fs.writeFileSync(out+'/axe-'+theme+'-'+width+'.json',JSON.stringify(violations,null,2));assert.equal(violations.length,0,JSON.stringify(violations));return {violations:0};});}
   }
  }
  await page.evaluate(mode=>{document.documentElement.dataset.themeMode=mode;frappe.ui.set_theme();document.dispatchEvent(new Event('pp:theme-changed'));},originalMode||'light');
  await page.setViewportSize({width:1440,height:1100});
  await check('Long amounts fit without clipping',async()=>{const details=await page.evaluate(()=>{const nodes=[...document.querySelectorAll('.pp-overview-metric strong')];const prior=nodes.map(n=>n.textContent);nodes.forEach(n=>n.textContent='999,999,999,999.99');plus_point.ui.fit_numbers(document.querySelector('.pp-overview'));const result=nodes.map(n=>({width:n.clientWidth,content:n.scrollWidth,font:getComputedStyle(n).fontSize}));nodes.forEach((n,i)=>n.textContent=prior[i]);plus_point.ui.fit_numbers(document.querySelector('.pp-overview'));return result;});assert(details.every(r=>r.content<=r.width+1));return details;});
  await check('Server error preserves figures and Retry recovers',async()=>{
   let fail=true;await page.route('**/api/method/plus_point.dashboard_view.view',route=>fail?route.fulfill({status:503,contentType:'application/json',body:'{"message":"Service temporarily unavailable"}'}):route.continue());await page.locator('[data-attendance-period="7"]').click();await page.locator('[data-overview-retry]').waitFor();assert(await page.locator('[data-overview-workers] tbody tr').count()>0);fail=false;await page.locator('[data-overview-retry]').click();await settled();await page.unroute('**/api/method/plus_point.dashboard_view.view');
  });
  await check('Route cleanup disposes charts and re-entry mounts four only',async()=>{
   await page.evaluate(()=>frappe.set_route('List','Employee'));await page.waitForFunction(()=>plus_point.charts.stats.active===0);await page.evaluate(()=>frappe.set_route('Workspaces','PLUS POINT'));await settled();assert.equal(await page.evaluate(()=>plus_point.charts.stats.active),4);assert(await page.locator('.body-sidebar [data-id=Overview] .pp-selected').count()>0);
  });
  await check('Steady idle DOM, no repeated data requests',async()=>{const v=await page.evaluate(async()=>{let count=0;const root=document.querySelector('.pp-overview');const observer=new MutationObserver(records=>count+=records.length);observer.observe(root,{childList:true,subtree:true,attributes:true});const requests=()=>performance.getEntriesByType('resource').filter(r=>r.name.includes('dashboard_view.view')).length;const before=requests();await new Promise(r=>setTimeout(r,1500));observer.disconnect();return {mutations:count,requests:requests()-before};});assert(v.mutations<10,JSON.stringify(v));assert.equal(v.requests,0);return v;});
  await check('Shared branding preserves worker list, agreement and event layouts',async()=>{
   const event=await page.locator('[data-overview-events] a').first().getAttribute('href'),agreement=await page.locator('[data-overview-milestones] a').first().getAttribute('href');
   await page.evaluate(()=>frappe.set_route('List','Employee'));await page.locator('.page-container:visible .list-row-head').waitFor();
   assert(await page.locator('.pp-global-bar:visible').count()>0);assert.equal(await page.evaluate(()=>getComputedStyle(document.body).getPropertyValue('--pp-brand-solid').trim()),'#ff5800');
   await page.evaluate(record=>frappe.set_route('pp-event-plans',{record}),new URL(event,site).searchParams.get('record'));await page.locator('.pp-event-overview:visible').waitFor({timeout:60000});assert.equal(await page.evaluate(()=>plus_point.charts.stats.active),0);
   await page.evaluate(record=>frappe.set_route('pp-agreements',{record}),new URL(agreement,site).searchParams.get('record'));await page.locator('.pp-agreement-document:visible').waitFor({timeout:60000});
   assert(await page.locator('.pp-global-bar:visible').count()>0);await page.evaluate(()=>frappe.set_route('Workspaces','PLUS POINT'));await settled();
  });
  await page.setViewportSize({width:1440,height:2250});await page.waitForTimeout(500);const height=await page.evaluate(()=>document.querySelector('.pp-overview').scrollHeight+80);await page.setViewportSize({width:1440,height});await page.evaluate(()=>{window.scrollTo(0,0);document.querySelectorAll('*').forEach(n=>{if(n.scrollTop)n.scrollTop=0;});});await page.waitForTimeout(250);await page.mouse.move(0,0);await page.screenshot({path:out+'/final-desktop.png',fullPage:true});
  checks.push({name:'No browser exceptions',passed:errors.length===0,details:errors});
 }finally{fs.writeFileSync(out+'/report.json',JSON.stringify({site,checks,errors},null,2));await browser.close();}
 console.log(JSON.stringify({passed:checks.filter(c=>c.passed).length,failed:checks.filter(c=>!c.passed).map(c=>({name:c.name,error:c.error})),errors},null,2));
 if(checks.some(c=>!c.passed))process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exitCode=1;});
