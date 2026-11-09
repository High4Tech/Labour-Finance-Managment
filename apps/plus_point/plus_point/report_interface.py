"""React report transport; the installed native reporting engine authorizes reads."""
import frappe
from plus_point.finance_hub import company_scope

REPORTS=('PLUS POINT Project Finances','PLUS POINT Worker Statement')


@frappe.whitelist()
def options():
    business=company_scope()
    return dict(company=business.name,currency=business.default_currency,
        projects=frappe.get_list('Project',filters={'company':business.name},fields=['name','project_name'],order_by='modified desc',limit_page_length=500),
        workers=frappe.get_list('Employee',filters={'company':business.name},fields=['name','employee_name'],order_by='employee_name',limit_page_length=2000),
        clients=frappe.get_list('Customer',filters={'disabled':0},fields=['name','customer_name'],order_by='customer_name',limit_page_length=500))


@frappe.whitelist()
def run(name,filters=None):
    if name not in REPORTS:frappe.throw('Choose a company business report.')
    business=company_scope();values=frappe.parse_json(filters) or {}
    allowed={'employee','view','customer','project','status','from_date','to_date','display_currency','include_archived'}
    if not isinstance(values,dict) or set(values)-allowed:frappe.throw('Use the supported report filters.')
    values['company']=business.name
    from frappe.desk.query_report import run as native_run
    return native_run(report_name=name,filters=values,ignore_prepared_report=True)
