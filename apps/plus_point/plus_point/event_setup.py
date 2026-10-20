"""Company-owned, resumable event setup using native business records."""
import json
import frappe
from frappe.utils import cint,getdate,today
from plus_point.setup_flow import linked,insert,require_customer
from plus_point.events import span

SELECTED='pp_event_setup_company_v1'
STEPS=['company','client','event','terms','workers','plan','vehicle','inventory','allocate','done']


def companies():
    return frappe.get_list('Company',fields=['name','company_name','default_currency'],order_by='name',limit_page_length=0)


def established(company):
    projects=frappe.get_list('Project',filters={'company':company},pluck='name',limit_page_length=0)
    return bool(projects and frappe.db.exists('PP Assignment',{'project':['in',projects]}))


def current():
    rows=companies();allowed={r.name for r in rows}
    company=frappe.defaults.get_user_default(SELECTED) or frappe.defaults.get_user_default('Company')
    company=company if company in allowed else rows[0].name if rows else None
    raw=frappe.db.get_value('Company',company,'pp_event_setup_state') if company else None
    if raw:return json.loads(raw)
    ready=bool(company and established(company))
    return dict(step='done' if ready else 'company',company=company,required=not ready)


def persist(saved):
    if saved.get('company'):
        linked('Company',saved['company']).check_permission('write')
        frappe.db.set_value('Company',saved['company'],'pp_event_setup_state',json.dumps(saved),update_modified=False)
        frappe.defaults.set_user_default(SELECTED,saved['company'])
    return saved


@frappe.whitelist()
def status():
    require_customer();saved=current()
    return dict(state=saved,companies=companies(),required=bool(saved.get('required') and saved['step']!='done'))


@frappe.whitelist(methods=['POST'])
def control(action):
    require_customer();saved=current()
    if saved.get('company'):
        frappe.db.get_value('Company',saved['company'],'name',for_update=True)
        saved=current()
    if action=='start' and saved['step']=='done':saved=dict(step='company',company=saved.get('company'),required=False)
    elif action=='back':saved['step']=STEPS[max(0,STEPS.index(saved['step'])-1)]
    elif action not in ('start','back'):frappe.throw('Choose start or back')
    return persist(saved)


def project_context(saved):
    return linked('Project',saved['project'],saved['company'])


@frappe.whitelist(methods=['POST'])
def advance(step,values=None):
    require_customer();values=frappe._dict(frappe.parse_json(values) or {})
    frappe.db.get_value('User',frappe.session.user,'name',for_update=True)
    saved=current()
    if saved.get('company'):
        frappe.db.get_value('Company',saved['company'],'name',for_update=True)
        saved=current()
    if step!=saved['step'] or step not in STEPS[:-1]:frappe.throw('Setup has moved on. Reopen the guide to continue.')
    frappe.db.savepoint('pp_event_setup_step')
    try:
        if step=='company':
            company=linked('Company',values.company).name if values.company else insert('Company',company_name=values.company_name,
                abbr=values.abbr,country=values.country,default_currency=values.currency).name
            if saved.get('company') and saved['company']!=company:saved=dict(step='company',required=not established(company))
            saved['company']=company;frappe.defaults.set_user_default('Company',company)
        else:
            company=saved['company'];linked('Company',company)
            if step=='client':
                client=linked('Customer',values.customer) if values.customer else insert('Customer',customer_name=values.customer_name,
                    customer_type='Company',customer_group='Commercial',territory='All Territories')
                if saved.get('customer') and saved['customer']!=client.name:
                    saved={key:saved[key] for key in ('company','step','required') if key in saved}
                saved.update(customer=client.name,client_label=client.customer_name)
            elif step=='event':
                span(values.start_date,values.end_date)
                if values.project:
                    project=linked('Project',values.project,company)
                    if project.customer!=saved['customer']:frappe.throw('Choose a project for this client')
                else:project=insert('Project',project_name=values.event_name,company=company,customer=saved['customer'],
                    expected_start_date=values.start_date,expected_end_date=values.end_date)
                if saved.get('project') and saved['project']!=project.name:
                    for key in ('contract_terms','billing_model','plan','vehicle_booking','equipment_booking'):saved.pop(key,None)
                if values.site:
                    site=linked('PP Site',values.site)
                    if site.project!=project.name or not site.is_active:frappe.throw('Choose an active venue for this project')
                else:site=insert('PP Site',site_name=values.site_name,project=project.name,address=values.address,is_active=1)
                saved.update(project=project.name,event_name=project.project_name,site=site.name,site_label=site.site_name,
                    start_date=str(getdate(values.start_date)),end_date=str(getdate(values.end_date)))
            elif step=='terms':
                project=project_context(saved)
                if values.contract_terms:
                    terms=linked('PP Contract Terms',values.contract_terms)
                    if terms.project!=project.name or terms.status!='Active':frappe.throw('Choose active terms for this event')
                else:
                    if not str(values.agreement or '').strip():frappe.throw('Describe the actual client agreement')
                    contract=insert('Contract',party_type='Customer',party_name=saved['customer'],start_date=saved['start_date'],
                        end_date=saved['end_date'],contract_terms=values.agreement)
                    terms=insert('PP Contract Terms',project=project.name,contract=contract.name,billing_model=values.billing_model,
                        fixed_amount=values.fixed_amount or 0,currency=frappe.db.get_value('Company',company,'default_currency'),
                        effective_start=saved['start_date'],effective_end=saved['end_date'],status='Active')
                saved.update(contract_terms=terms.name,billing_model=terms.billing_model)
            elif step=='workers':
                if values.employee:
                    employee=linked('Employee',values.employee,company)
                    if employee.status!='Active':frappe.throw('Choose an active worker')
                else:employee=insert('Employee',first_name=values.first_name,last_name=values.last_name,gender=values.gender,
                    date_of_birth=values.date_of_birth,date_of_joining=values.date_of_joining,company=company,status='Active',cell_number=values.cell_number)
                saved.update(employee=employee.name,worker_label=employee.employee_name)
                saved['plan']=frappe.db.get_value('PP Event Plan',{'project':saved['project']},'name')
            elif step=='plan':
                project=project_context(saved)
                previous=frappe.db.get_value('PP Event Plan',{'project':project.name},'name')
                if cint(values.use_existing_plan) and not previous:frappe.throw('This project has no saved plan. Uncheck reuse and enter its staffing requirements.')
                if cint(values.use_existing_plan) and previous:
                    plan=linked('PP Event Plan',previous);saved.update(start_date=str(plan.start_date),end_date=str(plan.end_date))
                else:
                    plan=linked('PP Event Plan',previous) if previous else frappe.new_doc('PP Event Plan')
                    staffing=values.staffing or [dict(site=saved['site'],phase='Event',start_date=saved['start_date'],end_date=saved['end_date'],workers_required=values.workers_required)]
                    for row in staffing:
                        if not row.get('site') and str(row.get('site_name') or '').strip():
                            title=str(row['site_name']).strip()
                            row['site']=frappe.db.get_value('PP Site',{'project':project.name,'site_name':title},'name') or insert('PP Site',site_name=title,project=project.name,is_active=1).name
                    plan.update(dict(event_name=project.project_name,project=project.name,company=company,contract_terms=saved['contract_terms'],
                        start_date=saved['start_date'],end_date=saved['end_date'],wage_rate=values.wage_rate,
                        client_rate=0 if saved['billing_model']=='Fixed' else values.client_rate,
                        staffing=staffing))
                    plan.save()
                saved['plan']=plan.name
            elif step=='vehicle':
                if cint(values.no_vehicle):
                    if saved.get('vehicle_booking'):
                        previous=linked('PP Vehicle Booking',saved['vehicle_booking']);previous.status='Cancelled';previous.save()
                    saved['vehicle_booking']=None
                else:
                    from plus_point.event_imports import save,validate
                    if values.vehicle:vehicle=linked('Vehicle',values.vehicle,company)
                    else:
                        row={key:str(values.get(key) if values.get(key) is not None else '') for key in ('license_plate','make','model','crew_seats','cargo_capacity','cargo_uom','fuel_type')};row['status']='Active'
                        validate('vehicles',company,row);vehicle=save('vehicles',company,row)
                    booking=linked('PP Vehicle Booking',saved['vehicle_booking']) if saved.get('vehicle_booking') else frappe.new_doc('PP Vehicle Booking')
                    booking.update(dict(vehicle=vehicle.name,project=saved['project'],site=saved['site'],purpose=values.purpose,
                        crew_count=values.crew_count or 0,cargo_load=values.cargo_load or 0,start_date=saved['start_date'],end_date=saved['end_date'],status='Planned'))
                    booking.save();saved.update(vehicle=vehicle.name,vehicle_booking=booking.name)
            elif step=='inventory':
                if cint(values.no_equipment):
                    if saved.get('equipment_booking'):
                        previous=linked('PP Equipment Booking',saved['equipment_booking']);previous.status='Cancelled';previous.save()
                    saved['equipment_booking']=None
                else:
                    from plus_point.event_imports import save,validate
                    from plus_point.events import positive
                    new_item=not values.item
                    count_stock=new_item or cint(values.set_stock_balance)
                    if new_item and (values.stock_quantity is None or values.stock_quantity==''):
                        frappe.throw('Enter the starting warehouse quantity for this new item. The item name alone does not add stock.')
                    if count_stock:
                        quantity=positive(values.quantity,'Quantity needed for this event')
                        counted=positive(values.stock_quantity,'Warehouse quantity',allow_zero=True)
                        if counted<quantity:
                            frappe.throw(f'Warehouse quantity is {counted}, but this event needs {quantity}. Enter the quantity you actually own or reduce the event quantity.')
                        positive(values.valuation_rate,'Value per unit')
                        if not cint(values.confirm_stock_balance):
                            frappe.throw('Confirm the warehouse quantity and value before saving the item and reserving it.')
                    if values.item:item=linked('Item',values.item)
                    else:
                        if frappe.db.exists('Item',values.item_code):
                            frappe.throw('This equipment code already exists. Choose existing item to use its recorded stock, or enter a different code.')
                        row=dict(item_code=values.item_code,item_name=values.item_name,stock_uom=values.stock_uom,status='Active')
                        validate('inventory_items',company,row);item=save('inventory_items',company,row)
                    warehouse=linked('Warehouse',values.warehouse,company) if values.warehouse else save('warehouses',company,dict(warehouse_name=values.warehouse_name))
                    if count_stock:
                        row=dict(item_code=item.name,warehouse=warehouse.name,date=today(),quantity=str(values.stock_quantity),valuation_rate=str(values.valuation_rate))
                        validate('stock_balances',company,row);save('stock_balances',company,row)
                    booking=linked('PP Equipment Booking',saved['equipment_booking']) if saved.get('equipment_booking') else frappe.new_doc('PP Equipment Booking')
                    booking.update(dict(item=item.name,warehouse=warehouse.name,project=saved['project'],site=saved['site'],quantity=values.quantity,
                        start_date=saved['start_date'],end_date=saved['end_date'],status='Planned'));booking.save()
                    saved.update(item=item.name,warehouse=warehouse.name,equipment_booking=booking.name)
            elif step=='allocate':
                from plus_point.events import allocate_crew
                allocate_crew(saved['plan'])
        saved['step']=STEPS[STEPS.index(step)+1]
        if saved['step']=='done':saved['required']=False
        return persist(saved)
    except Exception:
        frappe.db.rollback(save_point='pp_event_setup_step');raise
