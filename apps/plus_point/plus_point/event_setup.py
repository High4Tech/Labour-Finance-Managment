"""Company-owned, resumable event setup using native business records."""
import json
import frappe
from frappe.utils import cint,getdate,today
from plus_point.setup_flow import linked,insert,require_customer
from plus_point.events import span

SELECTED='pp_event_setup_company_v1'
STEPS=['company','client','event','terms','workers','plan','vehicle','inventory','allocate','done']


def companies():
    from plus_point import workspace
    filters={} if workspace.fixture_context() else {'name':workspace.company() or ''}
    return frappe.get_list('Company',filters=filters,fields=['name','company_name','default_currency','pp_invoice_currency','country','abbr'],order_by='name',limit_page_length=0)


def established(company):
    projects=frappe.get_list('Project',filters={'company':company},pluck='name',limit_page_length=0)
    return bool(projects and frappe.db.exists('PP Assignment',{'project':['in',projects]}))


def current():
    rows=companies();allowed={r.name for r in rows}
    company=frappe.defaults.get_user_default(SELECTED) or frappe.defaults.get_user_default('Company')
    company=company if company in allowed else rows[0].name if rows else None
    raw=frappe.db.get_value('Company',company,'pp_event_setup_state') if company else None
    if raw:return json.loads(raw)
    if not company:
        from plus_point.workspace import draft
        saved=draft()
        if saved:return saved
    ready=bool(company and established(company))
    return dict(step='done' if ready else 'company',company=company,required=not ready)


def persist(saved):
    if saved.get('company'):
        linked('Company',saved['company']).check_permission('write')
        frappe.db.set_value('Company',saved['company'],'pp_event_setup_state',json.dumps(saved),update_modified=False)
        frappe.defaults.set_user_default(SELECTED,saved['company'])
    else:
        from plus_point.workspace import save_draft
        save_draft(saved)
    return saved


def frontier(saved):
    # Legacy journeys have no explicit high-water mark until their next action.
    index=STEPS.index(saved['step'])
    if saved['step']=='done' and not saved.get('project'):index=0
    return max(index,int(saved.get('furthest',0)))


def step_values(saved):
    """Revisit the same native records; do not turn an edit into another insert."""
    step=saved['step'];result={}
    if step=='event' and saved.get('site'):
        site=linked('PP Site',saved['site'])
        result={k:site.get(k) for k in ('site_name','country','state','city','address_line1','address_line2','postal_code','latitude','longitude')}
    elif step=='terms' and saved.get('contract_terms'):
        terms=linked('PP Contract Terms',saved['contract_terms'])
        result=dict(billing_model=terms.billing_model,fixed_amount=terms.fixed_amount,agreement=linked('Contract',terms.contract).contract_terms)
    elif step=='plan' and saved.get('plan'):
        plan=linked('PP Event Plan',saved['plan'])
        result=dict(wage_rate=plan.wage_rate,client_rate=plan.client_rate,staffing=[{k:r.get(k) for k in ('site','phase','start_date','end_date','workers_required')} for r in plan.staffing])
    elif step=='vehicle':
        result['no_vehicle']=int(not saved.get('vehicle_booking') and frontier(saved)>STEPS.index(step))
        if saved.get('vehicle_booking'):
            booking=linked('PP Vehicle Booking',saved['vehicle_booking'])
            result.update({k:booking.get(k) for k in ('purpose','crew_count','cargo_load')})
    elif step=='inventory':
        result['no_equipment']=int(not saved.get('equipment_booking') and frontier(saved)>STEPS.index(step))
        if saved.get('equipment_booking'):result['quantity']=linked('PP Equipment Booking',saved['equipment_booking']).quantity
    return result


@frappe.whitelist()
def status():
    require_customer();saved=current()
    from plus_point.locations import currency_locked
    return dict(state=saved,companies=companies(),required=bool(saved.get('required') and not saved.get('skipped') and saved['step']!='done'),
        currency_locked=bool(currency_locked(saved.get('company'))),furthest=frontier(saved),values=step_values(saved))


@frappe.whitelist(methods=['POST'])
def control(action,step=None):
    require_customer()
    frappe.db.get_value('User',frappe.session.user,'name',for_update=True)
    saved=current()
    if saved.get('company'):
        frappe.db.get_value('Company',saved['company'],'name',for_update=True)
        saved=current()
    saved['furthest']=frontier(saved)
    if action in ('start','resume'):
        saved['skipped']=False
        if saved['step']!='done':saved['required']=True
    elif action=='skip':saved.update(skipped=True,required=False)
    elif action=='back':saved['step']=STEPS[max(0,STEPS.index(saved['step'])-1)]
    elif action=='go':
        if step not in STEPS[:-1] or STEPS.index(step)>saved['furthest']:frappe.throw('Complete the earlier steps before opening this section')
        saved['step']=step
    else:frappe.throw('Choose resume, skip, back or a completed step')
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
    saved['furthest']=frontier(saved)
    frappe.db.savepoint('pp_event_setup_step')
    try:
        if step=='company':
            from plus_point import workspace
            bound=workspace.company() if not workspace.fixture_context() else None
            if bound and values.company and values.company!=bound:frappe.throw('Use the company attached to this workspace')
            selected=values.company or bound
            if selected:
                doc=linked('Company',selected);company=doc.name
                if values.country:
                    from plus_point.locations import set_company_country
                    set_company_country(doc,values.country,values.currency)
            else:
                from plus_point.locations import country_defaults
                defaults=country_defaults(values.country)
                currency=values.currency or defaults['currency'];linked('Currency',currency)
                frappe.db.set_value('Currency',currency,'enabled',1)
                title=str(values.company_name or '').strip()
                if not title:frappe.throw('Enter your business name')
                abbr=str(values.abbr or '').strip() or ''.join(word[0] for word in title.split())[:5].upper()
                company=insert('Company',company_name=title,abbr=abbr,country=values.country,default_currency=currency,pp_invoice_currency=currency).name
            if saved.get('company') and saved['company']!=company:saved=dict(step='company',required=not established(company))
            saved['company']=company;frappe.defaults.set_user_default('Company',company)
        else:
            company=saved['company'];linked('Company',company)
            if step=='client':
                if values.customer:
                    client=linked('Customer',values.customer)
                    if cint(values.edit_client):
                        from plus_point.clients import save
                        client=save(values,client.name)
                else:
                    from plus_point.clients import create
                    client=create(values)
                if saved.get('customer') and saved['customer']!=client.name:
                    saved={key:saved[key] for key in ('company','step','required') if key in saved}
                saved.update(customer=client.name,client_label=client.customer_name)
            elif step=='event':
                span(values.start_date,values.end_date)
                if values.project:
                    project=linked('Project',values.project,company)
                    if project.customer!=saved['customer']:frappe.throw('Choose a project for this client')
                    # Date changes after planning require revisiting the plan explicitly.
                    if (str(getdate(project.expected_start_date))!=str(getdate(values.start_date)) or str(getdate(project.expected_end_date))!=str(getdate(values.end_date))):
                        if saved.get('plan'):frappe.throw('This event already has a plan. Change its dates in the event plan so staffing and reservations stay aligned.')
                        project.expected_start_date=values.start_date;project.expected_end_date=values.end_date;project.save()
                else:project=insert('Project',project_name=values.event_name,company=company,customer=saved['customer'],
                    expected_start_date=values.start_date,expected_end_date=values.end_date)
                if saved.get('project') and saved['project']!=project.name:
                    for key in ('contract_terms','billing_model','plan','vehicle_booking','equipment_booking'):saved.pop(key,None)
                    saved['furthest']=STEPS.index('event')
                if values.site:
                    site=linked('PP Site',values.site)
                    if site.project!=project.name or not site.is_active:frappe.throw('Choose an active venue for this project')
                    if cint(values.edit_site):
                        from plus_point.locations import site_values
                        site.update(dict(site_name=values.site_name,**site_values(values)));site.save()
                else:
                    from plus_point.locations import site_values
                    # Operator regression fixtures retain the older minimal API.
                    from plus_point.workspace import fixture_context
                    structured=site_values(values,required=not fixture_context() or bool(values.country))
                    if not structured['address']:structured['address']=values.address or ''
                    site=insert('PP Site',site_name=values.site_name,project=project.name,is_active=1,**structured)
                saved.update(project=project.name,event_name=project.project_name,site=site.name,site_label=site.site_name,
                    start_date=str(getdate(values.start_date)),end_date=str(getdate(values.end_date)))
            elif step=='terms':
                project=project_context(saved)
                if values.contract_terms:
                    terms=linked('PP Contract Terms',values.contract_terms)
                    if terms.project!=project.name or terms.status!='Active':frappe.throw('Choose active terms for this event')
                    if cint(values.edit_terms):
                        if not str(values.agreement or '').strip():frappe.throw('Describe the actual client agreement')
                        terms.update(dict(billing_model=values.billing_model,fixed_amount=values.fixed_amount if values.billing_model=='Fixed' else 0));terms.save()
                        contract=linked('Contract',terms.contract);contract.contract_terms=values.agreement;contract.save()
                else:
                    if not str(values.agreement or '').strip():frappe.throw('Describe the actual client agreement')
                    contract=insert('Contract',party_type='Customer',party_name=saved['customer'],start_date=saved['start_date'],
                        end_date=saved['end_date'],contract_terms=values.agreement)
                    terms=insert('PP Contract Terms',project=project.name,contract=contract.name,billing_model=values.billing_model,
                        fixed_amount=values.fixed_amount or 0,currency=frappe.db.get_value('Company',company,'default_currency'),
                        effective_start=saved['start_date'],effective_end=saved['end_date'],status='Active')
                saved.update(contract_terms=terms.name,billing_model=terms.billing_model)
            elif step=='workers':
                from plus_point.crew import validate_selected
                existing_plan=frappe.db.get_value('PP Event Plan',{'project':saved['project']},'name')
                if existing_plan:frappe.db.get_value('PP Event Plan',existing_plan,'name',for_update=True)
                if values.employees is not None:
                    names=validate_selected(values.employees,company,saved['start_date'],saved['end_date'],lock=True)
                elif values.employee:
                    employee=linked('Employee',values.employee,company)
                    if employee.status!='Active':frappe.throw('Choose an active worker')
                    names=[employee.name]
                else:employee=insert('Employee',first_name=values.first_name,last_name=values.last_name,gender=values.gender,
                    date_of_birth=values.date_of_birth,date_of_joining=values.date_of_joining,company=company,status='Active',cell_number=values.cell_number)
                if values.employees is None and not values.employee:names=[employee.name]
                saved.update(employee=names[0],employees=names,worker_label=frappe.db.get_value('Employee',names[0],'employee_name'))
                saved['plan']=existing_plan
                if saved.get('plan'):
                    from plus_point.crew import save_selection
                    save_selection(saved['plan'],names)
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
                if saved.get('employees'):
                    from plus_point.crew import save_selection
                    if not plan.crew_allocated:save_selection(plan.name,saved['employees'])
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
                        if values.purpose=='Crew':row.update(cargo_capacity='0',cargo_uom='units')
                        elif values.purpose=='Inventory':row['crew_seats']='0'
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
                        positive(values.valuation_rate or 0,'Value per unit',allow_zero=True)
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
                        row=dict(item_code=item.name,warehouse=warehouse.name,date=today(),quantity=str(values.stock_quantity),valuation_rate=str(values.valuation_rate or 0),allow_zero_valuation_rate=1)
                        validate('stock_balances',company,row);save('stock_balances',company,row)
                    booking=linked('PP Equipment Booking',saved['equipment_booking']) if saved.get('equipment_booking') else frappe.new_doc('PP Equipment Booking')
                    booking.update(dict(item=item.name,warehouse=warehouse.name,project=saved['project'],site=saved['site'],quantity=values.quantity,
                        start_date=saved['start_date'],end_date=saved['end_date'],status='Planned'));booking.save()
                    saved.update(item=item.name,warehouse=warehouse.name,equipment_booking=booking.name)
            elif step=='allocate':
                from plus_point.events import allocate_crew
                allocate_crew(saved['plan'])
        saved['step']=STEPS[STEPS.index(step)+1]
        saved['furthest']=max(frontier(saved),STEPS.index(saved['step']))
        if saved['step']=='done':saved['required']=False
        return persist(saved)
    except Exception:
        frappe.db.rollback(save_point='pp_event_setup_step');raise
