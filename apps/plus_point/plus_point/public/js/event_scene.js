/* Optional event scene. One template, bounded actors, no business mutations or polling. */
(()=>{
 frappe.provide('plus_point');
 const esc=value=>frappe.utils.escape_html(String(value??'')),count=value=>Math.max(0,Math.floor(Number(value)||0));
 const MAX_WORKERS=36,MAX_VEHICLES=6;
 let active=null;
 function timezone(){const value=frappe.boot?.time_zone?.system||frappe.sys_defaults?.time_zone||'UTC';try{new Intl.DateTimeFormat('en',{timeZone:value});return value;}catch{return 'UTC';}}
 function localNow(zone,now=new Date()){
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now).map(part=>[part.type,part.value]));
  return {day:parts.year+'-'+parts.month+'-'+parts.day,minutes:Number(parts.hour)*60+Number(parts.minute)};
 }
 function minutes(time){const match=/^(\d{2}):(\d{2})$/.exec(time||'');return match&&Number(match[1])<24&&Number(match[2])<60?Number(match[1])*60+Number(match[2]):null;}
 function snapshot(data,{site='',mode='schedule',start='09:00',end='18:00',now=new Date(),zone=timezone()}={}){
  const clock=localNow(zone,now),from=minutes(start),through=minutes(end),valid=from!==null&&through!==null&&from!==through;
  const overnight=valid&&through<from,inHours=valid&&(overnight?clock.minutes>=from||clock.minutes<through:clock.minutes>=from&&clock.minutes<through);
  // The early-morning part of an overnight shift belongs to the previous work date.
  const prior=new Date(clock.day+'T12:00:00Z');prior.setUTCDate(prior.getUTCDate()-1);
  const workDay=overnight&&clock.minutes<through?prior.toISOString().slice(0,10):clock.day;
  const day=mode==='schedule'?workDay:(workDay>=data.start_date&&workDay<=data.end_date?workDay:data.start_date);
  const sites=(data.timeline?.sites||[]).filter(item=>!site||item.site===site),ids=new Set(sites.map(item=>item.site));
  const booked=[...new Set((data.allocations||[]).filter(row=>ids.has(row.site)&&row.start_date<=day&&(!row.end_date||row.end_date>=day)).map(row=>row.employee))].length;
  const planned=sites.reduce((sum,item)=>sum+count(item.days?.find(row=>row.date===day)?.required??(data.staffing||[]).filter(row=>row.site===item.site&&row.start_date<=day&&row.end_date>=day).reduce((n,row)=>n+count(row.workers_required),0)),0);
  const cellAssigned=sites.reduce((sum,item)=>sum+Number(item.days?.find(row=>row.date===day)?.assigned||0),0);
  const assigned=Math.min(booked,count(cellAssigned));
  const vehicleRows=(data.reservations||[]).filter(row=>row.kind==='vehicle');
  const vehicles=vehicleRows.length?new Set(vehicleRows.filter(row=>(!site||row.site_id===site)&&row.start<=day&&row.end>=day).map(row=>row.title)).size:(!site?count(data.timeline?.vehicle_bookings):0);
  const within=day>=data.start_date&&day<=data.end_date,blocked=['Draft','Cancelled','Archived','Completed'].includes(data.event_status)||data.archived;
  const working=mode==='working'?true:mode==='closed'?false:valid&&within&&!blocked&&inHours;
  return {event:data.event_name||data.timeline?.title||__('Event'),reference:data.pp_reference||data.name||'',venue:sites.map(item=>item.title).join(', ')||__('No venue added'),planned,assigned,vehicles,working,mode,day,zone,start,end,valid,workerFigures:Math.min(MAX_WORKERS,assigned),vehicleFigures:Math.min(MAX_VEHICLES,vehicles),status:mode!=='schedule'?__('Demo preview'):!within?__(clock.day<data.start_date?'Upcoming event':'Event ended'):blocked?__(data.event_status||'Archived'):!valid?__('Set preview hours'):working?__('Within preview hours'):__('Outside preview hours')};
 }
 function createScene(host,initial,{onProject=()=>{}}={}){
  const T=window.PlusPointScene3D,geometries=new Set(),materials=new Set(),textures=new Set(),listeners=[],instances=[];
  let disposed=false,raf=0,last=0,elapsed=0,frames=0,paused=false,visible=!document.hidden,state=initial,angle=.68,zoom=1.2,observer,drag=null,shadowLight=null;
  const pan={x:3,z:1};
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),scene=new T.Scene(),camera=new T.OrthographicCamera(-24,24,16,-16,.1,160);
  const renderer=new T.WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;
  renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('role','img');renderer.domElement.setAttribute('aria-label',__('Event world. Drag or use arrow keys to explore; use the view buttons to zoom and rotate. Exact crew and vehicle counts are displayed over the scene.'));host.append(renderer.domElement);
  function dispose(){if(disposed)return;disposed=true;stop();observer?.disconnect();listeners.forEach(remove=>remove());instances.forEach(item=>item.dispose());shadowLight?.shadow.dispose();scene.clear();geometries.forEach(item=>item.dispose());materials.forEach(item=>item.dispose());textures.forEach(item=>item.dispose());renderer.dispose();renderer.forceContextLoss();renderer.domElement.remove();delete host.ppSceneDispose;}
  host.ppSceneDispose=dispose; // Also releases partial initialization if graphics fail.
  const geometry=value=>(geometries.add(value),value),material=(color,extra={})=>{const value=new T.MeshStandardMaterial({color,roughness:.85,...extra});materials.add(value);return value;};
  const boxGeo=geometry(new T.BoxGeometry(1,1,1)),roundGeo=geometry(new T.CylinderGeometry(1,1,1,12)),ballGeo=geometry(new T.SphereGeometry(1,10,8)),circleGeo=geometry(new T.CircleGeometry(1,24));
  const palette={white:material('#f6f8f3'),stone:material('#d6e2da'),teal:material('#087f70'),deep:material('#123f3d'),glass:material('#93c7be',{metalness:.25,roughness:.3}),road:material('#c3d1ca'),sand:material('#e1dfcf'),leaf:material('#398c71'),leafLight:material('#75ad89'),wood:material('#aa8563'),dark:material('#273b3c'),chrome:material('#c5d8d5'),window:material('#183f49'),light:material('#fff1b9',{emissive:'#ffdf87',emissiveIntensity:0}),sign:material('#0b6158')};
  const shadowMat=new T.MeshBasicMaterial({color:'#174c3d',transparent:true,opacity:.10,depthWrite:false});materials.add(shadowMat);
  function mesh(geo,mat,x,y,z,sx,sy,sz,parent=scene){const item=new T.Mesh(geo,mat);item.position.set(x,y,z);item.scale.set(sx,sy,sz);item.castShadow=!mat.transparent;item.receiveShadow=true;parent.add(item);return item;}
  const box=(mat,x,y,z,sx,sy,sz,parent)=>mesh(boxGeo,mat,x,y,z,sx,sy,sz,parent);
  function shadow(x,z,sx,sz,parent=scene){const item=mesh(circleGeo,shadowMat,x,.16,z,sx,sz,1,parent);item.rotation.x=-Math.PI/2;return item;}
  const hemi=new T.HemisphereLight('#f6fff9','#789c80',3),sun=new T.DirectionalLight('#fff6df',3.5);shadowLight=sun;sun.position.set(-15,26,18);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);Object.assign(sun.shadow.camera,{left:-34,right:34,top:34,bottom:-34,near:1,far:100});sun.shadow.camera.updateProjectionMatrix();sun.shadow.bias=-.0006;sun.shadow.normalBias=.035;scene.add(hemi,sun);
  // The world continues beyond the camera, rather than ending at a display plinth.
  const ground=mesh(geometry(new T.PlaneGeometry(180,180)),material('#e1eae4'),0,-.06,0,1,1,1);ground.rotation.x=-Math.PI/2;ground.castShadow=false;
  box(palette.white,0,.02,-.8,31,.16,24);box(palette.stone,0,.03,11.4,31.3,.18,.25);
  const grass=material('#bdd4bf'),neighbor=material('#d4e0da'),neighborGlass=material('#a6c1b7'),roadPaint=material('#fff5d7');
  box(palette.road,0,-.01,16,150,.05,8);box(palette.road,-21,-.01,-7,8,.05,70);box(palette.road,26,-.01,-7,7,.05,70);
  for(let x=-65;x<66;x+=4)box(roadPaint,x,.025,16,1.8,.02,.12);
  for(let z=-32;z<28;z+=4){box(roadPaint,-21,.025,z,.12,.02,1.8);box(roadPaint,26,.025,z,.12,.02,1.8);}
  for(const z of [12,20])box(palette.white,0,.02,z,150,.14,.55);
  for(const x of [-16.5,-25.5,21.5,30.1])box(palette.white,x,.02,-8,.55,.14,64);
  for(let i=0;i<7;i++){box(palette.white,-21,.03,10+i*.55,5.5,.025,.28);box(palette.white,26,.03,10+i*.55,5,.025,.28);}
  box(grass,-12,.1,-11,7,.12,5);box(grass,12,.1,-11,7,.12,5);box(grass,2,.02,-19,30,.06,6);
  // Soft surrounding blocks establish a place; they carry no invented event data.
  for(const [x,z,w,d,h] of [[-33,-15,12,13,5],[-33,5,11,9,3],[4,-30,22,10,5],[40,-10,13,16,4],[40,9,13,9,3]]){box(palette.white,x,.1,z,w+2,.2,d+2);box(neighbor,x,h/2+.2,z,w,h,d);box(palette.white,x,h+.32,z,w+.5,.25,d+.5);for(let j=0;j<Math.floor(w/3);j++)box(neighborGlass,x-w/2+1.6+j*3,h*.6,z+d/2+.01,1.8,h*.5,.04);}
  box(palette.road,0,.17,7.5,30.4,.04,5.4);box(palette.sand,-1,.18,2.5,22,.05,4.5);
  for(let x=-14;x<=14;x+=2)box(palette.white,x,.205,7.1,.8,.02,.10);
  // Fixed venue shell: all previews share this architecture and material palette.
  shadow(0,-3,11,5);box(palette.white,-1,2,-3.9,16,3.8,7.5);box(palette.deep,-1,.4,-3.9,16.3,.4,7.8);
  box(palette.glass,-1,1.9,-.10,14.5,2.6,.12);
  for(let x=-8;x<=6;x+=2.8){box(palette.white,x,1.95,.04,.14,3.1,.20);box(palette.light,x+1.35,3.15,.10,2.35,.12,.08);}
  box(palette.teal,-1,3.6,.12,16.3,.5,.25);box(palette.white,-1,4,-3.8,17,.35,8.1);
  for(let x=-9;x<8;x+=.65)box(palette.stone,x,4.22,-3.8,.10,.12,8.3);
  box(palette.teal,-1,4.32,-7.3,17.2,.40,.50);box(palette.white,-1,3.05,1,8,.18,2.2);
  for(const x of [-4.5,2.5])box(palette.teal,x,1.6,1.65,.12,3,.12);
  for(const x of [-3,-1.4,.2,1.8]){box(palette.deep,x,1.4,.03,1.25,2.45,.15);box(palette.light,x,1.5,.13,.85,1.75,.06);}
  box(palette.stone,-1,.27,1.1,8,.22,1.3);box(palette.white,-1,.18,2,9,.15,.5);
  // Entrance sign is generated locally; no textures or fonts are fetched.
  const label=document.createElement('canvas');label.width=1024;label.height=192;const ctx=label.getContext('2d');ctx.fillStyle='#0b6158';ctx.fillRect(0,0,1024,192);ctx.fillStyle='#ffffff';ctx.font='600 76px sans-serif';ctx.textAlign='center';ctx.fillText('PLUS POINT',512,100);ctx.font='24px sans-serif';ctx.fillText('E V E N T   P A V I L I O N',512,151);
  const texture=new T.CanvasTexture(label);texture.colorSpace=T.SRGBColorSpace;textures.add(texture);const labelMat=new T.MeshBasicMaterial({map:texture});materials.add(labelMat);mesh(geometry(new T.PlaneGeometry(5.8,1.08)),labelMat,-1,3.54,.27,1,1,1);
  // Quiet landscaped edge and parking remain constant across events.
  for(const [x,z] of [[-12,-7],[-12,-3],[-12,1],[11,-7],[11,-3],[11,1]]){box(palette.white,x,.35,z,1.6,.5,1.6);box(palette.stone,x,.62,z,1.45,.08,1.45);mesh(roundGeo,palette.wood,x,1.3,z,.12,1.4,.12);mesh(ballGeo,palette.leaf,x,2.5,z,.85,1.1,.85);mesh(ballGeo,palette.leafLight,x-.3,2.9,z,.64,.7,.64);shadow(x,z,1.25,.65);}
  for(const x of [-14,13]){box(palette.deep,x,1.8,4,.08,3.5,.08);box(palette.deep,x,3.55,3.7,.5,.12,.7);box(palette.light,x,3.47,3.7,.38,.04,.52);}
  // Arrival plaza, gateway and event banners make this an event venue, not a depot.
  box(palette.stone,-5,.14,9.8,8,.12,3);box(palette.teal,-9,2,9.8,.30,3.7,.35);box(palette.teal,-1,2,9.8,.30,3.7,.35);box(palette.teal,-5,3.9,9.8,8.3,.6,.40);
  for(const x of [-14,13]){box(palette.chrome,x,2.4,9.8,.07,4.6,.07);box(palette.teal,x+.55,3.2,9.8,1.1,1.8,.035);box(palette.white,x+.55,3.65,9.83,.55,.10,.025);}
  for(const x of [-12.5,11.5]){box(palette.wood,x,.6,5.1,2.4,.12,.55);for(const offset of [-.85,.85])box(palette.deep,x+offset,.35,5.1,.12,.5,.45);}
  for(const [x,z] of [[-13,-11],[13,-11],[-13,-17],[13,-17],[-28,-4],[-28,7],[32,-1],[32,8],[-9,23],[4,23],[17,23]]){mesh(roundGeo,palette.wood,x,.9,z,.13,1.8,.13);mesh(ballGeo,palette.leaf,x,2.4,z,.9,1.3,.9);mesh(ballGeo,palette.leafLight,x-.25,2.9,z,.7,.8,.7);}
  for(let x=-6;x<13;x+=3.4){box(palette.white,x,.21,9.4,.08,.02,3.1);}
  const vans=new T.Group();scene.add(vans);
  function van(index){const group=new T.Group();group.position.set(-7+index*3.5,.17,8.7);group.rotation.y=Math.PI/2;vans.add(group);shadow(0,0,1.9,.85,group);box(palette.white,0,1,0,1.35,1.28,3.15,group);box(palette.teal,0,.67,0,1.38,.32,3.17,group);box(palette.glass,0,1.22,1.59,1.08,.63,.025,group);box(palette.deep,0,.38,1.6,1.4,.18,.1,group);box(palette.light,-.45,.66,1.66,.23,.18,.06,group);box(palette.light,.45,.66,1.66,.23,.18,.06,group);for(const x of [-.69,.69])for(const z of [-.9,.95]){const tire=mesh(roundGeo,palette.dark,x,.34,z,.32,.13,.32,group);tire.rotation.z=Math.PI/2;for(const pos of [-.8,.1,.95])box(palette.window,x,1.28,pos,.025,.45,.55,group);}return group;}
  const instanced=(geo,mat,n)=>{const object=new T.InstancedMesh(geo,mat,n);object.instanceMatrix.setUsage(T.DynamicDrawUsage);object.frustumCulled=false;scene.add(object);instances.push(object);return object;};
  const actorMaterial=material('#ffffff'),bodies=instanced(boxGeo,actorMaterial,MAX_WORKERS),heads=instanced(ballGeo,actorMaterial,MAX_WORKERS),hats=instanced(ballGeo,palette.white,MAX_WORKERS),arms=instanced(boxGeo,actorMaterial,MAX_WORKERS*2),legs=instanced(boxGeo,palette.deep,MAX_WORKERS*2),feet=instanced(boxGeo,palette.dark,MAX_WORKERS*2),shadows=instanced(circleGeo,shadowMat,MAX_WORKERS),dummy=new T.Object3D();
  const colors=['#087f70','#178e7f','#3c7a8b','#daaa48'],skins=['#a87556','#c5916c','#deb490','#8f6047'];
  for(let i=0;i<MAX_WORKERS;i++){bodies.setColorAt(i,new T.Color(colors[i%9===0?3:i%3]));heads.setColorAt(i,new T.Color(skins[i%4]));for(let j=0;j<2;j++)arms.setColorAt(i*2+j,new T.Color(colors[i%9===0?3:i%3]));}
  function put(object,index,x,y,z,sx,sy,sz,rx=0,ry=0){dummy.position.set(x,y,z);dummy.scale.set(sx,sy,sz);dummy.rotation.set(rx,ry,0);dummy.updateMatrix();object.setMatrixAt(index,dummy.matrix);}
  function actors(time){
   for(let i=0;i<state.workerFigures;i++){
    const lane=i%3,w=14+lane*1.5,d=2.1+lane*.8,perimeter=2*(w+d),distance=(i*3.117+time*.48)%perimeter;
    let x,z,yaw;if(distance<w){x=distance-w/2-1;z=2.6+lane*.4;yaw=Math.PI/2;}else if(distance<w+d){x=w/2-1;z=2.6+lane*.4+distance-w;yaw=0;}else if(distance<2*w+d){x=w/2-1-(distance-w-d);z=2.6+lane*.4+d;yaw=-Math.PI/2;}else{x=-w/2-1;z=2.6+lane*.4+d-(distance-2*w-d);yaw=Math.PI;}
    const swing=state.working?Math.sin(time*5+i)*.42:0,c=Math.cos(yaw),s=Math.sin(yaw),part=(object,index,lx,y,lz,sx,sy,sz,rx=0)=>put(object,index,x+lx*c+lz*s,y,z-lx*s+lz*c,sx,sy,sz,rx,yaw);
    part(bodies,i,0,.87,0,.33,.43,.22);part(heads,i,0,1.22,0,.14,.16,.14);part(hats,i,0,1.33,0,.18,.085,.18);
    for(let j=0;j<2;j++){const direction=j?1:-1;part(arms,i*2+j,direction*.23,.86,Math.sin(swing*direction)*.12,.10,.44,.12,swing*direction);part(legs,i*2+j,direction*.09,.45,-Math.sin(swing*direction)*.12,.12,.43,.14,-swing*direction);part(feet,i*2+j,direction*.09,.22,-Math.sin(swing*direction)*.12+.04,.14,.11,.24);}
    put(shadows,i,x,.22,z,.32,.19,1,-Math.PI/2);
   }
   for(const item of instances)item.instanceMatrix.needsUpdate=true;
  }
  function lighting(){scene.background=new T.Color(state.working?'#e7f0e9':'#172f37');hemi.intensity=state.working?2.5:.85;sun.intensity=state.working?3.5:.35;sun.color.set(state.working?'#fff6df':'#87b4d2');palette.light.emissiveIntensity=state.working?1.4:0;palette.light.color.set(state.working?'#fff0bd':'#45656a');renderer.shadowMap.needsUpdate=true;}
  function update(next){state=next;for(const item of [bodies,heads,hats,shadows])item.count=state.workerFigures;for(const item of [arms,legs,feet])item.count=state.workerFigures*2;vans.clear();for(let i=0;i<state.vehicleFigures;i++)van(i);lighting();actors(elapsed);request();}
  function size(){if(disposed)return;const width=Math.max(1,host.clientWidth),height=Math.max(1,host.clientHeight),ratio=width/height,half=Math.max(12,21/ratio)/zoom;camera.left=-half*ratio;camera.right=half*ratio;camera.top=half;camera.bottom=-half;camera.position.set(pan.x+Math.sin(angle)*33,25,pan.z+Math.cos(angle)*33);camera.lookAt(pan.x,0,pan.z);camera.updateProjectionMatrix();camera.updateMatrixWorld();renderer.setSize(width,height,false);onProject(Object.fromEntries([['venue',-1,4,.5],['crew',-4,1.5,4],['vehicles',5,2,9]].map(([key,x,y,z])=>{const point=new T.Vector3(x,y,z).project(camera);return [key,{x:(point.x*.5+.5)*width,y:(.5-point.y*.5)*height}];})));request();}
  function animated(){return !disposed&&visible&&state.working&&state.workerFigures>0&&!paused&&!reduced.matches;}
  function tick(now){raf=0;if(disposed||!visible)return;if(!last||now-last>=1000/30){elapsed+=last?Math.min(.1,(now-last)/1000):0;last=now;actors(elapsed);renderer.render(scene,camera);frames++;}if(animated())raf=requestAnimationFrame(tick);}
  function request(){if(disposed||!visible||raf)return;last=0;raf=requestAnimationFrame(tick);}
  function stop(){cancelAnimationFrame(raf);raf=0;last=0;}
  function listen(target,event,fn){target.addEventListener(event,fn);listeners.push(()=>target.removeEventListener(event,fn));}
  listen(renderer.domElement,'pointerdown',event=>{if(event.button!==0)return;drag={x:event.clientX,y:event.clientY};renderer.domElement.setPointerCapture(event.pointerId);});
  listen(renderer.domElement,'pointermove',event=>{if(!drag)return;const dx=event.clientX-drag.x,dy=event.clientY-drag.y,scale=(camera.right-camera.left)/Math.max(1,host.clientWidth);pan.x=Math.max(-16,Math.min(16,pan.x-(dx*Math.cos(angle)+dy*Math.sin(angle))*scale));pan.z=Math.max(-16,Math.min(18,pan.z+(dx*Math.sin(angle)-dy*Math.cos(angle))*scale));drag={x:event.clientX,y:event.clientY};size();});
  listen(renderer.domElement,'pointerup',()=>drag=null);listen(renderer.domElement,'pointercancel',()=>drag=null);
  listen(renderer.domElement,'keydown',event=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home'].includes(event.key))return;event.preventDefault();if(event.key==='Home'){pan.x=3;pan.z=1;angle=.68;zoom=1.2;}else{pan.x=Math.max(-16,Math.min(16,pan.x+(event.key==='ArrowRight'?1:event.key==='ArrowLeft'?-1:0)));pan.z=Math.max(-16,Math.min(18,pan.z+(event.key==='ArrowDown'?1:event.key==='ArrowUp'?-1:0)));}size();});
  listen(document,'visibilitychange',()=>{visible=!document.hidden;if(visible)request();else stop();});listen(reduced,'change',()=>{stop();request();});
  listen(renderer.domElement,'webglcontextlost',event=>{event.preventDefault();stop();host.dispatchEvent(new CustomEvent('pp-scene-context-lost'));});
  observer=new ResizeObserver(size);observer.observe(host); // Exactly one, owned by the open scene.
  update(initial);size();
  return {update,pause(value){paused=value;stop();request();},view(delta=0,scale=0){angle+=delta;zoom=Math.max(.75,Math.min(2,zoom+scale));size();},reset(){angle=.68;zoom=1.2;pan.x=3;pan.z=1;size();},capture(){if(disposed)return null;renderer.render(scene,camera);return renderer.domElement.toDataURL('image/webp',.78);},stats:()=>({disposed,frames,running:!!raf,drawCalls:renderer.info.render.calls,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,workerFigures:state.workerFigures,vehicleFigures:state.vehicleFigures,pixelRatio:renderer.getPixelRatio(),pan:{...pan},zoom}),dispose};
 }
 function open(data,{onSection,onPoster}={}){
  active?.close();
  const dialog=new frappe.ui.Dialog({title:__('Event scene'),size:'extra-large',fields:[{fieldtype:'HTML',fieldname:'scene'}]});
  dialog.$wrapper.addClass('pp-event-scene-dialog');const root=dialog.fields_dict.scene.$wrapper[0];root.classList.add('pp-event-scene');
  root.innerHTML=`<div class="pp-scene-intro"><div><h3>${esc(data.event_name)}</h3><p>${esc(data.pp_reference||data.name)}</p></div><span class="pp-ui-badge" data-tone="info">${esc(__('Scheduled activity demo'))}</span></div>
   <div class="pp-scene-controls"><fieldset><legend>${esc(__('Preview'))}</legend><div class="pp-scene-modes">${[['schedule','Now'],['working','Working hours'],['closed','After hours']].map(([value,label])=>`<label><input type="radio" name="pp-scene-mode" value="${value}" ${value==='working'?'checked':''}><span>${esc(__(label))}</span></label>`).join('')}</div></fieldset><label class="pp-scene-venue-label">${esc(__('Venue'))}<select class="form-control" data-scene-site><option value="">${esc(__('All venues'))}</option>${(data.timeline?.sites||[]).map(site=>`<option value="${esc(site.site)}">${esc(site.title)}</option>`).join('')}</select></label></div>
   <div class="pp-scene-stage"><div class="pp-scene-canvas"></div>
    <dl class="pp-scene-facts">${[['planned','Required crew','users'],['assigned','Assigned crew','user'],['vehicles','Booked vehicles','truck']].map(([key,label,icon])=>`<div><dt><span class="pp-scene-fact-icon">${plus_point.icon(icon)}</span>${esc(__(label))}</dt><dd data-scene-count="${key}"></dd></div>`).join('')}</dl>
    <div class="pp-scene-markers">${[['venue','Explore venue','pin'],['crew','Inspect crew','users'],['vehicles','Inspect vehicles','truck']].map(([key,label,icon])=>`<button type="button" class="pp-scene-marker" data-scene-marker="${key}" aria-label="${esc(__(label))}" aria-pressed="${key==='venue'}" title="${esc(__(label))}">${plus_point.icon(icon)}</button>`).join('')}</div>
    <aside class="pp-scene-inspector" aria-label="${esc(__('Scene details'))}"><header><span>${plus_point.icon('pin')}</span><div><small data-scene-inspector-label>${esc(__('Event venue'))}</small><h4 data-scene-place></h4></div></header><div class="pp-scene-status"><span class="pp-ui-badge" data-scene-status></span></div><dl data-scene-inspection></dl>${onSection?`<button type="button" class="btn btn-default" data-scene-section>${esc(__('View venue details'))}</button>`:''}</aside>
    <div class="pp-scene-explore-hint">${plus_point.icon('pin')}<span>${esc(__('Drag to explore'))}</span></div>
    <div class="pp-scene-view-controls">${[['rotate-left','Rotate left','back'],['rotate-right','Rotate right','right'],['zoom-out','Zoom out','minus'],['zoom-in','Zoom in','plus'],['reset','Reset view','refresh'],['motion','Pause animation','pause']].map(([action,label,icon])=>`<button type="button" class="btn btn-default" data-scene-action="${action}" aria-label="${esc(__(label))}" title="${esc(__(label))}">${plus_point.icon(icon)}<span class="sr-only">${esc(__(label))}</span></button>`).join('')}</div>
   </div>
   <p class="pp-scene-explanation">${esc(__('Illustration based on saved assignments, not live positions. Larger teams use representative figures; the counts above remain exact.'))}</p>
   <details class="pp-scene-hours"><summary>${esc(__('Preview working hours'))}</summary><div><label>${esc(__('Starts'))}<input class="form-control" type="time" value="09:00" data-scene-start></label><label>${esc(__('Ends'))}<input class="form-control" type="time" value="18:00" data-scene-end></label><span>${esc(timezone())}</span></div><p>${esc(__('These hours are for this demo only and are not saved to the event. Now uses the current date and time in the site timezone.'))}</p><p data-scene-hours-error role="alert" hidden></p></details>
   <div class="pp-scene-footer"><span data-scene-caption></span><button type="button" class="btn btn-default" data-scene-close>${esc(__('Back to event details'))}</button></div>`;
  const host=root.querySelector('.pp-scene-canvas'),mode=()=>root.querySelector('[name=pp-scene-mode]:checked').value;
  let component=null,closed=false,paused=false,boundaryTimer=0;
  const input=()=>({mode:mode(),site:root.querySelector('[data-scene-site]').value,start:root.querySelector('[data-scene-start]').value,end:root.querySelector('[data-scene-end]').value});
  function inspect(state){const section=root.dataset.inspection||'venue',label=section==='crew'?__('Crew and staffing'):section==='vehicles'?__('Transport'):__('Event venue');root.querySelector('[data-scene-inspector-label]').textContent=label;root.querySelector('[data-scene-place]').textContent=section==='venue'?state.venue:section==='crew'?__('Crew on this event'):__('Booked transport');const rows=section==='crew'?[[__('Assigned'),state.assigned],[__('Required'),state.planned],[__('Still needed'),Math.max(0,state.planned-state.assigned)],[__('Work date'),state.day]]:section==='vehicles'?[[__('Booked vehicles'),state.vehicles],[__('Work date'),state.day],[__('Venue'),state.venue]]:[[__('Work date'),state.day],[__('Preview hours'),state.start+' – '+state.end],[__('Time zone'),state.zone]];root.querySelector('[data-scene-inspection]').innerHTML=rows.map(([label,value])=>'<div><dt>'+esc(label)+'</dt><dd>'+esc(value)+'</dd></div>').join('');root.querySelectorAll('[data-scene-marker]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.sceneMarker===section)));const action=root.querySelector('[data-scene-section]');if(action){action.textContent=__(section==='crew'?'View crew details':section==='vehicles'?'View transport details':'View venue details');action.onclick=()=>{active?.close();onSection(section==='vehicles'?'transport':'crew');};}}
  function refresh(){const state=snapshot(data,input()),error=root.querySelector('[data-scene-hours-error]');error.hidden=state.valid;error.textContent=state.valid?'':__('Choose different valid start and end times. Overnight hours are supported.');root.querySelectorAll('.pp-scene-hours input').forEach(field=>field.setAttribute('aria-invalid',String(!state.valid)));for(const key of ['planned','assigned','vehicles'])root.querySelector('[data-scene-count='+key+']').textContent=new Intl.NumberFormat().format(state[key]);const status=root.querySelector('[data-scene-status]');status.textContent=__(state.working?'Lights on · Working hours':'Lights off · Resting');status.dataset.tone=state.working?'success':'neutral';root.querySelector('[data-scene-caption]').textContent=state.status+' · '+state.day;root.dataset.lighting=state.working?'on':'off';inspect(state);if(component)component.update(state);return state;}
  function scheduleBoundary(){clearTimeout(boundaryTimer);if(closed||mode()!=='schedule')return;const clock=localNow(timezone()),options=input(),points=[minutes(options.start),minutes(options.end),1440].filter(value=>value!==null).map(value=>value<=clock.minutes?value+1440:value),wait=(Math.min(...points)-clock.minutes)*60000-new Date().getSeconds()*1000;boundaryTimer=setTimeout(()=>{refresh();scheduleBoundary();},Math.max(1000,wait));}
  const close=()=>{if(closed)return;closed=true;clearTimeout(boundaryTimer);try{if(onPoster&&component){const poster=component.capture();if(poster&&poster.length<350000)onPoster(poster);}}catch{/* A still preview must never prevent native dialog cleanup. */}finally{component?.dispose();if(active?.root===root)active=null;}};
  active={root,close:()=>{close();plus_point.close_dialog(dialog);}};dialog.$wrapper.one('hide.bs.modal',close);dialog.$wrapper.one('hidden.bs.modal',()=>dialog.$wrapper.remove());
  root.ppScene={stats:()=>component?.stats(),capture:()=>component?.capture(),close:()=>active?.close()};
  root.querySelector('[data-scene-close]').onclick=()=>active?.close();
  root.querySelectorAll('[name=pp-scene-mode],select,input[type=time]').forEach(field=>field.addEventListener('change',()=>{refresh();scheduleBoundary();}));
  root.querySelectorAll('[data-scene-marker]').forEach(button=>button.onclick=()=>{root.dataset.inspection=button.dataset.sceneMarker;inspect(snapshot(data,input()));});
  root.querySelectorAll('[data-scene-action]').forEach(button=>button.onclick=()=>{if(!component)return;const action=button.dataset.sceneAction;if(action==='reset')component.reset();else if(action==='motion'){paused=!paused;component.pause(paused);const label=__(paused?'Resume animation':'Pause animation');button.setAttribute('aria-label',label);button.title=label;button.innerHTML=plus_point.icon(paused?'play':'pause')+'<span class="sr-only">'+esc(label)+'</span>';}else component.view(action==='rotate-left'?-.25:action==='rotate-right'?.25:0,action==='zoom-in'?.15:action==='zoom-out'?-.15:0);});
  function unavailable(){component?.dispose();host.ppSceneDispose?.();component=null;host.innerHTML='<div class="pp-scene-unavailable" role="status"><strong>'+esc(__('3D preview is unavailable in this browser'))+'</strong><p>'+esc(__('The event counts are available below. You can continue managing the event in its details.'))+'</p></div>';root.querySelectorAll('[data-scene-action]').forEach(button=>button.disabled=true);root.dataset.ready='fallback';}
  host.addEventListener('pp-scene-context-lost',unavailable,{once:true});
  dialog.$wrapper.one('shown.bs.modal',()=>{if(closed)return;try{component=createScene(host,refresh(),{onProject:positions=>{for(const [key,position] of Object.entries(positions)){const marker=root.querySelector('[data-scene-marker='+key+']');marker.style.left=position.x+'px';marker.style.top=position.y+'px';marker.hidden=position.x<24||position.x>host.clientWidth-24||position.y<110||position.y>host.clientHeight-60;}}});root.dataset.ready='true';}catch(error){root.ppScene.error=error.message;unavailable();}});
  refresh();scheduleBoundary();dialog.show();return root;
 }
 plus_point.event_scene={version:3,snapshot,mount:createScene,open,close:()=>active?.close()};
})();
