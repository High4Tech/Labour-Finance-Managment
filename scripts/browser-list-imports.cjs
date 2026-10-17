/* Read-only regression for imports on populated lists, refresh and mobile. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),base='http://demo.localhost:8000',out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 assert(process.env.PP_BROWSER_PASSWORD,'Set PP_BROWSER_PASSWORD for the local customer test account');
 const browser=await chromium.launch({headless:true,...(process.env.PP_BROWSER_CHANNEL?{channel:process.env.PP_BROWSER_CHANNEL}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(25000);
 const failures=[];page.on('pageerror',error=>failures.push(error.message));
 page.on('response',response=>{if(response.status()>=400)failures.push(`HTTP ${response.status()}`);});
 const mapping=[['employee','employees'],['pp-work-entry','work'],['pp-milestone','milestones'],['purchase-invoice','expenses'],['sales-invoice','invoices'],['payment-entry','receipts'],['pp-wage-settlement','worker_payments']];
 const header=()=>page.locator('.page-head:visible');
 const modal=()=>page.locator('.pp-import-dialog:visible');
 const shown=async()=>{await modal().waitFor();await page.waitForFunction(()=>window.cur_dialog?.display && cur_dialog.$wrapper.hasClass('pp-import-dialog'));};
 try{
  await page.goto(base+'/login',{waitUntil:'domcontentloaded'});
  assert.equal(await page.evaluate(async credentials=> (await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(credentials)})).json()).message,{usr:process.env.PP_BROWSER_USER||'example@email.com',pwd:process.env.PP_BROWSER_PASSWORD}),'Logged In');
  for(const [route,kind] of mapping){
   await page.goto(base+'/desk/plus-point/'+route,{waitUntil:'domcontentloaded'});
   const button=header().getByRole('button',{name:'Import',exact:true});await button.waitFor();
   const positions=await page.evaluate(()=>{const a=document.querySelector('.page-head:not(.hide) .pp-list-import')?.getBoundingClientRect();const b=[...document.querySelectorAll('.page-head .primary-action')].find(el=>el.getBoundingClientRect().width)?.getBoundingClientRect();return a&&b?{dy:Math.abs(a.top-b.top),left:a.right<=b.left+2}:null;});
   assert(positions && positions.dy<8 && positions.left,'Import must sit next to Add in the header');
   if(kind==='employees'){
    assert(await page.evaluate(()=>cur_list.data.length>0),'This check must exercise a populated employee list');
    await page.screenshot({path:path.join(out,'workers-import-toolbar.png'),fullPage:true});
   }
   await button.click();await shown();
   assert.equal(await modal().locator('[data-fieldname="kind"] select').inputValue(),kind);
   const template=modal().getByRole('button',{name:'Download template',exact:true});await template.waitFor();
   assert(await template.evaluate(el=>{const upload=el.closest('.modal').querySelector('input[type=file]');return el.getBoundingClientRect().top<upload.getBoundingClientRect().top;}));
   const download=page.waitForEvent('download');await template.click();const file=await download;
   assert.equal(file.suggestedFilename(),`plus-point-${kind}.csv`);
   assert(fs.readFileSync(await file.path(),'utf8').replace(/^\ufeff/,'').startsWith('external_id,'));
   if(kind==='employees')await page.screenshot({path:path.join(out,'workers-import-template.png'),fullPage:true});
   await modal().getByRole('button',{name:'Close',exact:true}).click();
   await button.waitFor();
  }
  await page.goto(base+'/desk/plus-point/employee',{waitUntil:'domcontentloaded'});
  await header().getByRole('button',{name:'Import',exact:true}).waitFor();
  await page.setViewportSize({width:390,height:844});
  await header().getByRole('button',{name:'Import',exact:true}).click();
  await shown();
  await modal().getByRole('button',{name:'Download template',exact:true}).waitFor();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.screenshot({path:path.join(out,'workers-import-template-mobile.png'),fullPage:true});
  await modal().getByRole('button',{name:'Close',exact:true}).click();
  await page.reload({waitUntil:'domcontentloaded'});
  await header().getByRole('button',{name:'Import',exact:true}).waitFor();
  assert.deepEqual(failures,[]);
  console.log('PASS populated employee list + seven employee/finance headers, matching template downloads, refresh persistence and mobile');
 }catch(error){await page.screenshot({path:path.join(out,'list-import-failure.png'),fullPage:true});throw error;}
 finally{await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
