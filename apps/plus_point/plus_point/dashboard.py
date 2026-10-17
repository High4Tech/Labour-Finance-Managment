"""Read-only product dashboards. Native permissions and company scope apply."""
from collections import defaultdict
from decimal import Decimal

import frappe
from frappe.utils import add_days, add_months, getdate, today

from plus_point.finance import money


@frappe.whitelist()
def overview(company=None):
    platform = bool(frappe.conf.get('pp_control_plane'))
    if platform:
        from plus_point.platform import require_platform
        require_platform()
    else:
        from plus_point.api import _manager_only
        _manager_only()
    companies = frappe.get_list('Company', fields=['name', 'default_currency'], order_by='name', limit_page_length=0)
    names = {row.name for row in companies}
    if company and company not in names:
        frappe.throw('Choose a company you can access', frappe.PermissionError)
    if not company:
        default = frappe.defaults.get_user_default('Company')
        company = default if default in names else companies[0].name if companies else None
    result = dict(companies=companies, company=company, date=today(), is_platform=platform)
    if not company:
        return result
    result['currency'] = next(row.default_currency for row in companies if row.name == company)
    result.update(_platform(company) if platform else _customer(company))
    return result


def _customer(company):
    from plus_point.reporting import project_finances
    rows = project_finances(dict(company=company))[1]
    names = [row['project'] for row in rows]
    projects = {row.name: row for row in frappe.get_list('Project', filters={'company': company},
        fields=['name', 'project_name', 'status', 'is_active'], limit_page_length=0)}
    workers = frappe.get_list('Employee', filters={'company': company, 'status': 'Active'}, pluck='name', limit_page_length=0)
    sites = frappe.get_list('PP Site', filters={'project': ['in', names], 'is_active': 1}, pluck='name', limit_page_length=0) if names else []
    days = [str(add_days(today(), offset)) for offset in range(-6, 1)]
    attendance = defaultdict(Decimal)
    work = frappe.get_list('PP Work Entry', filters={'project': ['in', names], 'status': 'Approved',
        'work_date': ['between', [days[0], days[-1]]]}, fields=['work_date', 'units'], limit_page_length=0) if names else []
    for row in work:
        attendance[str(row.work_date)] += Decimal(str(row.units))
    total = lambda key: str(money(sum((money(row[key]) for row in rows), Decimal(0))))
    ranked = sorted(rows, key=lambda row: money(row['wages_outstanding']), reverse=True)[:5]
    return dict(workers=len(workers), active_sites=len(sites),
        open_projects=sum(1 for row in rows if projects[row['project']].status == 'Open' and projects[row['project']].is_active == 'Yes'),
        wages_unpaid=total('wages_outstanding'), client_balance=total('client_outstanding_gross'),
        earned_revenue=total('earned_revenue'), contribution=total('operational_profit'),
        attendance=[dict(date=day, units=str(attendance[day])) for day in days],
        projects=[dict(name=row['project'], title=projects[row['project']].project_name,
            earned_revenue=row['earned_revenue'], wages_unpaid=row['wages_outstanding'],
            contribution=row['operational_profit']) for row in ranked])


def _platform(company):
    from plus_point.tenancy import entitlement_status
    start = getdate(today()).replace(day=1)
    months = [str(add_months(start, offset))[:7] for offset in range(-5, 1)]
    invoices = frappe.get_list('Sales Invoice', filters={'company': company, 'docstatus': 1},
        fields=['posting_date', 'base_grand_total', 'outstanding_amount', 'conversion_rate'], limit_page_length=0)
    payments = frappe.get_list('Payment Entry', filters={'company': company, 'docstatus': 1, 'party_type': 'Customer',
        'posting_date': ['between', [months[0]+'-01', today()]]},
        fields=['posting_date', 'payment_type', 'base_received_amount', 'base_paid_amount'], limit_page_length=0)
    billed, cash = defaultdict(Decimal), defaultdict(Decimal)
    balance = Decimal(0)
    for row in invoices:
        balance += max(Decimal(0), Decimal(str(row.outstanding_amount)) * Decimal(str(row.conversion_rate)))
        if getdate(row.posting_date) <= getdate(today()):
            billed[str(row.posting_date)[:7]] += money(row.base_grand_total)
    for row in payments:
        if row.payment_type == 'Receive':
            cash[str(row.posting_date)[:7]] += money(row.base_received_amount)
        elif row.payment_type == 'Pay':
            cash[str(row.posting_date)[:7]] -= money(row.base_paid_amount)
    subscriptions = {row.name: row for row in frappe.get_list('Subscription', filters={'company': company},
        fields=['name', 'status', 'trial_period_end', 'current_invoice_end'], limit_page_length=0)}
    tenants = frappe.get_list('PP Tenant', fields=['name', 'organization_name', 'subscription', 'suspended'], limit_page_length=0)
    customers, counts = [], defaultdict(int)
    for tenant in tenants:
        subscription = subscriptions.get(tenant.subscription)
        if not subscription:
            continue
        trial = subscription.status == 'Trialing'
        expiry = subscription.trial_period_end if trial else subscription.current_invoice_end
        state = entitlement_status(dict(suspended=bool(tenant.suspended or subscription.status not in ('Active', 'Trialing', 'Grace Period')),
            valid_until=str(expiry) if expiry else '1970-01-01'))
        label = 'Trial' if trial and state == 'Active' else state
        counts[label] += 1
        customers.append(dict(name=tenant.name, title=tenant.organization_name, status=label, valid_until=str(expiry) if expiry else None))
    priority = {'Suspended': 0, 'Expired': 1, 'Trial': 2, 'Active': 3}
    customers.sort(key=lambda row: (priority[row['status']], row['valid_until'] or '', row['title']))
    pending = frappe.get_list('PP Support Request', filters={'tenant': ['in', [row['name'] for row in customers]],
        'status': ['in', ['Queued', 'Processing', 'Failed']]}, fields=['status'], limit_page_length=0) if customers else []
    return dict(customers=len(customers), active=counts['Active'], trials=counts['Trial'],
        restricted=counts['Suspended']+counts['Expired'], pending_support=len(pending),
        invoiced_month=str(money(billed[months[-1]])), receipts_month=str(money(cash[months[-1]])),
        client_balance=str(money(balance)), customers_preview=customers[:5],
        sales=[dict(month=month, invoiced=str(money(billed[month])), receipts=str(money(cash[month]))) for month in months])
