"""Explicit removal of unused records through native delete/link/permission rules."""
import frappe
from plus_point.setup_flow import require_customer

SUPPORTED={'Employee','Customer','Contract','Project','PP Site','PP Assignment','PP Event Plan',
    'PP Contract Terms','PP Work Entry','PP Daily Register','PP Milestone','PP Vehicle Booking',
    'PP Equipment Booking','Vehicle','Item','Warehouse','Sales Invoice','Payment Entry','Purchase Invoice','Expense Claim'}


def document(doctype,name,lock=False):
    require_customer()
    if doctype not in SUPPORTED:frappe.throw('This record cannot be removed here.')
    doc=frappe.get_doc(doctype,name,for_update=lock);doc.check_permission('read');doc.check_permission('delete')
    from plus_point.setup_flow import linked
    company=doc.get('company')
    if not company and doc.get('project'):company=linked('Project',doc.project).company
    if company:linked('Company',company)
    return doc


def protected(doc):
    if doc.docstatus!=0:return 'Posted or cancelled records are retained for accounting history. Use the record’s correction or cancellation workflow.'
    if doc.doctype=='PP Work Entry' and doc.status!='Draft':return 'Approved work has earned wages and cannot be deleted. Review its attendance and linked invoice.'
    if doc.doctype=='PP Milestone' and doc.status in ('Approved','Invoiced'):return 'Approved milestones record earnings and cannot be deleted. Review the linked client invoice.'
    if doc.doctype=='PP Event Plan' and doc.crew_allocated and frappe.db.exists('PP Assignment',{'pp_event_plan':doc.name}):return 'Release unused crew before deleting the event plan. Recorded attendance retains its original plan.'
    return ''


@frappe.whitelist()
def review(doctype,name):
    doc=document(doctype,name)
    title=doc.get_title()
    if doctype=='PP Work Entry':title=f"{frappe.db.get_value('Employee',doc.employee,'employee_name')} · {doc.work_date} · {doc.status}"
    return dict(doctype=doctype,name=name,title=title,blocked=protected(doc),
        message='Deleting a client also removes its unshared contact and address records. Shared profiles remain.' if doctype=='Customer'
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
        # No force, ignore_links or permission bypass. Native controllers,
        # submitted history, import receipts and dependencies stay authoritative.
        for name in names:frappe.delete_doc(doctype,name)
    except Exception:
        frappe.db.rollback(save_point='pp_remove_records');raise
    return dict(deleted=names,doctype=doctype)
