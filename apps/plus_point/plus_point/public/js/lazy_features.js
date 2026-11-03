/* Native Frappe loading, one promise per optional feature, retriable on failure. */
(()=>{
 frappe.provide('plus_point');const pp=plus_point,pending=new Map(),attempts=new Map();
 const features={
  company_tools:{file:'company_tools',css:true,nonblocking:true,version:'20261103-react-9',ready:()=>!!pp.scoped_search},
  wage_payments:{file:'wage_payments',css:true,nonblocking:true,version:'20261103-react-9',ready:()=>!!pp.wage_payments},
  react_ui:{file:'react_bridge',css:false,nonblocking:true,version:'20261103-react-9',ready:()=>!!pp.react_payments_mount},
  app_help:{file:'app_help',css:true,nonblocking:true,version:'20261101-scenes-4',ready:()=>!!pp.app_help},
  dashboard_journey:{file:'dashboard_journey',css:true,nonblocking:true,version:'20261101-scenes-4',ready:()=>!!pp.dashboard_journey},
  world_assets:{file:'world_assets',nonblocking:true,version:'20261101-scenes-4',ready:()=>!!pp.world_assets},
  dashboard_analytics:{file:'dashboard_overview',css:true,dependencies:['react_ui'],nonblocking:true,version:'20261103-react-9',ready:()=>typeof pp.render_customer_dashboard==='function'},
  dashboard_charts:{file:'charts',css:true,nonblocking:true,version:'20261101-scenes-4',ready:()=>!!pp.charts},
  echarts:{file:'vendor/echarts-dashboard.min',version:'6.1.0-1',nonblocking:true,ready:()=>!!window.PlusPointECharts},
  imports:{file:'imports',version:'20261029-upload-assets-2',ready:()=>!!pp.open_import&&!pp.open_import.ppLazy},
  event_calendar:{file:'event_calendar',css:true,version:'20261029-upload-assets-2',ready:()=>pp.render_event_timeline?.ppCalendarVersion===6},
  event_scene_engine:{file:'vendor/three-scene.min',nonblocking:true,version:'0.180.0-2',ready:()=>window.PlusPointScene3D?.PCFSoftShadowMap!==undefined},
  event_scene:{file:'event_scene',css:true,dependencies:['event_scene_engine','world_assets'],nonblocking:true,version:'20261101-scenes-4',ready:()=>pp.event_scene?.version===3},
  flow_builder:{file:'flow_builder',css:true,version:'20261103-react-9',ready:()=>typeof pp.flow_builder==='function'},
  freddy_runtime:{file:'freddy-runtime',ready:()=>!!pp.freddy_runtime}
 };
 pp.load_feature=name=>{
  const feature=features[name];if(!feature)return Promise.reject(Error('Unknown UI feature'));
  if(pending.has(name))return pending.get(name);if(feature.ready())return Promise.resolve();
  const request=(async()=>{
   await Promise.all((feature.dependencies||[]).map(key=>pp.load_feature(key)));
   const path='/assets/plus_point/js/'+feature.file+'.js';
   if(feature.nonblocking){
    // Native asset cache without its page-wide freeze. The plain cache key is
    // intentional: Frappe's extension detector does not accept query strings.
    // A failed native load is cached too, so explicit retries get a fresh key.
    const attempt=attempts.get(name)||0,key=attempt?path.replace(/([^/]+)$/,'retry-'+attempt+'/$1'):path;
    await frappe.assets.load_asset(key,path+'?v='+feature.version+(attempt?'&retry='+attempt:''));
   }else if(feature.version){const attempt=attempts.get(name)||0,key=attempt?path.replace(/([^/]+)$/,'retry-'+attempt+'/$1'):path;await frappe.assets.load_asset(key,path+'?v='+feature.version+(attempt?'&retry='+attempt:''));}else await frappe.require(path);
   if(feature.css&&!document.querySelector('link[href*="/assets/plus_point/css/'+feature.file+'.css"]')){const css='/assets/plus_point/css/'+feature.file+'.css';if(feature.nonblocking)await frappe.assets.load_asset(css,css+'?v='+feature.version);else if(feature.version)await frappe.assets.load_asset(css,css+'?v='+feature.version);else await frappe.require(css);}
   if(!feature.ready())throw Error(__('This tool could not load. Try opening it again.'));
  })().catch(error=>{pending.delete(name);attempts.set(name,(attempts.get(name)||0)+1);throw error;});pending.set(name,request);return request;
 };
 if(!pp.open_import){const open=async(...args)=>{await pp.load_feature('imports');return pp.open_import(...args);};open.ppLazy=true;pp.open_import=open;}
 if(!pp.render_event_timeline?.ppCalendarVersion)pp.render_event_timeline=async(root,...args)=>{await pp.load_feature('event_calendar');if(root.isConnected)return pp.render_event_timeline(root,...args);};
 // Start only the destination's React code while Frappe resolves its native
 // route/permission host. Unrelated app startup never loads the React runtime.
 pp.use_native_payments=()=>sessionStorage.getItem('pp:payments:advanced')==='1';
 const prepare=()=>{const route=frappe.get_route();if((route?.[0]==='List'&&route[1]==='PP Wage Settlement'||/\/pp-wage-settlement(?:\/view\/list)?\/?$/.test(location.pathname))&&!pp.use_native_payments())pp.load_feature('react_ui').then(()=>pp.react_prepare_payments()).catch(()=>{});};
 const prepareOverview=()=>{const r=frappe.get_route()||[],path=location.pathname;if(r[0]==='Workspaces'&&r[1]==='PLUS POINT'||path==='/desk/plus-point')pp.load_feature('react_ui').then(()=>pp.react_prepare_dashboard()).catch(()=>{});else if(r[0]==='List'&&['PP Contract Terms','PP Event Plan'].includes(r[1])&&!sessionStorage.getItem('pp:planning:advanced'))pp.load_feature('react_ui').then(()=>pp.react_prepare_planning()).catch(()=>{});else if(['List','Form'].includes(r[0])&&r[1]==='Employee'&&sessionStorage.getItem('pp:workers:advanced')!=='1')pp.load_feature('react_ui').then(()=>pp.react_prepare_workers()).catch(()=>{});else if(['List','Form'].includes(r[0])&&r[1]==='Customer'&&sessionStorage.getItem('pp:clients:advanced')!=='1')pp.load_feature('react_ui').then(()=>pp.react_prepare_clients()).catch(()=>{});};
 frappe.router.on('change',()=>{prepare();prepareOverview();});prepare();prepareOverview();
})();
