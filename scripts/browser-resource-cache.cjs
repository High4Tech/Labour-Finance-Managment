/* Read-only regression for a pre-consolidation Page script in browser storage. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),site=process.argv[2]||'qa.localhost';assert(['qa.localhost','high4tech-events-fd166a217c.localhost'].includes(site));
 const base='http://'+site+':8000',pwd=fs.readFileSync(path.join(root,'.env'),'utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim(),browser=await chromium.launch({channel:'chrome',headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));
 const app=page.locator('.page-container:visible .pp-resource-page[data-ready=true]'),sidebar=title=>page.locator('.body-sidebar a').filter({hasText:new RegExp('^\\s*'+title+'\\s*$')});
 try{
  await page.goto(base+'/login');await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),pwd);
  await page.goto(base+'/desk/pp-inventory?view=warehouses');await app.waitFor();
  await page.evaluate(()=>{
   const docs=JSON.parse(localStorage['_page:pp-inventory']);const cachedPage=docs.find(d=>d.name==='pp-inventory');
   cachedPage.script="frappe.pages['pp-inventory'].on_page_load=function(wrapper){frappe.ui.make_app_page({parent:wrapper,title:'Warehouse availability',single_column:true});plus_point.load_inventory(wrapper);};";
   localStorage['_page:pp-inventory']=JSON.stringify(docs);localStorage['pp-cache-regression-preference']='preserved';
  });
  await page.goto(base+'/desk/employee');await sidebar('Warehouses').waitFor();
  assert.equal(await page.evaluate(()=>localStorage.getItem('_page:pp-inventory')),null,'Old warehouse Page cache must be invalidated on boot');
  assert.equal(await page.evaluate(()=>localStorage.getItem('pp-cache-regression-preference')),'preserved');
  for(const title of ['Warehouses','Vehicles','Warehouses','Vehicles']){
   await sidebar(title).click();await app.waitFor();await app.getByRole('columnheader',{name:title==='Warehouses'?'Warehouse':'Vehicle',exact:true}).waitFor();
   const button=page.locator('.page-container:visible .primary-action');await button.click();await page.locator('.modal:visible').last().getByRole('heading',{name:title==='Warehouses'?'Add warehouse':'Add event vehicle',exact:true}).waitFor();await page.locator('.modal:visible .btn-modal-close').last().click();await page.locator('.modal:visible').waitFor({state:'hidden'});
  }
  assert(await page.evaluate(()=>JSON.parse(localStorage['_page:pp-inventory']).some(d=>String(d.script).includes('plus_point.mount_resource_page'))));
  assert.deepEqual(errors,[]);console.log('PASS stale warehouse Page cache is replaced, unrelated preferences survive, warehouse/vehicle sidebar switching and Add forms work: '+site);
 }finally{await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});

