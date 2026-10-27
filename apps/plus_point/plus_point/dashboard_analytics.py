"""Read-only dashboard slices. Native records, permissions and earned-work snapshots own amounts."""
from collections import defaultdict
from decimal import Decimal
import frappe
from frappe.utils import add_days, add_months, getdate, today
from plus_point.finance import money
from frappe.query_builder.functions import Sum


def scope(company):
    from plus_point.api import _manager_only
    from plus_point.event_setup import companies
    _manager_only()
    if frappe.conf.get('pp_control_plane') or company not in {r.name for r in companies()}:
        frappe.throw('Choose a company you can access', frappe.PermissionError)
    return frappe.get_list('Project', filters={'company': company, 'pp_archived': 0},
        fields=['name', 'project_name', 'customer', 'status', 'is_active'], limit_page_length=0)


def period_dates(period):
    end = getdate(today()); first = end.replace(day=1)
    if period == 'month': return first, end
    if period == 'last_month': return getdate(add_months(first, -1)), getdate(add_days(first, -1))
    if period in ('3months', '6months'): return getdate(add_months(first, -int(period[0])+1)), end
    frappe.throw('Choose an available chart period')


@frappe.whitelist()
def analytics(company, period='month', display_currency=None):
    projects = scope(company); names = [r.name for r in projects]
    start, end = period_dates(period)
    unlinked = set(frappe.get_list('PP Event Plan', filters={'project': ['in', names or ['']],
        'contract_terms': ['is', 'not set']}, pluck='project', limit_page_length=0))
    terms = frappe.get_list('PP Contract Terms', filters={'project': ['in', names or ['']]},
        fields=['name', 'project', 'billing_model'], limit_page_length=0)
    eligible = [r.name for r in terms if r.project not in unlinked]
    daily_terms = [r.name for r in terms if r.name in eligible and r.billing_model == 'Daily']
    filters = {'contract_terms': ['in', eligible or ['']], 'status': 'Approved', 'work_date': ['between', [start, end]]}
    work = frappe.get_list('PP Work Entry', filters=filters,
        fields=['work_date', Sum(frappe.qb.DocType('PP Work Entry').units).as_('units'), Sum(frappe.qb.DocType('PP Work Entry').wage_amount).as_('wages')], group_by='work_date', limit_page_length=0)
    revenue = frappe.get_list('PP Work Entry', filters={**filters, 'contract_terms': ['in', daily_terms or ['']]},
        fields=['work_date', Sum(frappe.qb.DocType('PP Work Entry').billable_amount).as_('revenue')], group_by='work_date', limit_page_length=0)
    values = {str(r.work_date): r for r in work}; charges = {str(r.work_date): r.revenue for r in revenue}
    months = defaultdict(lambda: {'revenue': Decimal(0), 'wages': Decimal(0)})
    daily = []
    for offset in range((end-start).days+1):
        date = str(add_days(start, offset)); row = values.get(date, {})
        units = Decimal(str(row.get('units') or 0)); wages = money(row.get('wages') or 0); charge = money(charges.get(date) or 0)
        daily.append(dict(date=date, units=str(units)))
        months[date[:7]]['wages'] += wages; months[date[:7]]['revenue'] += charge
    result = dict(company=company, currency=frappe.db.get_value('Company', company, 'default_currency'),
        period=period, start=str(start), end=str(end), work_series=daily,
        finance_series=[dict(month=month, **{k: str(money(v)) for k,v in amounts.items()}) for month, amounts in sorted(months.items())],
        approved_days=str(sum((Decimal(r['units']) for r in daily), Decimal(0))),
        finance_note='Approved daily client charges and all approved wages. Fixed milestone revenue is included in lifetime totals, not assigned an invented earning date.')
    from plus_point.exchange import present
    return present(result, display_currency)


def snapshot(company, financial_projects, workers):
    projects = scope(company); names = [r.name for r in projects]; by_project = {r.name: r for r in projects}
    sites = frappe.get_list('PP Site', filters={'project': ['in', names or ['']], 'is_active': 1},
        fields=['name', 'site_name', 'project'], limit_page_length=0)
    by_site = {r.name: r for r in sites}; active_sites = [s.name for s in sites if by_project[s.project].status == 'Open' and by_project[s.project].is_active == 'Yes']
    plans = frappe.get_list('PP Event Plan', filters={'company': company, 'project': ['in', names or ['']]},
        fields=['name', 'event_name', 'project', 'start_date', 'end_date', 'planning_state'], limit_page_length=0)
    draft_projects = {r.project for r in plans if r.planning_state == 'Draft'}
    assignments = frappe.get_list('PP Assignment', filters={'site': ['in', active_sites or ['']], 'employee': ['in', workers or ['']],
        'start_date': ['<=', today()]}, fields=['site', 'employee', 'end_date'], limit_page_length=0)
    distribution = defaultdict(int)
    for row in assignments:
        if by_site[row.site].project not in draft_projects and (not row.end_date or getdate(row.end_date) >= getdate(today())):
            distribution[row.site] += 1
    groups = [dict(name=key, title=by_site[key].site_name, value=value) for key,value in sorted(distribution.items(), key=lambda pair: (-pair[1], pair[0]))]
    # Individual assignment records, not unique people: the denominator and legend agree.
    from plus_point.events import lifecycle
    clients = {r.name: r.customer_name for r in frappe.get_list('Customer', filters={'name': ['in', [p.customer for p in projects if p.customer] or ['']]}, fields=['name','customer_name'], limit_page_length=0)}
    events = []
    for plan in plans:
        project = by_project[plan.project]; status = lifecycle(plan, cancelled=project.status == 'Cancelled')
        if status not in ('Active', 'Upcoming', 'Draft'): continue
        events.append(dict(name=plan.name, title=plan.event_name, start=str(plan.start_date), end=str(plan.end_date), status=status,
            client=clients.get(project.customer, ''), href='/desk/pp-event-plans?record='+plan.name))
    events.sort(key=lambda r: ({'Active': 0, 'Upcoming': 1, 'Draft': 2}[r['status']], r['start'], r['name']))
    approved = {'project': ['in', financial_projects or ['']], 'status': 'Approved'}
    earned = frappe.get_list('PP Work Entry', filters=approved, fields=['employee', Sum(frappe.qb.DocType('PP Work Entry').wage_amount).as_('amount')], group_by='employee', limit_page_length=0)
    paid = frappe.get_list('PP Wage Settlement', filters={'project': ['in', financial_projects or ['']], 'docstatus': 1}, fields=['employee', Sum(frappe.qb.DocType('PP Wage Settlement').amount).as_('amount')], group_by='employee', limit_page_length=0)
    recovered = frappe.get_list('PP Loan Recovery', filters={'project': ['in', financial_projects or ['']], 'docstatus': 1}, fields=['employee', Sum(frappe.qb.DocType('PP Loan Recovery').amount).as_('amount')], group_by='employee', limit_page_length=0)
    balance = defaultdict(Decimal)
    for rows, sign in [(earned, 1), (paid, -1), (recovered, -1)]:
        for row in rows: balance[row.employee] += money(row.amount)*sign
    employee_names = {r.name: r.employee_name for r in frappe.get_list('Employee', filters={'company':company}, fields=['name', 'employee_name'], limit_page_length=0)}
    payments = [dict(employee=employee, title=employee_names[employee], amount=str(money(amount))) for employee,amount in sorted(balance.items(), key=lambda pair: -pair[1]) if amount>0 and employee in employee_names]
    recent = frappe.get_list('PP Work Entry', filters=approved, fields=['name', 'employee', 'site', 'work_date', 'modified', 'units'], order_by='modified desc, name desc', limit_page_length=5)
    return dict(assignments=groups, assignment_total=sum(r['value'] for r in groups), events=events[:5], payments=payments[:5],
        recent=[dict(name=r.name, title=employee_names.get(r.employee, r.employee), date=str(r.modified), work_date=str(r.work_date), units=str(r.units), href='/desk/pp-daily-register?site='+r.site+'&work_date='+str(r.work_date)) for r in recent])
