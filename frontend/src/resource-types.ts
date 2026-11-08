import {t} from './bridge';
export type ResourceKind = 'equipment' | 'warehouses' | 'vehicles';
export const resourceScreens = {
 equipment: {title:'Inventory & equipment', singular:'Equipment', create:'Add equipment', doctype:'Item', path:'item', kind:'inventory_items'},
 warehouses: {title:'Warehouses', singular:'Warehouse', create:'Add warehouse', doctype:'Warehouse', path:'warehouse', kind:'warehouses'},
 vehicles: {title:'Vehicles', singular:'Vehicle', create:'Add vehicle', doctype:'Vehicle', path:'vehicle', kind:'vehicles'},
};
export type ResourceRow = {
 name:string; title:string; pp_reference?:string; disabled?:number; status?:string;
 warehouse_type?:string; stock_uom?:string; license_plate?:string; make?:string; model?:string;
 pp_event_enabled?:number; pp_crew_seats?:number; pp_cargo_capacity?:number; pp_cargo_uom?:string;
};
export type ResourceOptions = {company:string; units:string[]; permissions:Record<ResourceKind,Record<'read'|'write'|'create'|'delete',boolean>>};
export type Booking = {
 name:string; kind:'vehicle'|'equipment'; project:string; site:string; site_title:string; title:string;
 event:string; start_date:string; end_date:string; status:string; vehicle?:string; item?:string;
 warehouse?:string; quantity?:number; stock_uom?:string; purpose?:string; crew_count?:number; cargo_load?:number;
};
export type Stock = {name:string; title:string; uom:string; disabled:number; on_hand:number; reserved:number; available:number; updated_at?:string};
export type EquipmentProfile = {
 name:string; title:string; reference?:string; uom:string; disabled:number; description?:string;
 currency:string; daily_rate:string; bookings:Booking[];
 stock:{warehouse:string; title:string; on_hand:string; reserved:string; available:string}[];
};
export type Overview = {
 rows:ResourceRow[]; bookings:Booking[]; stock:Stock[];
 history:{posting_date:string; posting_time:string; item_code:string; actual_qty:number; qty_after_transaction:number; owner:string; creation:string}[];
};
export const resourceCall = <T,>(method:string,args:Record<string,unknown>={},signal?:AbortSignal) =>
 window.plus_point.form_rpc<T>('resources.'+method,args,{signal});
export const resourceUrl = (kind:ResourceKind,name:string) => '/desk/pp-inventory?view='+kind+'&record='+encodeURIComponent(name);
export const resourceStatus = (kind:ResourceKind,row:ResourceRow) => kind==='vehicles' ? row.status||'Inactive' : row.disabled ? 'Inactive' : 'Active';
export const resourceError = (error:unknown) => error instanceof Error ? error.message : t('Could not save. Review the details and try again.');

export function resourceEditorValues(kind:ResourceKind,row:ResourceRow,name:string,equipment?:EquipmentProfile):Record<string,string>{
 return kind==='equipment'?{item_code:name,item_name:row.title,stock_uom:equipment?.uom||'',status:row.disabled?'Inactive':'Active'}:kind==='vehicles'?{
  make:row.make||'',model:row.model||'',crew_seats:String(row.pp_crew_seats||0),cargo_capacity:String(row.pp_cargo_capacity||0),cargo_uom:row.pp_cargo_uom||'units',status:row.pp_event_enabled?'Active':'Inactive',
 }:{warehouse_type:['Owned','Rented'].includes(row.warehouse_type||'')?row.warehouse_type!:'Owned',status:row.disabled?'Inactive':'Active'};
}
