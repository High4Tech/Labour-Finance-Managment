/* Four bounded, lazy illustrated workflow banners. No dashboard WebGL renderer. */
(()=>{
 frappe.provide('plus_point');const pp=plus_point,esc=v=>frappe.utils.escape_html(String(v??''));
 pp.dashboard_journey={mount(root){
  const types=['client','crew','van','crane','warehouse','venue','worker-orange','worker-teal','client-active','warehouse-active','venue-active','loader'];
  const sprite=(type,extra='')=>{const i=types.indexOf(type);return '<i class="pp-journey-sprite '+extra+'" style="--sprite-x:'+((i%4)*100/3)+'%;--sprite-y:'+(Math.floor(i/4)*50)+'%"></i>';};
  const scenes=[
   {type:'client',pose:'client-active',place:'Client office',title:'Start with an agreement',description:'Agree the scope, client rates and payment milestones before the work begins.',cta:'Create agreement',href:'/desk/pp-agreements?record=new',vehicle:'van'},
   {type:'crew',place:'Worker house',title:'Get your team ready',description:'Keep worker profiles, pay and availability together. Plan the vehicles that take your crew to site.',cta:'Manage workers',href:'/desk/employee',secondary:'Manage vehicles',secondaryHref:'/desk/pp-inventory?view=vehicles',vehicle:'van'},
   {type:'warehouse',pose:'warehouse-active',place:'Warehouse',title:'Prepare the equipment',description:'See what is available, where it is stored and what is reserved. Send the right inventory to each event.',cta:'Manage inventory',href:'/desk/pp-inventory?view=equipment',vehicle:'loader'},
   {type:'venue',pose:'venue-active',place:'Event site',title:'Bring the plan to life',description:'Assign crew and vehicles, track attendance and follow the work through to payment.',cta:'Create event',href:'/desk/pp-event-plans?record=new',vehicle:'loader'}
  ];
  const section=document.createElement('section');section.className='pp-journey-banners';section.setAttribute('aria-label',__('From agreement to delivery'));
  section.innerHTML='<header><h2>'+esc(__('From agreement to delivery'))+'</h2><p>'+esc(__('Everything you need to move the work forward.'))+'</p></header><div class="pp-journey-grid">'+scenes.map(s=>'<article class="pp-journey-banner" data-scene="'+s.type+'"><div class="pp-journey-world" aria-hidden="true"><div class="pp-journey-road"></div><div class="pp-journey-model">'+sprite(s.type)+(s.pose?sprite(s.pose,'pp-journey-pose'):'')+'</div><div class="pp-journey-vehicle">'+sprite(s.vehicle)+'</div><div class="pp-journey-walker">'+sprite('worker-orange')+'</div><span class="pp-journey-place">'+esc(__(s.place))+'</span></div><div class="pp-journey-story"><h3>'+esc(__(s.title))+'</h3><p>'+esc(__(s.description))+'</p><div class="pp-journey-actions"><a class="btn btn-primary" href="'+s.href+'">'+esc(__(s.cta))+'</a>'+(s.secondary?'<a class="pp-journey-secondary" href="'+s.secondaryHref+'">'+esc(__(s.secondary))+'</a>':'')+'</div></div></article>').join('')+'</div>';
  root.append(section);
  const motion=matchMedia('(prefers-reduced-motion: reduce)');let dead=false,loaded=false;
  const wake=()=>{section.classList.toggle('pp-journey-paused',document.hidden||motion.matches);};
  const observer=new IntersectionObserver(entries=>{for(const entry of entries){entry.target.classList.toggle('pp-journey-visible',entry.isIntersecting);if(entry.isIntersecting&&!loaded){loaded=true;section.style.setProperty('--pp-journey-atlas','url(/assets/plus_point/images/dashboard-journey/event-world-atlas.png?v=20261101-scenes-4)');}}},{root:root.closest('.main-section'),rootMargin:'160px',threshold:.01});
  section.querySelectorAll('.pp-journey-banner').forEach(n=>observer.observe(n));document.addEventListener('visibilitychange',wake);motion.addEventListener('change',wake);wake();
  return {resize(){},destroy(){if(dead)return;dead=true;observer.disconnect();document.removeEventListener('visibilitychange',wake);motion.removeEventListener('change',wake);section.remove();}};
 }};
})();
