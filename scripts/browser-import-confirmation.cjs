/* Exercise real import consent, inline failures, native saves and idempotent replay. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const run=crypto.randomBytes(6).toString('hex'),fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({headless:true,channel:'msedge'}),page=await browser.newPage({viewport:{width:1320,height:900}}),errors=[];
 page.setDefaultTimeout(30000);page.on('pageerror',error=>errors.push(error.message));
 try{
  await page.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');
  await page.goto('http://qa.localhost:8000/desk/plus-point',{waitUntil:'domcontentloaded'});
  await page.locator('.pp-onboarding-shell[data-ready=true]').waitFor({timeout:60000});
  await page.evaluate(company=>plus_point.open_import(company,()=>{},'employees'),data.company);
  const dialog=page.locator('.pp-import-dialog:visible'),primary=dialog.getByRole('button',{name:/^(Review file(?: again)?|Import employees|Import another file)$/}),check=dialog.locator('.modal-footer input[data-fieldname=confirmed]');
  const oneModal=async()=>assert.equal(await page.locator('.modal:visible').count(),1,'Only the import dialog may be open');
  await dialog.getByRole('button',{name:'Review file',exact:true}).click();await dialog.locator('.pp-import-feedback').filter({hasText:'Choose a CSV or XLSX file first.'}).waitFor();await oneModal();
  await dialog.locator('input[type=file]').setInputFiles({name:'bad.csv',mimeType:'text/csv',buffer:Buffer.from('wrong,headers\ninvalid,row')});
  await dialog.getByRole('button',{name:'Review file',exact:true}).click();await dialog.locator('.pp-import-feedback').filter({hasText:'Column headers must match'}).waitFor();await oneModal();
  const columns=['external_id','employee','first_name','last_name','gender','date_of_birth','date_of_joining','cell_number','status'];
  const content=[columns.join(','),...Array.from({length:15},(_,i)=>['UX-'+run+'-'+i,'Import UX QA '+run+' '+i,'Import UX QA '+run,String(i),'Male','1990-01-01','2020-01-01','','Active'].join(','))].join('\n');
  const file={name:'workers.csv',mimeType:'text/csv',buffer:Buffer.from(content)};
  await dialog.locator('input[type=file]').setInputFiles(file);await dialog.getByRole('button',{name:'Review file',exact:true}).click();
  await dialog.getByText('Review before saving',{exact:true}).waitFor();assert.match(await dialog.locator('.pp-import-preview').innerText(),/15 create/);
  assert(await primary.isDisabled());assert(await check.isVisible());await dialog.getByText('Tick the review box to enable import.',{exact:true}).waitFor();await oneModal();
  await dialog.locator('.modal-body').evaluate(el=>el.scrollTop=0);
  assert(await check.isVisible());await page.screenshot({path:path.join(out,'import-confirmation-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await check.evaluate(el=>{const r=el.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight;}));
  assert(await primary.evaluate(el=>{const r=el.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth&&r.bottom<=innerHeight;}));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,'import-confirmation-mobile.png'),fullPage:true});
  await check.check();assert(await primary.isEnabled());
  await page.route('**/api/method/plus_point.imports.apply',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({_server_messages:JSON.stringify([JSON.stringify({message:'Temporary test connection failure. Review the file again.'})])})}));
  await primary.click();await dialog.locator('.pp-import-feedback').filter({hasText:'Temporary test connection failure.'}).waitFor();await oneModal();
  await page.unroute('**/api/method/plus_point.imports.apply');
  await dialog.getByRole('button',{name:'Review file again',exact:true}).click();await dialog.getByText('Review before saving',{exact:true}).waitFor();
  assert(await primary.isDisabled());assert.equal(await check.isChecked(),false);await check.check();await primary.click();
  await dialog.getByText('Import saved',{exact:true}).waitFor();assert.match(await dialog.locator('.pp-condition-success').innerText(),/15 created, 0 updated, 0 skipped/);await oneModal();
  const count=()=>page.evaluate(async company=>(await frappe.db.get_list('Employee',{filters:{company},fields:['name'],limit:100})).length,data.company);
  assert.equal(await count(),16);
  await primary.click();await dialog.locator('input[type=file]').setInputFiles(file);await dialog.getByRole('button',{name:'Review file',exact:true}).click();
  await dialog.getByText('Review before saving',{exact:true}).waitFor();assert.match(await dialog.locator('.pp-import-preview').innerText(),/15 skip/);assert(await primary.isDisabled());
  await check.check();await primary.click();await dialog.getByText('Import saved',{exact:true}).waitFor();assert.match(await dialog.locator('.pp-condition-success').innerText(),/0 created, 0 updated, 15 skipped/);
  assert.equal(await count(),16);assert.deepEqual(errors,[]);
  console.log('PASS one import dialog, inline file/server errors, persistent footer consent, disabled-until-reviewed action, mobile fit, actual 15-worker save and duplicate-free replay');
 }catch(error){await page.screenshot({path:path.join(out,'import-confirmation-failure.png'),fullPage:true});throw error;}
 finally{await browser.close();assert(fixture('end').restored);console.log('PASS exact disposable import receipts, employees and workspace settings restored');}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
