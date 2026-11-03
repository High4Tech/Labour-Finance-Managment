"""Permission-scoped worker dashboard from allocations, attendance and settlements."""
from collections import defaultdict
from decimal import Decimal
import frappe
from frappe.utils import getdate,today,add_days
from plus_point.setup_flow import require_customer,linked
from plus_point.finance import money


# Product form boundary. Native Employee hooks, permissions and payroll remain
# authoritative; only these presentation fields can be changed by this form.
WORKER_FIELDS = ('first_name', 'last_name', 'gender', 'date_of_birth', 'date_of_joining',
    'status', 'employee_number', 'department', 'designation', 'reports_to', 'employment_type',
    'pp_salary_basis', 'pp_daily_rate', 'pp_monthly_rate', 'pp_leaves_per_month',
    'pp_loan_allowed', 'pp_loan_wait_months', 'pp_loan_deduction_percent', 'cell_number',
    'personal_email', 'current_address', 'person_to_be_contacted', 'emergency_phone_number', 'relation')


@frappe.whitelist()
def form(employee=None):
    from plus_point.operations import company, event_roles
    from plus_point.people import DEPARTMENTS, senior
    business = company()
    worker = linked('Employee', employee, business.name) if employee else None
    frappe.has_permission('Employee', 'write' if worker else 'create', doc=worker, throw=True)
    departments = frappe.get_list('Department', filters={'company': business.name},
        fields=['name', 'department_name'], order_by='department_name', limit_page_length=0)
    managers = frappe.get_list('Employee', filters={'company': business.name, 'status': 'Active'},
        fields=['name', 'employee_name', 'designation'], order_by='employee_name', limit_page_length=0)
    meta = frappe.get_meta('Employee')
    fields = [key for key in WORKER_FIELDS if meta.has_field(key)]
    values = {key: worker.get(key) for key in fields} if worker else dict(status='Active',
        date_of_joining=today(), pp_salary_basis='Daily', pp_daily_rate=0, pp_monthly_rate=0,
        pp_leaves_per_month=0, pp_loan_allowed=0, pp_loan_wait_months=0, pp_loan_deduction_percent=10)
    return dict(values=values, modified=str(worker.modified) if worker else None,
        title=worker.employee_name if worker else '', reference=worker.get('pp_reference') if worker else '',
        company=business.name, currency=business.default_currency, fields=fields,
        departments=[dict(value=r.name,label=r.department_name) for r in departments],
        roles={r.name:list(dict.fromkeys(DEPARTMENTS.get(r.department_name,event_roles())+
            [role for role in event_roles() if role not in {x for group in DEPARTMENTS.values() for x in group}])) for r in departments},
        designations=event_roles(), managers=[dict(value=r.name,label=r.employee_name) for r in managers
            if r.name!=employee and senior(r.designation)],
        genders=frappe.get_list('Gender',pluck='name',order_by='name',limit_page_length=0),
        employment_types=frappe.get_list('Employment Type',pluck='name',order_by='name',limit_page_length=0))


@frappe.whitelist(methods=['POST'])
def save(values, employee=None, modified=None):
    from plus_point.operations import company
    from plus_point.benefits import atomic

    @atomic
    def persist():
        business=company()
        values_dict=frappe.parse_json(values)
        if not isinstance(values_dict,dict) or set(values_dict)-(set(WORKER_FIELDS)|{'new_category'}):
            frappe.throw('Use the worker profile fields to update this record.')
        if employee:
            # Lock before comparing the browser version, so simultaneous edits
            # cannot overwrite each other after passing the version check.
            current=frappe.db.get_value('Employee',employee,'modified',for_update=True)
            doc=linked('Employee',employee,business.name)
            doc.check_permission('write')
            if not modified or frappe.utils.get_datetime(current)!=frappe.utils.get_datetime(modified):
                frappe.throw('This worker was updated elsewhere. Reload the profile before saving.',frappe.TimestampMismatchError)
        else:
            frappe.has_permission('Employee','create',throw=True)
            doc=frappe.new_doc('Employee')
            doc.update(company=business.name,status='Active',create_user_automatically=0)
        if values_dict.get('designation')=='__new__':
            from plus_point.operations import create_category
            values_dict['designation']=create_category(values_dict.get('new_category'))['name']
        doc.update({key:value for key,value in values_dict.items() if key in WORKER_FIELDS and doc.meta.has_field(key)})
        doc.save()
        return dict(name=doc.name,modified=str(doc.modified))
    return persist()


@frappe.whitelist()
def workers(search='',status='',page=1):
    from plus_point.operations import company
    business=company();frappe.has_permission('Employee','read',throw=True)
    status=str(status or '')
    if status not in ('','Available','Assigned','Scheduled','Inactive'):
        frappe.throw('Choose All, Available, Assigned, Scheduled or Inactive workers.')
    page=max(1,frappe.utils.cint(page));size=20
    if page>501:frappe.throw('Narrow the worker search before loading more records.')
    filters={'company':business.name};search=str(search or '').strip()[:140]
    if search:filters['employee_name']=['like','%'+search+'%']
    names=frappe.get_list('Employee',filters={'company':business.name},pluck='name',limit_page_length=0)
    can_read_assignments=frappe.has_permission('PP Assignment','read')
    if status in ('Assigned','Available','Scheduled') and not can_read_assignments:
        frappe.throw('You need worker-assignment access to filter booking availability.',frappe.PermissionError)
    assignments=frappe.get_list('PP Assignment',filters={'employee':['in',names or ['']]},
        fields=['employee','start_date','end_date'],limit_page_length=0) if can_read_assignments else []
    active=[r for r in assignments if not r.end_date or getdate(r.end_date)>=getdate(today())]
    booked={r.employee for r in active if getdate(r.start_date)<=getdate(today())}
    scheduled={r.employee for r in active}-booked
    if status=='Assigned':filters.update(status='Active',name=['in',list(booked) or ['']])
    if status=='Available':filters.update(status='Active',name=['not in',list(booked|scheduled) or ['']])
    if status=='Scheduled':filters.update(status='Active',name=['in',list(scheduled) or ['']])
    if status=='Inactive':filters['status']=['!=','Active']
    total=frappe.get_list('Employee',filters=filters,fields=[{'COUNT':'name','as':'total'}])[0].total
    pages=max(1,(total+size-1)//size);page=min(page,pages)
    rows=frappe.get_list('Employee',filters=filters,fields=['name','employee_name','image','pp_reference',
        'status','department','designation','employment_type','branch'],order_by='employee_name,name',
        limit_start=(page-1)*size,limit_page_length=size)
    for row in rows:row['availability']='Inactive' if row.status!='Active' else 'Not available to view' if not can_read_assignments else 'Assigned' if row.name in booked else 'Scheduled' if row.name in scheduled else 'Available'
    return dict(rows=rows,page=page,pages=pages,total=total,
        can_create=bool(frappe.has_permission('Employee','create')),
        can_delete=bool(frappe.has_permission('Employee','delete')))


@frappe.whitelist()
def overview(employee,days=91):
    require_customer();worker=linked('Employee',employee);company=linked('Company',worker.company)
    days=frappe.utils.cint(days)
    if days not in (91,366):frappe.throw('Choose the last 3 months or the last year.')
    end=getdate(today());start=getdate(add_days(end,1-days))
    work=frappe.get_list('PP Work Entry',filters={'employee':employee,'status':'Approved'},
        fields=['name','work_date','project','site','units','wage_amount'],order_by='work_date desc,name',limit_page_length=0)
    # Follow parent company permissions before including any source in the profile.
    projects={r.name:r for r in frappe.get_list('Project',filters={'company':company.name,'pp_archived':0},fields=['name','project_name','status'],limit_page_length=0)}
    work=[r for r in work if r.project in projects]
    totals=defaultdict(Decimal);earned=Decimal(0)
    for row in work:
        if getdate(row.work_date)<=end:totals[str(row.work_date)]+=Decimal(str(row.units))
        earned+=money(row.wage_amount)
    paid=sum((money(r.amount) for r in frappe.get_list('PP Wage Settlement',filters={'employee':employee,'project':['in',list(projects) or ['']],'docstatus':1},fields=['amount'],limit_page_length=0)),Decimal(0))
    allocations=frappe.get_list('PP Assignment',filters={'employee':employee,'project':['in',list(projects) or ['']]},
        fields=['name','project','site','start_date','end_date','wage_rate'],order_by='start_date desc',limit_page_length=0)
    sites={r.name:r.site_name for r in frappe.get_list('PP Site',filters={'project':['in',list(projects) or ['']]},fields=['name','site_name'],limit_page_length=0)}
    expected=set()
    for row in allocations:
        first=max(start,getdate(row.start_date),getdate(worker.date_of_joining or row.start_date))
        last=min(end,getdate(row.end_date or end),getdate(worker.relieving_date or end))
        for offset in range(max(0,(last-first).days+1)):expected.add(str(add_days(first,offset)))
    registers=frappe.get_list('PP Daily Register',filters={'project':['in',list(projects) or ['']],'docstatus':0,'work_date':['between',[start,end]]},fields=['name','work_date'],limit_page_length=0)
    dates={r.name:str(r.work_date) for r in registers}
    draft=frappe.get_all('PP Register Line',filters={'parent':['in',list(dates) or ['']],'parenttype':'PP Daily Register','employee':employee},fields=['parent','attendance_status'])
    pending_dates={dates[r.parent] for r in draft if r.attendance_status not in ('Not marked','',None)}
    from plus_point.benefits import leave_map
    leaves=leave_map([employee],start,end)
    calendar=[]
    for offset in range(days):
        day=str(add_days(start,offset));units=totals.get(day)
        state=('Present' if units>=1 else 'Half day' if units>0 else 'Absent') if units is not None else 'Pending approval' if day in pending_dates else 'Not marked' if day in expected else 'No scheduled work'
        if units is None and (employee,day) in leaves:state='Full day leave' if leaves[(employee,day)]==1 else 'Half day leave'
        calendar.append(dict(date=day,status=state,units=str(units) if units is not None else None))
    full=sum(value>=1 for value in totals.values());half=sum(0<value<1 for value in totals.values());absent=sum(value==0 for value in totals.values())
    longest=current=0
    for row in calendar:
        current=current+1 if row['units'] is not None and Decimal(row['units'])>0 else 0;longest=max(longest,current)
    plan_rows=frappe.get_list('PP Event Plan',filters={'company':company.name},fields=['name','project','event_name'],limit_page_length=0)
    plans={r.project:r.name for r in plan_rows};titles={r.project:r.event_name for r in plan_rows}
    assignments=[dict(plan=plans.get(r.project),name=r.name,event=titles.get(r.project,projects[r.project].project_name),project=r.project,site=sites.get(r.site,r.site),
        start=str(r.start_date),end=str(r.end_date or ''),wage_rate=str(money(r.wage_rate))) for r in allocations if projects[r.project].status=='Open' and (not r.end_date or getdate(r.end_date)>=end)]
    history=[dict(name=r.name,date=str(r.work_date),event=projects[r.project].project_name,site=sites.get(r.site,r.site),
        status='Present' if Decimal(str(r.units))==1 else 'Half day' if Decimal(str(r.units))>0 else 'Absent',amount=str(money(r.wage_amount))) for r in work[:20]]
    from plus_point.benefits import balances
    benefits=balances(employee)
    assigned=any(getdate(r['start'])<=end for r in assignments)
    return dict(benefits=benefits,outstanding_after_loan=str(money(earned-paid-Decimal(benefits['recovered']))),image=worker.image or '',allocation_status='Assigned' if assigned else 'Scheduled' if assignments else 'Available',employee=employee,title=worker.employee_name,reference=worker.get('pp_reference') or employee,designation=worker.designation or '',department=worker.department or '',
        company=company.company_name,company_id=company.name,currency=company.default_currency,status=worker.status,
        phone=worker.cell_number or '',email=worker.personal_email or '',joining=str(worker.date_of_joining or ''),
        full_days=full,half_days=half,absent_days=absent,paid_days=str(sum(totals.values(),Decimal(0))),
        attendance_rate=round(100*(full+half*.5)/(full+half+absent),1) if full+half+absent else None,
        earned=str(money(earned)),paid=str(money(paid)),outstanding=str(money(earned-paid)),
        assignments=assignments,history=history,history_count=len(work),calendar=calendar,start=str(start),end=str(end),longest_streak=longest)
