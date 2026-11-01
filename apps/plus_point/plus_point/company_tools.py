"""Bounded, permission-scoped company search and personal notifications."""
from urllib.parse import quote
import frappe
from frappe.utils import strip_html
from plus_point.finance_hub import company_scope


SEARCH = {
    'agreements': ('PP Contract Terms', 'agreement_title', '/desk/pp-agreements?record='),
    'events': ('PP Event Plan', 'event_name', '/desk/pp-event-plans?record='),
    'workers': ('Employee', 'employee_name', '/desk/employee/'),
    'inventory': ('Item', 'item_name', '/desk/pp-inventory?view=equipment&record='),
    'warehouses': ('Warehouse', 'warehouse_name', '/desk/pp-inventory?view=warehouses&record='),
    'vehicles': ('Vehicle', 'license_plate', '/desk/pp-inventory?view=vehicles&record='),
    'clients': ('Customer', 'customer_name', '/desk/customer/'),
}


@frappe.whitelist()
def search(kind, text='', company=None):
    business = company_scope(company)
    if kind not in SEARCH:
        frappe.throw('Choose a supported search.', frappe.ValidationError)
    dt, title, route = SEARCH[kind]
    filters = {}
    if kind in ('events', 'workers', 'warehouses', 'vehicles'):
        filters['company'] = business.name
    elif kind == 'inventory':
        filters['is_stock_item'] = 1
    elif kind == 'agreements':
        projects = frappe.get_list('Project', filters={'company': business.name}, pluck='name', limit_page_length=0)
        filters.update(project=['in', projects or ['']], event_basis=0)
    text = str(text or '').strip()[:100]
    # Filter text is a bound query value; no raw SQL or privileged link search.
    or_filters = {title: ['like', '%'+text+'%'], 'name': ['like', '%'+text+'%']} if text else None
    rows = frappe.get_list(dt, filters=filters, or_filters=or_filters,
        fields=['name', title], order_by='modified desc', limit_page_length=20)
    return [dict(name=r.name, title=r.get(title) or r.name, href=route+quote(r.name)) for r in rows]


@frappe.whitelist()
def activity(company=None, page=1, mode='All'):
    business = company_scope(company)
    page = max(1, min(1000, frappe.utils.cint(page)))
    filters = {'for_user': frappe.session.user}
    if mode == 'Unread':
        filters['read'] = 0
    notifications = frappe.get_list('Notification Log', filters=filters,
        fields=['name', 'subject', 'read', 'creation', 'document_type', 'document_name'],
        order_by='creation desc', limit_start=(page-1)*25, limit_page_length=26)
    rows = []
    kinds = {'PP Contract Terms': 'agreements', 'PP Event Plan': 'jobs', 'Employee': 'workers',
        'PP Daily Register': 'attendance', 'PP Wage Settlement': 'payments', 'PP Worker Loan': 'loans'}
    for r in notifications[:25]:
        href = None
        if r.document_type and r.document_name and frappe.db.exists(r.document_type, r.document_name):
            doc = frappe.get_doc(r.document_type, r.document_name)
            if doc.has_permission('read'):
                kind = {'PP Contract Terms': 'agreements', 'PP Event Plan': 'events', 'Employee': 'workers'}.get(r.document_type)
                href = SEARCH[kind][2]+quote(r.document_name) if kind else '/desk/'+frappe.scrub(r.document_type).replace('_','-')+'/'+quote(r.document_name)
        rows.append(dict(name=r.name, title=strip_html(r.subject or ''), date=str(r.creation),
            read=bool(r.read), entity=kinds.get(r.document_type, 'bell'), href=href))
    # Company activity includes visible business records even when no personal alert exists.
    feed = []
    if page == 1 and mode == 'All':
        projects = frappe.get_list('Project', filters={'company': business.name}, fields=['name','project_name'], limit_page_length=0)
        names = [p.name for p in projects] or ['']
        titles = {p.name:p.project_name for p in projects}
        for dt, field, label, entity, route, condition in (
            ('PP Contract Terms','agreement_title','Agreement added','agreements',SEARCH['agreements'][2],{'project':['in',names],'event_basis':0}),
            ('PP Event Plan','event_name','Event added','jobs',SEARCH['events'][2],{'company':business.name}),
            ('Employee','employee_name','Worker added','workers',SEARCH['workers'][2],{'company':business.name}),
            ('PP Daily Register','project','Attendance updated','attendance','/desk/pp-daily-register?record=',{'project':['in',names]})):
            if not frappe.has_permission(dt,'read'): continue
            for r in frappe.get_list(dt, filters=condition, fields=['name',field,'modified'], order_by='modified desc', limit_page_length=20):
                feed.append(dict(title=r.get(field) if dt!='PP Daily Register' else titles.get(r.project,r.project), label=label,
                    entity=entity, date=str(r.modified), href=route+quote(r.name)))
        feed.sort(key=lambda r:r['date'],reverse=True)
    return dict(notifications=rows, feed=feed[:25], page=page, more=len(notifications)>25)


@frappe.whitelist(methods=['POST'])
def mark_read(names):
    company_scope()
    names=frappe.parse_json(names)
    if not isinstance(names,list) or len(names)>25: frappe.throw('Select up to 25 notifications.')
    rows=frappe.get_list('Notification Log',filters={'name':['in',names or ['']],'for_user':frappe.session.user},pluck='name',limit_page_length=25)
    if set(rows)!=set(names): frappe.throw('Choose your own notifications only.',frappe.PermissionError)
    for name in rows: frappe.db.set_value('Notification Log',name,'read',1,update_modified=False)
    unread=frappe.get_list('Notification Log',filters={'for_user':frappe.session.user,'read':0},fields=[{'COUNT':'name','as':'total'}],order_by=None,limit_page_length=1)
    return dict(updated=len(rows),unread=frappe.utils.cint(unread[0].total) if unread else 0)
