/* Native owner password setup with an exact QA user; never sets the real owner's password. */
const {chromium}=require('playwright'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
let stage="fixture";
(async()=>{
 const run=crypto.randomBytes(6).toString('hex');
 const fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.activation_testing.fixture','--kwargs',JSON.stringify({action,run_id:run})],{encoding:'utf8',stdio:['pipe','pipe','pipe']}).trim());
 let browser;
 try{
  const data=fixture('begin'),password='QA!'+crypto.randomBytes(20).toString('base64url');
  browser=await chromium.launch({headless:true,channel:'msedge'});
  const page=await browser.newPage();page.setDefaultTimeout(30000);
  stage="native form";await page.goto(data.setup_url,{waitUntil:'domcontentloaded'});
  await page.locator('#new_password').fill(password);await page.locator('#confirm_password').fill(password);
  await page.locator('#confirm_password').press('End');
  stage='save password';await page.locator('#update').click();
  await page.waitForURL(url=>url.pathname.startsWith('/desk'),{timeout:60000});
  stage='consumed key';assert.deepEqual(fixture('check'),{activated:true,key_consumed:true});
  const context=await browser.newContext(),login=await context.newPage();
  await login.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  const auth=async(usr,pwd)=>login.evaluate(async c=>{const r=await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)});return {status:r.status,body:await r.json()};},{usr,pwd});
  stage='wrong password';assert.equal((await auth(data.email,'incorrect-password')).status,401);
  stage='alias login';assert.equal((await auth(data.alias,password)).body.message,'Logged In');
  stage='email login';const emailContext=await browser.newContext(),emailPage=await emailContext.newPage();
  await emailPage.goto('http://qa.localhost:8000/login',{waitUntil:'domcontentloaded'});
  assert.equal(await emailPage.evaluate(async c=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)})).json()).message,{usr:data.email,pwd:password}),'Logged In');
  stage='key replay';const replayContext=await browser.newContext(),replay=await replayContext.newPage();await replay.goto(data.setup_url,{waitUntil:'domcontentloaded'});
  const replayStatus=await replay.evaluate(async ({key,password})=>(await fetch('/api/method/frappe.core.doctype.user.user.update_password',{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':window.frappe?.csrf_token||window.csrf_token||''},body:JSON.stringify({key,new_password:password})})).status,{key:new URL(data.setup_url).searchParams.get('key'),password});
  assert.equal(replayStatus,410);
  stage='cross site';const other=await browser.newPage();await other.goto('http://demo.localhost:8000/login',{waitUntil:'domcontentloaded'});
  const cross=await other.evaluate(async c=>(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(c)})).status,{usr:data.email,pwd:password});
  assert.equal(cross,401);
  console.log('PASS native password form, consumed one-time link, own password, email and optional login ID, invalid-password rejection and separate-site login isolation');
 }finally{if(browser)await browser.close();assert(fixture('end').restored);console.log('PASS exact QA user removed and configuration restored');}
})().catch(e=>{console.error('Activation browser check failed at '+stage+' ('+e.name+'); private links and credentials redacted');process.exitCode=1;});
