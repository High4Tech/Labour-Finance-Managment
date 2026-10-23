"""Event/site/day registers. Generating a roster never records attendance or wages."""
from decimal import Decimal
import frappe
from frappe.utils import getdate,today
from plus_point.setup_flow import require_customer,linked
from plus_point.finance import money,day_units

STATES={'Present':'1','Half day':'0.5','Absent':'0','Not marked':''}


def status_for(units):
    try:return {'1':'Present','0.5':'Half day','0':'Absent'}[str(day_units(units)).rstrip('0').rstrip('.') or '0']
    except ValueError:frappe.throw('Choose Present, Absent or Half day for this worker.')


def context(site,day):
    location=linked('PP Site',site);project=linked('Project',location.project)
    linked('Company',project.company)
    if not location.is_active:frappe.throw('This event site is inactive. Review the event sites before opening attendance.')
    plan_name=frappe.db.get_value('PP Event Plan',{'project':project.name},'name')
    plan=linked('PP Event Plan',plan_name) if plan_name else None
    phases=[r for r in plan.staffing if r.site==site and getdate(r.start_date)<=day<=getdate(r.end_date)] if plan else []
    required=sum(int(r.workers_required) for r in phases) if plan else None
    if plan and not phases:frappe.throw('This date is outside this site’s planned work days. Choose a planned date or review the event plan.')
    return location,project,plan,required


def roster(site,day):
    rows=frappe.get_list('PP Assignment',filters={'site':site,'start_date':['<=',day]},
        fields=['name','employee','start_date','end_date','wage_rate','client_rate'],order_by='employee',limit_page_length=0)
    result=[]
    for row in rows:
        if row.end_date and getdate(row.end_date)<day:continue
        worker=linked('Employee',row.employee)
        if worker.status!='Active' or worker.date_of_joining and getdate(worker.date_of_joining)>day or worker.relieving_date and getdate(worker.relieving_date)<day:continue
        from plus_point.benefits import leave_units
        if leave_units(worker.name,day)>=1:continue
        result.append(row)
    return result


def require_open_work(project,day):
    terms=frappe.get_all('PP Contract Terms',filters={'project':project.name,'status':'Active','effective_start':['<=',day]},fields=['effective_end'])
    if project.status!='Open' or not any(not row.effective_end or getdate(row.effective_end)>=day for row in terms):
        frappe.throw('This event is closed or has no active agreement for this date. Reopen the agreement and event before preparing new attendance. Existing attendance history remains available.')


@frappe.whitelist(methods=['POST'])
def prepare(site,work_date,project=None,refresh=False):
    require_customer();frappe.has_permission('PP Daily Register','create',throw=True)
    day=getdate(work_date)
    location,event,plan,required=context(site,day)
    if project and event.name!=project:frappe.throw('Choose a site belonging to the selected event.')
    from plus_point.budget import lock_project
    lock_project(event.name)
    existing=frappe.get_list('PP Daily Register',filters={'site':site,'work_date':day,'docstatus':['<',2]},
        fields=['name','docstatus'],order_by='docstatus desc,creation asc',limit_page_length=1)
    doc=linked('PP Daily Register',existing[0].name) if existing else frappe.new_doc('PP Daily Register')
    if existing and (doc.docstatus or not refresh):return dict(name=doc.name,workers=len(doc.entries),existing=True)
    require_open_work(event,day)
    doc.check_permission('write' if existing else 'create')
    doc.update(dict(site=site,project=event.name,work_date=str(day)))
    assignments=roster(site,day);active={r.name:r for r in assignments}
    for line in list(doc.entries):
        if line.assignment not in active:
            if line.attendance_status=='Not marked' and not line.work_entry:doc.remove(line)
            else:frappe.throw('A marked worker’s allocation changed. Review the event allocations before refreshing this register.')
    included={r.assignment for r in doc.entries}
    work={r.assignment:r for r in frappe.get_list('PP Work Entry',filters={'site':site,'work_date':day},
        fields=['name','assignment','units','status'],limit_page_length=0)}
    for row in assignments:
        if row.name in included:continue
        previous=work.get(row.name)
        doc.append('entries',dict(assignment=row.name,employee=row.employee,
            attendance_status=status_for(previous.units) if previous and previous.status=='Approved' else 'Not marked',
            units=str(previous.units) if previous and previous.status=='Approved' else '',work_entry=previous.name if previous else None))
    doc.save()
    return dict(name=doc.name,workers=len(doc.entries),existing=bool(existing))


@frappe.whitelist(methods=['POST'])
def ensure_today(company=None):
    require_customer()
    from plus_point.event_setup import companies as workspace_companies
    companies=[company] if company else [r.name for r in workspace_companies()]
    for name in companies:linked('Company',name)
    projects=frappe.get_list('Project',filters={'company':['in',companies],'status':'Open'},pluck='name',limit_page_length=0)
    if not projects:return dict(created=0)
    day=getdate(today());sites=set()
    for row in frappe.get_list('PP Assignment',filters={'project':['in',projects],'start_date':['<=',day]},fields=['site','end_date'],limit_page_length=0):
        if not row.end_date or getdate(row.end_date)>=day:sites.add(row.site)
    for name in frappe.get_list('PP Event Plan',filters={'project':['in',projects],'start_date':['<=',day],'end_date':['>=',day]},pluck='name',limit_page_length=0):
        for row in linked('PP Event Plan',name).staffing:
            if getdate(row.start_date)<=day<=getdate(row.end_date):sites.add(row.site)
    created=0
    for site in sorted(sites):
        if not frappe.db.get_value('PP Site',site,'is_active'):continue
        try:
            # A paused site phase may still have a broader legacy allocation.
            _,project,_,_=context(site,day)
            require_open_work(project,day)
        except frappe.ValidationError:
            frappe.clear_messages();continue
        result=prepare(site,str(day));created+=not result['existing']
    return dict(created=created)


def generate_today():
    if frappe.conf.get('pp_control_plane'):return
    from plus_point.tenancy import current_entitlement,entitlement_status
    entitlement=current_entitlement()
    if entitlement and entitlement_status(entitlement,getdate())!='Active':return
    previous=frappe.session.user
    try:
        frappe.set_user('Administrator');ensure_today()
    finally:frappe.set_user(previous)


def assignment_started(doc,method=None):
    if frappe.flags.in_migrate or frappe.conf.get('pp_control_plane'):return
    day=getdate(today())
    if getdate(doc.start_date)>day or doc.end_date and getdate(doc.end_date)<day:return
    if not frappe.db.exists('PP Event Plan',{'project':doc.project}):return
    try:context(doc.site,day)
    except frappe.ValidationError:
        frappe.clear_messages();return
    prepare(doc.site,str(day),doc.project,refresh=True)


def release_unmarked_roster(doc,method=None):
    """An automatically generated blank roster must not trap unused allocations."""
    references=frappe.get_all('PP Register Line',filters={'assignment':doc.name,'parenttype':'PP Daily Register'},fields=['parent'])
    for name in sorted({row.parent for row in references}):
        register=linked('PP Daily Register',name);register.check_permission('write')
        lines=[row for row in register.entries if row.assignment==doc.name]
        if register.docstatus or any(row.attendance_status!='Not marked' or row.work_entry for row in lines):
            frappe.throw('This worker has saved attendance. Clear unapproved attendance before releasing the allocation; approved history stays locked.')
        for row in lines:register.remove(row)
        register.save()


@frappe.whitelist(methods=['POST'])
def refresh_roster(name):
    require_customer();doc=linked('PP Daily Register',name);doc.check_permission('write')
    if doc.docstatus:frappe.throw('Approved attendance is locked. Open another date to record new work.')
    return prepare(doc.site,doc.work_date,doc.project,refresh=True)


@frappe.whitelist()
def detail(name):
    require_customer();doc=linked('PP Daily Register',name)
    location,event,plan,required=context(doc.site,getdate(doc.work_date))
    rows=[]
    for line in doc.entries:
        worker=linked('Employee',line.employee);allocation=linked('PP Assignment',line.assignment)
        previous=linked('PP Work Entry',line.work_entry) if line.work_entry else None
        state=line.attendance_status or status_for(line.units)
        rate=previous.wage_rate if previous else allocation.wage_rate
        rows.append(dict(id=line.name,assignment=line.assignment,employee=worker.name,title=worker.employee_name,
            designation=worker.designation or '',status=state,wage_rate=str(money(rate)),
            amount=str(money(Decimal(str(rate))*Decimal(STATES[state] or 0))),
            locked=bool(doc.docstatus or previous and previous.status=='Approved')))
    return dict(name=doc.name,project=event.name,event=plan.event_name if plan else event.project_name,
        plan=plan.name if plan else None,site=location.site_name,date=str(doc.work_date),required=required,
        currency=frappe.db.get_value('Company',event.company,'default_currency'),approved=doc.docstatus==1,can_correct=doc.docstatus==1 and 'System Manager' in frappe.get_roles(),rows=rows)


@frappe.whitelist(methods=['POST'])
def correct_marks(name,marks,reason):
    """Explicit owner correction with native versions, frozen rates and invoice adjustments."""
    require_customer()
    if 'System Manager' not in frappe.get_roles():frappe.throw('Only the company administrator can correct approved attendance.',frappe.PermissionError)
    reason=str(reason or '').strip()
    if not reason or len(reason)>1000:frappe.throw('Enter a correction reason of up to 1,000 characters.')
    preview=linked('PP Daily Register',name)
    from plus_point.budget import lock_project
    lock_project(preview.project)
    doc=frappe.get_doc('PP Daily Register',name,for_update=True);doc.check_permission('write')
    if doc.docstatus!=1:frappe.throw('Use Save draft or Approve for an unposted register.')
    data=frappe.parse_json(marks);entries={r.name:r for r in doc.entries}
    if not isinstance(data,list) or len(data)!=len(entries) or len({r.get('id') for r in data})!=len(entries):frappe.throw('Reload the complete attendance roster.')
    if any(r.get('id') not in entries or r.get('status') not in ('Present','Absent','Half day') for r in data):frappe.throw('Choose Present, Absent or Half day for every worker.')
    frappe.db.savepoint('pp_correct_attendance');previous_flag=frappe.flags.get('pp_attendance_correction');adjustments=[];changes=[]
    try:
        for mark in sorted(data,key=lambda r:entries[r['id']].employee):
            line=entries[mark['id']]
            if line.attendance_status==mark['status']:continue
            work=linked('PP Work Entry',line.work_entry);work.check_permission('write')
            if work.assignment!=line.assignment or work.project!=doc.project:frappe.throw('The attendance source changed. Reload before correcting.')
            old_amount=money(work.billable_amount);old_state=line.attendance_status
            source=linked('Sales Invoice',work.sales_invoice) if work.sales_invoice else None
            if source and source.docstatus==1 and not work.get('pp_invoice_amount_snapshot'):work.pp_invoice_amount_snapshot=old_amount
            frappe.flags.pp_attendance_correction=work.name
            work.units=STATES[mark['status']];work.save()
            if source and source.docstatus==0:
                for item in source.items:
                    if item.pp_source_type=='PP Work Entry' and item.pp_source_name==work.name:
                        item.rate=float(money(Decimal(str(work.billable_amount))/Decimal(str(source.conversion_rate))))
                        item.price_list_rate=item.rate;item.discount_percentage=0;item.discount_amount=0;item.margin_rate_or_amount=0
                source.save()
            elif source and source.docstatus==1:
                delta=money(work.billable_amount)-old_amount
                if delta:
                    from plus_point.operations import service_item
                    rate=Decimal(str(source.conversion_rate))
                    adjustment=frappe.get_doc(dict(doctype='Sales Invoice',company=source.company,customer=source.customer,project=source.project,
                        currency=source.currency,conversion_rate=source.conversion_rate,debit_to=source.debit_to,is_return=int(delta<0),
                        pp_attendance_correction=work.name,remarks=f'Attendance correction to {source.name}: {reason}',
                        items=[dict(item_code=service_item(),project=work.project,description=f'Attendance correction — {doc.work_date} — {frappe.db.get_value("Employee",line.employee,"employee_name")}',qty=-1 if delta<0 else 1,rate=float(money(abs(delta)/rate)))])).insert()
                    adjustments.append(adjustment.name)
            line.attendance_status=mark['status'];line.units=STATES[mark['status']]
            change=f'{frappe.db.get_value("Employee",line.employee,"employee_name")}: {old_state} → {mark["status"]}'
            changes.append(change);work.add_comment('Comment',frappe.utils.escape_html(f'Attendance correction: {change}. Reason: {reason}'))
        if changes:
            doc.flags.ignore_validate_update_after_submit=True;doc.save()
            doc.add_comment('Comment',frappe.utils.escape_html('Attendance corrected. '+ '; '.join(changes)+'. Reason: '+reason))
        return dict(name=doc.name,changed=len(changes),invoice_adjustments=adjustments)
    except Exception:
        frappe.db.rollback(save_point='pp_correct_attendance');raise
    finally:frappe.flags.pp_attendance_correction=previous_flag


@frappe.whitelist(methods=['POST'])
def save_marks(name,marks,approve=False):
    require_customer();preview=linked('PP Daily Register',name)
    from plus_point.budget import lock_project
    lock_project(preview.project)
    doc=frappe.get_doc('PP Daily Register',name,for_update=True);doc.check_permission('write')
    if doc.docstatus:frappe.throw('This register is already approved. Its attendance and wage history are locked.')
    marks=frappe.parse_json(marks)
    if not isinstance(marks,list) or len(marks)!=len(doc.entries):frappe.throw('The roster changed. Refresh attendance before saving.')
    entries={r.name:r for r in doc.entries};seen=set()
    for mark in marks:
        key=mark.get('id');state=mark.get('status')
        if key not in entries or key in seen or state not in STATES:frappe.throw('Choose a valid attendance status for each listed worker.')
        seen.add(key);entries[key].attendance_status=state;entries[key].units=STATES[state]
    frappe.db.savepoint('pp_attendance_save')
    try:
        doc.save()
        if frappe.utils.cint(approve):doc.submit()
    except Exception:
        frappe.db.rollback(save_point='pp_attendance_save');raise
    return dict(name=doc.name,approved=doc.docstatus==1)
