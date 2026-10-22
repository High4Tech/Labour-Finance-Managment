"""Permission-scoped worker dashboard from allocations, attendance and settlements."""
from collections import defaultdict
from decimal import Decimal
import frappe
from frappe.utils import getdate,today,add_days
from plus_point.setup_flow import require_customer,linked
from plus_point.finance import money


@frappe.whitelist()
def overview(employee,days=91):
    require_customer();worker=linked('Employee',employee);company=linked('Company',worker.company)
    days=frappe.utils.cint(days)
    if days not in (91,366):frappe.throw('Choose the last 3 months or the last year.')
    end=getdate(today());start=getdate(add_days(end,1-days))
    work=frappe.get_list('PP Work Entry',filters={'employee':employee,'status':'Approved'},
        fields=['name','work_date','project','site','units','wage_amount'],order_by='work_date desc,name',limit_page_length=0)
    # Follow parent company permissions before including any source in the profile.
    projects={r.name:r for r in frappe.get_list('Project',filters={'company':company.name},fields=['name','project_name','status'],limit_page_length=0)}
    work=[r for r in work if r.project in projects]
    totals=defaultdict(Decimal);earned=Decimal(0)
    for row in work:
        if getdate(row.work_date)<=end:totals[str(row.work_date)]+=Decimal(str(row.units))
        earned+=money(row.wage_amount)
    paid=sum((money(r.amount) for r in frappe.get_list('PP Wage Settlement',filters={'employee':employee,'project':['in',list(projects) or ['']],'docstatus':1},fields=['amount'],limit_page_length=0)),Decimal(0))
    allocations=frappe.get_list('PP Assignment',filters={'employee':employee,'project':['in',list(projects) or ['']]},
        fields=['name','project','site','start_date','end_date','wage_rate'],order_by='start_date desc',limit_page_length=0)
    sites={r.name:r.site_name for r in frappe.get_list('PP Site',filters={'project':['in',list(projects) or ['']]},fields=['name','site_name'],limit_page_length=0)}
    expected=set()
    for row in allocations:
        first=max(start,getdate(row.start_date),getdate(worker.date_of_joining or row.start_date))
        last=min(end,getdate(row.end_date or end),getdate(worker.relieving_date or end))
        for offset in range(max(0,(last-first).days+1)):expected.add(str(add_days(first,offset)))
    registers=frappe.get_list('PP Daily Register',filters={'project':['in',list(projects) or ['']],'docstatus':0,'work_date':['between',[start,end]]},fields=['name','work_date'],limit_page_length=0)
    dates={r.name:str(r.work_date) for r in registers}
    draft=frappe.get_all('PP Register Line',filters={'parent':['in',list(dates) or ['']],'parenttype':'PP Daily Register','employee':employee},fields=['parent','attendance_status'])
    pending_dates={dates[r.parent] for r in draft if r.attendance_status not in ('Not marked','',None)}
    calendar=[]
    for offset in range(days):
        day=str(add_days(start,offset));units=totals.get(day)
        state=('Present' if units>=1 else 'Half day' if units>0 else 'Absent') if units is not None else 'Pending approval' if day in pending_dates else 'Not marked' if day in expected else 'No scheduled work'
        calendar.append(dict(date=day,status=state,units=str(units) if units is not None else None))
    full=sum(value>=1 for value in totals.values());half=sum(0<value<1 for value in totals.values());absent=sum(value==0 for value in totals.values())
    longest=current=0
    for row in calendar:
        current=current+1 if row['units'] is not None and Decimal(row['units'])>0 else 0;longest=max(longest,current)
    plan_rows=frappe.get_list('PP Event Plan',filters={'company':company.name},fields=['name','project','event_name'],limit_page_length=0)
    plans={r.project:r.name for r in plan_rows};titles={r.project:r.event_name for r in plan_rows}
    assignments=[dict(plan=plans.get(r.project),name=r.name,event=titles.get(r.project,projects[r.project].project_name),project=r.project,site=sites.get(r.site,r.site),
        start=str(r.start_date),end=str(r.end_date or ''),wage_rate=str(money(r.wage_rate))) for r in allocations if projects[r.project].status=='Open' and (not r.end_date or getdate(r.end_date)>=end)]
    history=[dict(name=r.name,date=str(r.work_date),event=projects[r.project].project_name,site=sites.get(r.site,r.site),
        status='Present' if Decimal(str(r.units))==1 else 'Half day' if Decimal(str(r.units))>0 else 'Absent',amount=str(money(r.wage_amount))) for r in work[:20]]
    assigned=any(getdate(r['start'])<=end for r in assignments)
    return dict(image=worker.image or '',allocation_status='Assigned' if assigned else 'Scheduled' if assignments else 'Available',employee=employee,title=worker.employee_name,designation=worker.designation or '',department=worker.department or '',
        company=company.company_name,company_id=company.name,currency=company.default_currency,status=worker.status,
        phone=worker.cell_number or '',email=worker.personal_email or '',joining=str(worker.date_of_joining or ''),
        full_days=full,half_days=half,absent_days=absent,paid_days=str(sum(totals.values(),Decimal(0))),
        attendance_rate=round(100*(full+half*.5)/(full+half+absent),1) if full+half+absent else None,
        earned=str(money(earned)),paid=str(money(paid)),outstanding=str(money(earned-paid)),
        assignments=assignments,history=history,history_count=len(work),calendar=calendar,start=str(start),end=str(end),longest_streak=longest)
