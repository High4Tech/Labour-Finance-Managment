/* Render the shared world once at build time; no app/server or business data needed. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),assets=path.join(root,'apps/plus_point/plus_point/public'),out=path.join(assets,'images/event-scene');
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:650},reducedMotion:'reduce'});
  await page.setContent('<!doctype html><html><body style="margin:0"><div id="world" style="width:1440px;height:650px"></div></body></html>');
  await page.evaluate(()=>{window.frappe={provide(){},boot:{time_zone:{system:'UTC'}},utils:{escape_html:String}};window.plus_point={};window.__=text=>text;});
  await page.addScriptTag({path:path.join(assets,'js/vendor/three-scene.min.js')});await page.addScriptTag({path:path.join(assets,'js/event_scene.js')});
  await page.evaluate(()=>{const state={working:true,workerFigures:0,vehicleFigures:0};window.posterScene=plus_point.event_scene.mount(document.getElementById('world'),state);});
  await page.waitForFunction(()=>window.posterScene.stats().frames>0);
  const poster=await page.evaluate(()=>window.posterScene.capture()),bytes=Buffer.from(poster.split(',')[1],'base64');
  fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'world-preview.webp'),bytes);
  const manifest={source:'Original shared event_scene.js component, rendered with no workers or vehicle bookings',width:1440,height:650,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),runtime:'Static preview only. Does not initialize Three.js.'};
  fs.writeFileSync(path.join(out,'world-preview.json'),JSON.stringify(manifest,null,2)+'\n');await page.evaluate(()=>window.posterScene.dispose());console.log(JSON.stringify(manifest));
 }finally{await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
