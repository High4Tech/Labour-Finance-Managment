"""Resumable, user-owned setup. Native records keep their normal validations."""
import json

import frappe
from frappe.utils import getdate, today

KEY = 'pp_guided_setup_v1'
STEPS = ['company', 'worker', 'site', 'terms', 'assignment', 'import', 'done']


def require_customer():
    from plus_point.api import _manager_only
    _manager_only()
    if frappe.conf.get('pp_control_plane'):
        frappe.throw('Business setup belongs on the PLUS POINT customer site', frappe.PermissionError)


def linked(doctype, name, company=None):
    doc = frappe.get_doc(doctype, name)
    doc.check_permission('read')
    if company and doc.get('company') != company:
        frappe.throw(f'{doctype} must belong to the selected company')
    return doc


def state():
    raw = frappe.defaults.get_user_default(KEY, user=frappe.session.user)
    return json.loads(raw) if raw else dict(step='company', skipped=False)


def save_state(value):
    frappe.defaults.set_user_default(KEY, json.dumps(value), user=frappe.session.user)
    return value


def insert(doctype, **fields):
    return frappe.get_doc(dict(doctype=doctype, **fields)).insert()


@frappe.whitelist()
def status():
    require_customer()
    saved = state()
    companies = frappe.get_list('Company', fields=['name', 'default_currency'], limit_page_length=0)
    # Existing businesses can choose the guide without being interrupted on rollout.
    fresh = not frappe.get_list('PP Assignment', fields=['name'], limit_page_length=1)
    return dict(state=saved, companies=companies, auto_start=fresh and not saved.get('skipped') and saved['step'] != 'done')


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def site_query(doctype, txt, searchfield, start, page_len, filters):
    require_customer()
    projects = frappe.get_list('Project', filters={'company': filters.get('company')}, pluck='name', limit_page_length=0)
    if not projects:
        return []
    sites = frappe.get_list('PP Site', filters={'project':['in',projects], 'is_active':1,
        'site_name':['like',f'%{txt}%']}, fields=['name','site_name'], order_by='site_name,name',start=start, page_length=page_len)
    return [[site.name,site.site_name] for site in sites]


@frappe.whitelist(methods=['POST'])
def control(action):
    require_customer()
    saved = state()
    if action == 'skip':
        saved['skipped'] = True
    elif action == 'resume':
        saved['skipped'] = False
        if saved['step'] == 'done':
            saved = dict(step='company', skipped=False)
    else:
        frappe.throw('Unknown setup action')
    return save_state(saved)


@frappe.whitelist(methods=['POST'])
def advance(step, values=None):
    require_customer()
    values = frappe._dict(frappe.parse_json(values) or {})
    # Serialize double-clicks and concurrent setup tabs for this user.
    frappe.db.get_value('User', frappe.session.user, 'name', for_update=True)
    saved = state()
    if step != saved['step'] or step not in STEPS[:-1]:
        frappe.throw('Setup has moved on. Reopen the guide to continue from your saved step.')
    company = saved.get('company')
    if step != 'company':
        linked('Company', company)
    if step == 'company':
        if values.company:
            company = linked('Company', values.company).name
        else:
            company = insert('Company', company_name=values.company_name, abbr=values.abbr,
                country=values.country, default_currency=values.currency).name
        saved['company'] = company
    elif step == 'worker':
        if values.employee:
            worker = linked('Employee', values.employee, company)
            if worker.status != 'Active':
                frappe.throw('Choose an active worker')
        else:
            worker = insert('Employee', first_name=values.first_name, last_name=values.last_name,
                gender=values.gender, date_of_birth=values.date_of_birth, date_of_joining=values.date_of_joining,
                company=company, status='Active', cell_number=values.cell_number)
        saved.update(employee=worker.name, worker_label=worker.employee_name)
    elif step == 'site':
        if values.site:
            site = linked('PP Site', values.site)
            project = linked('Project', site.project, company)
            if not site.is_active:
                frappe.throw('Choose an active site')
        else:
            if values.project:
                project = linked('Project', values.project, company)
            else:
                customer = linked('Customer', values.customer) if values.customer else insert('Customer',
                    customer_name=values.customer_name, customer_type='Company',
                    customer_group='Commercial', territory='All Territories')
                project = insert('Project', project_name=values.project_name, company=company, customer=customer.name)
            site = insert('PP Site', site_name=values.site_name, project=project.name,
                          site_type='Main Site', address=values.address, is_active=1)
        saved.update(site=site.name, project=project.name, site_label=site.site_name)
    elif step == 'terms':
        project = linked('Project', saved['project'], company)
        if values.contract_terms:
            terms = linked('PP Contract Terms', values.contract_terms)
            if terms.project != project.name or terms.status != 'Active':
                frappe.throw('Choose active billing terms for this project')
        else:
            if not project.customer:
                frappe.throw('Add a client to the project before setting billing terms')
            if not (values.agreement or '').strip():
                frappe.throw('Describe the client agreement before continuing')
            start = str(getdate(values.effective_start)) if values.effective_start else today()
            contract = insert('Contract', party_type='Customer', party_name=project.customer,
                start_date=start, contract_terms=values.agreement)
            terms = insert('PP Contract Terms', contract=contract.name, project=project.name,
                billing_model=values.billing_model, fixed_amount=values.fixed_amount or 0,
                currency=frappe.db.get_value('Company', company, 'default_currency'),
                effective_start=start, status='Active')
        saved['contract_terms'] = terms.name
    elif step == 'assignment':
        # Every link is revalidated by PP Assignment, including company, status,
        # rate rules and overlapping deployments. No attendance is approved here.
        assignment = insert('PP Assignment', employee=saved['employee'], site=saved['site'],
            project=saved['project'], contract_terms=saved['contract_terms'],
            start_date=values.start_date, end_date=values.end_date,
            wage_rate=values.wage_rate, client_rate=values.client_rate or 0)
        saved['assignment'] = assignment.name
    saved.update(step=STEPS[STEPS.index(step)+1], skipped=False)
    return save_state(saved)
