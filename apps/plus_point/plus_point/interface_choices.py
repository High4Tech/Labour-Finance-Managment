"""Bounded native-permission link choices for React setup and utility forms."""
import frappe
from plus_point.setup_flow import require_customer,linked

TITLES={'Company':'company_name','Employee':'employee_name','Project':'project_name','Customer':'customer_name','Country':'name','Currency':'name','Gender':'name','PP Site':'site_name','PP Contract Terms':'agreement_title','Vehicle':'license_plate','Item':'item_name','Warehouse':'warehouse_name','UOM':'name','Designation':'name'}


@frappe.whitelist()
def choices(doctype,search='',company=None,project=None):
    require_customer()
    if doctype not in TITLES:frappe.throw('Choose a supported record type.')
    if company:linked('Company',company)
    filters={}
    if doctype in ('Employee','Project'):
        if not company:return []
        filters['company']=company
    if doctype=='Employee':filters['status']='Active'
    if doctype in ('Vehicle','Warehouse'):
        if not company:return []
        filters['company']=company
        filters.update({'pp_event_enabled':1} if doctype=='Vehicle' else {'is_group':0,'disabled':0})
    if doctype=='Item':filters.update(is_stock_item=1,disabled=0)
    if doctype in ('PP Site','PP Contract Terms'):
        projects=[linked('Project',project,company).name] if project else frappe.get_list('Project',filters={'company':company},pluck='name',limit_page_length=0)
        filters['project']=['in',projects or ['']]
        filters['is_active' if doctype=='PP Site' else 'status']=1 if doctype=='PP Site' else 'Active'
    title=TITLES[doctype];text=str(search or '').strip()[:100]
    rows=frappe.get_list(doctype,filters=filters,or_filters={title:['like','%'+text+'%'],'name':['like','%'+text+'%']} if text else None,fields=list(dict.fromkeys(['name',title])),order_by=title,limit_page_length=40)
    return [dict(value=row.name,label=row.get(title) or row.name) for row in rows]


@frappe.whitelist()
def record(doctype,name,company=None):
    """Only the address/terms fields required to prefill the setup editor."""
    require_customer()
    if doctype not in ('PP Site','PP Contract Terms'):
        frappe.throw('Choose an event site or client billing agreement.')
    doc=linked(doctype,name)
    linked('Project',doc.project,company)
    fields=('site_name','country','state','city','address_line1','address_line2','postal_code','latitude','longitude') if doctype=='PP Site' else ('billing_model','fixed_amount')
    result={key:doc.get(key) for key in fields}
    if doctype=='PP Contract Terms':result['agreement']=linked('Contract',doc.contract).contract_terms
    return result
