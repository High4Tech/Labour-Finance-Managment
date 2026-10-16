"""Host-managed site entitlements. Tenants cannot edit these through DocType APIs.

All sites have independent databases/users through native Frappe. This local
same-host deployment uses protected site_config, not browser-supplied tenant IDs.
"""
from datetime import date
import frappe
from frappe.utils import getdate

SYSTEM_RECORDS = {'Error Log', 'Activity Log', 'Access Log', 'Session Default',
                  'Route History', 'View Log', 'Scheduled Job Log', 'Version',
                  'Email Queue', 'Email Queue Recipient', 'RQ Job', 'Console Log'}


def current_entitlement():
    # Frappe caches site configuration in long-running processes. Read the host's
    # current entitlement so suspension and renewal apply without restarting web/jobs.
    override = frappe.flags.get('pp_test_entitlement')
    if override is not None and frappe.conf.get('allow_tests') and not getattr(frappe.local, 'request', None):
        return override
    from frappe.config import get_site_config
    return get_site_config(cached=False).get('pp_entitlement')


def entitlement_status(entitlement, today=None):
    if not entitlement:
        return 'Development'
    if entitlement.get('suspended'):
        return 'Suspended'
    if not entitlement.get('valid_until'):
        return 'Expired'
    today = today or date.today()
    end = date.fromisoformat(str(entitlement['valid_until']))
    return 'Active' if today <= end else 'Expired'


def enforce_write(doc, method=None):
    if frappe.flags.in_install or frappe.flags.in_migrate:
        return
    entitlement = current_entitlement()
    if entitlement and doc.doctype not in SYSTEM_RECORDS:
        if entitlement_status(entitlement, getdate()) != 'Active':
            frappe.throw('Subscription is expired or suspended. Existing records remain available for reading; contact High4Tech to renew.', frappe.PermissionError)
        quota = {'Employee': ('workers', {'status': 'Active'}),
                 'User': ('users', {'enabled': 1, 'user_type': 'System User', 'name': ['not in', ['Administrator', 'Guest']]}),
                 'PP Site': ('sites', {'is_active': 1})}.get(doc.doctype)
        if quota:
            key, filters = quota
            limit = int(entitlement.get('limits', {}).get(key, 0))
            if limit > 0:
                frappe.db.get_value('DocType', doc.doctype, 'name', for_update=True)
                active = (doc.status == 'Active' if doc.doctype == 'Employee' else
                          bool(doc.is_active) if doc.doctype == 'PP Site' else
                          bool(doc.enabled) and doc.user_type == 'System User' and doc.name not in ('Administrator', 'Guest'))
                if active:
                    filters = dict(filters, name=['!=', doc.name or '']) if doc.doctype != 'User' else filters
                    current = frappe.db.count(doc.doctype, filters)
                    old = doc.get_doc_before_save()
                    if doc.doctype == 'User' and old and old.enabled and old.user_type == 'System User':
                        current -= 1
                    if current >= limit:
                        frappe.throw(f'Subscription {key} limit reached ({limit})', frappe.PermissionError)


@frappe.whitelist()
def account_status():
    if frappe.session.user == 'Guest':
        frappe.throw('Sign in to see account status', frappe.PermissionError)
    entitlement = current_entitlement() or {}
    return dict(status=entitlement_status(entitlement), valid_until=entitlement.get('valid_until'),
                limits=entitlement.get('limits', {}))
