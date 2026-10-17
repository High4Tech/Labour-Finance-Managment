"""Approved operational activity, grouped in the database and scoped to readable projects."""
from collections import defaultdict
from decimal import Decimal

import frappe
from frappe.utils import add_days, getdate, today

from plus_point.finance import money
from plus_point.setup_flow import linked, require_customer


def client_activity(company, customer=None):
    projects = frappe.get_list('Project', filters={'company':company, **({'customer':customer} if customer else {})},
        fields=['name','project_name','customer'], limit_page_length=0)
    clients = frappe.get_list('Customer', filters={'name':['in',list({p.customer for p in projects if p.customer})]},
        fields=['name','customer_name'], order_by='customer_name', limit_page_length=0) if projects else []
    project_client = {p.name:p.customer for p in projects}
    days = [str(add_days(today(), offset)) for offset in range(-90,1)]
    names = list(project_client)
    # Project IDs have already passed native permissions. Aggregate before transfer
    # rather than returning every worker-day to the browser for a heatmap.
    rows = frappe.db.sql('''select project, work_date, sum(units) units, count(*) entries,
        count(distinct employee) workers, sum(wage_amount) wages
        from `tabPP Work Entry` where project in %(projects)s and status='Approved'
        and work_date between %(start)s and %(end)s group by project,work_date''',
        {'projects':names,'start':days[0],'end':days[-1]}, as_dict=True) if names else []
    grouped = defaultdict(lambda:defaultdict(lambda:dict(units=Decimal(0),entries=0,wages=Decimal(0))))
    overall = defaultdict(lambda:dict(units=Decimal(0),entries=0,wages=Decimal(0)))
    for row in rows:
        for target in (grouped[project_client[row.project]][str(row.work_date)],overall[str(row.work_date)]):
            target['units'] += Decimal(str(row.units))
            target['entries'] += row.entries
            target['wages'] += Decimal(str(row.wages))
    output = []
    for client in clients:
        cells = [dict(date=day, units=str(grouped[client.name][day]['units']),
            entries=grouped[client.name][day]['entries']) for day in days]
        active = [row for row in cells if Decimal(row['units'])>0]
        longest=current=0
        for row in cells:
            current=current+1 if Decimal(row['units'])>0 else 0
            longest=max(longest,current)
        output.append(dict(name=client.name,title=client.customer_name,
            projects=sum(p.customer==client.name for p in projects), active_days=len(active),
            units=str(sum((Decimal(row['units']) for row in cells),Decimal(0))),
            longest_streak=longest,last_work=active[-1]['date'] if active else None,days=cells))
    output.sort(key=lambda row:(row['last_work'] or '',row['title']),reverse=True)
    return dict(start=days[0],end=days[-1],client_count=len(output),clients=output if customer else output[:6],
        daily=[dict(date=day,units=str(overall[day]['units']),wages=str(money(overall[day]['wages'])),entries=overall[day]['entries']) for day in days])


@frappe.whitelist()
def customer_summary(customer, company=None):
    require_customer()
    linked('Customer',customer)
    companies = frappe.get_list('Company',pluck='name',limit_page_length=0)
    if company and company not in companies:
        frappe.throw('Choose a company you can access',frappe.PermissionError)
    if not company:
        projects=frappe.get_list('Project',filters={'customer':customer,'company':['in',companies]},
            fields=['company'],limit_page_length=0)
        company=next((p.company for p in projects),companies[0] if companies else None)
    return dict(company=company,**(client_activity(company,customer) if company else dict(clients=[],daily=[])))


@frappe.whitelist()
def day_detail(company, customer, day):
    require_customer()
    linked('Company',company)
    linked('Customer',customer)
    date=getdate(day)
    if date<getdate(add_days(today(),-90)) or date>getdate(today()):
        frappe.throw('Choose a day in the displayed 91-day activity period')
    projects=frappe.get_list('Project',filters={'company':company,'customer':customer},pluck='name',limit_page_length=0)
    rows=frappe.get_list('PP Work Entry',filters={'project':['in',projects],'status':'Approved','work_date':date},
        fields=['name','employee','site','units','wage_amount'],order_by='employee',limit_page_length=0) if projects else []
    employees={r.name:r.employee_name for r in frappe.get_list('Employee',filters={'name':['in',list({r.employee for r in rows})]},
        fields=['name','employee_name'],limit_page_length=0)} if rows else {}
    sites={r.name:r.site_name for r in frappe.get_list('PP Site',filters={'name':['in',list({r.site for r in rows})]},
        fields=['name','site_name'],limit_page_length=0)} if rows else {}
    for row in rows:
        row.update(worker=employees.get(row.employee,row.employee),site_title=sites.get(row.site,row.site))
    return dict(date=str(date),rows=rows,worker_days=str(sum((Decimal(str(r.units)) for r in rows),Decimal(0))))
