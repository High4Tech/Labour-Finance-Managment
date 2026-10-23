"""Composed warehouse/vehicle screens over native stock and reservation records."""
from collections import defaultdict
from decimal import Decimal
import frappe
from frappe.utils import today, getdate, add_days, cint
from plus_point.setup_flow import linked
from plus_point.operations import company
from plus_point.events import span, stock_available

KINDS={'vehicle':'PP Vehicle Booking','equipment':'PP Equipment Booking'}

def project_doc(project,write=False):
    business=company();doc=linked('Project',project,business.name)
    doc.check_permission('write' if write else 'read');return doc

def booking_rows(project=None,vehicle=None,warehouse=None):
    result=[];business=company().name
    for kind,doctype in KINDS.items():
        if vehicle and kind!='vehicle' or warehouse and kind!='equipment':continue
        filters={'company':business}
        for key,value in [('project',project),('vehicle',vehicle),('warehouse',warehouse)]:
            if value:filters[key]=value
        fields=['name','project','site','start_date','end_date','status','notes']+(['vehicle','purpose','crew_count','cargo_load','cargo_uom'] if kind=='vehicle' else ['item','warehouse','quantity','stock_uom'])
        result.extend(dict(row,kind=kind) for row in frappe.get_list(doctype,filters=filters,fields=fields,order_by='start_date desc',limit_page_length=200))
    projects={r.name:r.project_name for r in frappe.get_list('Project',filters={'name':['in',list({r['project'] for r in result}) or ['']]},fields=['name','project_name'],limit_page_length=400)}
    sites={r.name:r.site_name for r in frappe.get_list('PP Site',filters={'name':['in',list({r['site'] for r in result}) or ['']]},fields=['name','site_name'],limit_page_length=400)}
    items={r.name:r.item_name for r in frappe.get_list('Item',filters={'name':['in',list({r.get('item') for r in result if r.get('item')}) or ['']]},fields=['name','item_name'],limit_page_length=200)}
    for row in result:row.update(title=row.get('vehicle') or items.get(row.get('item'),row.get('item')),event=projects.get(row['project'],''),site_title=sites.get(row['site'],''))
    result=[frappe._dict(row) for row in result]
    return result

@frappe.whitelist()
def project_resources(project):
    doc=project_doc(project)
    return dict(project=doc.name,sites=frappe.get_list('PP Site',filters={'project':project,'is_active':1},fields=['name','site_name'],limit_page_length=100),rows=booking_rows(project=project))

@frappe.whitelist()
def overview(view='warehouses',name=None,start_date=None,end_date=None,offset=0):
    business=company();start_date=start_date or today();end_date=end_date or start_date;span(start_date,end_date)
    offset=max(0,cint(offset))
    if view=='vehicles':
        filters={'company':business.name}
        if name:filters['name']=linked('Vehicle',name,business.name).name
        vehicles=frappe.get_list('Vehicle',filters=filters,fields=['name','license_plate','make','model','pp_event_enabled','pp_crew_seats','pp_cargo_capacity','pp_cargo_uom'],order_by='license_plate',limit_start=offset,limit_page_length=51)
        bookings=frappe.get_list('PP Vehicle Booking',filters={'company':business.name,'vehicle':['in',[v.name for v in vehicles] or ['']],'status':'Planned','start_date':['<=',end_date],'end_date':['>=',start_date]},fields=['vehicle','name'],limit_page_length=0)
        assigned={r.vehicle for r in bookings}
        for row in vehicles:row['status']='Inactive' if not row.pp_event_enabled else 'Assigned' if row.name in assigned else 'Available'
        return dict(rows=vehicles[:50],more=len(vehicles)>50,bookings=booking_rows(vehicle=name) if name else [],start=start_date,end=end_date)
    if view!='warehouses':frappe.throw('Choose Warehouses or Vehicles.')
    filters={'company':business.name,'is_group':0}
    if name:filters['name']=linked('Warehouse',name,business.name).name
    warehouses=frappe.get_list('Warehouse',filters=filters,fields=['name','warehouse_name','disabled','pp_reference'],order_by='warehouse_name',limit_start=offset,limit_page_length=51)
    stock=warehouse_stock(name,start_date,end_date) if name else []
    history=frappe.get_list('Stock Ledger Entry',filters={'company':business.name,'warehouse':name,'is_cancelled':0},fields=['posting_date','item_code','actual_qty','qty_after_transaction','valuation_rate','voucher_type','voucher_no'],order_by='posting_date desc,posting_time desc,creation desc',limit_page_length=50) if name else []
    return dict(rows=warehouses[:50],more=len(warehouses)>50,stock=stock,history=history,bookings=booking_rows(warehouse=name) if name else [],start=start_date,end=end_date)

@frappe.whitelist()
def warehouse_stock(warehouse,start_date=None,end_date=None):
    linked('Warehouse',warehouse,company().name);start_date=start_date or today();end_date=end_date or start_date;span(start_date,end_date)
    # Fetch each dataset once, then sweep reservation dates per item in memory.
    bins=frappe.get_list('Bin',filters={'warehouse':warehouse},fields=['item_code','actual_qty','valuation_rate'],limit_page_length=500)
    items={r.name:r for r in frappe.get_list('Item',filters={'name':['in',[b.item_code for b in bins] or ['']],'is_stock_item':1},fields=['name','item_name','stock_uom','disabled'],limit_page_length=500)}
    bookings=frappe.get_list('PP Equipment Booking',filters={'warehouse':warehouse,'status':'Planned','start_date':['<=',end_date],'end_date':['>=',start_date]},fields=['item','quantity','start_date','end_date'],limit_page_length=0)
    changes=defaultdict(lambda:defaultdict(Decimal))
    for row in bookings:
        changes[row.item][max(getdate(start_date),getdate(row.start_date))]+=Decimal(str(row.quantity))
        changes[row.item][getdate(add_days(min(getdate(end_date),getdate(row.end_date)),1))]-=Decimal(str(row.quantity))
    result=[]
    for row in bins:
        item=items.get(row.item_code)
        if not item:continue
        current=peak=Decimal(0)
        for day in sorted(changes[row.item_code]):current+=changes[row.item_code][day];peak=max(peak,current)
        result.append(dict(name=item.name,title=item.item_name,uom=item.stock_uom,disabled=item.disabled,on_hand=row.actual_qty,reserved=float(peak),available=float(Decimal(str(row.actual_qty))-peak),valuation_rate=row.valuation_rate))
    return sorted(result,key=lambda r:r['title'].casefold())

@frappe.whitelist(methods=['POST'])
def save_booking(project,kind,values,name=None):
    doc=project_doc(project,True)
    if kind not in KINDS:frappe.throw('Choose a vehicle or equipment reservation.')
    v=frappe._dict(frappe.parse_json(values) or {})
    allowed=['site','start_date','end_date','status','notes']+(['vehicle','purpose','crew_count','cargo_load'] if kind=='vehicle' else ['warehouse','item','quantity'])
    booking=linked(KINDS[kind],name,doc.company) if name else frappe.new_doc(KINDS[kind])
    if name and booking.project!=project:frappe.throw('Choose a reservation in this event.')
    booking.update({k:v[k] for k in allowed if k in v});booking.project=project
    terms=frappe.db.get_value('PP Contract Terms',{'project':project},['effective_start','effective_end'],as_dict=True)
    if terms and (getdate(booking.start_date)<getdate(terms.effective_start) or terms.effective_end and getdate(booking.end_date)>getdate(terms.effective_end)):
        frappe.throw('Resource dates must be inside the agreement dates.')
    booking.save()
    from plus_point.signing import invalidate
    for terms in frappe.get_list('PP Contract Terms',filters={'project':project},pluck='name',limit_page_length=100):invalidate(terms)
    return dict(name=booking.name,status=booking.status)

@frappe.whitelist(methods=['POST'])
def update_profile(view,name,values):
    v=frappe._dict(frappe.parse_json(values) or {});business=company()
    doctype='Vehicle' if view=='vehicles' else 'Warehouse' if view=='warehouses' else None
    if not doctype:frappe.throw('Choose a warehouse or vehicle.')
    doc=linked(doctype,name,business.name);doc.check_permission('write')
    if doctype=='Warehouse' and cint(v.get('disabled')) and frappe.db.exists('PP Equipment Booking',{'warehouse':name,'status':'Planned','end_date':['>=',today()]}):
        frappe.throw('Cancel or move upcoming equipment reservations before deactivating this warehouse.')
    fields=['make','model','pp_event_enabled','pp_crew_seats','pp_cargo_capacity','pp_cargo_uom'] if doctype=='Vehicle' else ['disabled']
    doc.update({k:v[k] for k in fields if k in v});doc.save();return dict(name=doc.name)

@frappe.whitelist(methods=['POST'])
def count_stock(warehouse,item,quantity,valuation_rate,date):
    business=company();linked('Warehouse',warehouse,business.name);linked('Item',item)
    frappe.has_permission('Stock Reconciliation','create',throw=True);frappe.has_permission('Stock Reconciliation','submit',throw=True)
    from plus_point.event_imports import validate,save
    row=dict(date=date,item_code=item,warehouse=warehouse,quantity=str(quantity),valuation_rate=str(valuation_rate))
    validate('stock_balances',business.name,row)
    doc=save('stock_balances',business.name,row)
    return dict(name=doc.name)
