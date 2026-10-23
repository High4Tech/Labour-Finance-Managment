"""Worker-focused form choices and explicit future crew planning."""
import re
from collections import defaultdict
import frappe
from frappe.utils import getdate, add_days, cint
from plus_point.setup_flow import require_customer, linked

DEPARTMENTS = {
    'Event management': ['Event manager', 'Site supervisor', 'Crew leader'],
    'Event operations': ['Event crew', 'Stagehand', 'Decorator', 'Carpenter', 'Rigger'],
    'Technical production': ['Electrician', 'Lighting technician', 'AV technician', 'Sound technician'],
    'Logistics': ['Driver', 'Warehouse crew'],
    'Safety and security': ['Security staff'],
}

def senior(role):
    return bool(re.search(r'\b(manager|supervisor|senior|head|lead|leader|director)\b', role or '', re.I))

@frappe.whitelist(methods=['POST'])
def work_options(employee=None):
    from plus_point.operations import company, event_roles, ensure_event_role
    business=company();worker=linked('Employee',employee,business.name) if employee else None
    departments=[];roles={}
    for title, categories in DEPARTMENTS.items():
        name=frappe.db.get_value('Department',{'department_name':title,'company':business.name},'name')
        if not name:
            name=frappe.get_doc(dict(doctype='Department',department_name=title,company=business.name)).insert().name
        departments.append(dict(value=name,label=title));roles[name]=categories
        for category in categories:ensure_event_role(category)
    if worker and worker.department and worker.department not in roles:
        departments.append(dict(value=worker.department,label=frappe.db.get_value('Department',worker.department,'department_name')))
        roles[worker.department]=event_roles()
    managers=frappe.get_list('Employee',filters={'company':business.name,'status':'Active'},fields=['name','employee_name','designation'],order_by='employee_name',limit_page_length=0)
    return dict(departments=departments,roles=roles,designations=event_roles(),
        managers=[dict(value=r.name,label=r.employee_name) for r in managers if r.name!=employee and senior(r.designation)])

def validate_worker(doc,method=None):
    if frappe.conf.get('pp_control_plane'):return
    old=doc.get_doc_before_save()
    if doc.reports_to and (not old or old.reports_to!=doc.reports_to):
        manager=linked('Employee',doc.reports_to)
        if manager.name==doc.name or manager.company!=doc.company or manager.status!='Active' or not senior(manager.designation):
            frappe.throw('Reports to must be an active manager, supervisor or senior worker in your company.')
    if doc.department and doc.designation and (not old or (old.department,old.designation)!=(doc.department,doc.designation)):
        department=frappe.db.get_value('Department',doc.department,['department_name','company'],as_dict=True)
        if not department or department.company not in (None,'',doc.company):frappe.throw('Choose a department in your company.')
        allowed=DEPARTMENTS.get(department.department_name)
        if allowed and doc.designation not in allowed:frappe.throw('Choose a worker category belonging to this department.')

def peak(rows):
    changes=defaultdict(int)
    for row in rows:
        if not row.get('start_date') or not row.get('end_date'):continue
        quantity=cint(row.get('workers_required'))
        changes[getdate(row.get('start_date'))]+=quantity
        changes[getdate(add_days(row.get('end_date'),1))]-=quantity
    current=maximum=0
    for day in sorted(changes):current+=changes[day];maximum=max(maximum,current)
    return maximum

@frappe.whitelist()
def capacity(start_date,end_date,staffing=None,agreement=None):
    from plus_point.operations import company,terms_doc
    business=company()
    if agreement:terms_doc(agreement)
    from plus_point.crew import roster
    rows=roster(business.name,start_date,end_date)
    # Allocations in the agreement being edited are still usable by that event.
    own=set(frappe.get_list('PP Assignment',filters={'contract_terms':agreement},pluck='employee',limit_page_length=0)) if agreement else set()
    others=frappe.get_list('PP Assignment',filters={'contract_terms':['!=',agreement],'employee':['in',[r['name'] for r in rows] or ['']],'start_date':['<=',end_date]},fields=['employee','end_date'],limit_page_length=0) if agreement else []
    externally_booked={r.employee for r in others if not r.end_date or getdate(r.end_date)>=getdate(start_date)}
    available=sum(r['available'] or (r['reason']=='Booked for overlapping dates' and r['name'] in own and r['name'] not in externally_booked) for r in rows)
    required=peak(frappe.parse_json(staffing) or [])
    return dict(total=len(rows),available=available,required=required,shortfall=max(0,required-len(rows)))

def validate_capacity(doc):
    """A booking is not a new employee. Existing overloaded baselines can be reviewed."""
    rows=doc.get('staffing') or [];required=peak(rows)
    future=cint(doc.get('pp_future_crew_count'))
    if future<0:frappe.throw('Crew to add later cannot be negative.')
    old=doc.get_doc_before_save()
    if old and required<=peak(old.staffing):return
    company=frappe.db.get_value('Project',doc.project,'company')
    total=frappe.db.count('Employee',{'company':company,'status':'Active'})
    if required>total+future:
        frappe.throw(f'This agreement needs {required} crew per day; your company has {total} active crew. Add the maximum existing crew or explicitly enter {required-total} crew to add later.')

def install():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'PP Contract Terms':[dict(fieldname='pp_future_crew_count',label='Crew to add later',fieldtype='Int',default=0)]})
    if frappe.conf.get('pp_control_plane') or frappe.defaults.get_global_default('pp_manual_lists_v1'):return
    import json
    from frappe.model.utils.user_settings import get_user_settings, update_user_settings, sync_user_settings
    previous=frappe.session.user
    try:
        for user in frappe.get_all('User',filters={'enabled':1,'user_type':'System User'},pluck='name'):
            frappe.set_user(user)
            for doctype in ['Employee','PP Contract Terms','PP Event Plan','Sales Invoice','PP Daily Register']:
                settings=json.loads(get_user_settings(doctype));view=settings.get('List',{})
                filters=view.get('filters')
                if not isinstance(filters,list):continue
                # Retire the old single-company and active-project filters once.
                clean=[f for f in filters if not (len(f)>=4 and ((doctype=='Employee' and f[1:3]==['company','=']) or (doctype!='Employee' and f[1:3]==['project','in'])))]
                if clean!=filters:view['filters']=clean;update_user_settings(doctype,settings)
        sync_user_settings()
    finally:frappe.set_user(previous)
    frappe.defaults.set_global_default('pp_manual_lists_v1',1)
