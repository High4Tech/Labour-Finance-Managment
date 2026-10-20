"""Suggest saved project details only; never guess a new event's prices."""
import frappe
from plus_point.setup_flow import require_customer, linked


@frappe.whitelist()
def context(project=None,site=None,company=None):
    require_customer();result={}
    if site:
        venue=linked('PP Site',site)
        if project and venue.project!=project:frappe.throw('Choose a site from this event project.')
        project=venue.project;result['site']=venue.name
    if project:
        job=linked('Project',project);company=job.company
        result.update(project=job.name,company=company,customer=job.customer,
            start_date=job.expected_start_date,end_date=job.expected_end_date)
        plans=frappe.get_list('PP Event Plan',filters={'project':project},fields=['name','start_date','end_date','wage_rate','client_rate','contract_terms'],limit_page_length=2)
        if len(plans)==1:
            result.update({key:plans[0].get(key) for key in ('start_date','end_date','wage_rate','client_rate','contract_terms')})
        else:
            terms=frappe.get_list('PP Contract Terms',filters={'project':project,'status':'Active'},pluck='name',limit_page_length=2)
            if len(terms)==1:result['contract_terms']=terms[0]
        if not site:
            sites=frappe.get_list('PP Site',filters={'project':project,'is_active':1},pluck='name',limit_page_length=2)
            if len(sites)==1:result['site']=sites[0]
    if company:
        doc=linked('Company',company);result.update(company=company,country=doc.country,currency=doc.pp_invoice_currency or doc.default_currency)
        warehouses=frappe.get_list('Warehouse',filters={'company':company,'is_group':0,'disabled':0},pluck='name',limit_page_length=2)
        if len(warehouses)==1:result['warehouse']=warehouses[0]
    return result
