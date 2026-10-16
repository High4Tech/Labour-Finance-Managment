"""Tenant navigation using native site customizations, not upstream UI forks."""
import frappe


def configure_tenant_workspace():
    if frappe.conf.get('pp_control_plane'):
        return

    # Native per-user choices still win. Do not replace an operator's site layout.
    if not frappe.db.exists('Custom Sidebar', {'module': 'PLUS POINT', 'user': ''}):
        items = [dict(type='Link', link_type='Workspace', link_to='PLUS POINT', label='Overview')]
        for label, closed, links in [
            ('Daily work', 0, [('PP Daily Register', 'Attendance'), ('Employee', 'Workers'),
                              ('PP Site', 'Work sites'), ('PP Assignment', 'Assign workers')]),
            ('Billing and payments', 0, [('PP Contract Terms', 'Client billing'),
                                        ('Sales Invoice', 'Client invoices'), ('PP Wage Settlement', 'Worker payments')]),
            ('More', 1, [('Customer', 'Clients'), ('Contract', 'Client contracts'), ('Project', 'Projects'),
                         ('PP Work Entry', 'Wages earned'), ('PP Milestone', 'Fixed contract milestones'),
                         ('Payment Entry', 'Receipts and payments'), ('Company', 'Your company')]),
        ]:
            items.append(dict(type='Section Break', label=label, added=1, collapsible=1, keep_closed=closed))
            items.extend(dict(type='Link', link_type='DocType', link_to=doctype, label=title, child=1, added=1)
                         for doctype, title in links)
        items.append(dict(type='Link', link_type='DocType', link_to='PP Tenant', hidden=1))
        frappe.get_doc(dict(doctype='Custom Sidebar', module='PLUS POINT', user='', label='PLUS POINT',
                            sidebar_items=items)).insert(ignore_permissions=True)

    # Readable link labels are presentation metadata; names and references do not change.
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    for doctype in ('Employee', 'Project'):
        if not frappe.db.exists('Property Setter', {'doc_type': doctype, 'property': 'show_title_field_in_link'}):
            make_property_setter(doctype, None, 'show_title_field_in_link', 1, 'Check', for_doctype=True)

    # Customers start in the product workspace. Preserve an explicit site preference.
    if not frappe.db.get_single_value('System Settings', 'default_app'):
        frappe.db.set_single_value('System Settings', 'default_app', 'plus_point')
