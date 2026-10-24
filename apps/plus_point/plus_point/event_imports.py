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
LEGACY_SCHEMAS={key:list(value) for key,value in SCHEMAS.items()}
from plus_point.import_links import CLIENT_FIELDS
SCHEMAS['clients'] += CLIENT_FIELDS
SCHEMAS['events'] += ['customer_name','customer_type'] + ['client_'+key for key in CLIENT_FIELDS]
PREVIOUS_SCHEMAS={key:list(value) for key,value in SCHEMAS.items()}
SCHEMAS['clients']=[key for key in SCHEMAS['clients'] if key!='default_currency']
SCHEMAS['warehouses']=['external_id','warehouse_name','warehouse_type','status']
SCHEMAS['stock_balances']=['external_id','item_code','warehouse','quantity']
SCHEMAS['events']=[key for key in SCHEMAS['events'] if key not in ('wage_rate','client_default_currency')]+['designation','agreement_currency']
SCHEMAS['agreements']=['external_id','agreement_title','customer','start_date','end_date','status','billing_model','agreement_currency','fixed_amount','scope','conditions','site_name','designation','workers_per_day','client_rate']
TARGETS['agreements']='PP Contract Terms'
PROFILES.add('warehouses')


def target(kind,row):
    key={'clients':'customer','event_sites':'site','vehicles':'license_plate','inventory_items':'item_code','warehouses':'_warehouse'}.get(kind)
    return row.get(key) if key else None


def validate(kind,company,row):
    from plus_point.imports import required,row_date
    if kind=='agreements':
        linked('Customer',required(row,'customer'))
        for key in ('agreement_title','site_name','designation','scope','agreement_currency'):required(row,key)
        linked('Currency',row['agreement_currency']);linked('Designation',row['designation'])
        row_date(row,'start_date',historical=False);row_date(row,'end_date',historical=False);span(row['start_date'],row['end_date'])
        if getdate(row['start_date'])<getdate(frappe.utils.today()):frappe.throw('Upcoming agreements must start today or later.')
        if row.get('status') not in ('Draft','Active'):frappe.throw('Use Draft or Active status.')
        if row.get('billing_model') not in ('Daily','Fixed'):frappe.throw('Choose Daily or Fixed billing.')
        if positive(row.get('workers_per_day'),'Workers per day',whole=True)>500:frappe.throw('Use at most 500 workers per category.')
        if row['billing_model']=='Daily':positive(row.get('client_rate'),'Client rate per day')
        else:positive(row.get('fixed_amount'),'Fixed contract price')
    elif kind=='vehicles':
        from plus_point.input_rules import check
        check('license_plate',row.get('license_plate'))
    if kind in ('event_sites','vehicles','inventory_items') and row['status'] not in ('Active','Inactive'):
        frappe.throw('status must be Active or Inactive')
    if kind=='clients':
        required(row,'customer_name')
        from plus_point.import_links import client_values,validate_client
        validate_client(client_values(row))
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
    elif kind=='warehouses':
        required(row,'warehouse_name')
        if row.get('warehouse_type') and row['warehouse_type'] not in ('Owned','Rented'):frappe.throw('Choose Owned or Rented warehouse_type.')
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
        if not row.get('_new_client'):linked('Customer',required(row,'customer'))
        row_date(row,'start_date',historical=False);row_date(row,'end_date',historical=False)
        span(required(row,'start_date'),required(row,'end_date'))
        for key in ('event_name','site_name','agreement'):required(row,key)
        if 'designation' in row:linked('Designation',required(row,'designation'))
        if row.get('agreement_currency'):linked('Currency',row['agreement_currency'])
        if row['billing_model'] not in ('Daily','Fixed'):frappe.throw('billing_model must be Daily or Fixed')
        if positive(row['workers_per_day'],'Workers per day',whole=True)>500:frappe.throw('Use at most 500 workers per site per day')
        positive(row.get('wage_rate'),'Daily wage',allow_zero=True)
        positive(row['client_rate'],'Client daily rate',allow_zero=row['billing_model']=='Fixed')
        if row['billing_model']=='Fixed' and positive(row['client_rate'],'Client daily rate',allow_zero=True)!=0:frappe.throw('Fixed contracts use milestones; set client_rate to zero')
        if row['billing_model']=='Fixed' and positive(row['fixed_amount'],'Fixed client price')<=0:frappe.throw('Enter a fixed contract price')
    name=target(kind,row)
    if name and frappe.db.exists(TARGETS[kind],name):
        doc=linked(TARGETS[kind],name,company if kind in ('vehicles','warehouses') else None);doc.check_permission('write')
        if kind=='warehouses' and (doc.is_group or doc.disabled):frappe.throw('Choose an active leaf warehouse')
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
    return dict(label=row.get('agreement_title') or row.get('event_name') or row.get('customer_name') or row.get('site_name') or row.get('item_name') or row.get('license_plate') or row.get('warehouse_name') or row.get('item_code'),amount=value)


def save(kind,company,row,document=None):
    from plus_point.imports import required
    if kind=='agreements':
        from plus_point.operations import save_agreement
        import json
        created=save_agreement(dict(customer=row['customer'],agreement_title=row['agreement_title'],scope=row['scope'],
            effective_start=row['start_date'],effective_end=row['end_date'],status=row['status'],billing_model=row['billing_model'],
            agreement_currency=row['agreement_currency'],fixed_amount=row.get('fixed_amount') or 0,
            pp_conditions=json.dumps([c.strip() for c in row.get('conditions','').split('|') if c.strip()]),
            staffing=[dict(site_name=row['site_name'],designation=row['designation'],phase='Event',start_date=row['start_date'],
                end_date=row['end_date'],workers_required=row['workers_per_day'],wage_rate=0,client_rate=row.get('client_rate') or 0)]))
        return frappe.get_doc('PP Contract Terms',created['name'])
    name=document or target(kind,row)
    exists=bool(name and frappe.db.exists(TARGETS[kind],name))
    doc=frappe.get_doc(TARGETS[kind],name) if exists else frappe.new_doc(TARGETS[kind])
    if kind=='clients':
        from plus_point.import_links import client_values,validate_client
        values=client_values(row)
        if validate_client(values):
            from plus_point.clients import save as save_client
            return save_client(values,doc.name if exists else None)
        doc.update(dict(customer_name=row['customer_name'],customer_type=values['customer_type'],customer_group=doc.customer_group or 'Commercial',territory=doc.territory or 'All Territories'))
        if row.get('default_currency'):doc.default_currency=row['default_currency']
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
        parent=doc.parent_warehouse if exists else frappe.db.get_value('Warehouse',{'company':company,'is_group':1},'name')
        doc.update(dict(warehouse_name=row['warehouse_name'],company=company,is_group=0,parent_warehouse=parent))
        if row.get('warehouse_type'):
            from plus_point.resources import ensure_ownership
            ensure_ownership(row['warehouse_type']);doc.warehouse_type=row['warehouse_type']
        if row.get('status'):doc.disabled=int(row['status']=='Inactive')
    elif kind=='stock_balances':
        from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_difference_account
        purpose='Stock Reconciliation' if frappe.db.exists('Stock Ledger Entry',{'company':company}) else 'Opening Stock'
        doc.update(dict(company=company,purpose=purpose,expense_account=get_difference_account(purpose,company),posting_date=row['date'],set_posting_time=1,
            items=[dict(item_code=row['item_code'],warehouse=row['warehouse'],qty=float(row['quantity']),valuation_rate=float(row['valuation_rate']),allow_zero_valuation_rate=int(bool(row.get('allow_zero_valuation_rate'))))]))
        if row.get('_automatic_count'):
            stamp=frappe.utils.now_datetime();doc.posting_date=stamp.date();doc.posting_time=stamp.time()
        doc.insert();doc.submit();return doc
    elif kind=='events':
        from plus_point.events import create_event
        if row.get('_new_client'):
            from plus_point.import_links import find,validate_client
            values=row['_new_client']
            # Multiple events may share one new client. Reuse the first saved
            # profile; never overwrite an existing profile from an event row.
            customer=find('Customer',values['customer_name'],company,'customer',optional=True)
            if not customer:
                if validate_client(values):
                    from plus_point.clients import create
                    customer=create(values).name
                else:
                    client=frappe.get_doc(dict(doctype='Customer',customer_name=values['customer_name'],customer_type=values['customer_type'],customer_group='Commercial',territory='All Territories',default_currency=values.get('default_currency') or None)).insert()
                    customer=client.name
            row=dict(row,customer=customer)
        if row.get('designation'):
            from plus_point.operations import save_agreement,create_plan
            terms=save_agreement(dict(customer=row['customer'],agreement_title=row['event_name'],scope=row['agreement'],status='Active',
                effective_start=row['start_date'],effective_end=row['end_date'],billing_model=row['billing_model'],fixed_amount=row.get('fixed_amount') or 0,
                agreement_currency=row.get('agreement_currency') or frappe.db.get_value('Company',company,'default_currency'),
                staffing=[dict(site_name=row['site_name'],designation=row['designation'],phase='Event',start_date=row['start_date'],end_date=row['end_date'],workers_required=row['workers_per_day'],client_rate=row.get('client_rate') or 0,wage_rate=0)]))
            return frappe.get_doc('PP Event Plan',create_plan(terms['name'],row['event_name'])['name'])
        result=create_event(company,row['customer'],row['event_name'],row['start_date'],row['end_date'],row['agreement'],
            row['billing_model'],row.get('wage_rate') or 0,row['client_rate'] or 0,row['fixed_amount'] or 0,
            sites=[dict(site_name=row['site_name'],phase='Event',start_date=row['start_date'],end_date=row['end_date'],workers_required=int(positive(row['workers_per_day'],'Workers per day',whole=True)))])
        return frappe.get_doc('PP Event Plan',result['plan'])
    doc.save();return doc
