/* Render still SVG poses from the supplied procedural avatar for low-cost inline feedback. */
const fs=require('node:fs'),path=require('node:path'),{chromium}=require('playwright');
(async()=>{
 const root=path.resolve(__dirname,'..'),folder=path.join(root,'apps/plus_point/plus_point/public/images/freddy');fs.mkdirSync(folder,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{const page=await browser.newPage();await page.setContent('<div id="avatar"></div>');await page.addScriptTag({path:path.join(root,'apps/plus_point/plus_point/public/js/freddy-runtime.js')});
  for(const animation of ['confused','surprised','thinking','listening','happy','curious','sad','celebrate']){
   const svg=await page.evaluate(animation=>{const avatar=plus_point.freddy_runtime.create(document.querySelector('#avatar'),{animation,autoplay:false,size:'100%'});avatar.element.setAttribute('xmlns','http://www.w3.org/2000/svg');const source=new XMLSerializer().serializeToString(avatar.element);avatar.destroy();return source;},animation);
   fs.writeFileSync(path.join(folder,animation+'.svg'),svg.replace(/avatar-procedural-clip-[a-z0-9-]+/gi,'freddy-'+animation+'-clip'));
  }
  console.log('Rendered 8 still Freddy expressions.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error.stack);process.exitCode=1;});
