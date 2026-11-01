/* Decorative, scroll-driven event story. No WebGL, timers, polling or business mutations. */
(()=>{frappe.provide('plus_point');const pp=plus_point;
 pp.dashboard_journey={mount(root){
  const scroll=root.closest('.main-section')||document.querySelector('.main-section')||document.scrollingElement,motion=matchMedia('(prefers-reduced-motion: reduce)'),wide=matchMedia('(min-width:1600px)');
  let dead=false,frame=0,length=0,visible=false;
  const layer=document.createElement('div');layer.className='pp-journey-layer';layer.setAttribute('aria-hidden','true');
  const sprite=(name,extra='')=>{const i=['client','crew','van','crane','warehouse','venue','worker-orange','worker-teal'].indexOf(({attendance:'crew',approved:'client',billing:'client'})[name]||name);return '<i class="pp-journey-sprite '+extra+'" style="--sprite-x:'+((i%4)*100/3)+'%;--sprite-y:'+Math.floor(i/4)*100+'%"></i>';};
  const checkpoints=[['client','Agreement',.01],['crew','Crew',.19],['warehouse','Warehouse',.43],['venue','Event site',.66],['crane','Delivery',.75],['attendance','Attendance',.83],['approved','Approved work',.92],['billing','Client billing',.99]];
  layer.innerHTML='<svg class="pp-journey-road"><path class="pp-journey-road-bed"/><path class="pp-journey-road-lane"/></svg>'+checkpoints.map(([name,label])=>'<div class="pp-journey-checkpoint" data-checkpoint="'+name+'">'+sprite(name)+'<span>'+frappe.utils.escape_html(__(label))+'</span></div>').join('')+'<div class="pp-journey-traveller" data-traveller="van">'+sprite('van')+'</div><div class="pp-journey-traveller" data-traveller="worker">'+sprite('worker-orange')+'</div><div class="pp-journey-traveller" data-traveller="second">'+sprite('worker-teal')+'</div>';
  root.prepend(layer);root.classList.add('pp-has-journey');const road=layer.querySelector('.pp-journey-road-bed'),lane=layer.querySelector('.pp-journey-road-lane'),workflow=root.querySelector('.pp-overview-workflow');
  const place=(node,p,offset=0)=>{const point=road.getPointAtLength(Math.max(0,Math.min(1,p))*length);node.style.transform='translate3d('+(point.x+offset)+'px,'+point.y+'px,0) translate(-50%,-50%)';};
  function update(){frame=0;if(dead||!root.isConnected||!wide.matches||!length)return;
   const viewport=scroll===document.scrollingElement?innerHeight:scroll.clientHeight,rect=root.getBoundingClientRect(),sr=scroll===document.scrollingElement?{top:0}:scroll.getBoundingClientRect(),progress=Math.max(0,Math.min(1,(sr.top-rect.top)/(root.offsetHeight-viewport||1)));
   const p=motion.matches ? .02 : .02+progress*.94,van=layer.querySelector('[data-traveller=van]'),worker=layer.querySelector('[data-traveller=worker]'),second=layer.querySelector('[data-traveller=second]');
   place(van,p);place(worker,p,-12);place(second,Math.max(.01,p-.015),12);const walking=p<.24||p>.64;van.style.opacity=walking?'.28':'1';worker.style.opacity=walking?'1':'0';second.style.opacity=walking?'1':'0';
   layer.dataset.stage=p<.18?'agreement':p<.3?'boarding':p<.64?'travelling':p<.85?'working':'complete';
  }
  const schedule=()=>{if(!dead&&!frame&&wide.matches)frame=requestAnimationFrame(update);};
  function resize(){if(dead)return;const w=layer.clientWidth,h=root.offsetHeight;if(w<1||h<1||!wide.matches)return;const left=30,right=w-30,bottom=Math.max(300,h-80),d='M '+left+' 50 L '+left+' '+(bottom-40)+' Q '+left+' '+bottom+' '+(left+40)+' '+bottom+' L '+(right-40)+' '+bottom+' Q '+right+' '+bottom+' '+right+' '+(bottom-40)+' L '+right+' 50';road.setAttribute('d',d);lane.setAttribute('d',d);length=road.getTotalLength();checkpoints.forEach(([name,,p])=>place(layer.querySelector('[data-checkpoint='+name+']'),p));schedule();}
  const animationState=()=>workflow?.classList.toggle('pp-workflow-running',visible&&!document.hidden&&!motion.matches);
  const observer=workflow?new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;animationState();},{threshold:.1}):null;observer?.observe(workflow);
  const onMotion=()=>{animationState();schedule();},onWide=()=>resize();scroll.addEventListener('scroll',schedule,{passive:true});document.addEventListener('visibilitychange',animationState);motion.addEventListener('change',onMotion);wide.addEventListener('change',onWide);
  resize();
  return{resize,destroy(){if(dead)return;dead=true;cancelAnimationFrame(frame);scroll.removeEventListener('scroll',schedule);document.removeEventListener('visibilitychange',animationState);motion.removeEventListener('change',onMotion);wide.removeEventListener('change',onWide);observer?.disconnect();workflow?.classList.remove('pp-workflow-running');root.classList.remove('pp-has-journey');layer.remove();}};
 }};
})();
