"""Explicit removal of unused records through native delete/link/permission rules."""
import frappe
from plus_point.setup_flow import require_customer

SUPPORTED={'Employee','Customer','Contract','Project','PP Site','PP Assignment','PP Event Plan',
    'PP Contract Terms','PP Work Entry','PP Daily Register','PP Milestone','PP Vehicle Booking',
    'PP Equipment Booking','Vehicle','Item','Warehouse','Sales Invoice','Payment Entry','Purchase Invoice','Expense Claim','PP Worker Loan','PP Planning Draft'}


def document(doctype,name,lock=False):
    require_customer()
    if doctype not in SUPPORTED:frappe.throw('This record cannot be removed here.')
    if doctype in ('PP Contract Terms','PP Event Plan') and name.startswith('draft:'):
        from plus_point.drafts import checked
        doc=checked(name[6:],lock)
        if doc.kind!=('Agreement' if doctype=='PP Contract Terms' else 'Event'):
            frappe.throw('Open this draft in its matching list.',frappe.PermissionError)
        doc.check_permission('delete')
        return doc
    doc=frappe.get_doc(doctype,name,for_update=lock);doc.check_permission('read');doc.check_permission('delete')
    from plus_point.setup_flow import linked
    company=doc.get('company')
    if not company and doc.get('project'):company=linked('Project',doc.project).company
    if company:linked('Company',company)
    return doc


def protected(doc):
    if doc.doctype=='PP Planning Draft' and doc.status=='Scheduled':return 'Cancel scheduled creation in this event draft before deleting it.'
    if doc.doctype=='PP Planning Draft' and doc.status=='Completed':return 'This draft has already been created. Open the agreement or event to review it.'
    if doc.docstatus!=0:return 'Posted or cancelled records are retained for accounting history. Use the record’s correction or cancellation workflow.'
    if doc.doctype=='PP Work Entry' and doc.status!='Draft':return 'Approved work has earned wages and cannot be deleted. Review its attendance and linked invoice.'
    if doc.doctype=='PP Milestone' and doc.status in ('Approved','Invoiced'):return 'Approved milestones record earnings and cannot be deleted. Review the linked client invoice.'
    if doc.doctype=='PP Event Plan' and frappe.db.exists('PP Work Entry',{'project':doc.project}):return 'This event has recorded attendance. Cancel it to stop future work and keep its attendance and financial history.'
    if doc.doctype=='PP Assignment' and assignment_blocked(doc.name):return 'Saved attendance uses this booking. Keep its history; cancel the event to stop future work.'
    if doc.doctype=='PP Event Plan' and any(frappe.db.exists(dt,{'project':doc.project,'docstatus':1}) for dt in ('Sales Invoice','Payment Entry','Purchase Invoice')):return 'This event has posted finances. Cancel the event and keep its financial history.'
    if doc.doctype=='PP Event Plan' and frappe.db.exists('PP Assignment',{'project':doc.project}):return 'Review and release unused crew bookings before deleting this event.'
    return ''


@frappe.whitelist()
def review(doctype,name):
    doc=document(doctype,name)
    doctype=doc.doctype
    blocked=protected(doc);dependency=None
    if not blocked:
        from frappe.model.delete_doc import get_linked_docs, get_dynamic_linked_docs
        links=get_linked_docs(doc)+get_dynamic_linked_docs(doc)
        # Native on_trash removes these auxiliary rows before checking links.
        # Stock ledgers, reservations and financial records are never ignored.
        cleanup={'Item':{'Bin','Item Price'},'Warehouse':{'Bin'},'Customer':{'Address','Contact'}}.get(doctype,set())
        links=[row for row in links if row['reference_doctype'] not in cleanup]
        if doctype=='PP Assignment' and not assignment_blocked(doc.name):
            # The assignment trash hook removes only its unmarked roster lines.
            registers=frappe.get_all('PP Register Line',filters={'assignment':doc.name},pluck='parent')
            links=[row for row in links if not (row['reference_doctype']=='PP Daily Register' and row['reference_docname'] in registers)]
        if doctype=='Sales Invoice' and doc.docstatus==0:
            released={(r.pp_source_type,r.pp_source_name) for r in doc.items
                if r.get('pp_source_type') in ('PP Work Entry','PP Milestone') and r.get('pp_source_name')}
            links=[r for r in links if (r['reference_doctype'],r['reference_docname']) not in released]
        if doctype=='PP Contract Terms':
            def unsigned_link(row):
                if row['reference_doctype']!='PP Agreement Share':return False
                share=frappe.get_doc('PP Agreement Share',row['reference_docname'])
                return share.contract_terms==name and share.status!='Signed' and share.has_permission('delete')
            links=[row for row in links if not unsigned_link(row)]
        if links:
            link=links[0]
            reference=frappe.get_doc(link['reference_doctype'],link['reference_docname'])
            title=reference.get_title() if reference.has_permission('read') else link['reference_doctype']
            blocked=f"Used by {link['reference_doctype']}: {title}. Remove the unused linked record first; stock movements and posted financial records must be retained."
            if reference.has_permission('read'):dependency=dict(doctype=reference.doctype,name=reference.name,title=title)
    title=doc.get_title()
    if doctype=='PP Assignment':title=f"{frappe.db.get_value('Employee',doc.employee,'employee_name')} · {doc.start_date} – {doc.end_date or 'ongoing'}"
    if doctype=='PP Work Entry':title=f"{frappe.db.get_value('Employee',doc.employee,'employee_name')} · {doc.work_date} · {doc.status}"
    return dict(doctype=doctype,name=name,title=title,blocked=blocked,dependency=dependency,
        resolution='event' if doctype=='PP Event Plan' and blocked else 'assignment' if dependency and dependency['doctype']=='PP Assignment' else None,
        message='Deleting a client also removes its unshared contact and address records. Shared profiles remain.' if doctype=='Customer'
        else 'Open the linked event to change or remove its agreement. After removal/deletion, the unlinked event will not appear in finances until a replacement agreement is selected. Existing payroll and posted financial history must remain linked. Unused unsigned signing links are removed; signed evidence is retained.' if doctype=='PP Contract Terms'
        else 'Active events automatically recreate today’s attendance draft. Close the agreement to stop new drafts; approved history is retained.' if doctype=='PP Daily Register'
        else 'Linked records and permissions are checked again before deletion.')


@frappe.whitelist(methods=['POST'])
def remove(doctype,name):
    remove_many(doctype,[name])
    return dict(deleted=name,doctype=doctype)


def selected(names):
    names=frappe.parse_json(names)
    if not isinstance(names,list) or not 1<=len(names)<=50 or any(not isinstance(n,str) for n in names) or len(set(names))!=len(names):
        frappe.throw('Select 1–50 different records.')
    return sorted(names)


@frappe.whitelist()
def review_many(doctype,names):
    return dict(records=[review(doctype,name) for name in selected(names)])


@frappe.whitelist(methods=['POST'])
def remove_many(doctype,names):
    names=selected(names);docs=[document(doctype,name,True) for name in names]
    for doc in docs:
        reason=protected(doc)
        if reason:frappe.throw(reason)
    frappe.db.savepoint('pp_remove_records')
    try:
        # Native controllers, submitted history and operational link checks run
        # normally. The audit-only import receipts remain intact via the hook.
        for doc in docs:frappe.delete_doc(doc.doctype,doc.name)
    except Exception:
        frappe.db.rollback(save_point='pp_remove_records');raise
    return dict(deleted=names,doctype=doctype)


def assignment_blocked(name):
    if frappe.db.exists('PP Work Entry',{'assignment':name}):return 'Recorded attendance'
    for row in frappe.get_all('PP Register Line',filters={'assignment':name},fields=['parent','attendance_status','work_entry']):
        if row.work_entry or row.attendance_status!='Not marked' or frappe.db.get_value('PP Daily Register',row.parent,'docstatus'):
            return 'Saved attendance'
    return ''


def event_workers(event):
    """Only the event project; no planned pay is treated as earned wages."""
    from decimal import Decimal
    from plus_point.finance import money
    from plus_point.benefits import recovered
    assignments=frappe.get_list('PP Assignment',filters={'project':event.project},fields=['name','employee','site','start_date','end_date'],order_by='employee,start_date,name',limit_page_length=0)
    employees={r.employee for r in assignments}
    employees.update(frappe.get_list('PP Work Entry',filters={'project':event.project},pluck='employee',limit_page_length=0))
    rows=[]
    for employee in sorted(employees):
        worker=frappe.get_doc('Employee',employee);worker.check_permission('read')
        earned=sum((money(r.wage_amount) for r in frappe.get_list('PP Work Entry',filters={'project':event.project,'employee':employee,'status':'Approved'},fields=['wage_amount'],limit_page_length=0)),Decimal(0))
        paid=sum((money(r.amount) for r in frappe.get_list('PP Wage Settlement',filters={'project':event.project,'employee':employee,'docstatus':1},fields=['amount'],limit_page_length=0)),Decimal(0))
        deduction=recovered(employee,event.project)
        rows.append(dict(employee=employee,worker=worker.employee_name,earned=str(earned),paid=str(paid),deducted=str(deduction),outstanding=str(max(Decimal(0),earned-paid-deduction)),assignments=[dict(name=r.name,start=str(r.start_date),end=str(r.end_date or ''),site=frappe.db.get_value('PP Site',r.site,'site_name'),blocked=assignment_blocked(r.name)) for r in assignments if r.employee==employee]))
    return rows


@frappe.whitelist()
def event_review(name):
    from frappe.utils import today,getdate
    event=document('PP Event Plan',name);project=frappe.get_doc('Project',event.project);project.check_permission('read')
    currency=frappe.db.get_value('Company',project.company,'default_currency')
    accounts=frappe.get_list('Account',filters={'company':project.company,'is_group':0,'disabled':0,'account_type':['in',['Bank','Cash']],'account_currency':currency},fields=['name','account_name'],limit_page_length=0)
    return dict(name=event.name,title=event.event_name,ongoing=getdate(event.start_date)<=getdate(today())<=getdate(event.end_date),workers=event_workers(event),currency=currency,
        accounts=accounts,can_pay=frappe.has_permission('Payment Entry','create') and frappe.has_permission('Payment Entry','submit') and frappe.has_permission('PP Wage Settlement','create') and frappe.has_permission('PP Wage Settlement','submit'),can_cancel=project.has_permission('write'),cancelled=project.status=='Cancelled')


@frappe.whitelist(methods=['POST'])
def release_event_assignments(name,assignments):
    """Explicit, selected unused crew only. Native trash hooks clear blank rosters."""
    event=document('PP Event Plan',name)
    from plus_point.budget import lock_project
    lock_project(event.project)
    docs=[document('PP Assignment',key,True) for key in selected(assignments)]
    for doc in docs:
        if doc.project!=event.project:frappe.throw('Choose crew bookings from this event only.',frappe.PermissionError)
        if assignment_blocked(doc.name):frappe.throw('Saved attendance uses this booking. Keep its history and cancel the event instead.')
    frappe.db.savepoint('pp_event_release_selected')
    try:
        for doc in docs:frappe.delete_doc(doc.doctype,doc.name)
        if not frappe.db.exists('PP Assignment',{'pp_event_plan':event.name}):frappe.db.set_value('PP Event Plan',event.name,'crew_allocated',0)
    except Exception:
        frappe.db.rollback(save_point='pp_event_release_selected');raise
    return dict(released=[doc.name for doc in docs])


@frappe.whitelist(methods=['POST'])
def cancel_event(name):
    """Retain earned wages, invoices and attendance; release unused future capacity."""
    from frappe.utils import today,getdate
    from plus_point.budget import lock_project
    event=document('PP Event Plan',name);lock_project(event.project)
    project=frappe.get_doc('Project',event.project);project.check_permission('write')
    frappe.db.savepoint('pp_cancel_event')
    try:
        for key in frappe.get_list('PP Assignment',filters={'project':event.project},pluck='name',order_by='name',limit_page_length=0):
            assignment=document('PP Assignment',key,True)
            if not assignment_blocked(key):frappe.delete_doc('PP Assignment',key);continue
            dates=frappe.get_all('PP Work Entry',filters={'assignment':key},pluck='work_date')
            dates += [frappe.db.get_value('PP Daily Register',r.parent,'work_date') for r in frappe.get_all('PP Register Line',filters={'assignment':key},fields=['parent','attendance_status','work_entry']) if r.work_entry or r.attendance_status!='Not marked']
            last=max([getdate(today()),getdate(assignment.start_date)]+[getdate(d) for d in dates if d])
            if not assignment.end_date or getdate(assignment.end_date)>last:
                # Remove only blank future roster lines; marked dates remain booked.
                for parent in frappe.get_all('PP Daily Register',filters={'project':event.project,'work_date':['>',str(last)],'docstatus':0},pluck='name'):
                    register=frappe.get_doc('PP Daily Register',parent);blank=[r for r in register.entries if r.assignment==key and r.attendance_status=='Not marked' and not r.work_entry]
                    if blank:
                        register.check_permission('write')
                        for row in blank:register.remove(row)
                        register.save()
                assignment.end_date=str(last);assignment.save()
        project.status='Cancelled';project.save()
    except Exception:
        frappe.db.rollback(save_point='pp_cancel_event');raise
    return dict(cancelled=event.name,retained_history=True)


@frappe.whitelist(methods=['POST'])
def settle_event_crew(name,employees,account,posting_date,reference,balances=None):
    """Record confirmed real payments through native ERPNext and wage settlements."""
    from frappe.utils import getdate,today
    from plus_point.finance import money
    from plus_point.budget import lock_project
    event=document('PP Event Plan',name);lock_project(event.project)
    for dt in ('Payment Entry','PP Wage Settlement'):
        frappe.has_permission(dt,'create',throw=True);frappe.has_permission(dt,'submit',throw=True)
    employees=selected(employees);reference=str(reference or '').strip();balances=frappe.parse_json(balances or '{}')
    if not isinstance(balances,dict) or any(employee not in balances for employee in employees):frappe.throw('Review each selected worker’s outstanding balance before recording payments.')
    if not reference or len(reference)>140:frappe.throw('Enter the payment reference, up to 140 characters.')
    if not posting_date:frappe.throw('Enter the actual payment date.')
    if getdate(posting_date)>getdate(today()):frappe.throw('Use the actual payment date, today or earlier.')
    project=frappe.get_doc('Project',event.project);company=frappe.get_doc('Company',project.company)
    bank=frappe.get_doc('Account',account);bank.check_permission('read')
    if bank.company!=company.name or bank.is_group or bank.disabled or bank.account_type not in ('Bank','Cash') or bank.account_currency!=company.default_currency:
        frappe.throw('Choose an active bank or cash account in the company currency.')
    for employee in employees:frappe.db.get_value('Employee',employee,'name',for_update=True)
    rows={r['employee']:r for r in event_workers(event)}
    if any(employee not in rows for employee in employees):frappe.throw('Choose workers from this event only.',frappe.PermissionError)
    frappe.db.savepoint('pp_event_crew_payment');payments=[]
    try:
        for employee in employees:
            existing=frappe.db.get_value('Payment Entry',{'company':company.name,'project':event.project,'party_type':'Employee','party':employee,'reference_no':reference,'posting_date':posting_date,'docstatus':1},'name')
            if existing:
                payment=frappe.get_doc('Payment Entry',existing)
                if payment.paid_from==account and money(payment.paid_amount)==money(balances[employee]) and frappe.db.exists('PP Wage Settlement',{'payment_entry':existing,'docstatus':1}):payments.append(existing);continue
                frappe.throw('This payment reference already exists. Link that payment in Worker payments before recording another.')
            amount=money(rows[employee]['outstanding'])
            if amount!=money(balances[employee]):frappe.throw('The outstanding wage balance changed. Review the updated crew balances before recording payments.')
            if amount<=0:frappe.throw('This worker has no approved outstanding wages. Refresh the crew balances.')
            payment=frappe.get_doc(dict(doctype='Payment Entry',company=company.name,project=event.project,payment_type='Pay',party_type='Employee',party=employee,posting_date=posting_date,paid_from=account,paid_to=company.default_payable_account,paid_amount=float(amount),received_amount=float(amount),source_exchange_rate=1,target_exchange_rate=1,reference_no=reference,reference_date=posting_date)).insert();payment.submit()
            frappe.get_doc(dict(doctype='PP Wage Settlement',employee=employee,project=event.project,payment_entry=payment.name)).insert().submit();payments.append(payment.name)
    except Exception:
        frappe.db.rollback(save_point='pp_event_crew_payment');raise
    return dict(payments=payments)
