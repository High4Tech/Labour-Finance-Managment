/* Reproduce unsigned-share deletion dead ends; isolated QA, no external email. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('node:assert/strict'),{execFileSync}=require('child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa'),pwd=fs.readFileSync(path.join(root,'.env'),'utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim(),run=crypto.randomBytes(6).toString('hex');
 fs.mkdirSync(out,{recursive:true});
 const fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.hierarchy_browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin');let browser,page;
 const rpc=(method,args)=>page.evaluate(({method,args})=>plus_point.form_rpc(method,args),{method,args});
 try{
  browser=await chromium.launch({channel:'msedge',headless:true});page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(35000);
  await page.goto('http://qa.localhost:8000/login');await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),pwd);await page.goto('http://qa.localhost:8000/desk/plus-point');await page.getByRole('button',{name:'Skip onboarding',exact:true}).click();await page.locator('.pp-dashboard[data-ready=true]').waitFor();
  const day=await page.evaluate(()=>frappe.datetime.get_today());const a=await rpc('operations.save_agreement',{values:{agreement_title:data.prefix+' Agreement',scope:'Unsigned deletion audit',client:{customer_name:data.prefix+' Client',contact_name:'QA Client',email:'qa@example.invalid',country:'Pakistan',city:'Karachi',address_line1:'12 QA Road'},billing_model:'Daily',agreement_currency:'PKR',effective_start:day,effective_end:day,status:'Draft',staffing:[{site_name:'QA hall',designation:'Event crew',phase:'Event',start_date:day,end_date:day,workers_required:1,wage_rate:100,client_rate:150}]}});
  assert.equal((await rpc('record_actions.review',{doctype:'PP Contract Terms',name:a.name})).blocked,'');await rpc('signing.create_link',{name:a.name});
  const pending=await rpc('record_actions.review',{doctype:'PP Contract Terms',name:a.name});await rpc('operations.save_agreement',{name:a.name,values:{scope:'Revoked unused signing link'}});const revoked=await rpc('record_actions.review',{doctype:'PP Contract Terms',name:a.name});
  assert.equal(revoked.dependency.doctype,'PP Agreement Share');assert(revoked.blocked);
  await page.evaluate(name=>frappe.set_route('pp-agreements',{record:name}),a.name);await page.locator('.pp-operations[data-ready=true]').waitFor();await page.locator('[data-delete-record]').click();const dialog=page.locator('.pp-delete-dialog:visible');await dialog.waitFor();assert(await dialog.getByRole('button',{name:'Cannot delete linked records',exact:true}).isDisabled());
  await page.screenshot({path:path.join(out,'audit-signing-delete-blocked.png'),fullPage:true});await dialog.locator('[data-delete-dependency]').click();await page.waitForURL(/\/desk\/plus-point(?:$|\?)/,{timeout:20000});
  const observation={id:'QA-01',severity:'P2',status:'confirmed',area:'Delete unused agreement after sharing',beforeSharingDeletable:true,pendingShareBlocks:!!pending.blocked,revokedShareBlocks:!!revoked.blocked,blockingType:revoked.dependency.doctype,dependencyLinkRedirectsHome:true,expected:'An unsigned revoked request should offer a usable cleanup action; the blocking-record link must not redirect home.',screenshot:'.local/qa/audit-signing-delete-blocked.png'};
  fs.writeFileSync(path.join(out,'full-audit-signing-deletion-20261023.json'),JSON.stringify(observation,null,2));console.log('CONFIRMED '+JSON.stringify(observation));
 }catch(error){if(page)await page.screenshot({path:path.join(out,'audit-signing-delete-probe-failure.png'),fullPage:true}).catch(()=>{});throw error;}
 finally{try{await browser?.close();}finally{assert(fixture('end').restored);console.log('PASS signing-delete QA fixture restored');}}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
