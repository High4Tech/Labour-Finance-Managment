"""Approved wage balances and confirmation cadence. Never auto-disburse money."""
from collections import defaultdict
from decimal import Decimal
import frappe
from frappe.utils import add_days, getdate, get_first_day, today
from plus_point.finance import money
from plus_point.finance_hub import company_scope


def payment_items(items):
    """A bounded list of event/worker snapshots, never an arbitrary payment amount."""
    items=frappe.parse_json(items)
    if not isinstance(items,list) or not 1<=len(items)<=200:
        frappe.throw('Select between 1 and 200 worker balances.')
    result=[];seen=set()
    for row in items:
        if not isinstance(row,dict) or not all(isinstance(row.get(k),str) and row[k] for k in ('event','employee')) or 'balance' not in row:
            frappe.throw('Review each selected worker and event balance before recording payments.')
        key=(row['event'],row['employee'])
        if key in seen:frappe.throw('Select each worker balance once per event.')
        seen.add(key);amount=money(row['balance'])
        if amount<=0:frappe.throw('Choose workers with approved outstanding wages.')
        result.append(dict(event=key[0],employee=key[1],balance=str(amount)))
    return result


def payment_events(items,business):
    from plus_point.record_actions import document
    events={}
    for name in sorted({r['event'] for r in items}):
        event=document('PP Event Plan',name)
        if event.company!=business.name:frappe.throw('Choose worker balances from the selected company only.',frappe.PermissionError)
        events[name]=event
    return events


@frappe.whitelist()
def review_payments(items,company=None):
    from plus_point.record_actions import event_review
    business=company_scope(company);items=payment_items(items);events=payment_events(items,business)
    reviews={name:event_review(name) for name in events};rows=[]
    for item in items:
        review=reviews[item['event']]
        if not review['can_pay']:frappe.throw('You do not have permission to record worker payments.',frappe.PermissionError)
        worker=next((r for r in review['workers'] if r['employee']==item['employee']),None)
        if not worker:frappe.throw('Choose workers assigned to the selected events.',frappe.PermissionError)
        if money(worker['outstanding'])!=money(item['balance']):frappe.throw('A wage balance changed. Refresh the list and review the selected workers again.')
        rows.append(dict(item,worker=worker['worker'],event_name=review['title']))
    return dict(rows=rows,currency=business.default_currency,accounts=next(iter(reviews.values()))['accounts'],
        total=str(sum((money(r['balance']) for r in rows),Decimal(0))))


@frappe.whitelist(methods=['POST'])
def record_payments(items,account,posting_date,reference,company=None):
    """All selected events post together, or none do; native retry protection remains."""
    from plus_point.record_actions import settle_event_crew
    from plus_point.budget import lock_project
    business=company_scope(company);items=payment_items(items);events=payment_events(items,business)
    # Stable lock order across the entire batch prevents cross-event lock inversions.
    for project in sorted({e.project for e in events.values()}):lock_project(project)
    for employee in sorted({r['employee'] for r in items}):frappe.db.get_value('Employee',employee,'name',for_update=True)
    frappe.db.savepoint('pp_wage_payment_batch');payments=[]
    try:
        for name in sorted(events):
            selected=[r for r in items if r['event']==name]
            result=settle_event_crew(name=name,employees=[r['employee'] for r in selected],account=account,
                posting_date=posting_date,reference=reference,balances={r['employee']:r['balance'] for r in selected})
            payments.extend(result['payments'])
    except Exception:
        frappe.db.rollback(save_point='pp_wage_payment_batch');raise
    return dict(payments=payments)


def due_cutoff(event, day):
    """Daily closes yesterday; monthly closes the prior month, plus final event pay."""
    day=getdate(day)
    cycle=event.get('wage_payment_cycle') or 'Manual'
    if cycle=='Manual': return None
    cutoff=getdate(add_days(day,-1)) if cycle=='Daily' else getdate(add_days(get_first_day(day),-1))
    if getdate(event.end_date)<day: cutoff=max(cutoff,getdate(event.end_date))
    return min(cutoff,getdate(event.end_date))


@frappe.whitelist()
def overview(company=None, event=None, search='', page=1):
    business=company_scope(company)
    for dt in ('Employee','PP Work Entry','PP Wage Settlement','PP Loan Recovery'):
        frappe.has_permission(dt,'read',throw=True)
    events=frappe.get_list('PP Event Plan',filters={'company':business.name},
        fields=['name','event_name','project','start_date','end_date','wage_payment_cycle'],order_by='modified desc',limit_page_length=0)
    if event and event not in {e.name for e in events}: frappe.throw('Choose an event you can access.',frappe.PermissionError)
    selected=[e for e in events if not event or e.name==event]
    projects=[e.project for e in selected] or ['']
    workers={w.name:w for w in frappe.get_list('Employee',filters={'company':business.name},fields=['name','employee_name','image'],limit_page_length=0)}
    event_map={e.project:e for e in selected}
    totals=defaultdict(lambda:dict(earned=Decimal(0),paid=Decimal(0),deducted=Decimal(0),due_earned=Decimal(0)))
    # One grouped query per ledger; no per-worker balance calls or cached money.
    work=frappe.get_list('PP Work Entry',filters={'project':['in',projects],'status':'Approved'},
        fields=['project','employee','work_date',{'SUM':'wage_amount','as':'total'}],group_by='project,employee,work_date',order_by=None,limit_page_length=0)
    for row in work:
        if row.employee not in workers: continue
        value=totals[(row.project,row.employee)];value['earned']+=money(row.total)
        cutoff=due_cutoff(event_map[row.project],today())
        if cutoff and getdate(row.work_date)<=cutoff:value['due_earned']+=money(row.total)
    for dt,key in (('PP Wage Settlement','paid'),('PP Loan Recovery','deducted')):
        for row in frappe.get_list(dt,filters={'project':['in',projects],'docstatus':1},fields=['project','employee',{'SUM':'amount','as':'total'}],group_by='project,employee',order_by=None,limit_page_length=0):
            if row.employee in workers:totals[(row.project,row.employee)][key]+=money(row.total)
    for row in frappe.get_list('PP Assignment',filters={'project':['in',projects]},fields=['project','employee'],limit_page_length=0):
        if row.employee in workers:totals[(row.project,row.employee)]
    rows=[];query=str(search or '').strip().casefold()[:100]
    summary={k:Decimal(0) for k in ('earned','paid','deducted','outstanding','due')}
    for (project,employee),v in totals.items():
        item=event_map[project];worker=workers[employee]
        if query and query not in (worker.employee_name+' '+employee+' '+item.event_name).casefold():continue
        outstanding=max(Decimal(0),v['earned']-v['paid']-v['deducted'])
        due=max(Decimal(0),v['due_earned']-v['paid']-v['deducted'])
        status='No approved wages' if not v['earned'] else 'Paid' if not outstanding else 'Partly paid' if v['paid'] or v['deducted'] else 'Unpaid'
        values=dict(v,outstanding=outstanding,due=due)
        for key in summary:summary[key]+=values[key]
        rows.append(dict(employee=employee,worker=worker.employee_name,image=worker.image,event=item.name,event_name=item.event_name,
            cycle=item.wage_payment_cycle or 'Manual',status=status,**{k:str(v) for k,v in values.items()}))
    rows.sort(key=lambda r:(-float(r['due']),-float(r['outstanding']),r['worker'],r['event_name']))
    page=max(1,frappe.utils.cint(page));size=25
    return dict(currency=business.default_currency,today=today(),rows=rows[(page-1)*size:page*size],total=len(rows),page=page,
        pages=max(1,(len(rows)+size-1)//size),summary={k:str(v) for k,v in summary.items()},
        events=[dict(name=e.name,title=e.event_name,cycle=e.wage_payment_cycle or 'Manual') for e in events],
        can_pay=all(frappe.has_permission(dt,mode) for dt in ('Payment Entry','PP Wage Settlement') for mode in ('create','submit')))


@frappe.whitelist(methods=['POST'])
def set_cycle(event,cycle):
    from plus_point.events import plan_doc
    doc=plan_doc(event,True)
    if cycle not in ('Manual','Daily','Monthly'):frappe.throw('Choose Manual, Daily or Monthly payment confirmation.')
    doc.wage_payment_cycle=cycle;doc.save()
    return dict(cycle=cycle)
