"""Event staffing, date-bound resource reservations and actual-work comparison.

Plans create no work, wages, invoices or stock movements. ERPNext owns stock.
"""
from collections import defaultdict
from decimal import Decimal
import json

import frappe
from frappe.utils import add_days, getdate, today
from plus_point.finance import as_decimal
from plus_point.setup_flow import linked, require_customer


def span(start,end):
    start,end=getdate(start),getdate(end)
    if end<start or (end-start).days>365:
        frappe.throw('Use an inclusive date range of 1–366 days')
    return [str(add_days(start,i)) for i in range((end-start).days+1)]


def positive(value,label,whole=False,allow_zero=False):
    try:number=as_decimal(value or 0)
    except ValueError:frappe.throw(f'{label} must be a finite number')
    if not number.is_finite() or number<0 or (not allow_zero and number==0) or (whole and number!=number.to_integral_value()):
        frappe.throw(f'{label} must be a {"whole " if whole else ""}{"non-negative" if allow_zero else "positive"} number')
    return number


def context(doc):
    require_customer()
    project=linked('Project',doc.project)
    linked('Company',project.company)
    doc.company=project.company
    if doc.get('site'):
        site=linked('PP Site',doc.site)
        if site.project!=project.name or (not site.is_active and doc.get('status')!='Cancelled'):
            frappe.throw('Choose an active event site in this project')
    span(doc.start_date,doc.end_date)
    bounds=frappe.db.get_value('PP Event Plan',{'project':project.name},['start_date','end_date'],as_dict=True,for_update=True)
    if bounds and (getdate(doc.start_date)<getdate(bounds.start_date) or getdate(doc.end_date)>getdate(bounds.end_date)):
        frappe.throw('Resource dates must be inside the event plan')
    return project


def validate_plan(doc):
    require_customer();project=linked('Project',doc.project);linked('Company',project.company);doc.company=project.company
    if not doc.is_new():frappe.db.get_value('PP Event Plan',doc.name,'name',for_update=True)
    terms=linked('PP Contract Terms',doc.contract_terms)
    if doc.get('selected_crew'):
        from plus_point.crew import selection
        for name in selection(doc.selected_crew):linked('Employee',name,doc.company)
    if terms.project!=doc.project or terms.status!='Active':
        frappe.throw('Choose active client billing terms for this event project')
    days=span(doc.start_date,doc.end_date)
    if terms.effective_start and getdate(days[0])<getdate(terms.effective_start) or terms.effective_end and getdate(days[-1])>getdate(terms.effective_end):
        frappe.throw('Event dates must be inside the client billing agreement')
    positive(doc.wage_rate,'Daily crew wage')
    positive(doc.client_rate,'Client rate',allow_zero=terms.billing_model=='Fixed')
    if terms.billing_model=='Fixed' and as_decimal(doc.client_rate or 0)!=0:
        frappe.throw('Fixed contracts use milestones, not worker-day client charges')
    if not doc.staffing or len(doc.staffing)>60 or len({r.site for r in doc.staffing})>12:
        frappe.throw('Add 1–60 staffing phases covering at most 12 event sites')
    by_site=defaultdict(list)
    for row in doc.staffing:
        site=linked('PP Site',row.site)
        if site.project!=doc.project or not site.is_active:
            frappe.throw('Each staffing row needs an active site from this event project')
        span(row.start_date,row.end_date)
        if str(getdate(row.start_date))<days[0] or str(getdate(row.end_date))>days[-1]:
            frappe.throw('Staffing phases must be within the event dates')
        count=positive(row.workers_required,'Workers per day',whole=True)
        if count>500:frappe.throw('Use at most 500 workers per site per day')
        for first,last in by_site[row.site]:
            if getdate(row.start_date)<=last and getdate(row.end_date)>=first:
                frappe.throw('Staffing phases at the same site cannot overlap; use one daily requirement')
        by_site[row.site].append((getdate(row.start_date),getdate(row.end_date)))
    if doc.is_new() and doc.crew_allocated:
        frappe.throw('Use Preview crew plan and Allocate crew to create a deployment')
    if not doc.is_new():
        for doctype in ('PP Vehicle Booking','PP Equipment Booking'):
            for booking in frappe.get_all(doctype,filters={'project':doc.project,'status':'Planned'},fields=['start_date','end_date']):
                if getdate(booking.start_date)<getdate(doc.start_date) or getdate(booking.end_date)>getdate(doc.end_date):
                    frappe.throw('Update existing event resource bookings before shortening the event date range')
        old=doc.get_doc_before_save()
        if old and int(doc.crew_allocated or 0)!=int(old.crew_allocated or 0):
            frappe.throw('Use the crew allocation or release action to change deployment status')
        if old and (old.crew_allocated or frappe.db.exists('PP Assignment',{'pp_event_plan':doc.name})):
            keys=('project','contract_terms','start_date','end_date','wage_rate','client_rate','selected_crew')
            rows=lambda d:[(r.site,str(r.start_date),str(r.end_date),int(r.workers_required),r.phase) for r in d.staffing]
            if any(str(doc.get(k))!=str(old.get(k)) for k in keys) or rows(doc)!=rows(old):
                frappe.throw('Release unused crew before changing this plan. Recorded attendance keeps its original plan locked.')


def validate_vehicle(doc,method=None):
    if frappe.conf.get('pp_control_plane') or frappe.flags.in_migrate:return
    if doc.get('pp_crew_seats') is None:return
    positive(doc.pp_crew_seats,'Crew seats',whole=True,allow_zero=True)
    positive(doc.pp_cargo_capacity,'Inventory capacity',allow_zero=True)
    if not doc.is_new() and frappe.db.exists('DocType','PP Vehicle Booking'):
        rows=frappe.get_all('PP Vehicle Booking',filters={'vehicle':doc.name,'status':'Planned','end_date':['>=',today()]},
            fields=['company','purpose','crew_count','cargo_load','cargo_uom'])
        for row in rows:
            if not doc.pp_event_enabled or row.company!=doc.company or row.purpose=='Crew' and row.crew_count>doc.pp_crew_seats or row.purpose=='Inventory' and (row.cargo_load>doc.pp_cargo_capacity or row.cargo_uom!=doc.pp_cargo_uom):
                frappe.throw('Update or cancel future event bookings before reducing capacity, changing load units/company or disabling this vehicle')


def validate_vehicle_booking(doc):
    context(doc)
    vehicle=linked('Vehicle',doc.vehicle)
    frappe.db.get_value('Vehicle',vehicle.name,'name',for_update=True)
    # Re-read after the lock so a capacity update cannot leave a stale booking.
    vehicle=frappe.get_doc('Vehicle',vehicle.name)
    if vehicle.company!=doc.company:frappe.throw('Vehicle must belong to the event company')
    if doc.status=='Cancelled':return
    if not vehicle.pp_event_enabled:frappe.throw('Choose an active event vehicle')
    if doc.purpose=='Crew':
        count=positive(doc.crew_count,'Crew passengers',whole=True)
        if count>vehicle.pp_crew_seats:frappe.throw('Crew passengers exceed this vehicle’s seats (driver excluded)')
        doc.cargo_load=0;doc.cargo_uom=''
    elif doc.purpose=='Inventory':
        load=positive(doc.cargo_load,'Inventory load',whole=vehicle.pp_cargo_uom=='units')
        if load>as_decimal(vehicle.pp_cargo_capacity):frappe.throw('Inventory load exceeds vehicle capacity')
        doc.cargo_uom=vehicle.pp_cargo_uom;doc.crew_count=0
    else:frappe.throw('Choose Crew or Inventory transport')
    overlap=frappe.db.sql('''select name from `tabPP Vehicle Booking` where vehicle=%s and status='Planned'
        and name!=%s and start_date<=%s and end_date>=%s limit 1''',
        (doc.vehicle,doc.name or '',doc.end_date,doc.start_date))
    if overlap:frappe.throw('This vehicle is already booked on these dates. Change the vehicle/dates or cancel its earlier booking.')


def reserved_peak(item,warehouse,start,end,exclude=None):
    rows=frappe.get_all('PP Equipment Booking',filters={'item':item,'warehouse':warehouse,'status':'Planned',
        'name':['!=',exclude or ''],'start_date':['<=',end],'end_date':['>=',start]},fields=['quantity','start_date','end_date'])
    changes=defaultdict(Decimal)
    for row in rows:
        first=max(getdate(start),getdate(row.start_date));last=min(getdate(end),getdate(row.end_date))
        changes[str(first)]+=as_decimal(row.quantity);changes[str(add_days(last,1))]-=as_decimal(row.quantity)
    total=peak=Decimal(0)
    for day in sorted(changes):total+=changes[day];peak=max(peak,total)
    return peak


def stock_available(item,warehouse,start,end,exclude=None,lock=False):
    rows=frappe.db.sql('select actual_qty from tabBin where item_code=%s and warehouse=%s'+(' for update' if lock else ''),
        (item,warehouse))
    actual=as_decimal(rows[0][0]) if rows else Decimal(0)
    reserved=reserved_peak(item,warehouse,start,end,exclude)
    return dict(on_hand=str(actual),reserved=str(reserved),available=str(actual-reserved))


def validate_equipment_booking(doc):
    context(doc);warehouse=linked('Warehouse',doc.warehouse,doc.company);item=linked('Item',doc.item)
    doc.stock_uom=item.stock_uom
    if doc.status=='Cancelled':return
    if warehouse.is_group or warehouse.disabled or not item.is_stock_item or item.disabled:
        frappe.throw('Choose an active stock item and a non-group warehouse')
    qty=positive(doc.quantity,'Quantity reserved',whole=bool(frappe.db.get_value('UOM',item.stock_uom,'must_be_whole_number')))
    available=stock_available(doc.item,doc.warehouse,doc.start_date,doc.end_date,doc.name,lock=True)
    if qty>as_decimal(available['available']):
        frappe.throw(f"Not enough inventory for these dates. Available: {available['available']} {doc.stock_uom}. Reduce the quantity, change dates or review warehouse stock.")


def protect_stock_snapshot(doc,method=None):
    if frappe.conf.get('pp_control_plane') or not frappe.db.exists('DocType','PP Equipment Booking'):return
    for row in sorted(doc.items,key=lambda r:(r.item_code,r.warehouse)):
        stock_available(row.item_code,row.warehouse,today(),'9999-12-30',lock=True)
        peak=reserved_peak(row.item_code,row.warehouse,today(),'9999-12-30')
        if as_decimal(row.qty)<peak:
            frappe.throw('This stock balance is below equipment already reserved for events. Review or cancel those bookings first.')


def protect_stock_issue(doc,method=None):
    if frappe.conf.get('pp_control_plane') or not frappe.db.exists('DocType','PP Equipment Booking'):return
    changes=defaultdict(Decimal)
    for row in doc.items:
        qty=as_decimal(row.transfer_qty or row.qty or 0)
        if row.s_warehouse:changes[(row.item_code,row.s_warehouse)]-=qty
        if row.t_warehouse:changes[(row.item_code,row.t_warehouse)]+=qty
    for (item,warehouse),change in sorted(changes.items()):
        if change>=0:continue
        stock=stock_available(item,warehouse,today(),'9999-12-30',lock=True)
        if as_decimal(stock['on_hand'])+change<as_decimal(stock['reserved']):
            frappe.throw('This stock issue would consume equipment reserved for events. Review or cancel its reservations first.')


def plan_doc(name,write=False):
    require_customer();doc=linked('PP Event Plan',name)
    doc.check_permission('write' if write else 'read');linked('Project',doc.project,doc.company)
    return doc


def crew_proposal(doc,lock=False):
    people=frappe.get_list('Employee',filters={'company':doc.company,'status':'Active'},fields=['name','employee_name','date_of_joining','relieving_date'],order_by='name',limit_page_length=0)
    if len(people)>2000:frappe.throw('Use a smaller active crew pool for this local planner')
    if doc.get('selected_crew'):
        from plus_point.crew import selection
        chosen=selection(doc.selected_crew);by_name={p.name:p for p in people}
        people=[by_name[name] for name in chosen if name in by_name]
    if lock:
        for person in people:frappe.db.get_value('Employee',person.name,'name',for_update=True)
    busy=defaultdict(list);commitments=defaultdict(list)
    for row in frappe.get_all('PP Assignment',filters={'employee':['in',[p.name for p in people]],'start_date':['<=',doc.end_date]},
        fields=['employee','project','site','start_date','end_date']):
        if not row.end_date or getdate(row.end_date)>=getdate(doc.start_date):
            busy[row.employee].append((getdate(row.start_date),getdate(row.end_date or '9999-12-31')))
            commitments[row.employee].append(row)
    proposal,shortages=[],[];existing_coverage=0
    for phase in sorted(doc.staffing,key=lambda r:(str(r.start_date),str(r.end_date),r.site)):
        first,last=getdate(phase.start_date),getdate(phase.end_date)
        eligible=[p for p in people if (not p.date_of_joining or getdate(p.date_of_joining)<=first) and (not p.relieving_date or getdate(p.relieving_date)>=last)]
        covered=[p for p in eligible if any(r.project==doc.project and r.site==phase.site and getdate(r.start_date)<=first and getdate(r.end_date or '9999-12-31')>=last for r in commitments[p.name])
            and not any(r.site!=phase.site and getdate(r.start_date)<=last and getdate(r.end_date or '9999-12-31')>=first for r in commitments[p.name])]
        need=max(0,int(phase.workers_required)-len(covered));existing_coverage+=min(len(covered),int(phase.workers_required))
        candidates=[p for p in eligible if not any(a<=last and b>=first for a,b in busy[p.name])]
        chosen=candidates[:need]
        if len(chosen)<need:shortages.append(dict(site=phase.site,from_date=str(first),to_date=str(last),missing=need-len(chosen)))
        for person in chosen:
            proposal.append(dict(employee=person.name,worker=person.employee_name,site=phase.site,start_date=str(first),end_date=str(last)))
            busy[person.name].append((first,last))
    if len(proposal)>1000:frappe.throw('Split this event into smaller plans (maximum 1,000 generated assignments)')
    return dict(assignments=proposal,shortages=shortages,existing_coverage=existing_coverage)


@frappe.whitelist()
def preview_crew(plan,employees=None):
    doc=plan_doc(plan)
    if doc.crew_allocated:return dict(already_allocated=True,assignments=[],shortages=[])
    if employees is not None:
        from plus_point.crew import validate_selected
        doc.selected_crew=json.dumps(validate_selected(employees,doc.company,doc.start_date,doc.end_date))
    return crew_proposal(doc)


@frappe.whitelist(methods=['POST'])
def allocate_crew(plan):
    doc=plan_doc(plan,True);frappe.db.get_value('PP Event Plan',doc.name,'name',for_update=True);doc.reload()
    if doc.crew_allocated:return dict(created=0,already_allocated=True)
    if doc.get('selected_crew'):
        from plus_point.crew import validate_selected
        validate_selected(doc.selected_crew,doc.company,doc.start_date,doc.end_date,lock=True)
    validate_plan(doc);proposal=crew_proposal(doc,lock=True)
    if proposal['shortages']:frappe.throw('Not enough available workers for every phase. Add workers, close conflicting assignments or reduce the requirement, then preview again.')
    frappe.db.savepoint('pp_event_crew')
    try:
        for row in proposal['assignments']:
            frappe.get_doc(dict(doctype='PP Assignment',employee=row['employee'],site=row['site'],project=doc.project,
                contract_terms=doc.contract_terms,start_date=row['start_date'],end_date=row['end_date'],
                wage_rate=doc.wage_rate,client_rate=doc.client_rate,pp_event_plan=doc.name)).insert()
        frappe.db.set_value('PP Event Plan',doc.name,'crew_allocated',1)
    except Exception:
        frappe.db.rollback(save_point='pp_event_crew');raise
    return dict(created=len(proposal['assignments']),already_allocated=False)


@frappe.whitelist(methods=['POST'])
def release_crew(plan):
    doc=plan_doc(plan,True);frappe.db.get_value('PP Event Plan',doc.name,'name',for_update=True)
    names=frappe.get_list('PP Assignment',filters={'pp_event_plan':doc.name},pluck='name',order_by='name',limit_page_length=0)
    for name in names:
        frappe.db.get_value('PP Assignment',name,'name',for_update=True)
        if frappe.db.exists('PP Work Entry',{'assignment':name}) or frappe.db.exists('PP Register Line',{'assignment':name}):
            frappe.throw('Recorded or draft attendance uses this crew. Keep its plan and create a separate project/phase for revised future work.')
    frappe.db.savepoint('pp_release_event_crew')
    try:
        for name in names:frappe.delete_doc('PP Assignment',name)
        frappe.db.set_value('PP Event Plan',doc.name,'crew_allocated',0)
    except Exception:
        frappe.db.rollback(save_point='pp_release_event_crew');raise
    return dict(released=len(names))


@frappe.whitelist()
def timeline(plan):
    doc=plan_doc(plan);days=span(doc.start_date,doc.end_date);sites=sorted({r.site for r in doc.staffing})
    assignments=frappe.get_list('PP Assignment',filters={'project':doc.project,'site':['in',sites],
        'start_date':['<=',doc.end_date]},fields=['employee','site','start_date','end_date'],limit_page_length=0)
    actual=frappe.db.sql('''select site,work_date,sum(units) units from `tabPP Work Entry` where project=%s
        and status='Approved' and work_date between %s and %s group by site,work_date''',(doc.project,days[0],days[-1]),as_dict=True)
    actual={(r.site,str(r.work_date)):str(r.units) for r in actual}
    labels={r.name:r.site_name for r in frappe.get_list('PP Site',filters={'name':['in',sites]},fields=['name','site_name'],limit_page_length=0)}
    output=[]
    for site in sites:
        cells=[]
        for day in days:
            required=sum(int(r.workers_required) for r in doc.staffing if r.site==site and str(getdate(r.start_date))<=day<=str(getdate(r.end_date)))
            assigned=len({r.employee for r in assignments if r.site==site and str(r.start_date)<=day and (not r.end_date or str(r.end_date)>=day)})
            cells.append(dict(date=day,required=required,assigned=assigned,actual=actual.get((site,day),'0')))
        output.append(dict(site=site,title=labels.get(site,site),days=cells,worker_days=sum(c['required'] for c in cells)))
    return dict(plan=doc.name,title=doc.event_name,project=doc.project,company=doc.company,start=days[0],end=days[-1],
        duration=len(days),sites=output,crew_allocated=doc.crew_allocated,
        vehicle_bookings=frappe.db.count('PP Vehicle Booking',{'project':doc.project,'status':'Planned'}),
        equipment_bookings=frappe.db.count('PP Equipment Booking',{'project':doc.project,'status':'Planned'}))


@frappe.whitelist(methods=['POST'])
def create_event(company,customer,event_name,start_date,end_date,agreement,billing_model,wage_rate,client_rate=0,fixed_amount=0,sites=None):
    require_customer();linked('Company',company);linked('Customer',customer);span(start_date,end_date)
    if not str(event_name or '').strip() or not str(agreement or '').strip():frappe.throw('Enter the event name and client agreement')
    rows=frappe.parse_json(sites) or []
    if not rows or len(rows)>60:frappe.throw('Add site names, phase dates and workers per day')
    frappe.db.savepoint('pp_create_event')
    try:
        project=frappe.get_doc(dict(doctype='Project',project_name=event_name,company=company,customer=customer,
            expected_start_date=start_date,expected_end_date=end_date)).insert()
        contract=frappe.get_doc(dict(doctype='Contract',party_type='Customer',party_name=customer,
            start_date=start_date,end_date=end_date,contract_terms=agreement)).insert()
        terms=frappe.get_doc(dict(doctype='PP Contract Terms',contract=contract.name,project=project.name,
            effective_start=start_date,effective_end=end_date,billing_model=billing_model,fixed_amount=fixed_amount,
            currency=frappe.db.get_value('Company',company,'default_currency'),status='Active')).insert()
        locations={};staffing=[]
        for row in rows:
            title=str(row.get('site_name') or '').strip()
            if not title:frappe.throw('Enter each event site name')
            if title not in locations:locations[title]=frappe.get_doc(dict(doctype='PP Site',site_name=title,project=project.name,is_active=1)).insert().name
            staffing.append(dict(site=locations[title],phase=row.get('phase') or 'Event',start_date=row.get('start_date'),
                end_date=row.get('end_date'),workers_required=row.get('workers_required')))
        plan=frappe.get_doc(dict(doctype='PP Event Plan',event_name=event_name,project=project.name,company=company,
            contract_terms=terms.name,start_date=start_date,end_date=end_date,wage_rate=wage_rate,client_rate=client_rate,staffing=staffing)).insert()
    except Exception:
        frappe.db.rollback(save_point='pp_create_event');raise
    return dict(plan=plan.name,project=project.name,contract_terms=terms.name)


@frappe.whitelist()
def inventory(company,start_date=None,end_date=None):
    require_customer();linked('Company',company)
    start_date=start_date or today();end_date=end_date or start_date;span(start_date,end_date)
    warehouses=frappe.get_list('Warehouse',filters={'company':company,'is_group':0,'disabled':0},pluck='name',limit_page_length=0)
    items={r.name:r for r in frappe.get_list('Item',filters={'is_stock_item':1,'disabled':0},fields=['name','item_name','stock_uom'],limit_page_length=500)}
    bins=frappe.db.sql('select item_code,warehouse,actual_qty from tabBin where warehouse in %(warehouses)s and item_code in %(items)s',
        {'warehouses':warehouses,'items':list(items)},as_dict=True) if warehouses and items else []
    return dict(rows=[dict(item=r.item_code,title=items[r.item_code].item_name,warehouse=r.warehouse,uom=items[r.item_code].stock_uom,
        **stock_available(r.item_code,r.warehouse,start_date,end_date)) for r in bins],start=str(start_date),end=str(end_date))


@frappe.whitelist(methods=['POST'])
def save_resource(kind,company,values):
    require_customer();linked('Company',company)
    from plus_point.event_imports import SCHEMAS,validate,save
    if kind not in ('clients','vehicles','inventory_items','warehouses','event_sites'):frappe.throw('Choose an event resource type')
    raw=frappe.parse_json(values) or {}
    if kind=='clients':
        from plus_point.clients import create
        frappe.db.savepoint('pp_new_client')
        try:doc=create(raw)
        except Exception:
            frappe.db.rollback(save_point='pp_new_client');raise
        return dict(doctype=doc.doctype,name=doc.name)
    if kind=='vehicles' and raw.get('purpose') in ('Crew','Inventory'):
        if raw['purpose']=='Crew':raw.update(cargo_capacity=0,cargo_uom='units')
        else:raw['crew_seats']=0
    row={key:str(raw.get(key) if raw.get(key) is not None else '') for key in SCHEMAS[kind]}
    validate(kind,company,row);doc=save(kind,company,row)
    return dict(doctype=doc.doctype,name=doc.name)


def summary(company):
    plans=frappe.get_list('PP Event Plan',filters={'company':company,'end_date':['>=',today()]},
        fields=['name','event_name','start_date','end_date','crew_allocated'],order_by='start_date',limit_page_length=4)
    return [dict(row,duration=len(span(row.start_date,row.end_date))) for row in plans]


@frappe.whitelist()
def plans_for(company=None,customer=None,project=None):
    require_customer()
    companies=frappe.get_list('Company',pluck='name',limit_page_length=0)
    if company and company not in companies:frappe.throw('Choose your company',frappe.PermissionError)
    filters={'company':['in',[company] if company else companies]}
    if customer:linked('Customer',customer);filters['customer']=customer
    if project:linked('Project',project);filters['name']=project
    projects=frappe.get_list('Project',filters=filters,pluck='name',limit_page_length=0)
    return frappe.get_list('PP Event Plan',filters={'project':['in',projects]},fields=['name','event_name','company'],order_by='start_date desc',limit_page_length=20) if projects else []
