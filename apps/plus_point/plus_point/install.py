"""Native Desk configuration and small integration fields; no upstream forks."""
import json
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
    after_migrate()


def before_install():
    if not frappe.db.exists('Role', 'High4Tech Platform Admin'):
        frappe.get_doc(dict(doctype='Role', role_name='High4Tech Platform Admin', desk_access=1)).insert(ignore_permissions=True)


def local_defaults():
    """Use ERPNext's own setup fixtures on a fresh local development site."""
    if not frappe.local.site.endswith('.localhost'):
        raise RuntimeError('Local defaults are limited to .localhost sites')
    # Create this before web starts. Otherwise the first out-of-process API-key
    # generation can race a web process whose cached config has no encryption key.
    from frappe.utils.password import get_encryption_key
    get_encryption_key()
    from erpnext.setup.setup_wizard.operations.install_fixtures import install, install_defaults
    from frappe.desk.page.setup_wizard.install_fixtures import update_genders
    if not frappe.db.exists('Gender', 'Male'):
        update_genders()
    if not frappe.db.exists('Warehouse Type', 'Transit'):
        install(country='Pakistan')
    if not frappe.db.exists('Price List', 'Standard Selling'):
        install_defaults(frappe._dict(currency='PKR', country='Pakistan'))
    from frappe.utils import getdate
    year = getdate().year
    if not frappe.db.exists('Fiscal Year', str(year)):
        frappe.get_doc(dict(doctype='Fiscal Year', year=str(year), year_start_date=f'{year}-01-01', year_end_date=f'{year}-12-31')).insert()
    frappe.db.commit()


def after_migrate():
    before_install()
    for doctype, columns, name in [
        ('PP Work Entry', ['employee', 'work_date'], 'pp_employee_work_date'),
        ('PP Work Entry', ['contract_terms', 'status'], 'pp_terms_status'),
        ('PP Assignment', ['site', 'start_date'], 'pp_site_start'),
        ('PP Milestone', ['contract_terms', 'status'], 'pp_milestone_terms_status'),
    ]:
        frappe.db.add_index(doctype, columns, name)
    create_custom_fields({
        'Sales Invoice Item': [
            dict(fieldname='pp_source_type', label='PLUS POINT Source Type', fieldtype='Select',
                 options='\nPP Work Entry\nPP Milestone', read_only=1, no_copy=1),
            dict(fieldname='pp_source_name', label='PLUS POINT Source', fieldtype='Dynamic Link',
                 options='pp_source_type', read_only=1, no_copy=1),
        ],
    })
    if not frappe.db.exists('Workspace', 'PLUS POINT'):
        links = [dict(type='Link', link_type='DocType', link_to=name, label=label)
                 for name, label in [('Customer', 'Client companies'), ('Contract', 'Client contracts'),
                    ('Project', 'Projects'), ('PP Site', 'Work sites'), ('Employee', 'Workers'),
                    ('PP Assignment', 'Worker allocations'), ('PP Daily Register', 'Daily attendance'),
                    ('PP Work Entry', 'Worker earnings'), ('PP Contract Terms', 'Billing terms'),
                    ('PP Milestone', 'Fixed contract milestones'), ('Sales Invoice', 'Client invoices'),
                    ('Payment Entry', 'Receipts and payments'), ('PP Wage Settlement', 'Worker payments')]]
        frappe.get_doc(dict(doctype='Workspace', name='PLUS POINT', label='PLUS POINT',
            title='PLUS POINT', module='PLUS POINT', public=1, icon='organization',
            content=json.dumps([dict(id='heading', type='header', data=dict(text='<b>PLUS POINT</b>', col=12)),
                dict(id='operations', type='card', data=dict(card_name='Workforce operations', col=12))]),
            links=[dict(type='Card Break', label='Workforce operations')] + links)).insert(ignore_permissions=True)
    if frappe.conf.get('pp_control_plane') and not frappe.db.exists('Workspace', 'High4Tech'):
        names = ['PP Tenant', 'Subscription Plan', 'Subscription', 'Customer', 'Sales Invoice', 'Payment Entry', 'User', 'Error Log']
        frappe.get_doc(dict(doctype='Workspace', name='High4Tech', label='High4Tech',
            title='High4Tech', module='PLUS POINT', public=1, icon='organization',
            roles=[dict(role='High4Tech Platform Admin')],
            content=json.dumps([dict(id='platform-heading', type='header', data=dict(text='<b>High4Tech Super Admin</b>', col=12)),
                dict(id='platform-operations', type='card', data=dict(card_name='Platform operations', col=12))]),
            links=[dict(type='Card Break', label='Platform operations')] +
                  [dict(type='Link', link_type='DocType', link_to=name, label=name) for name in names])).insert(ignore_permissions=True)
    from plus_point.ux import configure_tenant_workspace
    configure_tenant_workspace()
