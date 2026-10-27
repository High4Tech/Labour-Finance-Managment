"""Non-HTTP, exact QA-only fixture for concurrent reservation verification."""
import re,time
import frappe
from frappe.utils import today,add_days
from plus_point.event_testing import guard,hierarchy_browser_fixture


def race(action,run_id,index=0):
    guard('qa.localhost')
    if not re.fullmatch('[a-f0-9]{12}',run_id):raise RuntimeError('Exact QA run required')
    prefix='Event Browser QA '+run_id;code=prefix+' Race equipment'
    if action=='begin':
        from plus_point.tests.test_operations import insert
        from plus_point.events import create_event
        data=hierarchy_browser_fixture('begin',run_id)
        customer=insert('Customer',customer_name=prefix+' Client',customer_type='Company',customer_group='Commercial',territory='All Territories')
        insert('Item',item_code=code,item_name='QA reservation race equipment',stock_uom='Nos',is_stock_item=1,item_group='Services')
        warehouse=frappe.db.get_value('Warehouse',{'company':prefix,'is_group':0},'name')
        # Deliberately synthetic balance to isolate locking, never a financial posting.
        balance=insert('Bin',item_code=code,warehouse=warehouse);balance.db_set('actual_qty',12)
        vehicle=insert('Vehicle',license_plate='QA-'+run_id,make='Toyota',model='Crew van',company=prefix,fuel_type='Diesel',uom='Litre',last_odometer=0,pp_event_enabled=1,pp_crew_seats=3,pp_cargo_capacity=100,pp_cargo_uom='units')
        events=[]
        for i in (0,1):
            events.append(create_event(prefix,customer.name,prefix+' Race '+str(i),add_days(today(),1),add_days(today(),2),'QA reservation locking','Daily',100,150,
                sites=[dict(site_name='Race venue',phase='Event',start_date=add_days(today(),1),end_date=add_days(today(),2),workers_required=1)]))
        frappe.db.commit();return dict(ready=True,item=code,warehouse=warehouse,vehicle=vehicle.name,events=events)
    if not frappe.db.exists('Company',prefix):raise RuntimeError('Exact fixture company required')
    if action=='attempt':
        from plus_point.resources import save_booking
        event=frappe.get_doc('PP Event Plan',frappe.db.get_value('PP Event Plan',{'company':prefix,'event_name':prefix+' Race '+str(int(index))},'name'))
        warehouse=frappe.db.get_value('Bin',{'item_code':code},'warehouse')
        frappe.db.sql('SELECT actual_qty FROM tabBin WHERE item_code=%s AND warehouse=%s FOR UPDATE',(code,warehouse))
        time.sleep(1)  # Force both independent sessions to contend on the same stock row.
        try:
            save_booking(event.project,'equipment',dict(site=event.staffing[0].site,item=code,warehouse=warehouse,quantity=8,start_date=event.start_date,end_date=event.end_date,status='Planned'))
            frappe.db.commit();return dict(saved=True)
        except frappe.ValidationError:
            frappe.db.rollback();return dict(saved=False,reason='Insufficient date-based availability')
    if action!='end':raise RuntimeError('Choose a QA fixture action')
    if frappe.db.exists('GL Entry',{'company':prefix}) or frappe.db.exists('Stock Ledger Entry',{'item_code':code}):raise RuntimeError('Posted history; cleanup refused')
    for name in frappe.get_all('PP Equipment Booking',filters={'item':code,'company':prefix},pluck='name'):frappe.delete_doc('PP Equipment Booking',name)
    for name in frappe.get_all('Bin',filters={'item_code':code},pluck='name'):frappe.db.delete('Bin',{'name':name})
    frappe.delete_doc('Item',code)
    return hierarchy_browser_fixture('end',run_id)
