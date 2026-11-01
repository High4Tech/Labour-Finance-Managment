"""Bounded read-only projections for the Figma overview. Native records own every value."""
from collections import defaultdict
from decimal import Decimal
from urllib.parse import quote

import frappe
from frappe.utils import add_days, cint, getdate, today
from frappe.query_builder.functions import Sum
from plus_point.dashboard_analytics import scope
from plus_point.finance import money


def dates(start=None, end=None):
    end = getdate(end or today())
    start = getdate(start or add_days(end, -29))
    if end < start or (end-start).days > 365:
        frappe.throw('Choose a date range of up to 366 days, with the end on or after the start.')
    return start, end


@frappe.whitelist()
def view(company, start=None, end=None, search='', page=1, event_status='Active', worker_status='All', display_currency=None):
    projects = scope(company)  # Manager authorization, company access and archive filtering.
    start, end = dates(start, end)
    if event_status not in ('All', 'Active', 'Upcoming') or worker_status not in ('All', 'Available', 'Assigned', 'Inactive'):
        frappe.throw('Choose an available status filter.')
    page = max(1, min(100000, cint(page)))
    names = [p.name for p in projects] or ['']
    project_map = {p.name: p for p in projects}
    currency = frappe.db.get_value('Company', company, 'default_currency')
    employees = frappe.get_list('Employee', filters={'company': company},
        fields=['name', 'employee_name', 'designation', 'image', 'status', 'pp_reference'], order_by='employee_name,name', limit_page_length=0)
    assignments = frappe.get_list('PP Assignment', filters={'project': ['in', names]},
        fields=['employee', 'start_date', 'end_date', 'project'], limit_page_length=0)
    plans = frappe.get_list('PP Event Plan', filters={'company': company, 'project': ['in', names]},
        fields=['name', 'event_name', 'project', 'start_date', 'end_date', 'planning_state', 'modified', 'creation'], limit_page_length=0)
    event_titles = {p.project: p.event_name for p in plans}
    draft_projects = {p.project for p in plans if p.planning_state == 'Draft'}
    assigned = {a.employee for a in assignments if a.project not in draft_projects and
        project_map[a.project].status != 'Cancelled' and getdate(a.start_date) <= getdate(today()) <= getdate(a.end_date or '9999-12-31')}
    loans = frappe.get_list('PP Worker Loan', filters={'company': company, 'docstatus': 1},
        fields=['name', 'employee', 'amount', 'loan_date'], limit_page_length=0)
    recoveries = frappe.get_list('PP Loan Recovery', filters={'company': company, 'docstatus': 1},
        fields=['loan', 'employee', 'amount', 'project'], limit_page_length=0)
    recovered = defaultdict(Decimal)
    for r in recoveries: recovered[r.loan] += money(r.amount)
    loan_balances = defaultdict(Decimal)
    for loan in loans: loan_balances[loan.employee] += max(Decimal(0), money(loan.amount)-recovered[loan.name])
    # Match the financial report: an unlinked event is not part of agreement finances.
    linked_projects = set(frappe.get_list('PP Contract Terms', filters={'project': ['in', names]}, pluck='project', limit_page_length=0))
    unlinked_projects = set(frappe.get_list('PP Event Plan', filters={'project': ['in', names], 'contract_terms': ['is', 'not set']}, pluck='project', limit_page_length=0))
    financial_projects = linked_projects - unlinked_projects
    financial_names = list(financial_projects) or ['']
    earned = frappe.get_list('PP Work Entry', filters={'project': ['in', financial_names], 'status': 'Approved'},
        fields=['employee', Sum(frappe.qb.DocType('PP Work Entry').wage_amount).as_('amount')], group_by='employee', limit_page_length=0)
    paid = frappe.get_list('PP Wage Settlement', filters={'project': ['in', financial_names], 'docstatus': 1},
        fields=['employee', Sum(frappe.qb.DocType('PP Wage Settlement').amount).as_('amount')], group_by='employee', limit_page_length=0)
    wages = defaultdict(Decimal)
    for rows, sign in ((earned, 1), (paid, -1), ([r for r in recoveries if r.project in financial_projects], -1)):
        for r in rows: wages[r.employee] += money(r.amount)*sign
    filtered = []
    search = str(search or '').strip().casefold()[:100]
    for e in employees:
        status = 'Inactive' if e.status != 'Active' else 'Assigned' if e.name in assigned else 'Available'
        if worker_status != 'All' and status != worker_status: continue
        if search and search not in ' '.join(str(e.get(k) or '') for k in ('employee_name', 'designation', 'name', 'pp_reference')).casefold(): continue
        filtered.append(dict(name=e.name, title=e.employee_name, designation=e.designation or '', image=e.image,
            reference=e.pp_reference or e.name, status=status, wages_unpaid=str(money(max(Decimal(0), wages[e.name]))), loan=str(money(loan_balances[e.name]))))
    total = len(filtered); pages = max(1, (total+4)//5); page = min(page, pages)
    from plus_point.events import lifecycle
    events = []
    for p in plans:
        status = lifecycle(p, cancelled=project_map[p.project].status == 'Cancelled')
        if status not in ('Active', 'Upcoming') or event_status != 'All' and status != event_status: continue
        events.append(dict(name=p.name, title=p.event_name, status=status, start=str(p.start_date), end=str(p.end_date), href='/desk/pp-event-plans?record='+quote(p.name)))
    events.sort(key=lambda r: (r['status'] != 'Active', r['start'], r['name']))
    from plus_point.operations import coverage
    for event in events[:3]:
        rows = coverage(frappe.get_doc('PP Event Plan', event['name']))
        planned = sum(r['planned'] for r in rows)
        covered = sum(min(r['planned'], r['assigned']) for r in rows)
        event.update(progress=round(covered/planned*100, 1) if planned else 0, planned=planned, covered=covered)
    terms = frappe.get_list('PP Contract Terms', filters={'project': ['in', names]},
        fields=['name', 'project', 'billing_model', 'pp_daily_checkpoints', 'pp_agreement_rate', 'event_basis', 'governing_agreement', 'creation', 'modified'], limit_page_length=0)
    term_map = {t.name: t for t in terms}
    milestones = frappe.get_list('PP Milestone', filters={'contract_terms': ['in', list(term_map) or ['']], 'status': ['!=', 'Invoiced']},
        fields=['name', 'contract_terms', 'milestone_title', 'due_date', 'amount', 'status'], limit_page_length=0)
    upcoming = [dict(name=m.name, title=m.milestone_title, due=str(m.due_date) if m.due_date else '', amount=str(money(m.amount)),
        status=m.status, agreement=m.contract_terms, href='/desk/pp-agreements?record='+quote(m.contract_terms)+'&tab=milestones') for m in milestones]
    for t in terms:
        for row in frappe.parse_json(t.pp_daily_checkpoints or '[]'):
            if row.get('invoice'): continue
            # A future checkpoint has no earned amount until approved attendance exists.
            upcoming.append(dict(name=row.get('id'), title=row.get('title') or 'Daily payment', due=row.get('due_date') or '', amount=None,
                status='Scheduled', agreement=t.name, href='/desk/pp-agreements?record='+quote(t.governing_agreement or t.name)+'&tab=milestones'))
    upcoming.sort(key=lambda r: (r['due'] or '9999', r['title']))
    sites = frappe.get_list('PP Site', filters={'project': ['in', names]}, fields=['name', 'site_name'], limit_page_length=0)
    site_map = {s.name: s.site_name for s in sites}
    registers = frappe.get_list('PP Daily Register', filters={'project': ['in', names], 'work_date': ['between', [start, end]]},
        fields=['name', 'project', 'site', 'work_date', 'docstatus', 'modified', 'creation'], order_by='work_date desc, modified desc', limit_page_length=0)
    register_map = {r.name: r for r in registers}
    lines = frappe.get_list('PP Register Line', parent_doctype='PP Daily Register', filters={'parent': ['in', list(register_map) or ['']]},
        fields=['parent', 'attendance_status', 'units'], limit_page_length=0)
    daily = defaultdict(lambda: [Decimal(0), 0])
    for line in lines:
        register = register_map[line.parent]
        if register.docstatus != 1: continue
        daily[str(register.work_date)][0] += Decimal(str(line.units or 0))
        daily[str(register.work_date)][1] += 1
    chart = [dict(date=str(add_days(start, i)), present=str(daily[str(add_days(start,i))][0]), total=daily[str(add_days(start,i))][1]) for i in range((end-start).days+1)]
    count = sum(r['total'] for r in chart); present = sum((Decimal(r['present']) for r in chart), Decimal(0))
    work = frappe.get_list('PP Work Entry', filters={'project': ['in', financial_names], 'status': 'Approved', 'work_date': ['between', [start, end]]},
        fields=['work_date', 'wage_amount', 'billable_amount', 'contract_terms'], limit_page_length=0)
    series = {r['date']: dict(date=r['date'], revenue=Decimal(0), wages=Decimal(0), loans=Decimal(0)) for r in chart}
    for w in work:
        series[str(w.work_date)]['wages'] += money(w.wage_amount)
        if term_map.get(w.contract_terms, {}).get('billing_model') == 'Daily': series[str(w.work_date)]['revenue'] += money(w.billable_amount)
    for loan in loans:
        if str(loan.loan_date) in series: series[str(loan.loan_date)]['loans'] += money(loan.amount)
    feed = []
    for dt, title_field, label, symbol, route, filters in (
        ('Employee', 'employee_name', 'Worker added', 'client', '/desk/employee/', {'company': company}),
        ('PP Event Plan', 'event_name', 'Event added', 'calendar', '/desk/pp-event-plans?record=', {'company': company, 'project': ['in', names]}),
        ('PP Contract Terms', 'name', 'Agreement added', 'document', '/desk/pp-agreements?record=', {'project': ['in', names], 'event_basis': 0}),
        ('PP Daily Register', 'name', 'Attendance updated', 'check-square', '/desk/pp-daily-register?record=', {'project': ['in', names]})):
        extra = ['project', 'docstatus'] if dt == 'PP Daily Register' else ['project'] if dt == 'PP Contract Terms' else []
        order = 'modified desc' if dt == 'PP Daily Register' else 'creation desc'
        for r in frappe.get_list(dt, filters=filters, fields=list(dict.fromkeys(['name', title_field, 'modified', 'creation']+extra)), order_by=order, limit_page_length=25):
            title = event_titles.get(r.get('project'), project_map.get(r.get('project'), {}).get('project_name', r.get(title_field)))
            item_label = ('Attendance approved' if r.docstatus == 1 else 'Attendance cancelled' if r.docstatus == 2 else 'Attendance draft updated') if dt == 'PP Daily Register' else label
            tone = ('success' if r.docstatus == 1 else 'error' if r.docstatus == 2 else 'neutral') if dt == 'PP Daily Register' else 'brand'
            feed.append(dict(name=r.name, title=title, label=item_label, symbol=symbol, tone=tone, date=str(r.modified if dt == 'PP Daily Register' else r.creation), href=route+quote(r.name)))
    feed.sort(key=lambda r: r['date'], reverse=True)
    result = dict(company=company, currency=currency, start=str(start), end=str(end), workers=filtered[(page-1)*5:page*5], worker_total=total, page=page, pages=pages,
        loans_outstanding=str(money(sum(loan_balances.values(), Decimal(0)))), events=events[:3], event_count=len(events), milestones=upcoming[:3],
        feed=feed[:25], attendance=chart, attendance_rate=round(float(present/count*100), 1) if count else None,
        registers=[dict(name=r.name, title=event_titles.get(r.project, project_map[r.project].project_name), date=str(r.work_date), site=site_map.get(r.site, ''), status='Approved' if r.docstatus==1 else 'Cancelled' if r.docstatus==2 else 'Draft',
            href='/desk/pp-daily-register?site='+quote(r.site)+'&work_date='+str(r.work_date)) for r in registers[:4]],
        metric_series=[{k: str(money(v)) if k!='date' else v for k,v in r.items()} for r in series.values()])
    from plus_point.exchange import present as convert
    return convert(result, display_currency)
