"""Section landing pages: live summaries and native work lists, without charts."""
import json
import frappe
from urllib.parse import quote, urlencode
from plus_point.navigation import CUSTOMER_GROUPS, PLATFORM_GROUPS


@frappe.whitelist()
def overview(section,company=None):
    # Old bookmarks continue into the consolidated finance workspace.
    if section=='Business reports' and not frappe.conf.get('pp_control_plane'):
        section='Payments and costs'
    from plus_point.dashboard import overview as dashboard
    data=dashboard(company)
    groups=PLATFORM_GROUPS if data['is_platform'] else CUSTOMER_GROUPS
    if section not in dict(groups):
        frappe.throw('Choose an available section')
    company=data['company']
    links=[]
    projects=frappe.get_list('Project',filters={'company':company,'pp_archived':0},fields=['name','customer'],limit_page_length=0) if company and not data['is_platform'] else []
    names=[p.name for p in projects]
    customers=list({p.customer for p in projects if p.customer})
    subscriptions=frappe.get_list('Subscription',filters={'company':company},pluck='name',limit_page_length=0) if data['is_platform'] and company else []
    tenants=frappe.get_list('PP Tenant',filters={'subscription':['in',subscriptions]},pluck='name',limit_page_length=0) if subscriptions else []
    for target,title in dict(groups)[section]:
        if target.startswith('Page:'):
            links.append(dict(title=title,doctype=None,path='/desk/'+target[5:]+(('?view=vehicles' if title=='Vehicles' else '?view=warehouses') if target=='Page:pp-inventory' else ''),count=None,is_report=False));continue
        if target.startswith('Report:'):
            name=target[7:]
            if frappe.get_doc('Report',name).is_permitted():
                links.append(dict(title=title,doctype=None,path='/desk/query-report/'+quote(name)+'?company='+quote(company or ''),count=None))
            continue
        if not frappe.has_permission(target,'read'):
            continue
        meta=frappe.get_meta(target)
        filters={}
        if target=='Item' and not data['is_platform']:filters['is_stock_item']=int(title=='Inventory items')
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
        path='/desk/'+frappe.scrub(target).replace('_','-')+('/view/list' if section=='Payments and costs' and not data['is_platform'] else ('?' + query if query else ''))
        links.append(dict(title=title,doctype=target,path=path,count=count))
    if section=='Inventory and transport' and not data['is_platform']:
        counts={row['title']:row['count'] for row in links}
        reservations=0
        if company:
            for target in ('PP Vehicle Booking','PP Equipment Booking'):
                if frappe.has_permission(target,'read'):
                    rows=frappe.get_list(target,filters={'company':company,'status':'Planned','end_date':['>=',frappe.utils.today()]},
                        fields=[{'COUNT':'name','as':'total'}],limit_page_length=1,order_by=None)
                    reservations+=int(rows[0].total if rows else 0)
        data['resources']=dict(items=frappe.db.count('Item',{'is_stock_item':1,'disabled':0}),warehouses=frappe.db.count('Warehouse',{'company':company,'is_group':0}),vehicles=frappe.db.count('Vehicle',{'company':company}),reservations=reservations)
    if section=='Payments and costs' and not data['is_platform']:
        from plus_point.finance_hub import summary
        data['loans']=summary(company) if company else dict(enabled=False)
        data['related_links']=[]
        if frappe.has_permission('Expense Claim','read'):
            data['related_links'].append(dict(title='Worker reimbursements',path='/desk/expense-claim/view/list'))
        data['report_links']=[]
        for name,title in [('PLUS POINT Project Finances','Event finances'),('PLUS POINT Worker Statement','Worker statements')]:
            if frappe.get_doc('Report',name).is_permitted():
                data['report_links'].append(dict(title=title,path='/desk/query-report/'+quote(name)))
    data.update(section=section,links=links)
    return data
