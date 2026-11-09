/* Help uses the authoritative React controls; native framework help remains authorized. */
(()=>{frappe.provide('plus_point');plus_point.app_help={open:()=>plus_point.load_feature('react_ui').then(()=>plus_point.react_help())};})();
