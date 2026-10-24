"""Explicit removal of unused records through native delete/link/permission rules."""
import frappe
from plus_point.setup_flow import require_customer

SUPPORTED={'Employee','Customer','Contract','Project','PP Site','PP Assignment','PP Event Plan',
    'PP Contract Terms','PP Work Entry','PP Daily Register','PP Milestone','PP Vehicle Booking',
    'PP Equipment Booking','Vehicle','Item','Warehouse','Sales Invoice','Payment Entry','Purchase Invoice','Expense Claim','PP Worker Loan'}


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
    blocked=protected(doc);dependency=None
    if not blocked:
        from frappe.model.delete_doc import get_linked_docs, get_dynamic_linked_docs
        links=get_linked_docs(doc)+get_dynamic_linked_docs(doc)
        # Native on_trash removes these auxiliary rows before checking links.
        # Stock ledgers, reservations and financial records are never ignored.
        cleanup={'Item':{'Bin','Item Price'},'Warehouse':{'Bin'},'Customer':{'Address','Contact'}}.get(doctype,set())
        links=[row for row in links if row['reference_doctype'] not in cleanup]
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
    if doctype=='PP Work Entry':title=f"{frappe.db.get_value('Employee',doc.employee,'employee_name')} · {doc.work_date} · {doc.status}"
    return dict(doctype=doctype,name=name,title=title,blocked=blocked,dependency=dependency,
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
        for name in names:frappe.delete_doc(doctype,name)
    except Exception:
        frappe.db.rollback(save_point='pp_remove_records');raise
    return dict(deleted=names,doctype=doctype)
