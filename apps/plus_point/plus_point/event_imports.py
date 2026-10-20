"""Catalog and opening-stock adapters for the existing review/apply import flow."""
import frappe
from frappe.utils import getdate
from plus_point.setup_flow import linked
from plus_point.events import positive,span

SCHEMAS={
 'clients':['external_id','customer','customer_name','customer_type'],
 'event_sites':['external_id','site','site_name','project','address','status'],
 'vehicles':['external_id','license_plate','make','model','crew_seats','cargo_capacity','cargo_uom','fuel_type','status'],
 'inventory_items':['external_id','item_code','item_name','stock_uom','status'],
 'warehouses':['external_id','warehouse_name'],
 'stock_balances':['external_id','date','item_code','warehouse','quantity','valuation_rate'],
 'events':['external_id','event_name','customer','start_date','end_date','site_name','workers_per_day','billing_model','fixed_amount','wage_rate','client_rate','agreement'],
}
TARGETS=dict(clients='Customer',event_sites='PP Site',vehicles='Vehicle',inventory_items='Item',warehouses='Warehouse',stock_balances='Stock Reconciliation',events='PP Event Plan')
PROFILES={'clients','event_sites','vehicles','inventory_items'}


def target(kind,row):
    key={'clients':'customer','event_sites':'site','vehicles':'license_plate','inventory_items':'item_code'}.get(kind)
    return row.get(key) if key else None


def validate(kind,company,row):
    from plus_point.imports import required,row_date
    if kind in ('event_sites','vehicles','inventory_items') and row['status'] not in ('Active','Inactive'):
        frappe.throw('status must be Active or Inactive')
    if kind=='clients':
        required(row,'customer_name')
        if row['customer_type'] not in ('Company','Individual'):frappe.throw('customer_type must be Company or Individual')
    elif kind=='event_sites':
        required(row,'site_name');linked('Project',required(row,'project'),company)
    elif kind=='vehicles':
        for key in ('license_plate','make','model'):required(row,key)
        positive(row['crew_seats'],'Crew seats',whole=True,allow_zero=True);positive(row['cargo_capacity'],'Cargo capacity',allow_zero=True)
        if row['cargo_uom'] not in ('units','kg','m³'):frappe.throw('cargo_uom must be units, kg or m³')
        if row['fuel_type'] not in ('Petrol','Diesel','Natural Gas','Electric'):frappe.throw('Choose a valid fuel_type')
    elif kind=='inventory_items':
        for key in ('item_code','item_name','stock_uom'):required(row,key)
        linked('UOM',row['stock_uom'])
    elif kind=='warehouses':required(row,'warehouse_name')
    elif kind=='stock_balances':
        row_date(row,'date');item=linked('Item',required(row,'item_code'));warehouse=linked('Warehouse',required(row,'warehouse'),company)
        if not item.is_stock_item or item.disabled or item.has_serial_no or item.has_batch_no or warehouse.is_group or warehouse.disabled:
            frappe.throw('Use an active, unbatched stock item and a leaf warehouse in this company')
        positive(row['quantity'],'Counted quantity',allow_zero=True)
        positive(row['valuation_rate'],'Value per stock unit',allow_zero=bool(row.get('allow_zero_valuation_rate')))
        from plus_point.events import reserved_peak
        if positive(row['quantity'],'Counted quantity',allow_zero=True)<reserved_peak(item.name,warehouse.name,frappe.utils.today(),'9999-12-30'):
            frappe.throw('Quantity is below event reservations. Review bookings first.')
    elif kind=='events':
        linked('Customer',required(row,'customer'));span(required(row,'start_date'),required(row,'end_date'))
        for key in ('event_name','site_name','agreement'):required(row,key)
        if row['billing_model'] not in ('Daily','Fixed'):frappe.throw('billing_model must be Daily or Fixed')
        positive(row['workers_per_day'],'Workers per day',whole=True);positive(row['wage_rate'],'Daily wage')
        positive(row['client_rate'],'Client daily rate',allow_zero=row['billing_model']=='Fixed')
        if row['billing_model']=='Fixed' and positive(row['fixed_amount'],'Fixed client price')<=0:frappe.throw('Enter a fixed contract price')
    name=target(kind,row)
    if name and frappe.db.exists(TARGETS[kind],name):
        doc=linked(TARGETS[kind],name,company if kind=='vehicles' else None);doc.check_permission('write')
        if kind=='event_sites':linked('Project',doc.project,company)
        if kind=='inventory_items' and not doc.is_stock_item:frappe.throw('This code belongs to a billing service. Use a new inventory item code.')
        if kind=='vehicles':
            from plus_point.events import validate_vehicle
            doc.update(dict(pp_crew_seats=int(positive(row['crew_seats'],'Crew seats',whole=True,allow_zero=True)),pp_cargo_capacity=float(row['cargo_capacity'] or 0),pp_cargo_uom=row['cargo_uom'],pp_event_enabled=int(row['status']=='Active')))
            validate_vehicle(doc)
        if kind=='inventory_items' and doc.stock_uom!=row['stock_uom'] and frappe.db.exists('Stock Ledger Entry',{'item_code':doc.name}):
            frappe.throw('The stock unit cannot change after stock postings. Use a new item code with its own stock unit.')
    value=None
    if kind=='stock_balances':
        from plus_point.finance import money
        value=str(money(positive(row['quantity'],'Counted quantity',allow_zero=True)*positive(row['valuation_rate'],'Value per unit',allow_zero=bool(row.get('allow_zero_valuation_rate')))))
    return dict(label=row.get('customer_name') or row.get('site_name') or row.get('event_name') or row.get('item_name') or row.get('license_plate') or row.get('warehouse_name') or row.get('item_code'),amount=value)


def save(kind,company,row,document=None):
    from plus_point.imports import required
    name=document or target(kind,row)
    exists=bool(name and frappe.db.exists(TARGETS[kind],name))
    doc=frappe.get_doc(TARGETS[kind],name) if exists else frappe.new_doc(TARGETS[kind])
    if kind=='clients':doc.update(dict(customer_name=row['customer_name'],customer_type=row['customer_type'],customer_group='Commercial',territory='All Territories'))
    elif kind=='event_sites':doc.update(dict(site_name=row['site_name'],project=row['project'],address=row['address'],is_active=int(row['status']=='Active')))
    elif kind=='vehicles':
        doc.update(dict(license_plate=row['license_plate'],make=row['make'],model=row['model'],company=company,
            pp_event_enabled=int(row['status']=='Active'),pp_crew_seats=int(positive(row['crew_seats'],'Crew seats',whole=True,allow_zero=True)),pp_cargo_capacity=float(row['cargo_capacity'] or 0),
            pp_cargo_uom=row['cargo_uom'],fuel_type=row['fuel_type'],uom='Litre'))
        if not exists:doc.last_odometer=0
    elif kind=='inventory_items':
        if not frappe.db.exists('Item Group','Event Equipment'):
            frappe.get_doc(dict(doctype='Item Group',item_group_name='Event Equipment',parent_item_group='All Item Groups',is_group=0)).insert()
        doc.update(dict(item_code=row['item_code'],item_name=row['item_name'],stock_uom=row['stock_uom'],is_stock_item=1,
            disabled=int(row['status']=='Inactive'),item_group='Event Equipment'))
    elif kind=='warehouses':
        parent=frappe.db.get_value('Warehouse',{'company':company,'is_group':1},'name')
        doc.update(dict(warehouse_name=row['warehouse_name'],company=company,is_group=0,parent_warehouse=parent))
    elif kind=='stock_balances':
        from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_difference_account
        purpose='Stock Reconciliation' if frappe.db.exists('Stock Ledger Entry',{'company':company}) else 'Opening Stock'
        doc.update(dict(company=company,purpose=purpose,expense_account=get_difference_account(purpose,company),posting_date=row['date'],set_posting_time=1,
            items=[dict(item_code=row['item_code'],warehouse=row['warehouse'],qty=float(row['quantity']),valuation_rate=float(row['valuation_rate']),allow_zero_valuation_rate=int(bool(row.get('allow_zero_valuation_rate'))))]))
        doc.insert();doc.submit();return doc
    elif kind=='events':
        from plus_point.events import create_event
        result=create_event(company,row['customer'],row['event_name'],row['start_date'],row['end_date'],row['agreement'],
            row['billing_model'],row['wage_rate'],row['client_rate'] or 0,row['fixed_amount'] or 0,
            sites=[dict(site_name=row['site_name'],phase='Event',start_date=row['start_date'],end_date=row['end_date'],workers_required=int(positive(row['workers_per_day'],'Workers per day',whole=True)))])
        return frappe.get_doc('PP Event Plan',result['plan'])
    doc.save();return doc
