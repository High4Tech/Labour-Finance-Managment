"""Exact local QA fixtures for native password setup; no HTTP entry points."""
import json
import re
from pathlib import Path

import frappe


CONFIG_KEYS=('pp_signup_reference','pp_signup_company','pp_signup_owner','pp_signup_setup_initialized','host_name')
SETTINGS=('setup_complete','enable_onboarding','default_app','time_zone','country','currency','language','allow_login_using_user_name')


def fixture(action,run_id):
    if (getattr(frappe.local,'request',None) or not frappe.conf.get('allow_tests')
            or frappe.local.site!='qa.localhost' or not re.fullmatch('[a-f0-9]{12}',run_id)):
        raise RuntimeError('Exact local QA operator fixture required')
    from frappe.installer import update_site_config
    from plus_point.activation import initialize_customer
    from plus_point.platform import setup_local_owner
    frappe.set_user('Administrator')
    email=f'activation-qa-{run_id}@example.invalid';reference=f'activation-qa-{run_id}'
    alias=f'qa-{run_id}';organization=f'Activation QA {run_id}'
    backup=Path(frappe.get_site_path('private','backups',reference+'.json'))
    if action=='begin':
        if backup.exists() or frappe.db.exists('User',email):raise RuntimeError('Restore this exact fixture first')
        saved=dict(config={k:frappe.conf.get(k) for k in CONFIG_KEYS},settings={k:frappe.db.get_single_value('System Settings',k) for k in SETTINGS})
        backup.parent.mkdir(parents=True,exist_ok=True);backup.write_text(json.dumps(saved),encoding='utf-8')
        for key,value in dict(pp_signup_reference=reference,pp_signup_company=organization,pp_signup_owner=email,
                pp_signup_setup_initialized=False,host_name='http://qa.localhost:8000').items():
            update_site_config(key,value);frappe.conf[key]=value
        setup_local_owner(email,organization)
        result=initialize_customer(reference,email,organization,alias,True)
        return dict(email=email,alias=alias,organization=organization,**result)
    if not backup.exists():raise RuntimeError('Exact fixture backup required')
    if action=='check':
        result=initialize_customer(reference,email,organization,alias,False)
        return dict(**result,key_consumed=not bool(frappe.db.get_value('User',email,'reset_password_key')))
    if action!='end':raise RuntimeError('Unknown fixture operation')
    saved=json.loads(backup.read_text(encoding='utf-8'))
    if frappe.db.exists('User',email):frappe.delete_doc('User',email,ignore_permissions=True)
    for key,value in saved['config'].items():update_site_config(key,value)
    frappe.db.set_single_value('System Settings',saved['settings'])
    frappe.clear_cache();frappe.db.commit();backup.unlink()
    return dict(restored=True)


def workspace_summary(reference):
    """Operator-only activation verification, excluding passwords and reset links."""
    if getattr(frappe.local,'request',None) or frappe.conf.get('pp_signup_reference')!=reference:
        raise RuntimeError('Bound local operator required')
    email=frappe.conf.get('pp_signup_owner')
    return dict(owner_enabled=bool(frappe.db.get_value('User',email,'enabled')),
        setup_complete=bool(frappe.db.get_single_value('System Settings','setup_complete')),
        counts={dt:frappe.db.count(dt) for dt in ('Company','Customer','Employee','Project','PP Site','PP Work Entry','Vehicle','Sales Invoice')},
        roles=frappe.get_roles(email),has_private_setup=bool(frappe.db.get_value('User',email,'reset_password_key')))
