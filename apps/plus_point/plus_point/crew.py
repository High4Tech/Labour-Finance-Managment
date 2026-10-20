"""Shared date-aware worker selection for onboarding and normal crew assignments."""
import json
import frappe
from frappe.utils import getdate
from plus_point.setup_flow import linked,require_customer


def selection(value):
    if isinstance(value,str):value=frappe.parse_json(value)
    if not isinstance(value,list) or not value or len(value)>2000 or any(not isinstance(v,str) for v in value):
        frappe.throw('Select at least one worker (up to 2,000).')
    if len(value)!=len(set(value)):frappe.throw('Each worker can be selected only once.')
    return value


def roster(company,start_date,end_date,lock=False):
    require_customer();linked('Company',company)
    from plus_point.events import span
    span(start_date,end_date);first,last=getdate(start_date),getdate(end_date)
    people=frappe.get_list('Employee',filters={'company':company,'status':'Active'},
        fields=['name','employee_name','cell_number','date_of_joining','relieving_date'],order_by='employee_name,name',limit_page_length=2001)
    if len(people)>2000:frappe.throw('Use at most 2,000 active workers in this workspace.')
    names=sorted(p.name for p in people)
    if lock:
        fresh=[]
        for name in names:
            person=frappe.db.get_value('Employee',name,['name','employee_name','cell_number','date_of_joining','relieving_date','company','status'],as_dict=True,for_update=True)
            if person and person.company==company and person.status=='Active':fresh.append(person)
        people=fresh
    booked=set()
    if names:
        # Locking reads see bookings committed while waiting on the employee locks.
        rows=frappe.db.sql('''SELECT employee FROM `tabPP Assignment`
            WHERE employee IN %(names)s AND start_date<=%(last)s
            AND (end_date IS NULL OR end_date>=%(first)s)''' + (' FOR UPDATE' if lock else ''),
            dict(names=names,first=first,last=last))
        booked={r[0] for r in rows}
    result=[]
    for person in people:
        reason=('Booked for overlapping dates' if person.name in booked else
            'Joining date is after the event starts' if person.date_of_joining and getdate(person.date_of_joining)>first else
            'Employment ends before the event finishes' if person.relieving_date and getdate(person.relieving_date)<last else '')
        result.append(dict(name=person.name,worker=person.employee_name,phone=person.cell_number or '',available=not reason,reason=reason))
    return result


@frappe.whitelist()
def available(company,start_date,end_date):
    rows=roster(company,start_date,end_date)
    return dict(rows=rows,start_date=start_date,end_date=end_date,available=sum(r['available'] for r in rows))


@frappe.whitelist(methods=['POST'])
def add_worker(company,values):
    require_customer();linked('Company',company);values=frappe._dict(frappe.parse_json(values) or {})
    doc=frappe.get_doc(dict(doctype='Employee',company=company,status='Active',create_user_automatically=0,
        **{key:values.get(key) for key in ('first_name','last_name','gender','date_of_birth','date_of_joining','cell_number')})).insert()
    return dict(name=doc.name,worker=doc.employee_name)


def validate_selected(value,company,start_date,end_date,lock=False):
    names=selection(value);people={r['name']:r for r in roster(company,start_date,end_date,lock)}
    for name in names:
        if name not in people:frappe.throw('A selected worker is inactive, missing or outside this company. Refresh the worker list.')
        if not people[name]['available']:frappe.throw(f"{people[name]['worker']}: {people[name]['reason']}. Remove this worker or change the dates.")
    return names


@frappe.whitelist(methods=['POST'])
def save_selection(plan,employees):
    from plus_point.events import plan_doc
    doc=plan_doc(plan,True);frappe.db.get_value('PP Event Plan',doc.name,'name',for_update=True);doc.reload()
    if doc.crew_allocated:frappe.throw('Release unused crew before changing this event’s selection. Recorded attendance keeps its original assignments.')
    names=validate_selected(employees,doc.company,doc.start_date,doc.end_date,lock=True)
    doc.selected_crew=json.dumps(names);doc.save()
    return dict(selected=names)


@frappe.whitelist(methods=['POST'])
def assign(project,site,contract_terms,start_date,end_date,wage_rate,client_rate,employees):
    """Bulk manual allocations share the exact same pool and conflict checks."""
    require_customer();project=linked('Project',project);linked('Company',project.company)
    venue=linked('PP Site',site);terms=linked('PP Contract Terms',contract_terms)
    if venue.project!=project.name or terms.project!=project.name:frappe.throw('Choose the site and agreement for this event project.')
    from plus_point.events import context
    context(frappe._dict(project=project.name,site=site,start_date=start_date,end_date=end_date))
    if terms.status!='Active' or (terms.effective_start and getdate(start_date)<getdate(terms.effective_start)) or (terms.effective_end and getdate(end_date)>getdate(terms.effective_end)):
        frappe.throw('Assignment dates must be inside the active client agreement.')
    frappe.has_permission('PP Assignment','create',throw=True)
    names=validate_selected(employees,project.company,start_date,end_date,lock=True)
    frappe.db.savepoint('pp_selected_assignments')
    try:
        result=[]
        for name in names:
            doc=frappe.get_doc(dict(doctype='PP Assignment',employee=name,project=project.name,site=site,contract_terms=contract_terms,
                start_date=start_date,end_date=end_date,wage_rate=wage_rate,client_rate=client_rate)).insert()
            result.append(doc.name)
        return dict(created=len(result),assignments=result)
    except Exception:
        frappe.db.rollback(save_point='pp_selected_assignments');raise
