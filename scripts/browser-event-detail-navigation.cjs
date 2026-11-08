/* Existing company event navigation; no event or finance writes. */
const fs=require('node:fs'),assert=require('node:assert/strict'),{chromium}=require('playwright');
(async()=>{
 const out='.local/qa/event-detail-navigation';fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:1600,height:1100}}),errors=[],checks=[];
 page.setDefaultTimeout(30000);page.on('pageerror',error=>errors.push(error.stack||error.message));
 await page.route('**/api/method/plus_point.drafts.save',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({message:{name:'QA-NAVIGATION-DRAFT',revision:1,status:'Draft'}})}));
 try{
  const origin='http://high4tech-events-fd166a217c.localhost:8000';
  await page.goto(origin+'/login');
  const pwd=fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim();
  await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),pwd);
  await page.goto(origin+'/desk/pp-event-plan',{waitUntil:'commit'});
  const list=page.locator('[data-pp-react-root=planning]');await list.locator('tbody a.pp-r-record-name').first().waitFor();
  const rows=await list.locator('tbody tr').evaluateAll(nodes=>nodes.map(row=>({href:row.querySelector('a.pp-r-record-name')?.getAttribute('href'),status:row.querySelector('.pp-ui-badge')?.textContent})));
  const ready=rows.find(row=>row.href?.includes('?record=')&&row.status!=='Draft');
  const draft=rows.find(row=>row.href?.includes('?record=')&&row.status==='Draft');
  assert(ready,'A saved event is required for the read-only navigation check.');
  assert(draft,'A saved Draft event is required to exercise the reported regression.');
  for(const saved of [ready,draft]){
   if(!page.url().endsWith('/desk/pp-event-plan')){
    await page.evaluate(()=>frappe.set_route('List','PP Event Plan'));
    await list.locator('tbody a.pp-r-record-name').first().waitFor();
   }
   await list.locator('a.pp-r-record-name').evaluateAll((nodes,href)=>nodes.find(node=>node.getAttribute('href')===href).click(),saved.href);
   await page.waitForFunction(()=>{const root=document.querySelector('#page-pp-event-plans .pp-operations');return root?.dataset.ready==='true'&&root.dataset.recordKey===location.pathname+location.search;});
   const state=await page.evaluate(()=>({path:location.pathname+location.search,profile:!!document.querySelector('.pp-event-overview'),builder:!!document.querySelector('.pp-operations.pp-flow-builder'),status:document.querySelector('.pp-event-profile [data-state]')?.getAttribute('data-state'),errors:[...document.querySelectorAll('#page-pp-event-plans [role=alert]')].map(node=>node.textContent)}));
   checks.push({name:saved.status+' list record opens event details',...state});
   await page.screenshot({path:out+'/opened-'+saved.status+'.png',fullPage:true});
   assert(state.profile&&!state.builder,JSON.stringify(state));
   assert(!new URL(page.url()).searchParams.has('edit'));
  }
  const edit=page.getByRole('link',{name:'Edit event',exact:true});await edit.click();
  await page.waitForSelector('.pp-operations.pp-flow-builder .pp-builder-content');
  assert(new URL(page.url()).searchParams.has('edit'));
  checks.push({name:'Edit event is a separate explicit action',passed:true});
  assert.deepEqual(errors,[]);console.log('PASS saved and Draft event list → detail → explicit edit');
 }finally{fs.writeFileSync(out+'/report.json',JSON.stringify({checks,errors},null,2));await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
