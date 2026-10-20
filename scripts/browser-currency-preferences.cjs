/* Country suggestions, explicit currency overrides and the client-invoice rate screen. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1320,height:1000}}),errors=[];
 const countryRequests=[];page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('plus_point.locations.country_defaults'))countryRequests.push(r.postData());});
 try{
  await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
  await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});
  const root=page.locator('.pp-onboarding-shell'),step=name=>page.locator(`.pp-onboarding-shell[data-ready=true][data-step=${name}]`).waitFor({timeout:60000});
  const values=v=>page.evaluate(async v=>{for(const [key,value] of Object.entries(v))await frappe.container.page.pp_setup_form.set_value(key,value);},v);
  const get=key=>page.evaluate(key=>frappe.container.page.pp_setup_form.get_value(key),key),save=()=>root.locator('.pp-onboarding-save').click();
  const rpc=(method,args={})=>page.evaluate(async({method,args})=>plus_point.setup_rpc(method,args),{method,args});
  await step('company');await values({country:'Saudi Arabia'});await page.waitForFunction(()=>frappe.container.page.pp_setup_form.get_value('currency')==='SAR');
  assert(await root.locator('[data-fieldname=currency] input').isEditable());await values({currency:'USD'});await save();await step('client');
  let state=await rpc('plus_point.event_setup.status');assert.equal(state.companies[0].default_currency,'USD');assert.equal(state.companies[0].pp_invoice_currency,'USD');
  await values({customer_name:data.prefix+' Client',contact_name:'Ayesha Malik',email:'ayesha@example.invalid',country:'United Arab Emirates',city:'Dubai',address_line1:'12 Exhibition Road'});
  await page.waitForFunction(()=>frappe.container.page.pp_setup_form.get_value('default_currency')==='AED');await values({default_currency:'USD'});
  await page.screenshot({path:path.join(out,'currency-uae-client-usd.png'),fullPage:true});await save();await step('event');
  const client=(await rpc('plus_point.event_setup.status')).state.customer;assert.equal((await rpc('plus_point.clients.details',{customer:client})).default_currency,'USD');
  await root.locator('.pp-onboarding-step[data-step=client]').click();await step('client');assert.equal(await get('default_currency'),'USD');
  const dates=await page.evaluate(()=>({start:frappe.datetime.add_days(frappe.datetime.get_today(),2),end:frappe.datetime.add_days(frappe.datetime.get_today(),4)}));
  const event=await rpc('plus_point.events.create_event',{company:data.company,customer:client,event_name:data.prefix+' Currency',start_date:dates.start,end_date:dates.end,agreement:'Currency QA agreement',billing_model:'Daily',wage_rate:10,client_rate:20,sites:JSON.stringify([{site_name:'Dubai QA hall',phase:'Event',start_date:dates.start,end_date:dates.end,workers_required:1}])});
  await page.route('**/api/method/plus_point.billing.quote',route=>{const args=route.request().postDataJSON();return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({message:{rate:args.currency==='USD'?'1':'1.1',currency:args.currency,base_currency:'USD',as_of:Math.floor(Date.now()/1000)}})});});
  await page.evaluate(name=>frappe.set_route('Form','PP Contract Terms',name),event.contract_terms);await page.getByRole('button',{name:'Prepare client invoice',exact:true}).click();
  const dialog=page.locator('.modal:visible');await dialog.getByText('Client invoice currency',{exact:true}).waitFor();
  await page.waitForFunction(()=>window.cur_dialog?.get_value('exchange_rate')===1);assert.equal(await page.evaluate(()=>cur_dialog.get_value('invoice_currency')),'USD');
  assert(await dialog.locator('[data-fieldname=invoice_currency] input').isEditable());await page.evaluate(()=>cur_dialog.set_value('invoice_currency','EUR'));await page.waitForFunction(()=>cur_dialog.get_value('exchange_rate')===1.1);
  await page.evaluate(()=>cur_dialog.set_value('exchange_rate',1.2));assert.equal(await page.evaluate(()=>cur_dialog.get_value('exchange_rate')),1.2);
  await dialog.getByRole('button',{name:'Create draft invoice',exact:true}).click();await dialog.getByText('Choose a service item, currency and positive exchange rate.',{exact:true}).waitFor();assert.equal(await page.locator('.modal:visible').count(),1);
  await page.screenshot({path:path.join(out,'invoice-currency-rate.png'),fullPage:true});await page.evaluate(()=>cur_dialog.hide());await dialog.waitFor({state:'hidden'});
  await page.evaluate(()=>frappe.set_route('pp-onboarding'));await step('client');await root.locator('.pp-onboarding-step[data-step=company]').click();await step('company');
  await values({country:'United Arab Emirates'});await page.waitForFunction(()=>frappe.container.page.pp_setup_form.get_value('currency')==='AED');await values({currency:'GBP'});await save();await step('client');
  state=await rpc('plus_point.event_setup.status');assert.equal(state.companies[0].country,'United Arab Emirates');assert.equal(state.companies[0].default_currency,'USD');assert.equal(state.companies[0].pp_invoice_currency,'GBP');
  assert.equal((await rpc('plus_point.clients.details',{customer:client})).default_currency,'USD');assert.deepEqual(errors,[]);
  console.log('PASS Saudi→SAR suggestion, enabled USD override, UAE client→AED suggestion with saved USD override, existing-client override retention, invoice currency/rate edit, inline validation and future-currency changes without rewriting accounting base');
 }catch(error){await page.screenshot({path:path.join(out,'currency-preferences-failure.png'),fullPage:true});console.error(JSON.stringify({errors,countryRequests}));throw error;}
 finally{await browser.close();assert(fixture('end').restored);console.log('PASS exact currency settings and QA business records restored');}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
