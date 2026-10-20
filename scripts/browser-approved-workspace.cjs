/* Inspect an approved local workspace without setting its real owner's password or creating data. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),{chromium}=require('playwright');
let stage="fixture";
(async()=>{
 assert(process.env.PP_SIGNUP_REFERENCE,'Supply the approved signup reference');
 const root=path.resolve(__dirname,'..'),out=path.join(root,'.local','qa');fs.mkdirSync(out,{recursive:true});
 const settings=Object.fromEntries(fs.readFileSync(path.join(root,'.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')&&!x.startsWith('#')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)];}));
 const state=JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','platform.localhost','execute','plus_point.activation.progress_local','--kwargs',JSON.stringify({reference:process.env.PP_SIGNUP_REFERENCE})],{cwd:root,encoding:'utf8'}));
 assert.equal(state.activation,'Ready');
 const browser=await chromium.launch({headless:true,channel:'msedge'}),admin=await browser.newPage({viewport:{width:1440,height:1000}}),customer=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
 for(const p of [admin,customer]){p.setDefaultTimeout(30000);p.setDefaultNavigationTimeout(60000);p.on('pageerror',e=>errors.push(e.message));await p.addLocatorHandler(p.locator('.modal:visible').filter({hasText:'New updates are available'}),()=>p.keyboard.press('Escape'));}
 const login=async(p,origin,home)=>{await p.goto(origin+'/login',{waitUntil:'domcontentloaded'});assert.equal(await p.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,settings.PP_ADMIN_PASSWORD),'Logged In');await p.goto(origin+home,{waitUntil:'domcontentloaded'});};
 try{
  stage='admin login';await login(admin,'http://platform.localhost:8000','/desk/high4tech');await admin.waitForFunction(()=>window.frappe?.set_route);
  stage='signup form';await admin.evaluate(ref=>frappe.set_route('Form','PP Signup Request',ref),process.env.PP_SIGNUP_REFERENCE);
  stage='company login action';await admin.getByRole('button',{name:'Company login',exact:true}).click();
  stage='company login modal';const modal=admin.locator('.modal:visible').last();await modal.getByText(state.login_email,{exact:false}).waitFor();
  const setup=await modal.getByRole('link',{name:'Set your password',exact:true}).getAttribute('href');
  assert.equal(new URL(setup).origin,new URL(state.login_url).origin);
  stage='native setup page';const password=await browser.newPage();await password.goto(setup,{waitUntil:'domcontentloaded'});
  await password.getByRole('heading',{name:'Set Password',exact:true}).waitFor();assert.equal(await password.locator('#new_password').inputValue(),'');
  await password.screenshot({path:path.join(out,'approved-password-setup.png'),fullPage:true});
  console.log('PASS approved-request Company login action, registered email, correct private destination and untouched native password setup form');
  stage='customer operator login';await login(customer,new URL(state.login_url).origin,'/desk/plus-point');
  stage='company onboarding';await customer.locator('.pp-event-setup-dialog:visible').getByText('Your event company',{exact:true}).waitFor();
  const organization=await customer.evaluate(()=>frappe.boot.plus_point.signup_company_name);
  assert.equal(await customer.locator('.pp-event-setup-dialog:visible [data-fieldname=company_name] input').inputValue(),organization);
  assert(await customer.locator('#body').evaluate(el=>el.inert));
  await customer.screenshot({path:path.join(out,'approved-company-onboarding.png'),fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('PASS actual empty customer workspace opens its own company onboarding, prefilled business name and disabled background; no company data created and owner password left untouched');
 }finally{await browser.close();}
})().catch(e=>{console.error('Approved workspace browser check failed at '+stage+' ('+e.name+'); private links and credentials redacted');process.exitCode=1;});
