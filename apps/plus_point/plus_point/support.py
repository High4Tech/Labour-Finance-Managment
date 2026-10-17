"""Audited platform-to-customer account support using native jobs and User security."""
import json
from pathlib import Path
import re
import subprocess

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from plus_point.platform import require_platform

OPERATIONS = ('Reset password', 'Change login ID')


@frappe.whitelist(methods=['POST'])
def request_account_help(tenant, operation, new_username=None):
    require_platform()
    doc = frappe.get_doc(dict(doctype='PP Support Request', tenant=tenant,
        operation=operation, new_username=new_username or '', status='Queued')).insert()
    return dict(name=doc.name, status=doc.status)


def validate_request(doc):
    require_platform()
    if doc.operation not in OPERATIONS:
        frappe.throw('Choose password reset or login ID change')
    old = doc.get_doc_before_save()
    if old:
        if getattr(frappe.local, 'request', None) or not frappe.flags.get('pp_support_processing'):
            frappe.throw('Support requests are processed by the background worker', frappe.PermissionError)
        for field in ('tenant', 'operation', 'new_username', 'target_site', 'target_email', 'requested_by'):
            if doc.get(field) != old.get(field):
                frappe.throw('A queued support request cannot change its customer or action')
        return
    tenant = frappe.get_doc('PP Tenant', doc.tenant)
    tenant.check_permission('read')
    if doc.status != 'Queued':
        frappe.throw('New support requests must be queued')
    if (not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.localhost', tenant.site_hostname)
            or tenant.site_hostname == frappe.local.site):
        frappe.throw('Choose a registered customer site')
    if tenant.owner_email.strip().casefold() in ('administrator', 'guest'):
        frappe.throw('Support applies to the customer owner login, not system accounts')
    if doc.operation == 'Change login ID':
        if not re.fullmatch(r'[A-Za-z0-9._-]{3,64}', doc.new_username or ''):
            frappe.throw('Use 3–64 letters, numbers, dots, underscores or hyphens for the login ID')
        if doc.new_username.casefold() in ('administrator', 'guest'):
            frappe.throw('Choose a login ID other than a built-in system account')
    elif doc.new_username:
        frappe.throw('A password reset does not change the login ID')
    doc.target_site, doc.target_email = tenant.site_hostname, tenant.owner_email
    doc.requested_by = frappe.session.user
    doc.status_message = 'Waiting for the account support worker'
    doc.completed_on = doc.expires_on = None
    doc.result_secret = ''


def enqueue_request(doc):
    frappe.enqueue('plus_point.support.process_request', queue='short',
                   enqueue_after_commit=True, request_name=doc.name, timeout=120)


def process_request(request_name):
    """Native RQ worker on the platform; tenant connection lives in a child process."""
    if getattr(frappe.local, 'request', None):
        frappe.throw('Background execution required', frappe.PermissionError)
    require_platform()
    frappe.db.get_value('PP Support Request', request_name, 'name', for_update=True)
    doc = frappe.get_doc('PP Support Request', request_name)
    if doc.status != 'Queued':
        return
    frappe.flags.pp_support_processing = True
    try:
        tenant = frappe.get_doc('PP Tenant', doc.tenant)
        if (tenant.site_hostname, tenant.owner_email) != (doc.target_site, doc.target_email):
            frappe.throw('The customer owner changed; create a fresh support request')
        doc.status, doc.status_message = 'Processing', 'Updating the customer owner login'
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        args = dict(email=doc.target_email, operation=doc.operation, new_username=doc.new_username)
        # No password or reset key appears in arguments. Secret stdout stays in memory.
        result = subprocess.run(['bench', '--site', doc.target_site, 'execute',
            'plus_point.support.apply_owner_help', '--kwargs', json.dumps(args)],
            cwd=Path('/home/frappe/frappe-bench'), text=True, capture_output=True,
            check=True, timeout=90)
        outcome = json.loads(result.stdout)
        if outcome.get('reset_link'):
            from frappe.utils.password import set_encrypted_password
            set_encrypted_password(doc.doctype, doc.name, outcome['reset_link'], 'result_secret')
            doc.result_secret = '********'
            doc.expires_on = add_to_date(now_datetime(), minutes=20)
        doc.status = 'Completed'
        doc.status_message = ('Password reset is ready. No email was sent.' if doc.operation == 'Reset password'
                              else 'Customer login ID updated. The email address is unchanged.')
        doc.completed_on = now_datetime()
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as error:
        frappe.db.rollback()
        frappe.log_error(title='PLUS POINT account support failed',
            message=f'Request {doc.name}: {type(error).__name__}. Child output redacted.')
        # Never persist subprocess output, credentials, reset links or tracebacks.
        doc.reload()
        doc.status = 'Failed'
        doc.status_message = 'Account support could not complete. Check the registered owner login and try a new request.'
        doc.completed_on = now_datetime()
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    finally:
        frappe.flags.pp_support_processing = False


def apply_owner_help(email, operation, new_username=None):
    """Trusted CLI only. Reuses native User validation, hashing and session handling."""
    if getattr(frappe.local, 'request', None) or frappe.conf.get('pp_control_plane'):
        frappe.throw('Customer-site operator execution required', frappe.PermissionError)
    if not frappe.local.site.endswith('.localhost') or email.strip().casefold() in ('administrator', 'guest'):
        frappe.throw('Unsupported account support target')
    if operation not in OPERATIONS:
        frappe.throw('Unsupported support action')
    user = frappe.get_doc('User', email)
    if user.name in ('Administrator', 'Guest'):
        frappe.throw('System accounts are not customer support targets')
    if not user.enabled or user.user_type != 'System User':
        frappe.throw('The registered customer owner must have an enabled business login')
    if operation == 'Reset password':
        user.validate_reset_password()
        link = user._reset_password(send_email=False)
        from frappe.sessions import clear_sessions
        clear_sessions(user=email, force=True)
        frappe.db.commit()
        return dict(reset_link=link)
    if not re.fullmatch(r'[A-Za-z0-9._-]{3,64}', new_username or '') or new_username.casefold() in ('administrator', 'guest'):
        frappe.throw('Invalid login ID')
    # Identity-only operator update. A full User save also writes contacts/shares,
    # which must remain locked on a suspended subscription. Native validation
    # and the native unique index enforce username rules and concurrent clashes.
    frappe.db.get_value('User', email, 'name', for_update=True)
    user.username = new_username
    user.validate_username()
    if user.username != new_username:
        frappe.throw('That login ID is already in use')
    frappe.db.set_value('User', email, 'username', user.username)
    frappe.db.set_single_value('System Settings', 'allow_login_using_user_name', 1)
    frappe.clear_cache(user=email)
    from frappe.sessions import clear_sessions
    clear_sessions(user=email, force=True)
    frappe.db.commit()
    return dict(username=user.username)


@frappe.whitelist()
def account_help_result(request_name):
    require_platform()
    doc = frappe.get_doc('PP Support Request', request_name)
    doc.check_permission('read')
    result = dict(name=doc.name, status=doc.status, message=doc.status_message,
                  login_email=doc.target_email, expires_on=doc.expires_on)
    if doc.status == 'Completed' and doc.operation == 'Reset password' and doc.expires_on and get_datetime(doc.expires_on) > now_datetime():
        from frappe.utils.password import get_decrypted_password
        result['reset_link'] = get_decrypted_password(doc.doctype, doc.name, 'result_secret', raise_exception=False)
    return result


def purge_results():
    if not frappe.conf.get('pp_control_plane'):
        return
    from frappe.utils.password import remove_encrypted_password
    for name in frappe.get_all('PP Support Request', filters={'expires_on': ['<', now_datetime()]}, pluck='name'):
        remove_encrypted_password('PP Support Request', name, 'result_secret')
