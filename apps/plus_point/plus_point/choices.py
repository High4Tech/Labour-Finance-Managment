"""Complete link pickers, paged through native permission-checked searches."""
import frappe
from frappe.utils import cint


@frappe.whitelist()
def page(doctype, txt='', start=0, query=None, filters=None, searchfield=None,
         reference_doctype=None, link_fieldname=None, ignore_user_permissions=False):
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in to choose a record.', frappe.PermissionError)
    if not (frappe.has_permission(doctype, 'read') or frappe.has_permission(doctype, 'select')):
        frappe.throw('You cannot view this list.', frappe.PermissionError)
    start=cint(start)
    if start < 0:frappe.throw('Invalid list position.')
    if isinstance(filters,str):filters=frappe.parse_json(filters)
    if doctype=='Currency' and (filters is None or isinstance(filters,dict)):
        # Choosing a currency enables it through the existing company/client
        # save flow. Its metadata need not already be used in these books.
        filters=dict(filters or {});filters.setdefault('include_disabled',1)
    from frappe.desk.search import search_widget, build_for_autosuggest
    rows=search_widget(doctype, str(txt or ''), query=query, filters=filters,
        searchfield=searchfield, start=start, page_length=200,
        reference_doctype=reference_doctype, link_fieldname=link_fieldname,
        ignore_user_permissions=ignore_user_permissions)
    # A native/custom query can cap its own page below 200. Continue until an
    # empty page rather than mistaking that cap for the end of the list.
    return dict(rows=build_for_autosuggest(rows, doctype), more=bool(rows), next_start=start+len(rows))
