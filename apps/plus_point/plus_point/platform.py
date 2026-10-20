"""Platform-only directory; ERPNext owns plans, subscriptions, billing and receipts."""
import secrets
import frappe
from frappe.utils import getdate, nowdate


def require_platform():
    if not frappe.conf.get('pp_control_plane') or 'High4Tech Platform Admin' not in frappe.get_roles():
        frappe.throw('High4Tech platform site and Platform Admin role required', frappe.PermissionError)


def export_entitlement(tenant):
    """Operator CLI only. Deliberately not whitelisted for tenant/browser calls."""
    require_platform()
    doc = frappe.get_doc('PP Tenant', tenant)
    subscription = frappe.get_doc('Subscription', doc.subscription)
    approved = subscription.status in ('Active', 'Trialing', 'Grace Period')
    expiry = subscription.trial_period_end if subscription.status == 'Trialing' else subscription.current_invoice_end
    if subscription.get('pp_demo_workspace'):
        expiry=subscription.trial_period_end
    # Never trust a stale native status after its paid/trial period ends.
    valid_until = str(getdate(expiry)) if expiry else '1970-01-01'
    signup=frappe.db.get_value('PP Signup Request',{'workspace_site':doc.site_hostname,'review_status':'Approved'},['name','activation_status','login_username'],as_dict=True)
    return dict(signup_reference=signup.name if signup else None,signup_status=signup.activation_status if signup else None,login_username=signup.login_username if signup else None,site=doc.site_hostname, owner_email=doc.owner_email, organization=doc.organization_name, entitlement=dict(valid_until=valid_until,
        suspended=bool(doc.suspended or not approved),
        limits=dict(workers=doc.worker_limit, users=doc.user_limit, sites=doc.site_limit)))


def export_all():
    require_platform()
    return [export_entitlement(name) for name in frappe.get_all('PP Tenant', pluck='name')]


def setup_local_owner(email, organization):
    """Trusted provisioning CLI only; never a whitelisted account-management API."""
    if not frappe.local.site.endswith('.localhost'):
        raise RuntimeError('This development provisioner supports local sites only')
    if not frappe.db.exists('User', email):
        from frappe.utils.password import update_password
        roles = ['System Manager', 'HR Manager', 'Accounts Manager', 'Projects Manager',
                 'Sales Manager', 'Purchase Manager', 'Stock Manager']
        frappe.get_doc(dict(doctype='User', email=email, first_name=organization,
            enabled=1, send_welcome_email=0, roles=[dict(role=role) for role in roles])).insert()
        update_password(email, secrets.token_urlsafe(48))
        frappe.db.commit()
    return 'Local tenant owner account ready; credentials not printed'
