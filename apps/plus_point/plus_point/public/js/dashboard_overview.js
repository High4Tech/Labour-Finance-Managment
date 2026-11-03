/* Company overview is owned entirely by React. Native platform reports stay native. */
(()=>{
 const pp=window.plus_point;
 pp.render_customer_dashboard=(root,data)=>{
  if(root.dataset.ppReactRoot==='dashboard')return;
  const css='/assets/plus_point/css/dashboard_journey.css';
  if(!document.querySelector('link[href*="'+css+'"]')){const link=document.createElement('link');link.rel='stylesheet';link.href=css+'?v=20261101-scenes-4';document.head.append(link);}
  return pp.react_dashboard_mount(root,data);
 };
})();
