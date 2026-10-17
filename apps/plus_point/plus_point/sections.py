"""Section landing pages: live summaries and native work lists, without charts."""
import json
import frappe
from urllib.parse import quote, urlencode
from plus_point.navigation import CUSTOMER_GROUPS, PLATFORM_GROUPS


@frappe.whitelist()
def overview(section,company=None):
    from plus_point.dashboard import overview as dashboard
    data=dashboard(company)
    groups=PLATFORM_GROUPS if data['is_platform'] else CUSTOMER_GROUPS
    if section not in dict(groups):
        frappe.throw('Choose an available section')
    company=data['company']
    links=[]
    projects=frappe.get_list('Project',filters={'company':company},fields=['name','customer'],limit_page_length=0) if company and not data['is_platform'] else []
    names=[p.name for p in projects]
    customers=list({p.customer for p in projects if p.customer})
    subscriptions=frappe.get_list('Subscription',filters={'company':company},pluck='name',limit_page_length=0) if data['is_platform'] and company else []
    tenants=frappe.get_list('PP Tenant',filters={'subscription':['in',subscriptions]},pluck='name',limit_page_length=0) if subscriptions else []
    for target,title in dict(groups)[section]:
        if target.startswith('Report:'):
            name=target[7:]
            if frappe.get_doc('Report',name).is_permitted():
                links.append(dict(title=title,doctype=None,path='/desk/query-report/'+quote(name)+'?company='+quote(company or ''),count=None))
            continue
        if not frappe.has_permission(target,'read'):
            continue
        meta=frappe.get_meta(target)
        filters={}
        if meta.has_field('company'):
            filters['company']=company
        elif meta.has_field('project') and not data['is_platform']:
            filters['project']=['in',names]
        elif target=='Customer' and not data['is_platform']:
            filters['name']=['in',customers]
        elif target=='Contract' and not data['is_platform']:
            filters.update(party_type='Customer',party_name=['in',customers])
        elif target=='PP Tenant' and data['is_platform']:
            filters['name']=['in',tenants]
        elif target=='PP Support Request' and data['is_platform']:
            filters['tenant']=['in',tenants]
        if company:
            counts=frappe.get_list(target,filters=filters,fields=[{'COUNT':'name','as':'total'}],limit_page_length=1,order_by=None)
            count=counts[0].total if counts else 0
        else:
            count=0
        query=urlencode({key:json.dumps(value) if isinstance(value,list) else value for key,value in filters.items()}) if company else ''
        path='/desk/'+frappe.scrub(target).replace('_','-')+('?' + query if query else '')
        links.append(dict(title=title,doctype=target,path=path,count=count))
    data.update(section=section,links=links)
    return data
