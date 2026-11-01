/* Bake the shared event-world kit once. Dashboard clients only load PNGs. */
const fs=require('fs'),path=require('path'),{chromium}=require('playwright');
(async()=>{
 const base=path.resolve(__dirname,'../apps/plus_point/plus_point/public'),out=path.join(base,'images/dashboard-journey');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try{const page=await browser.newPage();await page.goto('about:blank');
  await page.evaluate(()=>{window.frappe={provide:n=>{window[n]||={};}};});
  await page.addScriptTag({path:path.join(base,'js/vendor/three-scene.min.js')});
  await page.addScriptTag({path:path.join(base,'js/world_assets.js')});
  const sprites=[];for(const type of ['client','crew','van','crane','warehouse','venue','worker-orange','worker-teal']){
   const png=await page.evaluate(type=>{
    const T=window.PlusPointScene3D,geometries=[],materials=[],material=color=>{const m=new T.MeshStandardMaterial({color,roughness:.9});materials.push(m);return m;};
    const boxGeo=new T.BoxGeometry(1,1,1),roundGeo=new T.CylinderGeometry(1,1,1,12),ballGeo=new T.SphereGeometry(1,12,8);geometries.push(boxGeo,roundGeo,ballGeo);
    const palette=Object.fromEntries(Object.entries({white:'#f6f8f3',stone:'#d6e2da',teal:'#087f70',deep:'#123f3d',glass:'#93c7be',dark:'#273b3c',window:'#183f49',light:'#fff1b9',orange:'#ff5800',wood:'#aa8563',leaf:'#398c71'}).map(([n,c])=>[n,material(c)]));
    const mesh=(geo,mat,x,y,z,sx,sy,sz,parent)=>{const o=new T.Mesh(geo,mat);o.position.set(x,y,z);o.scale.set(sx,sy,sz);parent?.add(o);return o;},box=(mat,x,y,z,sx,sy,sz,parent)=>mesh(boxGeo,mat,x,y,z,sx,sy,sz,parent),k={T,box,mesh,roundGeo,ballGeo,palette,material};
    const scene=new T.Scene(),group=type.startsWith('worker-')?plus_point.world_assets.worker(k,{color:type.endsWith('orange')?'#ff5800':'#087f70',pose:.12}):plus_point.world_assets.checkpoint(k,type);scene.add(group);scene.add(new T.HemisphereLight('#ffffff','#aec3bc',2.5));const sun=new T.DirectionalLight('#fff5e8',3.5);sun.position.set(5,10,7);scene.add(sun);
    const span=type.startsWith('worker-')?1.05:({client:1.4,crew:1.8,van:2.2,crane:3.2,warehouse:3.8,venue:3.8}[type]),cy=type==='crane'?1.8:1,camera=new T.OrthographicCamera(-span,span,span,-span,.1,100);camera.position.set(8,cy+9,11);camera.lookAt(0,cy,0);
    const renderer=new T.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});renderer.setSize(256,256);renderer.setPixelRatio(1);renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.2;renderer.render(scene,camera);const result=renderer.domElement.toDataURL('image/png').split(',')[1];geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();renderer.forceContextLoss();return result;
   },type);sprites.push(png);process.stdout.write(type+' rendered\n');
  }
  const atlas=await page.evaluate(async sprites=>{const canvas=document.createElement('canvas');canvas.width=1024;canvas.height=512;const ctx=canvas.getContext('2d');for(let i=0;i<sprites.length;i++){const image=new Image();image.src='data:image/png;base64,'+sprites[i];await image.decode();ctx.drawImage(image,(i%4)*256,Math.floor(i/4)*256);}return canvas.toDataURL('image/png').split(',')[1];},sprites);fs.writeFileSync(path.join(out,'event-world-atlas.png'),Buffer.from(atlas,'base64'));
 }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exitCode=1;});
