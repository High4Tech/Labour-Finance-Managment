/* Same local company, isolated browser contexts; baseline assets never deployed. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{const root=path.resolve(__dirname,'..'),site='http://high4tech-events-fd166a217c.localhost:8000',base=process.env.PP_BASELINE_REF||'75a4299',results=[];const browser=await chromium.launch({channel:'msedge',headless:true});
 try{for(const phase of ['before','after'])for(let run=0;run<2;run++){
  console.log('Measuring '+phase+' '+(run+1));const context=await browser.newContext({viewport:{width:1440,height:1100}}),page=await context.newPage(),overrides=new Map(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/method/frappe.utils.change_log.show_update_popup*',r=>r.fulfill({contentType:'application/json',body:'{"message":null}'}));
  { // Fulfil the same assets in both phases to avoid favouring the baseline transport.
   for(const file of ['js/icons.js','js/runtime.js','js/dashboard_journey.js','css/dashboard_journey.css','js/lazy_features.js','js/dashboard_overview.js','css/dashboard_overview.css','js/experience.js','js/onboarding.js','js/appearance.js','js/business_reports.js','js/app_shell.js','css/app_shell.css','js/ui_components.js','css/ui_components.css','js/dashboard.js','js/charts.js','css/brand.css']){const body=phase==='before'?execFileSync('git',['show',base+':apps/plus_point/plus_point/public/'+file],{cwd:root,encoding:'utf8'}):fs.readFileSync(path.join(root,'apps/plus_point/plus_point/public',file),'utf8');overrides.set('/assets/plus_point/'+file,Buffer.byteLength(body));await page.route('**/assets/plus_point/'+file+'*',r=>r.fulfill({contentType:file.endsWith('.css')?'text/css':'application/javascript',body}));}

  }
  await page.goto(site+'/login',{waitUntil:'domcontentloaded',timeout:90000});await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim());
  const start=Date.now();await page.goto(site+'/desk/plus-point',{waitUntil:'domcontentloaded',timeout:90000});await page.waitForSelector('.pp-overview[data-analytics-ready=true]',{timeout:90000});await page.waitForFunction(()=>document.querySelector('.pp-overview').getAttribute('aria-busy')!=='true');const readyMs=Date.now()-start;
  const sample=await page.evaluate(()=>({resources:performance.getEntriesByType('resource').filter(r=>/\.(js|css)(\?|$)/.test(r.name)).map(r=>({name:new URL(r.name).pathname,bytes:r.encodedBodySize})),apiRequests:performance.getEntriesByType('resource').filter(r=>r.name.includes('/api/method/plus_point.dashboard')).length,dom:document.querySelectorAll('*').length,heap:performance.memory?.usedJSHeapSize,active:plus_point.charts.stats.active}));sample.resources=sample.resources.map(r=>({...r,bytes:overrides.get(r.name)??r.bytes}));
  const began=Date.now();await page.locator('[data-attendance-period="7"]').click();await page.waitForFunction(()=>!document.querySelector('.pp-overview').hasAttribute('aria-busy'));const interactionMs=Date.now()-began;
  await page.evaluate(()=>frappe.set_route('List','Employee'));await page.waitForFunction(()=>plus_point.charts.stats.active===0);assert.equal(errors.length,0,errors.join('\n'));
  const row={phase,run,readyMs,interactionMs,...sample,errors};results.push(row);await context.close();
 }
 fs.writeFileSync('.local/qa/dashboard-polish/performance.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results.map(r=>({phase:r.phase,run:r.run,readyMs:r.readyMs,interactionMs:r.interactionMs,bytes:r.resources.reduce((s,r)=>s+r.bytes,0),requests:r.resources.length,apiRequests:r.apiRequests,dom:r.dom,heap:r.heap,active:r.active})),null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
