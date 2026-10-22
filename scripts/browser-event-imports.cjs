/* All template downloads; actual event/client creation, consent, replay and mobile. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1320,height:1000}}),errors=[];
 page.setDefaultTimeout(30000);page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
  await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});
  await page.locator('.pp-onboarding-shell[data-ready=true]').waitFor({timeout:60000});
  await page.evaluate(company=>plus_point.open_import(company,()=>{},'events'),data.company);
  const dialog=page.locator('.pp-import-dialog:visible');await dialog.waitFor();
  await page.waitForFunction(()=>window.cur_dialog?.display&&cur_dialog.$wrapper.hasClass('pp-import-dialog'));
  const kinds=['employees','work','milestones','expenses','invoices','receipts','worker_payments','clients','event_sites','events','vehicles','inventory_items','warehouses','stock_balances'],headers={};
  for(const kind of kinds){
   await page.evaluate(async kind=>{await cur_dialog.set_value('kind',kind);},kind);
   const download=page.waitForEvent('download');await dialog.getByRole('button',{name:'Download template',exact:true}).click();const file=await download;
   assert.equal(file.suggestedFilename(),`plus-point-${kind}.csv`);
   headers[kind]=fs.readFileSync(await file.path(),'utf8').replace(/^\ufeff/,'').trim().split(',');
   assert.equal(headers[kind][0],'external_id');assert.equal(new Set(headers[kind]).size,headers[kind].length);
  }
  assert(headers.events.includes('client_contact_name'));assert(headers.clients.includes('country'));assert(headers.employees.includes('passport_number'));
  await page.evaluate(async()=>{await cur_dialog.set_value('kind','events');});
  const day=new Date();day.setUTCDate(day.getUTCDate()+2);const first=day.toISOString().slice(0,10);day.setUTCDate(day.getUTCDate()+1);const last=day.toISOString().slice(0,10);
  const rows=[0,1].map(i=>({external_id:`EVT-${run}-${i}`,event_name:`${data.prefix} event ${i}`,customer:data.prefix+' Client',start_date:first,end_date:last,site_name:'Exhibition Hall',workers_per_day:'2',billing_model:'Daily',fixed_amount:'0',wage_rate:'100',client_rate:'150',agreement:'Event staffing agreement',customer_type:'Company',client_contact_name:'Ayesha Malik',client_email:'client@example.invalid',client_phone:'+966501234567',client_country:'Saudi Arabia',client_address_line1:'12 Exhibition Road',client_city:'Riyadh',client_default_currency:'USD'}));
  const csv=cell=>'"'+String(cell??'').replaceAll('"','""')+'"';
  const content=[headers.events.join(','),...rows.map(row=>headers.events.map(k=>csv(row[k])).join(','))].join('\n');
  const file={name:'event-plans.csv',mimeType:'text/csv',buffer:Buffer.from(content)};
  await dialog.locator('input[type=file]').setInputFiles(file);await dialog.getByRole('button',{name:'Review file',exact:true}).click();
  await dialog.getByText('Review before saving',{exact:true}).waitFor();assert.match(await dialog.locator('.pp-import-preview').innerText(),/2 create/);
  assert.match(await dialog.locator('.pp-import-preview').innerText(),/Create client: .* with contact and address/);
  const count=()=>page.evaluate(async company=>(await frappe.db.get_list('Project',{filters:{company},fields:['name'],limit:100})).length,data.company);
  assert.equal(await count(),0);
  const primary=dialog.getByRole('button',{name:'Import records',exact:true}),check=dialog.locator('.modal-footer input[data-fieldname=confirmed]');
  assert(await primary.isDisabled());assert.equal(await page.locator('.modal:visible').count(),1);
  await page.screenshot({path:path.join(out,'event-import-review-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});assert(await check.isVisible());assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert(await primary.evaluate(el=>{const r=el.getBoundingClientRect();return r.right<=innerWidth&&r.bottom<=innerHeight;}));
  await page.screenshot({path:path.join(out,'event-import-review-mobile.png'),fullPage:true});
  await check.check();await primary.click();await dialog.getByText('Import saved',{exact:true}).waitFor();
  assert.match(await dialog.locator('.pp-condition-success').innerText(),/2 created, 0 updated, 0 skipped/);assert.equal(await count(),2);
  const clients=await page.evaluate(async customer=>await frappe.db.get_list('Customer',{filters:{customer_name:customer},fields:['name','customer_primary_contact','customer_primary_address','default_currency'],limit:10}),data.prefix+' Client');
  assert.equal(clients.length,1);assert(clients[0].customer_primary_contact);assert(clients[0].customer_primary_address);assert.equal(clients[0].default_currency,'USD');
  await dialog.getByRole('button',{name:'Import another file',exact:true}).click();await dialog.locator('input[type=file]').setInputFiles(file);await dialog.getByRole('button',{name:'Review file',exact:true}).click();
  await dialog.getByText('Review before saving',{exact:true}).waitFor();assert.match(await dialog.locator('.pp-import-preview').innerText(),/2 skip/);await check.check();await primary.click();
  await dialog.getByText('Import saved',{exact:true}).waitFor();assert.equal(await count(),2);assert.deepEqual(errors,[]);
  console.log('PASS all 14 template downloads, full new client details, preview without writes, one visible dialog, mobile consent, two saved event plans sharing one client and duplicate-free replay');
 }catch(error){await page.screenshot({path:path.join(out,'event-import-failure.png'),fullPage:true});throw error;}
 finally{await browser.close();assert(fixture('end').restored);console.log('PASS exact disposable event plans, client/contact/address, receipts and workspace settings restored');}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
