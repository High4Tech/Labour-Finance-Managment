"""Product navigation only. Native document permissions remain the security boundary."""
import frappe
import json

CUSTOMER_GROUPS = [
    ('Daily work', [('PP Daily Register', 'Attendance'), ('Employee', 'Workers')]),
    ('Inventory and transport', [('Page:pp-inventory','Warehouses'),('Page:pp-inventory','Vehicles')]),
    ('Clients and billing', [('PP Contract Terms', 'Client agreements'), ('PP Event Plan','Event plans'),('Sales Invoice', 'Billing and finances')]),
    ('Payments and costs', [('PP Wage Settlement', 'Worker payments'), ('Payment Entry', 'Receipts and payments'),
                           ('Purchase Invoice', 'Project expenses'), ('Expense Claim', 'Expense claims')]),
    ('Business reports', [('Report:PLUS POINT Project Finances', 'Project finances'),
                          ('Report:PLUS POINT Worker Statement', 'Worker statement')]),
    ('Business setup', [('Item', 'Billing items'),
                        ('Supplier', 'Suppliers'), ('Account', 'Accounts'), ('PP Work Entry', 'Wages earned')]),
]
PLATFORM_GROUPS = [
    ('PLUS POINT customers', [('PP Signup Request', 'Signup approvals'), ('PP Tenant', 'Customer accounts'), ('PP Support Request', 'Customer support')]),
    ('Pricing and access', [('Subscription Plan', 'Pricing plans'), ('Subscription', 'Subscriptions')]),
    ('Software sales', [('Sales Invoice', 'Software invoices'), ('Payment Entry', 'Receipts and payments')]),
    ('Business finances', [('Purchase Invoice', 'Business expenses'), ('Report:Profit and Loss Statement', 'Financial results'),
                          ('Report:Accounts Receivable', 'Outstanding invoices')]),
    ('Billing setup', [('Customer', 'Billing contacts'), ('Company', 'High4Tech company'), ('Item', 'Software items'),
                       ('Supplier', 'Service providers'), ('Account', 'Accounts')]),
]
COMMON_DEPENDENCIES = ['Address', 'Contact', 'Currency', 'Country', 'Fiscal Year', 'Cost Center',
    'Mode of Payment', 'Payment Terms Template', 'Sales Taxes and Charges Template', 'Tax Category',
    'Purchase Taxes and Charges Template', 'UOM', 'Item Group', 'Customer Group', 'Territory', 'Payment Term',
    'Bank Account', 'Bank', 'Journal Entry']


def product_navigation(platform):
    groups = PLATFORM_GROUPS if platform else CUSTOMER_GROUPS
    saved = json.loads(frappe.defaults.get_user_default('pp_section_order_v1') or '[]')
    ordered = [label for label in saved if label in dict(groups)]
    ordered += [label for label,_ in groups if label not in ordered]
    groups = [(label,dict(groups)[label]) for label in ordered]
    home = 'High4Tech' if platform else 'PLUS POINT'
    items = [dict(type='Link', link_type='Workspace', link_to=home, label='Overview', is_default_module=1)]
    if not platform:
        from plus_point.event_setup import current
        state=current()
        if state.get('step')!='done' and not state.get('skipped'):items.append(dict(type='Link',link_type='Page',link_to='pp-onboarding',label='Onboarding',is_default_module=1))
    doctypes, reports = set(COMMON_DEPENDENCIES), set()
    for label, entries in groups:
        visible = []
        for name, title in entries:
            if name.startswith('Page:'):
                visible.append(dict(type='Link',link_type='Page',link_to=name[5:],label=title,child=1,is_default_module=1,**({'route_options':json.dumps({'view':'vehicles' if title=='Vehicles' else 'warehouses'})} if name=='Page:pp-inventory' else {})));continue
            is_report = name.startswith('Report:')
            target = name.removeprefix('Report:')
            if is_report:
                reports.add(target)
                allowed = frappe.db.exists('Report', target) and frappe.get_doc('Report', target).is_permitted()
            else:
                doctypes.add(target)
                allowed = frappe.has_permission(target, 'read')
            if allowed:
                item=dict(type='Link', link_type='Report' if is_report else 'DocType',
                    link_to=target, label=title, child=1, is_default_module=1)
                if is_report:
                    report=frappe.get_doc('Report',target)
                    item['report']=dict(report_type=report.report_type,ref_doctype=report.ref_doctype)
                if name=='Item' and not platform:item['route_options']=json.dumps({'is_stock_item':int(title=='Inventory items')})
                visible.append(item)
        if visible:
            items.append(dict(type='Section Break', label=label, collapsible=1,
                              keep_closed=int(label in ('Business setup', 'Billing setup'))))
            items.append(dict(type='Link',link_type='Page',link_to='pp-section',label=label+' overview',
                route_options=json.dumps({'section':label}),child=1,is_default_module=1))
            items.extend(visible)
    # Native forms open these related records; they are not extra sidebar modules.
    if not platform:
        doctypes.update(['Vehicle','Warehouse','Item','Stock Reconciliation','PP Vehicle Booking','PP Equipment Booking','Employee Advance', 'Designation', 'Gender', 'Department', 'Employment Type',
                         'Branch', 'Employee Grade', 'Holiday List', 'PP Import Record', 'Company','Customer','Contract','Project','PP Contract Terms','PP Event Plan','PP Site','PP Assignment','PP Milestone','Sales Invoice','PP Agreement Staffing'])
    return dict(items=items, doctypes=sorted(doctypes), reports=sorted(reports), workspace=home,
                pages=['pp-section']+([] if platform else ['pp-inventory','pp-onboarding','pp-agreements','pp-event-plans','pp-client-billing']),groups=ordered)


@frappe.whitelist(methods=['POST'])
def save_section_order(order):
    if frappe.session.user=='Guest':
        frappe.throw('Sign in to arrange your sections',frappe.PermissionError)
    values=frappe.parse_json(order)
    allowed=[label for label,_ in (PLATFORM_GROUPS if frappe.conf.get('pp_control_plane') else CUSTOMER_GROUPS)]
    if not isinstance(values,list) or len(values)!=len(allowed) or set(values)!=set(allowed):
        frappe.throw('Include each available section once')
    frappe.defaults.set_user_default('pp_section_order_v1',json.dumps(values))
    return product_navigation(bool(frappe.conf.get('pp_control_plane')))
