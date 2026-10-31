/* Same local company, isolated browser contexts; baseline assets never deployed. */
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{const root=path.resolve(__dirname,'..'),site='http://high4tech-events-fd166a217c.localhost:8000',base=process.env.PP_BASELINE_REF||'392e637',results=[];const browser=await chromium.launch({channel:'msedge',headless:true});
 try{for(const phase of ['before','after'])for(let run=0;run<2;run++){
  const context=await browser.newContext({viewport:{width:1440,height:1100}}),page=await context.newPage(),overrides=new Map(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/method/frappe.utils.change_log.show_update_popup*',r=>r.fulfill({contentType:'application/json',body:'{"message":null}'}));
  if(phase==='before'){
   for(const file of ['js/lazy_features.js','js/dashboard_analytics.js','css/dashboard_analytics.css','js/charts.js','js/ui_components.js','css/ui_components.css','js/experience.js','js/runtime.js']){const body=execFileSync('git',['show',base+':apps/plus_point/plus_point/public/'+file],{cwd:root,encoding:'utf8'});overrides.set('/assets/plus_point/'+file,Buffer.byteLength(body));await page.route('**/assets/plus_point/'+file+'*',r=>r.fulfill({contentType:file.endsWith('.css')?'text/css':'application/javascript',body}));}
   await page.route('**/assets/plus_point/css/brand.css*',r=>r.fulfill({contentType:'text/css',body:''}));
  }
  await page.goto(site+'/login');await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim());
  const start=Date.now();await page.goto(site+'/desk/plus-point');await page.waitForSelector('.pp-dashboard[data-analytics-ready=true]',{timeout:90000});await page.waitForFunction(()=>document.querySelector('.pp-dashboard').getAttribute('aria-busy')!=='true');const readyMs=Date.now()-start;
  const sample=await page.evaluate(()=>({resources:performance.getEntriesByType('resource').filter(r=>/\.(js|css)(\?|$)/.test(r.name)).map(r=>({name:new URL(r.name).pathname,bytes:r.encodedBodySize})),apiRequests:performance.getEntriesByType('resource').filter(r=>r.name.includes('/api/method/plus_point.dashboard')).length,dom:document.querySelectorAll('*').length,heap:performance.memory?.usedJSHeapSize,active:plus_point.charts.stats.active}));sample.resources=sample.resources.filter(r=>!(phase==='before'&&r.name.endsWith('/brand.css'))).map(r=>({...r,bytes:overrides.get(r.name)??r.bytes}));
  const began=Date.now();if(phase==='after'){await page.locator('[data-attendance-period="7"]').click();await page.waitForFunction(()=>!document.querySelector('.pp-overview').hasAttribute('aria-busy'));}else{await page.getByRole('combobox',{name:'Chart period',exact:true}).click();await page.getByRole('option',{name:'Last month',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('[data-chart=work]').hasAttribute('aria-busy'));}const interactionMs=Date.now()-began;
  await page.evaluate(()=>frappe.set_route('List','Employee'));await page.waitForFunction(()=>plus_point.charts.stats.active===0);assert.equal(errors.length,0,errors.join('\n'));
  const row={phase,run,readyMs,interactionMs,...sample,errors};results.push(row);await context.close();
 }
 fs.writeFileSync('.local/qa/overview-performance.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results.map(r=>({phase:r.phase,run:r.run,readyMs:r.readyMs,interactionMs:r.interactionMs,bytes:r.resources.reduce((s,r)=>s+r.bytes,0),requests:r.resources.length,apiRequests:r.apiRequests,dom:r.dom,heap:r.heap,active:r.active})),null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
