/* Read-only, same live company: previous native renderer vs current ECharts.
 * Baseline source is served only into isolated browser contexts, never deployed. */
const fs=require('fs'),path=require('path'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const root=path.resolve(__dirname,'..'),out=path.join(root,'.local/qa'),base=process.env.PP_BASELINE_REF||'39e7e484afd3859642eb3045f6999e1cee47c94a',origin='http://high4tech-events-fd166a217c.localhost:8000',results=[];
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{for(const phase of ['before','after'])for(let run=0;run<2;run++){
  const context=await browser.newContext({viewport:{width:1600,height:1200}}),page=await context.newPage();page.setDefaultTimeout(90000);const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/api/method/frappe.utils.change_log.show_update_popup*',r=>r.fulfill({contentType:'application/json',body:'{"message":null}'}));
  if(phase==='before')for(const file of ['js/lazy_features.js','js/dashboard_analytics.js','css/dashboard_analytics.css',...(process.env.PP_BASELINE_REF?['js/charts.js','css/charts.css','js/ui_components.js','css/ui_components.css','js/operations.js','css/operations.css','js/agreement_profile.js','css/agreement_profile.css','js/agreement_share.js','js/event_profile.js']:[])]){const body=execFileSync('git',['show',base+':apps/plus_point/plus_point/public/'+file],{cwd:root,encoding:'utf8'});await page.route('**/assets/plus_point/'+file+'*',r=>r.fulfill({contentType:file.endsWith('.css')?'text/css':'application/javascript',body}));}
  await page.goto(origin+'/login',{waitUntil:'domcontentloaded'});await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),fs.readFileSync(path.join(root,'.env'),'utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim());
  const start=Date.now();await page.goto(origin+'/desk/plus-point',{waitUntil:'domcontentloaded'});await page.locator('.pp-dashboard[data-analytics-ready=true]').waitFor();await page.locator('[data-chart=work] svg').waitFor();const readyMs=Date.now()-start;
  const sample=await page.evaluate(()=>({resources:performance.getEntriesByType('resource').filter(r=>/\.(js|css)(\?|$)/.test(r.name)).map(r=>({name:new URL(r.name).pathname,bytes:r.encodedBodySize})),dom:document.querySelectorAll('*').length,heap:performance.memory?.usedJSHeapSize,active:plus_point.dashboard_chart_stats.active,kpis:[...document.querySelectorAll('.pp-kpi-value')].map(n=>n.textContent)}));
  const periodStart=Date.now();await page.getByRole('combobox',{name:'Chart period',exact:true}).click();await page.getByRole('option',{name:'Last 3 months',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('[data-chart=work]').hasAttribute('aria-busy'));const periodMs=Date.now()-periodStart;
  await page.evaluate(()=>frappe.set_route('List','Employee','List'));await page.locator('.page-container:visible .list-row-head').waitFor();assert.equal(await page.evaluate(()=>plus_point.dashboard_chart_stats.active),0);assert.deepEqual(errors,[]);
  results.push({phase,run,readyMs,periodMs,...sample,errors});await context.close();
 }
 assert.deepEqual(results[0].kpis,results[2].kpis);fs.writeFileSync(path.join(out,process.env.PP_PERF_REPORT||'chart-performance.json'),JSON.stringify(results,null,2));
 console.log(JSON.stringify(results.map(r=>({phase:r.phase,run:r.run,readyMs:r.readyMs,periodMs:r.periodMs,bytes:r.resources.reduce((s,r)=>s+r.bytes,0),requests:r.resources.length,dom:r.dom,heap:r.heap,active:r.active})),null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
