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
 function createScene(host,initial){
  const T=window.PlusPointScene3D,geometries=new Set(),materials=new Set(),textures=new Set(),listeners=[],instances=[];
  let disposed=false,raf=0,last=0,elapsed=0,frames=0,paused=false,visible=!document.hidden,state=initial,angle=.68,zoom=1,observer;
  const reduced=matchMedia('(prefers-reduced-motion: reduce)'),scene=new T.Scene(),camera=new T.OrthographicCamera(-24,24,16,-16,.1,160);
  const renderer=new T.WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,1.5));renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
  renderer.domElement.setAttribute('role','img');renderer.domElement.setAttribute('aria-label',__('Illustrated event venue with assigned workers and booked vehicles. Counts are available below.'));host.append(renderer.domElement);
  function dispose(){if(disposed)return;disposed=true;stop();observer?.disconnect();listeners.forEach(remove=>remove());instances.forEach(item=>item.dispose());scene.clear();geometries.forEach(item=>item.dispose());materials.forEach(item=>item.dispose());textures.forEach(item=>item.dispose());renderer.dispose();renderer.forceContextLoss();renderer.domElement.remove();delete host.ppSceneDispose;}
  host.ppSceneDispose=dispose; // Also releases partial initialization if graphics fail.
  const geometry=value=>(geometries.add(value),value),material=(color,extra={})=>{const value=new T.MeshStandardMaterial({color,roughness:.85,...extra});materials.add(value);return value;};
  const boxGeo=geometry(new T.BoxGeometry(1,1,1)),roundGeo=geometry(new T.CylinderGeometry(1,1,1,12)),ballGeo=geometry(new T.SphereGeometry(1,10,8)),circleGeo=geometry(new T.CircleGeometry(1,24));
  const palette={white:material('#f6f8f3'),stone:material('#d6e2da'),teal:material('#087f70'),deep:material('#123f3d'),glass:material('#93c7be',{metalness:.25,roughness:.3}),road:material('#c3d1ca'),sand:material('#e1dfcf'),leaf:material('#398c71'),leafLight:material('#75ad89'),wood:material('#aa8563'),dark:material('#273b3c'),chrome:material('#c5d8d5'),window:material('#183f49'),light:material('#fff1b9',{emissive:'#ffdf87',emissiveIntensity:0}),sign:material('#0b6158')};
  const shadowMat=new T.MeshBasicMaterial({color:'#174c3d',transparent:true,opacity:.10,depthWrite:false});materials.add(shadowMat);
  function mesh(geo,mat,x,y,z,sx,sy,sz,parent=scene){const item=new T.Mesh(geo,mat);item.position.set(x,y,z);item.scale.set(sx,sy,sz);parent.add(item);return item;}
  const box=(mat,x,y,z,sx,sy,sz,parent)=>mesh(boxGeo,mat,x,y,z,sx,sy,sz,parent);
  function shadow(x,z,sx,sz,parent=scene){const item=mesh(circleGeo,shadowMat,x,.16,z,sx,sz,1,parent);item.rotation.x=-Math.PI/2;return item;}
  const hemi=new T.HemisphereLight('#f6fff9','#789c80',3),sun=new T.DirectionalLight('#fff6df',3.5);sun.position.set(-9,18,12);scene.add(hemi,sun);
  box(palette.stone,0,-.38,0,31,.8,23);box(palette.white,0,.06,0,30.7,.18,22.7);
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
  function lighting(){scene.background=new T.Color(state.working?'#e7f0e9':'#172f37');hemi.intensity=state.working?3:1.4;sun.intensity=state.working?3.5:.45;sun.color.set(state.working?'#fff6df':'#87b4d2');palette.light.emissiveIntensity=state.working?1.4:0;palette.light.color.set(state.working?'#fff0bd':'#45656a');}
  function update(next){state=next;for(const item of [bodies,heads,hats,shadows])item.count=state.workerFigures;for(const item of [arms,legs,feet])item.count=state.workerFigures*2;vans.clear();for(let i=0;i<state.vehicleFigures;i++)van(i);lighting();actors(elapsed);request();}
  function size(){if(disposed)return;const width=Math.max(1,host.clientWidth),height=Math.max(1,host.clientHeight),ratio=width/height,half=Math.max(12,21/ratio)/zoom;camera.left=-half*ratio;camera.right=half*ratio;camera.top=half;camera.bottom=-half;camera.position.set(Math.sin(angle)*33,25,Math.cos(angle)*33);camera.lookAt(-1,0,0);camera.updateProjectionMatrix();renderer.setSize(width,height,false);request();}
  function animated(){return !disposed&&visible&&state.working&&state.workerFigures>0&&!paused&&!reduced.matches;}
  function tick(now){raf=0;if(disposed||!visible)return;if(!last||now-last>=1000/30){elapsed+=last?Math.min(.1,(now-last)/1000):0;last=now;actors(elapsed);renderer.render(scene,camera);frames++;}if(animated())raf=requestAnimationFrame(tick);}
  function request(){if(disposed||!visible||raf)return;last=0;raf=requestAnimationFrame(tick);}
  function stop(){cancelAnimationFrame(raf);raf=0;last=0;}
  function listen(target,event,fn){target.addEventListener(event,fn);listeners.push(()=>target.removeEventListener(event,fn));}
  listen(document,'visibilitychange',()=>{visible=!document.hidden;if(visible)request();else stop();});listen(reduced,'change',()=>{stop();request();});
  listen(renderer.domElement,'webglcontextlost',event=>{event.preventDefault();stop();host.dispatchEvent(new CustomEvent('pp-scene-context-lost'));});
  observer=new ResizeObserver(size);observer.observe(host); // Exactly one, owned by the open scene.
  update(initial);size();
  return {update,pause(value){paused=value;stop();request();},view(delta=0,scale=0){angle+=delta;zoom=Math.max(.75,Math.min(1.6,zoom+scale));size();},reset(){angle=.68;zoom=1;size();},stats:()=>({disposed,frames,running:!!raf,drawCalls:renderer.info.render.calls,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,workerFigures:state.workerFigures,vehicleFigures:state.vehicleFigures,pixelRatio:renderer.getPixelRatio()}),dispose};
 }
 function open(data){
  active?.close();
  const dialog=new frappe.ui.Dialog({title:__('Event scene'),size:'extra-large',fields:[{fieldtype:'HTML',fieldname:'scene'}]});
  dialog.$wrapper.addClass('pp-event-scene-dialog');const root=dialog.fields_dict.scene.$wrapper[0];root.classList.add('pp-event-scene');
  root.innerHTML=`<div class="pp-scene-intro"><div><h3>${esc(data.event_name)}</h3><p>${esc(data.pp_reference||data.name)}</p></div><span class="pp-ui-badge" data-tone="info">${esc(__('Scheduled activity demo'))}</span></div>
   <div class="pp-scene-controls"><fieldset><legend>${esc(__('Preview'))}</legend><div class="pp-scene-modes">${[['schedule','Now'],['working','Working hours'],['closed','After hours']].map(([value,label])=>`<label><input type="radio" name="pp-scene-mode" value="${value}" ${value==='working'?'checked':''}><span>${esc(__(label))}</span></label>`).join('')}</div></fieldset><label class="pp-scene-venue-label">${esc(__('Venue'))}<select class="form-control" data-scene-site><option value="">${esc(__('All venues'))}</option>${(data.timeline?.sites||[]).map(site=>`<option value="${esc(site.site)}">${esc(site.title)}</option>`).join('')}</select></label></div>
   <div class="pp-scene-stage"><div class="pp-scene-status"><span class="pp-ui-badge" data-scene-status></span><span data-scene-place></span></div><div class="pp-scene-canvas"></div><div class="pp-scene-view-controls">${[['rotate-left','Rotate left','back'],['rotate-right','Rotate right','right'],['zoom-out','Zoom out','minus'],['zoom-in','Zoom in','plus'],['reset','Reset view','refresh'],['motion','Pause animation','pause']].map(([action,label,icon])=>`<button type="button" class="btn btn-default" data-scene-action="${action}" aria-label="${esc(__(label))}" title="${esc(__(label))}">${plus_point.icon(icon)}<span class="sr-only">${esc(__(label))}</span></button>`).join('')}</div></div>
   <dl class="pp-scene-facts">${[['planned','Required crew'],['assigned','Available assigned crew'],['vehicles','Booked vehicles']].map(([key,label])=>`<div><dt>${esc(__(label))}</dt><dd data-scene-count="${key}"></dd></div>`).join('')}</dl>
   <p class="pp-scene-explanation">${esc(__('Illustration based on saved assignments, not live positions. Larger teams use representative figures; the counts above remain exact.'))}</p>
   <details class="pp-scene-hours"><summary>${esc(__('Preview working hours'))}</summary><div><label>${esc(__('Starts'))}<input class="form-control" type="time" value="09:00" data-scene-start></label><label>${esc(__('Ends'))}<input class="form-control" type="time" value="18:00" data-scene-end></label><span>${esc(timezone())}</span></div><p>${esc(__('These hours are for this demo only and are not saved to the event. Now uses the current date and time in the site timezone.'))}</p><p data-scene-hours-error role="alert" hidden></p></details>
   <div class="pp-scene-footer"><span data-scene-caption></span><button type="button" class="btn btn-default" data-scene-close>${esc(__('Back to event details'))}</button></div>`;
  const host=root.querySelector('.pp-scene-canvas'),mode=()=>root.querySelector('[name=pp-scene-mode]:checked').value;
  let component=null,closed=false,paused=false,boundaryTimer=0;
  const input=()=>({mode:mode(),site:root.querySelector('[data-scene-site]').value,start:root.querySelector('[data-scene-start]').value,end:root.querySelector('[data-scene-end]').value});
  function refresh(){const state=snapshot(data,input()),error=root.querySelector('[data-scene-hours-error]');error.hidden=state.valid;error.textContent=state.valid?'':__('Choose different valid start and end times. Overnight hours are supported.');root.querySelectorAll('.pp-scene-hours input').forEach(field=>field.setAttribute('aria-invalid',String(!state.valid)));for(const key of ['planned','assigned','vehicles'])root.querySelector('[data-scene-count='+key+']').textContent=new Intl.NumberFormat().format(state[key]);const status=root.querySelector('[data-scene-status]');status.textContent=__(state.working?'Lights on · Working hours':'Lights off · Resting');status.dataset.tone=state.working?'success':'neutral';root.querySelector('[data-scene-place]').textContent=state.venue;root.querySelector('[data-scene-caption]').textContent=state.status+' · '+state.day;root.dataset.lighting=state.working?'on':'off';if(component)component.update(state);return state;}
  function scheduleBoundary(){clearTimeout(boundaryTimer);if(closed||mode()!=='schedule')return;const clock=localNow(timezone()),options=input(),points=[minutes(options.start),minutes(options.end),1440].filter(value=>value!==null).map(value=>value<=clock.minutes?value+1440:value),wait=(Math.min(...points)-clock.minutes)*60000-new Date().getSeconds()*1000;boundaryTimer=setTimeout(()=>{refresh();scheduleBoundary();},Math.max(1000,wait));}
  const close=()=>{if(closed)return;closed=true;clearTimeout(boundaryTimer);component?.dispose();if(active?.root===root)active=null;};
  active={root,close:()=>{close();plus_point.close_dialog(dialog);}};dialog.$wrapper.one('hide.bs.modal',close);dialog.$wrapper.one('hidden.bs.modal',()=>dialog.$wrapper.remove());
  root.ppScene={stats:()=>component?.stats(),close:()=>active?.close()};
  root.querySelector('[data-scene-close]').onclick=()=>active?.close();
  root.querySelectorAll('[name=pp-scene-mode],select,input[type=time]').forEach(field=>field.addEventListener('change',()=>{refresh();scheduleBoundary();}));
  root.querySelectorAll('[data-scene-action]').forEach(button=>button.onclick=()=>{if(!component)return;const action=button.dataset.sceneAction;if(action==='reset')component.reset();else if(action==='motion'){paused=!paused;component.pause(paused);const label=__(paused?'Resume animation':'Pause animation');button.setAttribute('aria-label',label);button.title=label;button.innerHTML=plus_point.icon(paused?'play':'pause')+'<span class="sr-only">'+esc(label)+'</span>';}else component.view(action==='rotate-left'?-.25:action==='rotate-right'?.25:0,action==='zoom-in'?.15:action==='zoom-out'?-.15:0);});
  function unavailable(){component?.dispose();host.ppSceneDispose?.();component=null;host.innerHTML='<div class="pp-scene-unavailable" role="status"><strong>'+esc(__('3D preview is unavailable in this browser'))+'</strong><p>'+esc(__('The event counts are available below. You can continue managing the event in its details.'))+'</p></div>';root.querySelectorAll('[data-scene-action]').forEach(button=>button.disabled=true);root.dataset.ready='fallback';}
  host.addEventListener('pp-scene-context-lost',unavailable,{once:true});
  dialog.$wrapper.one('shown.bs.modal',()=>{if(closed)return;try{component=createScene(host,refresh());root.dataset.ready='true';}catch(error){root.ppScene.error=error.message;unavailable();}});
  refresh();scheduleBoundary();dialog.show();return root;
 }
 plus_point.event_scene={version:1,snapshot,open,close:()=>active?.close()};
})();
