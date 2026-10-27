/* Native Frappe loading, one promise per optional feature, retriable on failure. */
(()=>{
 frappe.provide('plus_point');const pp=plus_point,pending=new Map();
 const features={
  imports:{file:'imports',ready:()=>!!pp.open_import&&!pp.open_import.ppLazy},
  event_calendar:{file:'event_calendar',css:true,ready:()=>pp.render_event_timeline?.ppCalendarVersion===4},
  flow_builder:{file:'flow_builder',css:true,ready:()=>typeof pp.flow_builder==='function'},
  freddy_runtime:{file:'freddy-runtime',ready:()=>!!pp.freddy_runtime}
 };
 pp.load_feature=name=>{
  const feature=features[name];if(!feature)return Promise.reject(Error('Unknown UI feature'));
  if(feature.ready())return Promise.resolve();if(pending.has(name))return pending.get(name);
  const request=(async()=>{await frappe.require('/assets/plus_point/js/'+feature.file+'.js');if(feature.css&&!document.querySelector('link[href*="/assets/plus_point/css/'+feature.file+'.css"]'))await frappe.require('/assets/plus_point/css/'+feature.file+'.css');if(!feature.ready())throw Error(__('This tool could not load. Try opening it again.'));})().catch(error=>{pending.delete(name);throw error;});pending.set(name,request);return request;
 };
 if(!pp.open_import){const open=async(...args)=>{await pp.load_feature('imports');return pp.open_import(...args);};open.ppLazy=true;pp.open_import=open;}
 if(!pp.render_event_timeline?.ppCalendarVersion)pp.render_event_timeline=async(root,...args)=>{await pp.load_feature('event_calendar');if(root.isConnected)return pp.render_event_timeline(root,...args);};
})();
