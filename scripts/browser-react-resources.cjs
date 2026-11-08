const fs=require('fs'), assert=require('node:assert/strict'),{chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});const errors=[];
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(20000);page.on('pageerror',e=>errors.push(e.stack||e.message));
  const origin='http://high4tech-events-fd166a217c.localhost:8000';
  await page.goto(origin+'/login');
  const pwd=fs.readFileSync('.env','utf8').match(/^PP_ADMIN_PASSWORD=(.*)$/m)[1].trim();
  assert.equal(await page.evaluate(async pwd=>(await(await fetch('/api/method/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({usr:'Administrator',pwd})})).json()).message,pwd),'Logged In');
  await page.goto(origin+'/desk/item',{waitUntil:'commit'});
  for(const [doctype,kind] of [['Item','equipment'],['Warehouse','warehouses'],['Vehicle','vehicles']]){
   await page.waitForFunction(()=>window.frappe?.set_route);
   if(doctype!=='Item')await page.evaluate(doctype=>frappe.set_route('List',doctype),doctype);
   const list=page.locator('[data-pp-react-root=resource-list]');await list.locator('table').waitFor();
   await page.waitForFunction(()=>document.querySelector('[data-pp-react-root=resource-list] section[aria-busy=false]'));
   assert.equal(await list.getByRole('alert').count(),0,await list.innerText());
   await list.getByRole('button',{name:'Add '+(kind==='equipment'?'equipment':kind==='warehouses'?'warehouse':'vehicle'),exact:true}).click();
   const dialog=page.getByRole('dialog');await dialog.getByRole('button',{name:'Save',exact:true}).click();
   assert(await dialog.locator('[aria-invalid=true]').count()>0);
   await page.keyboard.press('Escape');assert.equal(await dialog.count(),0);
   const link=list.locator('tbody a.pp-r-record-name').first();
   if(await link.count()){
    await link.click();
    const profile=page.locator('[data-pp-react-root=resource-profile]');await profile.getByRole('heading',{level:1}).waitFor();
    assert.equal(await profile.getByRole('alert').count(),0,await profile.innerText());
    await profile.getByRole('button',{name:'Edit details',exact:true}).click();
    await dialog.getByRole('button',{name:'Save',exact:true}).waitFor();
    let mutation;
    await page.route('**/api/method/plus_point.resources.update_profile',route=>{
     mutation=JSON.parse(route.request().postData());
     return route.fulfill({status:417,contentType:'application/json',body:JSON.stringify({exc_type:'ValidationError',_server_messages:JSON.stringify([JSON.stringify({message:'QA simulated edit conflict; your changes are kept.'})])})});
    });
    await dialog.getByRole('button',{name:'Save',exact:true}).click();
    await dialog.getByRole('alert').filter({hasText:'QA simulated edit conflict'}).waitFor();
    assert(mutation.name);
    assert.equal(mutation.view,kind);
    await page.unroute('**/api/method/plus_point.resources.update_profile');
    await page.keyboard.press('Escape');assert.equal(await dialog.count(),0);
    if(kind==='vehicles'){
     const choice=await page.evaluate(async()=>{
      const events=await plus_point.form_rpc('resources.assignable_events');
      for(const event of events.slice(0,10)){
       const vehicles=await plus_point.form_rpc('resources.booking_options',{project:event.project,kind:'vehicle',start_date:event.start_date,end_date:event.end_date});
       const vehicle=vehicles.find(row=>row.available&&row.pp_crew_seats>=1);
       if(vehicle)return {event,vehicle};
      }
     });
     assert(choice,'A read-only vehicle booking test needs an available event and vehicle');
     await profile.getByRole('button',{name:'Assign to event',exact:true}).click();
     await dialog.getByRole('combobox',{name:'Event',exact:true}).click();
     await page.getByRole('option',{name:choice.event.event_name+' · '+choice.event.pp_reference,exact:true}).click();
     await dialog.getByRole('combobox',{name:'Site',exact:true}).click();
     const sites=page.getByRole('listbox',{name:'Site',exact:true}).getByRole('option');
     await sites.nth(1).click();
     await dialog.getByRole('combobox',{name:'Vehicle',exact:true}).click();
     await page.getByRole('option').filter({hasText:choice.vehicle.license_plate||choice.vehicle.name}).first().click();
     let booking;
     await page.route('**/api/method/plus_point.resources.save_booking',route=>{
      booking=JSON.parse(route.request().postData());
      return route.fulfill({status:417,contentType:'application/json',body:JSON.stringify({exc_type:'ValidationError',_server_messages:JSON.stringify([JSON.stringify({message:'QA reservation conflict; no live booking saved.'})])})});
     });
     await dialog.getByRole('button',{name:'Confirm reservation',exact:true}).click();
     await dialog.getByRole('alert').filter({hasText:'QA reservation conflict'}).waitFor();
     assert.equal(booking.project,choice.event.project);assert.equal(booking.kind,'vehicle');
     assert.equal(booking.values.vehicle,choice.vehicle.name);assert(booking.values.site);
     assert.equal(await dialog.getByRole('combobox',{name:'Vehicle',exact:true}).getAttribute('aria-invalid'),'true');
     await page.unroute('**/api/method/plus_point.resources.save_booking');
     await page.keyboard.press('Escape');
     console.log('PASS event/site/vehicle reservation, native availability and retained inline conflict');
    }
    fs.mkdirSync('.local/qa/react-resources',{recursive:true});await page.screenshot({path:'.local/qa/react-resources/'+kind+'.png',fullPage:true});
   }
   console.log('PASS '+doctype+' list/profile, inline validation, intercepted save conflict and disposal');
  }
  assert.deepEqual(errors,[]);
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
