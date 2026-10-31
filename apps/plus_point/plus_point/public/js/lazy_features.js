/* Native Frappe loading, one promise per optional feature, retriable on failure. */
(()=>{
 frappe.provide('plus_point');const pp=plus_point,pending=new Map(),attempts=new Map();
 const features={
  dashboard_analytics:{file:'dashboard_analytics',css:true,dependencies:['dashboard_charts'],nonblocking:true,version:'20261028-workflow-refinement-2',ready:()=>typeof pp.render_customer_dashboard==='function'},
  dashboard_charts:{file:'charts',css:true,nonblocking:true,version:'20261028-workflow-refinement-2',ready:()=>!!pp.charts},
  echarts:{file:'vendor/echarts-dashboard.min',version:'6.1.0-1',nonblocking:true,ready:()=>!!window.PlusPointECharts},
  imports:{file:'imports',version:'20261029-upload-assets-2',ready:()=>!!pp.open_import&&!pp.open_import.ppLazy},
  event_calendar:{file:'event_calendar',css:true,version:'20261029-upload-assets-2',ready:()=>pp.render_event_timeline?.ppCalendarVersion===6},
  event_scene_engine:{file:'vendor/three-scene.min',nonblocking:true,version:'0.180.0-1',ready:()=>!!window.PlusPointScene3D},
  event_scene:{file:'event_scene',css:true,dependencies:['event_scene_engine'],nonblocking:true,version:'20261031-scene-demo-1',ready:()=>pp.event_scene?.version===1},
  flow_builder:{file:'flow_builder',css:true,version:'20261029-upload-assets-2',ready:()=>typeof pp.flow_builder==='function'},
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
})();
