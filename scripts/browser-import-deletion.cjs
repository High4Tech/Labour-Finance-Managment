/* Real imported-event deletion on a disposable QA company; no customer deletion. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('node:assert/strict'),{execFileSync}=require('child_process'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),pwd=fs.readFileSync(path.join(root,'.env'),'utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim(),run=crypto.randomBytes(6).toString('hex');
 const fixture=action=>JSON.parse(execFileSync('docker',['compose','exec','-T','-w','/home/frappe/frappe-bench','frappe','bench','--site','qa.localhost','execute','plus_point.event_testing.hierarchy_browser_fixture','--kwargs',JSON.stringify({action,run_id:run})],{cwd:root,encoding:'utf8'}));
 const data=fixture('begin'),browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage(),errors=[];page.setDefaultTimeout(45000);page.on('pageerror',e=>errors.push(e.message));
 const rpc=(method,args)=>page.evaluate(({method,args})=>plus_point.form_rpc(method,args),{method,args});
 try{
  await page.goto('http://qa.localhost:8000/login');await page.evaluate(pwd=>fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})}),pwd);
  await page.goto('http://qa.localhost:8000/desk/plus-point');await page.getByRole('button',{name:'Skip onboarding',exact:true}).click();await page.locator('.pp-dashboard[data-ready=true]').waitFor();
  const dates=await page.evaluate(()=>[frappe.datetime.add_days(frappe.datetime.get_today(),2),frappe.datetime.add_days(frappe.datetime.get_today(),3)]);
  const columns=['external_id','event_name','customer','start_date','end_date','site_name','workers_per_day','billing_model','fixed_amount','wage_rate','client_rate','agreement'];
  const values=['EVT-'+run+'-1',data.prefix+' Imported event',data.prefix+' Client',...dates,'Imported hall','1','Daily','0','100','150','QA agreement'];
  const content=Buffer.from(columns.join(',')+'\n'+values.map(v=>'"'+v.replaceAll('"','""')+'"').join(',')+'\n').toString('base64');
  const preview=await rpc('imports.preview',{kind:'events',company:data.company,filename:'events.csv',content});assert(preview.valid,JSON.stringify(preview));
  const applied=await rpc('imports.apply',{token:preview.token}),name=applied.rows[0].document;
  const receipts=await page.evaluate(name=>frappe.db.get_list('PP Import Record',{filters:{document_type:'PP Event Plan',document_name:name},fields:['name','content_hash'],limit:1}),name);assert.equal(receipts.length,1);
  await page.evaluate(name=>frappe.set_route('List','PP Event Plan','List',{name}),name);await page.waitForFunction(name=>window.cur_list?.doctype==='PP Event Plan'&&cur_list.data.some(r=>r.name===name),name);
  await page.locator('.list-row-container').filter({hasText:data.prefix+' Imported event'}).locator('input[type=checkbox]').check();await page.locator('.pp-delete-selected').click();
  const dialog=page.locator('.pp-delete-dialog:visible');await dialog.waitFor();assert.equal(await dialog.getByText('Review record',{exact:true}).count(),0);assert(await dialog.getByRole('button',{name:'Delete',exact:true}).isEnabled());
  await dialog.getByRole('button',{name:'Delete',exact:true}).click();await dialog.waitFor({state:'hidden'});assert.equal(await page.evaluate(name=>frappe.db.exists('PP Event Plan',name),name),false);
  assert.deepEqual(await page.evaluate(name=>frappe.db.get_list('PP Import Record',{filters:{document_type:'PP Event Plan',document_name:name},fields:['name','content_hash'],limit:1}),name),receipts);
  const replay=await rpc('imports.preview',{kind:'events',company:data.company,filename:'events.csv',content});assert.equal(replay.valid,false);assert(replay.rows[0].error.includes('deleted'));
  assert.deepEqual(errors,[]);console.log('PASS actual imported event selected and deleted from list; import receipt/hash retained; no review loop; replay blocked');
 }catch(error){await page.screenshot({path:path.join(root,'.local','qa','import-delete-failure.png'),fullPage:true}).catch(()=>{});throw error;}
 finally{await browser.close();assert(fixture('end').restored);console.log('PASS disposable QA fixture restored');}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
