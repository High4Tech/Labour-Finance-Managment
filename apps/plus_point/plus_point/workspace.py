"""One subscribed business profile per customer site; clients are Customers."""
import json
import frappe

SETTINGS='PP Workspace Settings'


def fixture_context():
    return bool(frappe.conf.get('allow_tests') and not getattr(frappe.local,'request',None)
        and frappe.flags.get('pp_test_entitlement') is not None)


def company():
    if frappe.conf.get('pp_control_plane'):return None
    bound=frappe.db.get_single_value(SETTINGS,'company') if frappe.db.exists('DocType',SETTINGS) else None
    if bound and frappe.db.exists('Company',bound):return bound
    rows=frappe.get_all('Company',pluck='name',order_by='creation')
    if not rows:return None
    # Preserve the profile that already owns the business's work if older setup
    # created spare Company records. Never delete or reassign historical records.
    return max(rows,key=lambda name:(frappe.db.count('Project',{'company':name}),frappe.db.count('Employee',{'company':name})))


def bind_existing():
    if frappe.conf.get('pp_control_plane') or fixture_context():return
    name=company()
    if name:
        frappe.db.set_single_value(SETTINGS,'company',name)
        frappe.db.set_single_value('Global Defaults','default_company',name)
        frappe.defaults.set_global_default('company',name)
        # Native new-document defaults must agree with the one business shown
        # in PLUS POINT, including an owner who selected an older spare profile.
        for user in frappe.get_all('User',filters={'enabled':1,'user_type':'System User'},pluck='name'):
            frappe.defaults.set_user_default('Company',name,user=user)
            frappe.defaults.set_user_default('pp_event_setup_company_v1',name,user=user)


def prevent_extra_company(doc,method=None):
    if frappe.conf.get('pp_control_plane') or frappe.flags.in_install or frappe.flags.in_migrate or fixture_context():return
    frappe.db.get_value('DocType','Company','name',for_update=True)
    if frappe.db.count('Company'):
        frappe.throw('This subscription has one company workspace. Add the businesses that hire you under Clients, and their jobs under Event projects.')


def company_created(doc,method=None):
    if frappe.conf.get('pp_control_plane') or frappe.flags.in_install or fixture_context():return
    if frappe.db.exists('DocType',SETTINGS):frappe.db.set_single_value(SETTINGS,'company',doc.name)


def company_query(user=None):
    if frappe.conf.get('pp_control_plane') or fixture_context():return ''
    name=company()
    return '`tabCompany`.name='+frappe.db.escape(name) if name else ''


def company_permission(doc,user=None,permission_type=None):
    if frappe.conf.get('pp_control_plane') or fixture_context() or doc.is_new():return True
    bound=company()
    if bound and doc.name!=bound:return False
    return True


def draft():
    raw=frappe.db.get_single_value(SETTINGS,'onboarding_state')
    return json.loads(raw) if raw else None


def save_draft(state):
    frappe.db.set_single_value(SETTINGS,'onboarding_state',json.dumps(state))


def audit_local():
    if getattr(frappe.local,'request',None) or not frappe.local.site.endswith('.localhost'):raise RuntimeError('Local operator required')
    owner=frappe.conf.get('pp_signup_owner');visible=None;default=None
    if owner and frappe.db.exists('User',owner):
        previous=frappe.session.user
        try:
            frappe.set_user(owner);visible=frappe.get_list('Company',pluck='name');default=frappe.defaults.get_user_default('Company')
        finally:frappe.set_user(previous)
    return dict(company=company(),owner_visible_companies=visible,owner_default_company=default,profiles=[dict(name=r.name,country=r.country,currency=r.default_currency,
        projects=frappe.db.count('Project',{'company':r.name}),workers=frappe.db.count('Employee',{'company':r.name}),
        ledger=frappe.db.count('GL Entry',{'company':r.name})) for r in frappe.get_all('Company',fields=['name','country','default_currency'])])
