/* Actual customer-side roster, attendance approval, finances and worker dashboard. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.hierarchy_browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];let originalTheme;
 page.setDefaultTimeout(60000);page.setDefaultNavigationTimeout(60000);page.on('pageerror',error=>errors.push(error.stack));
 const rpc=(method,args={})=>page.evaluate(({method,args})=>plus_point.form_rpc(method,args),{method,args});
 const native=(method,args={})=>page.evaluate(async({method,args})=>(await frappe.call({method,type:'POST',args})).message,{method,args});
 const summary=project=>rpc('api.project_summary',{project});
 const waitSave=async(button,approve)=>{const response=page.waitForResponse(r=>r.url().endsWith('/plus_point.attendance.save_marks')&&JSON.parse(r.request().postData()||'{}').approve===(approve?1:0));await button.click();const result=await(await response).json();assert(!result.exc_type,JSON.stringify(result));return result.message;};
 try{
  await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
  await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});await page.locator('.pp-onboarding-shell[data-ready=true]').waitFor({timeout:60000});
  originalTheme=await page.evaluate(()=>document.documentElement.dataset.themeMode);
  await page.getByRole('button',{name:'Skip onboarding',exact:true}).click();await page.locator('.pp-dashboard[data-ready=true]').waitFor();
  const role=(await rpc('operations.create_category',{title:'QA role '+run})).name;
  await native('frappe.client.set_value',{doctype:'Employee',name:data.worker,fieldname:'designation',value:role});
  await page.evaluate(()=>frappe.set_route('pp-agreements',{record:'new'}));
  const app=page.locator('.page-container:visible .pp-operations[data-ready=true]');await app.waitFor();
  const fill=async(selector,fields)=>page.evaluate(async({selector,fields})=>{const form=document.querySelector(selector).pp_form;for(const [key,value] of Object.entries(fields))await form.set_value(key,value);},{selector,fields});
  await fill('.pp-op-client-choice',{client_mode:'Add new client'});await page.waitForTimeout(250);
  await fill('.pp-op-client-fields',{customer_name:data.prefix+' Client',customer_type:'Company',contact_name:'Ayesha Malik',email:'client@example.invalid',country:'Pakistan',city:'Karachi',address_line1:'12 Festival Road'});
  const day=await page.evaluate(()=>frappe.datetime.get_today()),end=await page.evaluate(()=>frappe.datetime.add_days(frappe.datetime.get_today(),3));
  await fill('.pp-op-terms',{agreement_title:data.prefix+' Festival agreement',effective_start:day,effective_end:end,billing_model:'Fixed',fixed_amount:10000,scope:'Setup, stage operations and pack down',auto_invoice:1});
  await page.evaluate(({role,day,end})=>{const form=document.querySelector('.pp-op-staffing').pp_form;form.fields_dict.staffing.df.data=[{site_name:'Main stage',designation:role,start_date:day,end_date:end,workers_required:1,wage_rate:1000,client_rate:0,phase:'Event',country:'Pakistan',city:'Karachi',address_line1:'12 Festival Road'}];form.fields_dict.staffing.grid.refresh();},{role,day,end});
  await app.getByRole('button',{name:'Save agreement',exact:true}).click();await app.getByRole('heading',{name:data.prefix+' Festival agreement',exact:true}).waitFor();
  let catalogue=await rpc('operations.catalogue');const agreement=catalogue.agreements.find(r=>r.title===data.prefix+' Festival agreement');assert(agreement);
  assert.equal(await app.locator('.pp-op-index').count(),0);
  assert.equal(await app.locator('.pp-op-client-fields .frappe-control[data-fieldname=country]').count(),1);
  await app.locator('summary').getByText('Agreement and billing',{exact:true}).click();await app.getByText('Fixed contract value (PKR)',{exact:true}).waitFor();
  const groups=await page.evaluate(()=>frappe.boot.plus_point.navigation.items);assert(!groups.some(r=>['Event sites','Assign workers','Clients','Event projects','Client invoices','Fixed milestones','Your company'].includes(r.label)));
  await app.locator('.pp-op-comment').fill('Agreement & venue reviewed');await app.getByRole('button',{name:'Post comment',exact:true}).click();await app.locator('.pp-op-comment-list').getByText('Agreement & venue reviewed',{exact:true}).waitFor();
  await page.screenshot({path:path.join(out,'hierarchy-agreement-desktop.png'),fullPage:true});
  await app.getByRole('link',{name:'Plan this event',exact:true}).click();await app.getByRole('button',{name:'Create event plan',exact:true}).waitFor();
  await fill('.pp-op-new-plan',{event_name:data.prefix+' Festival'});await app.getByRole('button',{name:'Create event plan',exact:true}).click();await app.getByRole('heading',{name:data.prefix+' Festival',exact:true}).first().waitFor();
  catalogue=await rpc('operations.catalogue');const plan=catalogue.plans.find(r=>r.contract_terms===agreement.name);assert(plan);
  await app.getByRole('button',{name:'Auto-select available crew',exact:true}).click();await app.getByText('1 workers assigned.',{exact:true}).waitFor();await app.locator('summary').getByText('Assigned workers',{exact:true}).click();await app.getByRole('link',{name:'Sana Browser QA',exact:true}).waitFor();assert.equal((await rpc('operations.plan',{name:plan.name})).allocations.length,1);
  await app.getByRole('button',{name:'Choose workers',exact:true}).click();await app.locator('.pp-op-crew-options').waitFor();assert(await app.locator('.pp-op-crew-options input[type=checkbox]').isDisabled());assert(await app.locator('.pp-op-crew-options input[type=checkbox]').isChecked());await app.getByText('Assigned to this site',{exact:true}).waitFor();await app.getByRole('button',{name:'Close',exact:true}).click();
  await app.getByRole('button',{name:'Adjust headcount',exact:true}).click();await fill('.pp-op-headcount-form',{workers_required:2});await app.getByRole('button',{name:'Save planned headcount',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('.pp-op-headcount-form'));await app.locator('summary').getByText('Crew coverage',{exact:true}).click();await app.getByText('Planned extra: 1; missing: 1',{exact:true}).waitFor();await app.locator('summary').getByText('Assigned workers',{exact:true}).click();
  await page.screenshot({path:path.join(out,'hierarchy-event-desktop.png'),fullPage:true});
  await app.getByRole('button',{name:'Move or unassign',exact:true}).click();await app.getByRole('button',{name:'Save allocation change',exact:true}).click();await app.getByText('Choose the destination event, site and through date before moving this worker.',{exact:true}).waitFor();
  await fill('.pp-op-transfer-fields',{action:'Unassign',effective_date:await page.evaluate(()=>frappe.datetime.add_days(frappe.datetime.get_today(),1))});await app.getByRole('button',{name:'Save allocation change',exact:true}).click();await app.getByText('Worker allocation updated. Recorded wages were preserved.',{exact:true}).waitFor();
  assert.equal(String((await rpc('operations.plan',{name:plan.name})).allocations[0].end_date),day);
  await app.locator('summary').getByText('Assigned workers',{exact:true}).click();
  await app.getByRole('link',{name:'Sana Browser QA',exact:true}).click();const profile=page.locator('.pp-worker-profile[data-ready=true]');await profile.waitFor();await profile.getByText('Assigned',{exact:true}).waitFor();await profile.getByRole('button',{name:'Add photo',exact:true}).waitFor();assert.equal(await profile.getByText('Company',{exact:true}).count(),0);
  const uploaded=await page.evaluate(async employee=>{const bytes=Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jM90AAAAASUVORK5CYII='),c=>c.charCodeAt(0)),form=new FormData();form.append('file',new Blob([bytes],{type:'image/png'}),'worker-photo.png');form.append('doctype','Employee');form.append('docname',employee);form.append('is_private','1');const response=await fetch('/api/method/upload_file',{method:'POST',headers:{'X-Frappe-CSRF-Token':frappe.csrf_token},body:form});return (await response.json()).message;},data.worker);assert(uploaded?.file_url);
  await rpc('operations.set_photo',{employee:data.worker,file_url:uploaded.file_url});await page.evaluate(()=>cur_frm.reload_doc());await profile.getByRole('button',{name:'Update photo',exact:true}).waitFor();assert.equal(await profile.locator('.pp-worker-avatar img').count(),1);
  await page.waitForFunction(()=>document.querySelector('.pp-record-activity .form-footer'));
  assert(await page.evaluate(()=>{const rail=document.querySelector('.pp-record-rail').getBoundingClientRect(),main=document.querySelector('.pp-worker-profile').getBoundingClientRect();return rail.x>=main.right-5;}));
  const comment='Crew briefing checked '+run;
  const editable=page.locator('.pp-record-activity [contenteditable=true]').first();await editable.fill(comment);
  const posted=page.waitForResponse(r=>r.url().includes('frappe.desk.form.utils.add_comment'));await page.locator('.pp-record-activity').getByRole('button',{name:'Comment',exact:true}).click();assert((await(await posted).json()).message);assert.equal((await native('frappe.client.get_list',{doctype:'Comment',filters:{reference_doctype:'Employee',reference_name:data.worker,content:['like','%'+run+'%']},fields:['name']})).length,1);
  await page.screenshot({path:path.join(out,'hierarchy-worker-rail-desktop.png'),fullPage:true});
  await page.evaluate(()=>plus_point.set_theme('dark'));await page.setViewportSize({width:390,height:844});await page.waitForTimeout(300);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(out,'hierarchy-worker-mobile.png'),fullPage:true});
  await page.setViewportSize({width:1440,height:1100});await page.evaluate(company=>frappe.set_route('List','Employee',{company}),data.company);await page.waitForFunction(worker=>window.cur_list?.__pp_states?.[worker]==='Assigned',data.worker);await page.locator('.list-row-container').getByText('Assigned',{exact:true}).first().waitFor();
  // Reproduce the reported cross-page ID leak, then use the actual list entry.
  for(const mode of ['pp-agreements','pp-event-plans','pp-client-billing']){
   await page.evaluate(({mode,record})=>{if(mode==='pp-agreements')frappe.route_options={record};return frappe.set_route(mode);},{mode,record:plan.name});
   await page.waitForFunction(mode=>frappe.get_route()[0]===mode&&[...document.querySelectorAll('.pp-operations[data-ready=true]')].some(root=>root.getClientRects().length&&root.querySelector('[data-list-record]')),mode);await app.locator('.pp-op-search').waitFor();assert.equal(await app.locator('.pp-op-index').count(),0);assert.equal(await app.locator('[data-list-record]').count(),1);assert.equal(await app.locator('.pp-onboarding-errors:visible').count(),0);
  }
  await page.evaluate(record=>frappe.set_route('pp-client-billing',{record}),plan.name);await app.getByText('That record is no longer available in this section. Choose a record from the list.',{exact:true}).waitFor();
  await app.getByRole('link',{name:'Open',exact:true}).click();await app.getByRole('button',{name:'Add milestone',exact:true}).waitFor();
  await app.getByRole('button',{name:'Add milestone',exact:true}).click();await fill('.pp-op-milestone-fields',{milestone_title:'Stage setup accepted',due_date:day,amount:2000,status:'Approved'});await app.getByRole('button',{name:'Save milestone',exact:true}).click();
  await page.waitForFunction(()=>document.querySelectorAll('[data-review-invoice]').length===1);let bill=await rpc('operations.billing',{contract_terms:agreement.name});assert.equal(bill.invoices.length,1);assert.equal(bill.invoices[0].docstatus,0);assert.equal(Number(bill.invoices[0].grand_total),2000);
  await app.getByRole('button',{name:'Review invoice',exact:true}).click();await app.getByRole('link',{name:'Download PDF',exact:true}).waitFor();
  const pdfPath=await app.getByRole('link',{name:'Download PDF',exact:true}).getAttribute('href'),cookies=await page.context().cookies('http://qa.localhost:8000');let pdf;
  try{pdf=await page.request.get('http://127.0.0.1:8000'+pdfPath,{headers:{Host:'qa.localhost:8000',Cookie:cookies.map(r=>r.name+'='+r.value).join('; ')}});}catch{throw new Error('Local PDF request failed');}
  assert.equal(pdf.status(),200);assert.match(pdf.headers()['content-disposition'],/attachment/);assert.equal((await pdf.body()).subarray(0,4).toString(),'%PDF');

  await app.getByRole('button',{name:'Email invoice',exact:true}).click();await app.getByText('Connect an outgoing email account before sending invoices. The PDF is available to download.',{exact:true}).waitFor();
  await app.getByRole('button',{name:'Generate from approved work',exact:true}).click();await app.getByText('No approved items waiting for an invoice',{exact:true}).waitFor();
  await native('frappe.client.set_value',{doctype:'PP Contract Terms',name:agreement.name,fieldname:'auto_invoice',value:0});
  await app.getByRole('button',{name:'Add milestone',exact:true}).first().click();await fill('.pp-op-milestone-fields',{milestone_title:'Event delivery accepted',due_date:day,amount:1000,status:'Approved'});await app.getByRole('button',{name:'Save milestone',exact:true}).click();await app.getByText('Event delivery accepted',{exact:true}).waitFor();
  await app.getByRole('button',{name:'Generate from approved work',exact:true}).click();await app.getByRole('button',{name:'Create invoice draft',exact:true}).waitFor();assert.equal(await app.locator('[data-fieldname=item_code]').count(),0);await app.getByRole('button',{name:'Create invoice draft',exact:true}).click();await page.waitForFunction(()=>document.querySelectorAll('[data-review-invoice]').length===2);bill=await rpc('operations.billing',{contract_terms:agreement.name});assert.equal(bill.invoices.length,2);
  await page.screenshot({path:path.join(out,'hierarchy-billing-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(out,'hierarchy-billing-mobile.png'),fullPage:true});
  assert.deepEqual(errors,[]);console.log('PASS inline agreement/client/venue/category save, agreement-first event creation, automatic category crew allocation, merged sidebar, worker allocation/photo controls, right comments posting, PDF invoice download, automatic milestone draft, email configuration state and mobile dark layouts');
 }catch(error){await page.screenshot({path:path.join(out,'hierarchy-failure.png'),fullPage:true});console.error('PAGE ERRORS',errors);throw error;}
 finally{
  try{if(originalTheme)await page.evaluate(async value=>{await frappe.xcall('frappe.core.doctype.user.user.switch_theme',{theme:{light:'Light',dark:'Dark',automatic:'Automatic'}[value]});},originalTheme);}
  finally{await browser.close();assert(fixture('end').restored);console.log('PASS exact hierarchy QA records and workspace restored');}
 }
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
