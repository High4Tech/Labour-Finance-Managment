const fs=require('fs'),assert=require('node:assert/strict'),{chromium}=require('playwright');
(async()=>{const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.setDefaultTimeout(25000);page.on('pageerror',e=>errors.push(e.message));
try{
 fs.mkdirSync('.local/qa/react-finance',{recursive:true});
 const origin='http://high4tech-events-fd166a217c.localhost:8000';await page.goto(origin+'/login');
 const pwd=fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim();
 assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,pwd),'Logged In');
 await page.goto(origin+'/desk/payment-entry',{waitUntil:'commit'});
 for(const doctype of ['Payment Entry','Purchase Invoice','Expense Claim','Sales Invoice']){
  await page.waitForFunction(()=>window.frappe?.set_route);
  if(doctype!=='Payment Entry')await page.evaluate(dt=>frappe.set_route('List',dt),doctype);
  const list=page.locator('[data-pp-react-root=finance-list]');await list.locator('table').waitFor();
  await list.getByRole('button',{name:/^(Record payment|Record expense|Record reimbursement|Create invoice)$/}).click();
  const form=page.locator('[data-pp-react-root=finance-record]');await form.getByRole('heading',{name:'Accounting details',exact:true}).waitFor();
  assert.equal(await form.getByRole('alert').count(),0,await form.innerText());
  const schema=await page.evaluate(dt=>plus_point.form_rpc('finance_records.detail',{doctype:dt}),doctype);
  assert(schema.fields.length>3);assert(schema.can_write);
  // Invalid required fields must not perform a server write.
  const nativeWrites=[];const onRequest=r=>{if(r.url().endsWith('/plus_point.finance_records.save'))nativeWrites.push(r.url());};page.on('request',onRequest);
  await form.getByRole('button',{name:'Save draft',exact:true}).click();
  assert(await form.locator('[aria-invalid=true]').count()>0,await form.innerText());assert.equal(nativeWrites.length,0);page.off('request',onRequest);
  await form.getByRole('button',{name:'Add line',exact:true}).click().catch(()=>{});
  if(await page.getByRole('dialog').count()){await page.getByRole('dialog').getByRole('button',{name:'Apply line',exact:true}).click();assert(await page.getByRole('dialog').locator('[aria-invalid=true]').count()>0);await page.keyboard.press('Escape');}
  await page.screenshot({path:'.local/qa/react-finance/'+doctype.replaceAll(' ','-')+'.png',fullPage:true});
  if(doctype==='Payment Entry'){
   const remarks=form.getByLabel('Remarks',{exact:true});await remarks.fill('QA unsaved handoff only');
   await form.getByRole('button',{name:'Advanced accounting controls',exact:true}).click();
   await page.waitForFunction(()=>!document.querySelector('[data-pp-react-root=finance-record]'));
   assert.equal(await page.evaluate(()=>cur_frm.doc.remarks),'QA unsaved handoff only');
   await page.getByRole('button',{name:'Back to company form',exact:true}).click();
   await form.getByRole('heading',{name:'Accounting details',exact:true}).waitFor();
   assert.equal(await form.getByLabel('Remarks',{exact:true}).inputValue(),'QA unsaved handoff only');
   const calls=[];const observe=r=>{if(r.url().includes('/plus_point.finance_records.'))calls.push(r.url());};page.on('request',observe);
   await page.waitForTimeout(3500);page.off('request',observe);assert.deepEqual(calls,[],'Idle accounting form must not poll or reload');
   // Clear the local test draft before leaving; no save request is sent.
   await form.getByLabel('Remarks',{exact:true}).fill('');
   await page.evaluate(()=>{cur_frm.doc.remarks='';cur_frm.doc.__unsaved=0;});
   console.log('PASS unsaved advanced return and zero idle accounting requests');
  }
  await page.evaluate(()=>frappe.set_route('List','Payment Entry'));
  console.log('PASS '+doctype+' shared form and inline validation');
 }
 const agreement=await page.evaluate(async()=>{const result=await plus_point.form_rpc('company_tools.search',{kind:'agreements',text:''});return result[0]?.name;});
 assert(agreement);await page.evaluate(name=>frappe.set_route('pp-client-billing',{record:name}),agreement);
 const billing=page.locator('[data-pp-react-root=billing]');await billing.getByRole('heading',{name:'Client invoices',exact:true}).waitFor();
 assert.equal(await billing.getByRole('alert').count(),0,await billing.innerText());
 await billing.getByRole('button',{name:'Add extra invoice',exact:true}).click();
 const dialog=page.getByRole('dialog');await dialog.getByRole('button',{name:'Create invoice draft',exact:true}).click();assert(await dialog.locator('[aria-invalid=true]').count()>0);await page.keyboard.press('Escape');
 fs.mkdirSync('.local/qa/react-finance',{recursive:true});await page.screenshot({path:'.local/qa/react-finance/billing.png',fullPage:true});
 assert.deepEqual(errors,[]);console.log('PASS billing summary, payment schedule and invoice dialog');
 await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>{document.documentElement.dataset.theme='dark';});
 await billing.getByRole('button',{name:'Add extra invoice',exact:true}).click();
 const bounds=await page.getByRole('dialog').boundingBox();assert(bounds.x>=0&&bounds.x+bounds.width<=390);
 await page.keyboard.press('Escape');
 const stats=await page.evaluate(()=>plus_point.react_ui.stats);assert.equal(stats.activeRoots,1);
 console.log('PASS mobile dialog bounds, Escape and one active screen root');
}finally{await browser.close();}})().catch(error=>{console.error(error);process.exitCode=1;});
