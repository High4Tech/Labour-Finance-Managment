"""Small React event editing boundary; native event validators remain authoritative."""
import frappe
from plus_point.benefits import atomic
from plus_point.events import plan_doc
from plus_point.operations import terms_doc


@frappe.whitelist(methods=['POST'])
@atomic
def requirements(name, names, values=None, remove=0):
    doc = plan_doc(name, True)
    terms = terms_doc(doc.contract_terms, True)
    keys = frappe.parse_json(names)
    if not isinstance(keys, list) or not keys or len(keys) > 100 or any(not isinstance(key,str) for key in keys) or len(set(keys)) != len(keys):
        frappe.throw('Select up to 100 crew requirements from this event.')
    selected = [r for r in doc.staffing if r.name in keys]
    if len(selected) != len(keys):
        frappe.throw('Reload the event and select its current crew requirements.')
    if frappe.utils.cint(remove):
        for row in selected:
            assignments = frappe.get_list('PP Assignment', filters={
                'project': doc.project, 'site': row.site, 'start_date': ['<=', row.end_date]},
                fields=['end_date', 'employee'], limit_page_length=0)
            for assignment in assignments:
                if (not assignment.end_date or frappe.utils.getdate(assignment.end_date) >= frappe.utils.getdate(row.start_date)) and (
                    not row.designation or frappe.db.get_value('Employee', assignment.employee, 'designation') == row.designation):
                    frappe.throw('Release or move this role’s assigned workers before removing its requirement. Recorded work stays protected.')
        for row in selected:
            doc.remove(row)
    else:
        update = frappe.parse_json(values) or {}
        allowed = {'workers_required', 'phase', 'start_date', 'end_date', 'client_rate', 'wage_rate'}
        if not isinstance(update,dict) or not update or set(update) - allowed:
            frappe.throw('Choose crew quantities, phases, dates or rates to update.')
        if 'client_rate' in update and terms.get('event_basis') and any(float(r.client_rate or 0) != float(update['client_rate']) for r in selected):
            terms.commercial_status = 'Pending'
            terms.commercial_source = 'Changed event client rate requires confirmation.'
            terms.save()
        for row in selected:
            row.update(update)
    doc.save()
    return dict(name=doc.name)
