"""Composed warehouse/vehicle screens over native stock and reservation records."""
from collections import defaultdict
from decimal import Decimal
import frappe
from frappe.utils import today, getdate, add_days, cint, now_datetime
from plus_point.setup_flow import linked
from plus_point.operations import company
from plus_point.events import span, positive
from plus_point.benefits import atomic

KINDS={'vehicle':'PP Vehicle Booking','equipment':'PP Equipment Booking'}


@frappe.whitelist()
def equipment_profile(name):
    business=company();item=linked('Item',name)
    if not item.is_stock_item:frappe.throw('Open service and accounting items in the advanced Item view.')
    warehouses=frappe.get_list('Warehouse',filters={'company':business.name,'is_group':0,'disabled':0},fields=['name','warehouse_name'],limit_page_length=200)
    names=[w.name for w in warehouses]
    quantities={r.warehouse:Decimal(str(r.actual_qty)) for r in frappe.get_all('Bin',filters={'warehouse':['in',names or ['']],'item_code':name},fields=['warehouse','actual_qty'])}
    reserved=defaultdict(Decimal)
    for booking in frappe.get_list('PP Equipment Booking',filters={'company':business.name,'item':name,'warehouse':['in',names or ['']],'status':'Planned','start_date':['<=',today()],'end_date':['>=',today()]},fields=['warehouse','quantity'],limit_page_length=0):reserved[booking.warehouse]+=Decimal(str(booking.quantity))
    stock=[]
    for warehouse in warehouses:
        actual=quantities.get(warehouse.name,Decimal(0));held=reserved[warehouse.name]
        values=dict(on_hand=str(actual),reserved=str(held),available=str(actual-held))
        if Decimal(str(values['on_hand'])) or Decimal(str(values['reserved'])):
            stock.append(dict(warehouse=warehouse.name,title=warehouse.warehouse_name,**values))
    bookings=booking_rows(item=item.name)
    price=frappe.db.get_value('Item Price',{'item_code':item.name,'price_list':'Event daily hire '+business.default_currency,'currency':business.default_currency,'selling':1,'uom':item.stock_uom},'price_list_rate')
    return dict(name=item.name,title=item.item_name,reference=item.get('pp_reference'),uom=item.stock_uom,disabled=item.disabled,description=item.description,stock=stock,bookings=bookings,currency=business.default_currency,daily_rate=str(price or 0))


@frappe.whitelist(methods=['POST'])
@atomic
def save_equipment_rate(name,amount):
    """A native Item Price default, separate from stock valuation and invoices."""
    business=company();item=linked('Item',name);item.check_permission('write')
    if not item.is_stock_item:frappe.throw('Choose reusable event equipment.')
    from plus_point.finance import money
    amount=money(amount)
    if amount<0:frappe.throw('Enter a daily hire rate of zero or more.')
    frappe.db.get_value('Item',name,'name',for_update=True)
    price_list='Event daily hire '+business.default_currency
    if not frappe.db.exists('Price List',price_list):
        frappe.get_doc(dict(doctype='Price List',price_list_name=price_list,selling=1,buying=0,enabled=1,currency=business.default_currency)).insert()
    key=frappe.db.get_value('Item Price',{'item_code':name,'price_list':'Event daily hire '+business.default_currency,'currency':business.default_currency,'selling':1,'uom':item.stock_uom},'name')
    price=frappe.get_doc('Item Price',key) if key else frappe.new_doc('Item Price')
    price.update(dict(item_code=name,price_list=price_list,currency=business.default_currency,uom=item.stock_uom,price_list_rate=float(amount)))
    price.save();return dict(name=price.name,daily_rate=str(amount))


@frappe.whitelist()
def assignable_events():
    business=company()
    projects=frappe.get_list('Project',filters={'company':business.name,'status':'Open','pp_archived':0},pluck='name',limit_page_length=0)
    return frappe.get_list('PP Event Plan',filters={'company':business.name,'project':['in',projects or ['']]},fields=['name','event_name','pp_reference','project','start_date','end_date'],order_by='start_date desc,event_name',limit_page_length=1000)


@frappe.whitelist()
def booking_options(project,kind,start_date,end_date,item=None,name=None):
    """Permission-scoped suggestions; the booking save still locks and rechecks."""
    doc=project_doc(project)
    if kind not in KINDS:frappe.throw('Choose equipment or a vehicle.')
    span(start_date,end_date)
    if name:
        current=linked(KINDS[kind],name,doc.company)
        if current.project!=project:frappe.throw('Choose a reservation in this event.')
    if kind=='vehicle':
        vehicles=frappe.get_list('Vehicle',filters={'company':doc.company,'pp_event_enabled':1},fields=['name','license_plate','make','model','pp_crew_seats','pp_cargo_capacity','pp_cargo_uom'],order_by='license_plate,name',limit_page_length=1000)
        booked=set(frappe.get_list('PP Vehicle Booking',filters={'company':doc.company,'status':'Planned','name':['!=',name or ''],'start_date':['<=',end_date],'end_date':['>=',start_date]},pluck='vehicle',limit_page_length=0))
        return [dict(v,available=v.name not in booked) for v in vehicles]
    if not item:return []
    equipment=linked('Item',item)
    if equipment.disabled or not equipment.is_stock_item:frappe.throw('Choose active reusable equipment.')
    warehouses=frappe.get_list('Warehouse',filters={'company':doc.company,'is_group':0,'disabled':0},fields=['name','warehouse_name'],order_by='warehouse_name,name',limit_page_length=1000)
    from plus_point.events import stock_available
    result=[]
    for warehouse in warehouses:
        amounts=stock_available(item,warehouse.name,start_date,end_date,exclude=name)
        if Decimal(amounts['on_hand'])>0:
            result.append(dict(warehouse=warehouse.name,title=warehouse.warehouse_name,uom=equipment.stock_uom,**amounts))
    return result


def install_agreement_transport():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'PP Contract Terms':[dict(fieldname='pp_transport_requirements',label='Vehicle requirements',fieldtype='Long Text',hidden=1)]})


def transport_requirements(values,start,end,sites):
    rows=frappe.parse_json(values or '[]')
    if not isinstance(rows,list) or len(rows)>30:frappe.throw('Use at most 30 vehicle requirements.')
    result=[]
    for row in rows:
        if not isinstance(row,dict):frappe.throw('Enter a vehicle requirement.')
        title=str(row.get('vehicle_type') or '').strip()
        if not title or len(title)>140:frappe.throw('Enter a vehicle type of at most 140 characters.')
        quantity=positive(row.get('quantity'),'Number of vehicles',whole=True)
        if quantity>100:frappe.throw('Use at most 100 vehicles per requirement.')
        first,last=row.get('start_date') or start,row.get('end_date') or end
        span(first,last)
        if getdate(first)<getdate(start) or getdate(last)>getdate(end):frappe.throw('Vehicle requirement dates must be within the agreement.')
        site=str(row.get('site_name') or '').strip()
        if site and site not in sites:frappe.throw('Choose a site in this agreement for the vehicles.')
        notes=str(row.get('notes') or '').strip()
        if len(notes)>1000:frappe.throw('Use at most 1,000 characters for vehicle notes.')
        result.append(dict(vehicle_type=title,quantity=int(quantity),site_name=site,start_date=str(getdate(first)),end_date=str(getdate(last)),notes=notes))
    return result

def project_doc(project,write=False):
    business=company();doc=linked('Project',project,business.name)
    doc.check_permission('write' if write else 'read');return doc

def booking_rows(project=None,vehicle=None,warehouse=None,item=None):
    result=[];business=company().name
    for kind,doctype in KINDS.items():
        if vehicle and kind!='vehicle' or (warehouse or item) and kind!='equipment':continue
        filters={'company':business}
        for key,value in [('project',project),('vehicle',vehicle),('warehouse',warehouse),('item',item)]:
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
    warehouses=frappe.get_list('Warehouse',filters=filters,fields=['name','warehouse_name','warehouse_type','disabled','pp_reference'],order_by='warehouse_name',limit_start=offset,limit_page_length=51)
    stock=warehouse_stock(name,start_date,end_date) if name else []
    history=frappe.get_list('Stock Ledger Entry',filters={'company':business.name,'warehouse':name,'is_cancelled':0},fields=['posting_date','posting_time','creation','owner','item_code','actual_qty','qty_after_transaction','valuation_rate','voucher_type','voucher_no'],order_by='posting_date desc,posting_time desc,creation desc',limit_page_length=50) if name else []
    return dict(rows=warehouses[:50],more=len(warehouses)>50,stock=stock,history=history,bookings=booking_rows(warehouse=name) if name else [],start=start_date,end=end_date)

@frappe.whitelist()
def warehouse_stock(warehouse,start_date=None,end_date=None):
    linked('Warehouse',warehouse,company().name);start_date=start_date or today();end_date=end_date or start_date;span(start_date,end_date)
    # Fetch each dataset once, then sweep reservation dates per item in memory.
    bins=frappe.get_list('Bin',filters={'warehouse':warehouse},fields=['item_code','actual_qty','valuation_rate','modified'],limit_page_length=500)
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
        result.append(dict(name=item.name,title=item.item_name,uom=item.stock_uom,disabled=item.disabled,on_hand=row.actual_qty,reserved=float(peak),available=float(Decimal(str(row.actual_qty))-peak),valuation_rate=row.valuation_rate,updated_at=row.modified))
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
    if doctype=='Warehouse' and v.get('warehouse_type'):
        ensure_ownership(v.warehouse_type)
    fields=['make','model','pp_event_enabled','pp_crew_seats','pp_cargo_capacity','pp_cargo_uom'] if doctype=='Vehicle' else ['disabled','warehouse_type']
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


def ensure_ownership(value):
    if value not in ('Owned','Rented'):frappe.throw('Choose Owned or Rented for warehouse ownership.')
    if not frappe.db.exists('Warehouse Type',value):
        frappe.get_doc(dict(doctype='Warehouse Type',name=value,description=value+' warehouse')).insert()


@frappe.whitelist()
def list_states(view,names):
    values=frappe.parse_json(names) or []
    if not isinstance(values,list) or len(values)>200:frappe.throw('Review at most 200 records at a time.')
    business=company()
    if view=='warehouses':
        return frappe.get_list('Warehouse',filters={'company':business.name,'name':['in',values or ['']]},fields=['name','warehouse_name','warehouse_type','disabled','is_group'],limit_page_length=200)
    if view!='vehicles':frappe.throw('Choose Warehouses or Vehicles.')
    rows=frappe.get_list('Vehicle',filters={'company':business.name,'name':['in',values or ['']]},fields=['name','make','model','pp_crew_seats','pp_cargo_capacity','pp_event_enabled'],limit_page_length=200)
    bookings=frappe.get_list('PP Vehicle Booking',filters={'company':business.name,'vehicle':['in',[r.name for r in rows] or ['']],'status':'Planned','start_date':['<=',today()],'end_date':['>=',today()]},pluck='vehicle',limit_page_length=0)
    for row in rows:row['availability']='Inactive' if not row.pp_event_enabled else 'Assigned' if row.name in bookings else 'Available'
    return rows


@frappe.whitelist(methods=['POST'])
@atomic
def update_stock(warehouse,rows):
    """Absolute quantities, one native posting, existing unit values and server time."""
    business=company();location=linked('Warehouse',warehouse,business.name);location.check_permission('write')
    frappe.has_permission('Stock Reconciliation','create',throw=True);frappe.has_permission('Stock Reconciliation','submit',throw=True)
    if location.disabled or location.is_group:frappe.throw('Choose an active storage warehouse.')
    changes=frappe.parse_json(rows) or []
    if not isinstance(changes,list) or not 1<=len(changes)<=200:frappe.throw('Save 1–200 quantity changes together.')
    if any(not isinstance(r,dict) or not r.get('item') for r in changes):frappe.throw('Choose an item for each quantity.')
    if len({r['item'] for r in changes})!=len(changes):frappe.throw('Each item can appear only once.')
    frappe.db.get_value('Warehouse',warehouse,'name',for_update=True)
    items=[]
    from plus_point.events import reserved_peak
    for row in sorted(changes,key=lambda r:r['item']):
        item=linked('Item',row['item'])
        if item.disabled or not item.is_stock_item or item.has_serial_no or item.has_batch_no:frappe.throw('Choose active equipment without serial or batch tracking.')
        quantity=positive(row.get('quantity'),'Quantity',whole=bool(frappe.db.get_value('UOM',item.stock_uom,'must_be_whole_number')),allow_zero=True)
        current=frappe.db.sql('select actual_qty,valuation_rate from tabBin where item_code=%s and warehouse=%s for update',(item.name,warehouse),as_dict=True)
        actual=Decimal(str(current[0].actual_qty)) if current else Decimal(0)
        if row.get('expected_quantity') is None or Decimal(str(row['expected_quantity']))!=actual:
            frappe.throw(f'{item.item_name} changed since you opened this list. Refresh before saving.')
        if quantity<reserved_peak(item.name,warehouse,today(),'9999-12-30'):frappe.throw(f'{item.item_name}: quantity cannot be below equipment reserved for events.')
        if quantity==actual:continue
        rate=Decimal(str(current[0].valuation_rate or 0)) if current else Decimal(0)
        items.append(dict(item_code=item.name,warehouse=warehouse,qty=float(quantity),valuation_rate=float(rate),allow_zero_valuation_rate=int(rate==0)))
    stamp=now_datetime()
    if not items:return dict(updated=0,updated_at=str(stamp))
    from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_difference_account
    purpose='Stock Reconciliation' if frappe.db.exists('Stock Ledger Entry',{'company':business.name}) else 'Opening Stock'
    doc=frappe.get_doc(dict(doctype='Stock Reconciliation',company=business.name,purpose=purpose,
        expense_account=get_difference_account(purpose,business.name),posting_date=stamp.date(),posting_time=stamp.time(),set_posting_time=1,items=items,remarks='Warehouse list quantity update'))
    doc.insert();doc.submit()
    return dict(name=doc.name,updated=len(items),updated_at=str(stamp))


@frappe.whitelist(methods=['POST'])
def attach_item(warehouse,item):
    location=linked('Warehouse',warehouse,company().name);location.check_permission('write');equipment=linked('Item',item)
    if location.disabled or location.is_group or equipment.disabled or not equipment.is_stock_item:frappe.throw('Choose active equipment and a storage warehouse.')
    from erpnext.stock.utils import get_bin
    get_bin(item,warehouse)
    return dict(name=item)


@frappe.whitelist()
def agreement_vehicle_options(start_date,end_date,agreement=None):
    business=company();span(start_date,end_date)
    from plus_point.operations import terms_doc
    own=terms_doc(agreement).project if agreement else None
    vehicles=frappe.get_list('Vehicle',filters={'company':business.name},fields=['name','license_plate','make','model','pp_event_enabled','pp_crew_seats'],limit_page_length=500,order_by='make,model,license_plate')
    bookings=frappe.get_list('PP Vehicle Booking',filters={'company':business.name,'status':'Planned','start_date':['<=',end_date],'end_date':['>=',start_date]},fields=['vehicle','project'],limit_page_length=0)
    booked={b.vehicle for b in bookings if b.project!=own}
    for row in vehicles:row.update(vehicle_type=' '.join(filter(None,[row.make,row.model])),available=bool(row.pp_event_enabled and row.name not in booked))
    return vehicles
