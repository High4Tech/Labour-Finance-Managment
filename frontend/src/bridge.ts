export type Args = Record<string, unknown>;
declare global {
 interface Window {
  plus_point: {
   form_rpc<T=unknown>(method:string,args?:Args,options?:{signal?:AbortSignal}):Promise<T>;
   open_attendance_picker():void;
   open_file_upload(options:Record<string,unknown>):void;
   dashboard_company?:string;
   load_feature(name:string):Promise<void>;
   app_shell?:{setContext(data:unknown):void;setAttention(rows:unknown[]):void;clearAttention():void};
   delete_records(doctype:string,names:string[],after:()=>void):void;
   open_import(company?:string,after?:()=>void,kind?:string,label?:string,options?:Record<string,unknown>):Promise<void>;
   charts:{ready():Promise<void>;create(host:HTMLElement,options:Record<string,unknown>):ChartHandle;stats:{active:number;created:number;destroyed:number}};
   ui:{amount(value:unknown):string};
   react_ui?:{mountPayments(host:HTMLElement,list:NativeList):void; unmount(host:HTMLElement):void; stats:{activeRoots:number;mounts:number;unmounts:number}};
  };
  frappe:{new_doc(doctype:string):void; set_route(...route:unknown[]):void; datetime:{get_today():string;prettyDate(value:string):string};model:{can_delete(doctype:string):boolean};session:{user:string};boot:{plus_point:{company_identity?:{name:string}}};realtime?:{on(name:string,fn:(data?:{doctype?:string})=>void):void;off(name:string,fn:(data?:{doctype?:string})=>void):void;doctype_subscribe(name:string):void;doctype_unsubscribe(name:string):void}};
  __(text:string):string;
 }
}
export interface ChartHandle{update(options:Record<string,unknown>):void;refresh():void;resize():void;destroy():void}
export interface NativeList {
 page:{main:{get(index:number):HTMLElement};set_primary_action(label:string,run:()=>void,icon?:string):void;clear_primary_action():void};
 make_new_doc():void;
}
export const t=(text:string)=>window.__?.(text)||text;
export const rpc=<T,>(method:string,args:Args={},signal?:AbortSignal)=>window.plus_point.form_rpc<T>('wage_payments.'+method,args,{signal});
export const amount=(value:unknown)=>window.plus_point.ui.amount(value);
export const company=()=>window.plus_point.dashboard_company;
export const today=()=>window.frappe.datetime.get_today();
export const relativeDate=(value:string)=>window.frappe.datetime.prettyDate(value);
export const changed=()=>document.dispatchEvent(new Event('pp:data-changed'));
