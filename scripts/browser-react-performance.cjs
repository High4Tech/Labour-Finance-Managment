/* Read-only route, lifecycle and resource measurements. No posting interception or synthetic data. */
const fs=require('fs'),assert=require('node:assert/strict'),{chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[],nativeQueries=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('frappe.desk.reportview.get')){try{const body=r.postDataJSON();if(['PP Contract Terms','PP Event Plan','PP Wage Settlement','Employee','Customer'].includes(body?.doctype))nativeQueries.push(body.doctype);}catch{}}});
 try{
  const origin='http://high4tech-events-fd166a217c.localhost:8000';await page.goto(origin+'/login');await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim());
  const start=Date.now();await page.goto(origin+'/desk/pp-wage-settlement',{waitUntil:'commit',timeout:90000});await page.waitForSelector('[data-pp-react-root=payments] [data-rows] table');const coldReadyMs=Date.now()-start;
  const routes=[['PP Contract Terms','planning'],['PP Event Plan','planning'],['Employee','workers'],['Customer','clients'],['PP Wage Settlement','payments']];
  const visit=async([doctype,owner])=>{const start=Date.now();await page.evaluate(doctype=>frappe.set_route('List',doctype,'List'),doctype);await page.waitForSelector('[data-pp-react-root='+owner+'] tbody a,[data-pp-react-root='+owner+'] tbody .pp-empty-state');await page.waitForFunction(owner=>{const root=document.querySelector('[data-pp-react-root='+owner+']');return root&&!root.querySelector('[aria-busy=true]');},owner);assert.equal(await page.evaluate(()=>plus_point.react_ui.stats.activeRoots),1);return Date.now()-start;};
  for(const route of routes)await visit(route);
  const cdp=await page.context().newCDPSession(page),snapshot=async()=>{await cdp.send('HeapProfiler.collectGarbage');const metrics=await cdp.send('Performance.getMetrics');return page.evaluate(metrics=>({nodes:document.querySelectorAll('*').length,listListeners:frappe.realtime.socket.listeners('list_update').length,roots:plus_point.react_ui.stats.activeRoots,heapBytes:metrics.metrics.find(m=>m.name==='JSHeapUsedSize')?.value??performance.memory?.usedJSHeapSize}),metrics);};
  const before=await snapshot(),times=[];for(let i=0;i<4;i++)for(const route of routes)times.push({doctype:route[0],ms:await visit(route)});const after=await snapshot();
  assert.equal(after.roots,1);assert.equal(after.listListeners,before.listListeners);assert(after.nodes<=before.nodes+30,JSON.stringify({before,after}));assert.equal(nativeQueries.length,0);assert.deepEqual(errors,[]);
  const assets=await page.evaluate(()=>performance.getEntriesByType('resource').filter(r=>/\.(js|css)(\?|$)/.test(r.name)).reduce((n,r)=>n+r.decodedBodySize,0));
  const result={coldReadyMs,decodedAssets:assets,before,after,warmRoutes:times,medianWarmMs:times.map(t=>t.ms).sort((a,b)=>a-b)[Math.floor(times.length/2)],duplicateNativeQueries:nativeQueries.length,errors};fs.mkdirSync('.local/qa/react-performance',{recursive:true});fs.writeFileSync('.local/qa/react-performance/report.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
