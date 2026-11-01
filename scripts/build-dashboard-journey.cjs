/* Bake the shared event-world kit once. Dashboard clients only load PNGs. */
const fs=require('fs'),path=require('path'),{chromium}=require('playwright');
(async()=>{
 const base=path.resolve(__dirname,'../apps/plus_point/plus_point/public'),out=path.join(base,'images/dashboard-journey');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{const page=await browser.newPage();await page.goto('about:blank');
  await page.evaluate(()=>{window.frappe={provide:n=>{window[n]||={};}};});
  await page.addScriptTag({path:path.join(base,'js/vendor/three-scene.min.js')});
  await page.addScriptTag({path:path.join(base,'js/world_assets.js')});
  const sprites=[];for(const type of ['client','crew','van','crane','warehouse','venue','worker-orange','worker-teal','client-active','warehouse-active','venue-active','loader','worker-portrait']){
   const png=await page.evaluate(type=>{
    const T=window.PlusPointScene3D,geometries=[],materials=[],material=color=>{if(['#087f70','#398c71','#3c7a8b'].includes(color))color='#e97824';const m=new T.MeshStandardMaterial({color,roughness:.9});materials.push(m);return m;};
    const boxGeo=new T.BoxGeometry(1,1,1),roundGeo=new T.CylinderGeometry(1,1,1,12),ballGeo=new T.SphereGeometry(1,12,8);geometries.push(boxGeo,roundGeo,ballGeo);
    const palette=Object.fromEntries(Object.entries({white:'#f6f8f3',stone:'#d6e2da',teal:'#e97824',deep:'#3a424b',glass:'#adc5d5',dark:'#273b3c',window:'#183f49',light:'#fff1b9',orange:'#ff5800',wood:'#aa8563',leaf:'#899b69'}).map(([n,c])=>[n,material(c)]));
    const mesh=(geo,mat,x,y,z,sx,sy,sz,parent)=>{const o=new T.Mesh(geo,mat);o.position.set(x,y,z);o.scale.set(sx,sy,sz);parent?.add(o);return o;},box=(mat,x,y,z,sx,sy,sz,parent)=>mesh(boxGeo,mat,x,y,z,sx,sy,sz,parent),k={T,box,mesh,roundGeo,ballGeo,palette,material};
    const scene=new T.Scene(),group=type.startsWith('worker-')?plus_point.world_assets.worker(k,{color:type.endsWith('orange')?'#ff5800':'#087f70',pose:.12}):plus_point.world_assets.checkpoint(k,type);scene.add(group);scene.add(new T.HemisphereLight('#ffffff','#aec3bc',2.5));const sun=new T.DirectionalLight('#fff5e8',3.5);sun.position.set(5,10,7);scene.add(sun);
    const portrait=type==='worker-portrait',span=portrait?.4:type.startsWith('worker-')?1.05:({client:3.2,crew:3.3,van:2.2,loader:2.2,crane:3.2,warehouse:3.5,venue:3.8}[type.replace(/-active$/,'')]),cy=portrait?1.1:type==='crane'?1.8:.8,camera=new T.OrthographicCamera(-span,span,span,-span,.1,100);
    if(portrait){for(const x of [-.05,.05])mesh(ballGeo,palette.dark,x,1.24,.128,.012,.014,.01,group);mesh(ballGeo,material('#c28d65'),0,1.2,.145,.025,.027,.026,group);for(const x of [-.1,.1])box(palette.white,x,.89,.115,.035,.38,.01,group);box(palette.white,0,.76,.117,.33,.032,.01,group);}
    // Keep frontage parallel to the road, and render transport side-on facing right.
    camera.position.set(['van','loader'].includes(type)?-14:0,cy+(portrait?.35:['van','loader'].includes(type)?2:9),['van','loader'].includes(type)?0:14);camera.lookAt(0,cy,0);
    const renderer=new T.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});renderer.setSize(512,512);renderer.setPixelRatio(1);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;renderer.render(scene,camera);const result=renderer.domElement.toDataURL('image/png').split(',')[1];geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();renderer.forceContextLoss();return result;
   },type);if(type==='worker-portrait')fs.writeFileSync(path.join(out,'worker-portrait.png'),Buffer.from(png,'base64'));else sprites.push(png);process.stdout.write(type+' rendered\n');
  }
  const atlas=await page.evaluate(async sprites=>{const canvas=document.createElement('canvas');canvas.width=2048;canvas.height=1536;const ctx=canvas.getContext('2d');for(let i=0;i<sprites.length;i++){const image=new Image();image.src='data:image/png;base64,'+sprites[i];await image.decode();ctx.drawImage(image,(i%4)*512,Math.floor(i/4)*512);}return canvas.toDataURL('image/png').split(',')[1];},sprites);fs.writeFileSync(path.join(out,'event-world-atlas.png'),Buffer.from(atlas,'base64'));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
