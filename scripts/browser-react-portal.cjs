/* Public UI contract. Responses are intercepted; native signing/security is tested on QA. */
const fs=require('node:fs'),assert=require('node:assert/strict'),{chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[],checks=[];
 const out='.local/qa/react-portal';fs.mkdirSync(out,{recursive:true});page.on('pageerror',e=>errors.push(e.message));
 let payload,accepts=0;
 const review={html:'<h2>Event staffing agreement</h2><p>Supply crew for the client.</p>',status:'Pending',events:[{title:'Client event',reference:'EVT-QA',status:'Upcoming',start:'2026-11-10',end:'2026-11-11',required_worker_days:10,assigned_worker_days:8,phases:[{title:'Event period',start:'2026-11-10',end:'2026-11-11',status:'Upcoming'}]}]};
 await page.route('**/api/method/plus_point.signing.review?*',route=>route.fulfill({contentType:'application/json',body:JSON.stringify({message:review})}));
 await page.route('**/api/method/plus_point.signing.accept',route=>{accepts++;payload=route.request().postDataJSON();return route.fulfill({contentType:'application/json',body:'{"message":{"signed":true}}'});});
 try{
  await page.goto('http://high4tech-events-fd166a217c.localhost:8000/agree?token=ui-contract-fixture',{waitUntil:'commit'});
  await page.getByRole('heading',{name:'Event staffing agreement',exact:true}).waitFor();
  await page.getByRole('button',{name:'Sign agreement',exact:true}).click();assert.equal(accepts,0);assert.equal(await page.locator('[aria-invalid=true]').count(),3);checks.push('Required signer/email/consent errors block submission');
  await page.getByLabel('Full name *',{exact:true}).fill('Ayesha Malik');await page.getByLabel('Email *',{exact:true}).fill('ayesha@example.invalid');await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Sign agreement',exact:true}).click();
  await page.getByText('Agreement signed. The company has been notified.',{exact:true}).waitFor();assert.equal(accepts,1);assert.equal(payload.signer,'Ayesha Malik');assert.equal(payload.consent,1);assert.equal(payload.token,'ui-contract-fixture');assert.equal(await page.getByRole('button',{name:'Sign agreement',exact:true}).count(),0);checks.push('Signing posts once to existing endpoint and replaces signature form');
  await page.getByRole('tab',{name:'Event progress',exact:true}).click();await page.getByRole('heading',{name:'Client event',exact:true}).waitFor();assert(await page.getByText('EVT-QA',{exact:true}).isVisible());checks.push('Progress uses scoped event response');
  await page.screenshot({path:out+'/desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:out+'/mobile.png',fullPage:true});checks.push('Mobile portal fits viewport');
  assert.deepEqual(errors,[]);
 }finally{fs.writeFileSync(out+'/report.json',JSON.stringify({checks,errors},null,2));await browser.close();}
 console.log(JSON.stringify({checks,errors}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;});
