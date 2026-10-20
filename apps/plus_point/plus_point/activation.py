"""Approved local signups receive isolated sites; billing remains simulated.

Only the trusted operator process touches another site's database. Initial
passwords are random and never returned. Frappe owns one-time password setup.
"""
import hashlib
import json
import re
import sys
import unicodedata

import frappe
from frappe.utils import add_days,add_to_date,get_datetime,now_datetime,today
from plus_point.platform import require_platform


def local_platform():
    require_platform()
    if not frappe.local.site.endswith('.localhost'):frappe.throw('Local activation only',frappe.PermissionError)


def hostname(doc):
    slug=unicodedata.normalize('NFKD',doc.business_name).encode('ascii','ignore').decode().lower()
    slug=re.sub('[^a-z0-9]+','-',slug).strip('-')[:32].strip('-') or 'company'
    return f'{slug}-{hashlib.sha256(doc.name.encode()).hexdigest()[:10]}.localhost'


def queue(reference):
    """Role-gated registry transaction; web requests never spawn site installers."""
    local_platform()
    doc=frappe.get_doc('PP Signup Request',reference,for_update=True)
    if doc.review_status!='Approved' or doc.payment_status!='Demo payment submitted':
        frappe.throw('Approve the submitted signup before creating its company workspace')
    if doc.activation_status in ('Queued','Creating','Ready','Active'):return state(doc)
    frappe.db.savepoint('pp_signup_activation')
    try:
        site=hostname(doc)
        if doc.workspace_site and doc.workspace_site!=site:frappe.throw('Workspace identity changed; contact the operator')
        if not doc.workspace_site:
            if frappe.db.exists('PP Tenant',site):frappe.throw('This workspace address is already registered')
            company=frappe.defaults.get_user_default('Company') or frappe.db.get_single_value('Global Defaults','default_company')
            if not company:
                companies=frappe.get_list('Company',pluck='name',limit_page_length=2)
                if len(companies)==1:company=companies[0]
            if not company:frappe.throw('Choose High4Tech’s default accounting company first')
            frappe.get_doc('Company',company).check_permission('read')
            title=doc.business_name
            if frappe.db.exists('Customer',title):title=f'{title} (trial {doc.name})'
            customer=frappe.get_doc(dict(doctype='Customer',customer_name=title,customer_type='Company',
                customer_group='Commercial',territory='All Territories')).insert(ignore_permissions=True)
            subscription=frappe.get_doc(dict(doctype='Subscription',party_type='Customer',party=customer.name,company=company,
                start_date=today(),trial_period_start=today(),trial_period_end=add_days(today(),30),
                pp_demo_workspace=1,submit_invoice=0,generate_invoice_at='End of the current subscription period',
                plans=[dict(plan=doc.plan,qty=1)])).insert(ignore_permissions=True)
            frappe.get_doc(dict(doctype='PP Tenant',organization_name=doc.business_name,site_hostname=site,
                owner_email=doc.email,subscription=subscription.name,user_limit=1)).insert(ignore_permissions=True)
            doc.workspace_site=site;doc.workspace_subscription=subscription.name
        else:
            tenant=frappe.get_doc('PP Tenant',site)
            if tenant.owner_email!=doc.email or tenant.subscription!=doc.workspace_subscription:
                frappe.throw('Registered company identity differs from this signup')
        doc.activation_status='Queued';doc.activation_message='Waiting for the local workspace worker. No payment was collected.'
        doc.flags.signup_activation=True;doc.save(ignore_permissions=True)
    except Exception:
        frappe.db.rollback(save_point='pp_signup_activation');raise
    return state(doc)


@frappe.whitelist(methods=['POST'])
def activate(reference):return queue(reference)


def state(doc,include_secret=False):
    result=dict(activation=doc.activation_status or 'Not requested',activation_message=doc.activation_message or '',
        workspace_url=f'http://{doc.workspace_site}:8000/desk/plus-point' if doc.workspace_site else None,
        login_url=f'http://{doc.workspace_site}:8000/login' if doc.workspace_site else None,
        login_email=doc.email if doc.workspace_site else None,login_username=doc.login_username or None,
        setup_expires_on=doc.setup_expires_on)
    if include_secret and doc.activation_status=='Ready' and doc.setup_expires_on and get_datetime(doc.setup_expires_on)>now_datetime():
        from frappe.utils.password import get_decrypted_password
        result['setup_url']=get_decrypted_password(doc.doctype,doc.name,'setup_secret',raise_exception=False)
    return result


@frappe.whitelist()
def account_details(reference):
    local_platform();doc=frappe.get_doc('PP Signup Request',reference);doc.check_permission('read')
    return state(doc,True)


@frappe.whitelist(methods=['POST'])
def refresh_setup(reference):
    local_platform();doc=frappe.get_doc('PP Signup Request',reference,for_update=True)
    return requeue_setup(doc)


def requeue_setup(doc):
    if doc.review_status!='Approved' or doc.activation_status!='Ready':frappe.throw('Wait until this approved workspace is ready')
    doc.activation_status='Queued';doc.activation_message='Checking whether password setup is still required.'
    doc.flags.signup_activation=True;doc.save(ignore_permissions=True)
    return state(doc)


def activate_local(reference):
    local_platform()
    if getattr(frappe.local,'request',None):frappe.throw('Local operator only')
    result=queue(reference);frappe.db.commit();return result


def progress_local(reference):
    local_platform()
    if getattr(frappe.local,'request',None):frappe.throw('Local operator only')
    return state(frappe.get_doc('PP Signup Request',reference))


def operator_doc(reference):
    local_platform()
    if getattr(frappe.local,'request',None):frappe.throw('Local operator execution required',frappe.PermissionError)
    doc=frappe.get_doc('PP Signup Request',reference,for_update=True)
    if doc.review_status!='Approved' or not doc.workspace_site or doc.workspace_site!=hostname(doc):
        frappe.throw('Invalid approved workspace binding')
    tenant=frappe.get_doc('PP Tenant',doc.workspace_site)
    if tenant.owner_email!=doc.email or tenant.subscription!=doc.workspace_subscription:frappe.throw('Workspace owner changed')
    return doc


def mark_creating(reference):
    doc=operator_doc(reference)
    if doc.activation_status in ('Queued','Creating'):
        doc.activation_status='Creating';doc.activation_message='Creating your private company workspace. This can take a few minutes.'
        doc.flags.signup_activation=True;doc.save(ignore_permissions=True);frappe.db.commit()


def finish_from_stdin():
    payload=json.loads(sys.stdin.read(16384));doc=operator_doc(payload['reference'])
    if doc.activation_status not in ('Creating','Ready'):frappe.throw('Workspace is not being initialized')
    if payload.get('failed'):
        if doc.activation_status!='Creating':return
        doc.activation_status='Failed';doc.activation_message='Workspace setup could not finish. Choose Retry workspace setup; existing data is retained.'
    elif payload.get('activated'):
        from frappe.utils.password import remove_encrypted_password
        remove_encrypted_password(doc.doctype,doc.name,'setup_secret')
        doc.setup_secret='';doc.setup_expires_on=None;doc.activation_status='Active';doc.activation_message='Your company login is ready. Sign in with your own password.'
    elif payload.get('setup_url'):
        from urllib.parse import urlsplit
        url=urlsplit(payload['setup_url'])
        if url.scheme!='http' or url.netloc!=doc.workspace_site+':8000' or url.path!='/update-password' or not re.fullmatch(r'key=[A-Za-z0-9]+',url.query):
            frappe.throw('Invalid password setup destination')
        from frappe.utils.password import set_encrypted_password
        set_encrypted_password(doc.doctype,doc.name,payload['setup_url'],'setup_secret');doc.setup_secret='********'
        doc.setup_expires_on=add_to_date(now_datetime(),seconds=min(max(int(payload.get('expires_seconds',900)),60),1200))
        doc.activation_status='Ready';doc.activation_message='Your empty workspace is ready. Set your password, then complete company onboarding. No email was sent.'
    else:return
    doc.flags.signup_activation=True;doc.save(ignore_permissions=True);frappe.db.commit()


def initialize_customer(reference,email,organization,username='',issue_link=False):
    """Child CLI, bound to the new site's protected configuration."""
    if (getattr(frappe.local,'request',None) or frappe.conf.get('pp_control_plane')
            or frappe.conf.get('pp_signup_reference')!=reference or not frappe.local.site.endswith('.localhost')):
        frappe.throw('Bound customer-site operator required',frappe.PermissionError)
    if frappe.conf.get('pp_signup_owner')!=email:frappe.throw('Signup owner differs from this workspace')
    from frappe.installer import update_site_config
    from frappe.desk.page.setup_wizard.setup_wizard import disable_future_access,enable_setup_wizard_complete
    for app in frappe.get_installed_apps():enable_setup_wizard_complete(app)
    disable_future_access()
    frappe.db.set_single_value('System Settings',dict(setup_complete=1,enable_onboarding=0,default_app='plus_point',
        time_zone='Asia/Karachi',country='Pakistan',currency='PKR',language='en',allow_login_using_user_name=int(bool(username))))
    user=frappe.get_doc('User',email)
    if username and user.username!=username:
        if user.last_login:frappe.throw('The owner login is already in use; use customer support to change it')
        user.username=username;user.validate_username()
        if user.username!=username:frappe.throw('Choose a different company login ID')
        frappe.db.set_value('User',email,'username',username)
    initialized=bool(frappe.conf.get('pp_signup_setup_initialized'))
    if user.last_login or initialized and not user.reset_password_key:
        frappe.db.commit();return dict(activated=True)
    if not issue_link:
        frappe.db.commit();return dict(activated=False)
    user.validate_reset_password();link=user._reset_password(send_email=False)
    expiry=int(frappe.db.get_single_value('System Settings','reset_password_link_expiry_duration') or 900)
    update_site_config('pp_signup_setup_initialized',True)
    frappe.clear_cache(user=email);frappe.db.commit()
    return dict(setup_url=link,expires_seconds=expiry)


def purge_results():
    if not frappe.conf.get('pp_control_plane'):return
    from frappe.utils.password import remove_encrypted_password
    for name in frappe.get_all('PP Signup Request',filters={'setup_expires_on':['<',now_datetime()]},pluck='name'):
        remove_encrypted_password('PP Signup Request',name,'setup_secret')
