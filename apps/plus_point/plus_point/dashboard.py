"""Read-only product dashboards. Native permissions and company scope apply."""
from collections import defaultdict
from decimal import Decimal
from urllib.parse import quote

import frappe
from frappe.utils import add_days, add_months, getdate, today

from plus_point.finance import money


@frappe.whitelist()
def overview(company=None, display_currency=None):
    platform = bool(frappe.conf.get('pp_control_plane'))
    if platform:
        from plus_point.platform import require_platform
        require_platform()
    else:
        from plus_point.api import _manager_only
        _manager_only()
    if platform:
        companies = frappe.get_list('Company', fields=['name', 'company_name', 'default_currency'], order_by='name', limit_page_length=0)
    else:
        from plus_point.event_setup import companies as workspace_companies
        companies=workspace_companies()
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
    result['notifications'] = notifications(result.get('conditions',[]),company)
    from plus_point.exchange import present
    return present(result, display_currency)


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
    from plus_point.budget import status as budget_status, costs_many
    from plus_point.activity import client_activity
    activity = client_activity(company)
    cost_totals=costs_many(names)
    budgets = [budget_status(name,totals=cost_totals[name]) for name in names]
    rank = {'error': 0, 'warning': 1, 'empty': 2, 'success': 3}
    budgets.sort(key=lambda row: (rank[row['level']], row['title']))
    conditions = []
    def condition(level, title, message, label, path, action=None):
        merged={'/desk/pp-contract-terms':'/desk/pp-agreements','/desk/project':'/desk/pp-agreements?record=new','/desk/pp-site':'/desk/pp-agreements','/desk/pp-assignment':'/desk/pp-event-plans'}
        if path in merged:path=merged[path];action=None
        elif path.startswith('/desk/project/'):path='/desk/pp-event-plans?project='+path.rsplit('/',1)[-1];action=None
        if path.startswith('/desk/query-report/'):
            path += '?company='+quote(company,safe='')
        conditions.append(dict(level=level, title=title, message=message, label=label, path=path, action=action))
    if not rows:
        if projects:
            condition('empty', 'Add billing terms to a project', 'Your projects need PLUS POINT billing terms before contractor work and results can appear here.', 'Set up billing terms', '/desk/pp-contract-terms', 'new:PP Contract Terms')
        else:
            condition('empty', 'Start your first project', 'Set up a project and its billing terms to see work and financial results.', 'Create project', '/desk/project', 'new:Project')
    for budget in budgets:
        if budget['level'] in ('error', 'warning'):
            condition(budget['level'], 'Spending budget exceeded' if budget['level']=='error' else 'Spending budget needs attention',
                f"{budget['title']}. "
                'New spending above the limit is stopped; review the budget before approving more costs.',
                'Review spending budget', '/desk/project/'+quote(budget['project'],safe=''))
            conditions[-1].update(amount=budget['used'], budget_limit=budget['limit'], currency=budget['currency'])
    if budgets and any(not row['enabled'] for row in budgets):
        first = next(row for row in budgets if not row['enabled'])
        condition('empty', 'Set a spending limit', 'One or more projects have no spending stop enabled. Add a separate budget to protect future approvals.',
            'Set spending budget', '/desk/project/'+quote(first['project'],safe=''))
    if not workers:
        condition('empty', 'No active workers yet', 'Add your workers before assigning them to a work site.', 'Add worker', '/desk/employee', 'new:Employee')
    elif rows and not sites:
        condition('empty', 'Add a work site', 'Create a work location under the project before assigning workers or recording attendance.', 'Add work site', '/desk/pp-site', 'new:PP Site')
    elif sites and not attendance[days[-1]]:
        assignments = frappe.get_list('PP Assignment', filters={'site':['in',sites], 'start_date':['<=',today()]},
            fields=['employee','end_date'],limit_page_length=0)
        assigned = any(row.employee in workers and (not row.end_date or getdate(row.end_date)>=getdate(today())) for row in assignments)
        if not assigned:
            condition('empty','No workers assigned for today','Add a dated worker assignment before preparing today’s attendance.','Assign workers','/desk/pp-assignment','new:PP Assignment')
        else:
            condition('warning', 'No approved attendance today', 'Review today’s register if work took place. Saved drafts do not count as approved work.',
                'Review attendance', '/desk/pp-daily-register?work_date='+today())
    elif attendance[days[-1]]:
        condition('success', 'Attendance recorded today', 'Approved worker-days are included in the chart and wage totals.', 'View attendance', '/desk/pp-daily-register')
    if money(total('operational_profit')) < 0:
        condition('warning', 'Project costs exceed earned revenue', 'Review project costs and billing milestones. This does not change the amount owed to workers.',
            'Review project finances', '/desk/query-report/PLUS%20POINT%20Project%20Finances')
    if money(total('wages_outstanding')) > 0:
        condition('warning', 'Worker payments are outstanding', 'Review approved wages and link actual employee payments. Recording wages does not pay them.', 'Review worker payments', '/desk/pp-wage-settlement')
        conditions[-1]['value']=total('wages_outstanding')
    elif rows:
        condition('success', 'No unpaid approved wages', 'All currently approved earnings are covered by linked wage payments, or no wages have been approved yet.', 'View worker statement', '/desk/query-report/PLUS%20POINT%20Worker%20Statement')
    from plus_point.events import summary as event_summary
    return dict(workers=len(workers), active_sites=len(sites),event_plans=event_summary(company),
        budgets=budgets, conditions=conditions, activity=activity,
        open_projects=sum(1 for row in rows if projects[row['project']].status == 'Open' and projects[row['project']].is_active == 'Yes'),
        wages_unpaid=total('wages_outstanding'), client_balance=total('client_outstanding_gross'),
        earned_revenue=total('earned_revenue'), contribution=total('operational_profit'),
        wages_earned=total('labour_cost'), wages_paid=total('wages_paid'), other_costs=total('other_project_costs'),
        cash_received=total('cash_collected_gross'), invoiced_net=total('invoiced_net'),
        attendance=[dict(date=day, units=str(attendance[day])) for day in days],
        projects=[dict(name=row['project'], title=projects[row['project']].project_name,
            earned_revenue=row['earned_revenue'], wages_unpaid=row['wages_outstanding'],
            contribution=row['operational_profit']) for row in ranked])


def notifications(conditions,company):
    import hashlib
    import json
    read=set(json.loads(frappe.defaults.get_user_default('pp_read_updates_v1') or '[]'))
    result=[]
    for condition in conditions:
        if condition['level'] not in ('error','warning'):
            continue
        key=hashlib.sha256(json.dumps([company,condition],sort_keys=True).encode()).hexdigest()
        result.append(dict(condition,id=key,read=key in read))
    return result


@frappe.whitelist(methods=['POST'])
def mark_updates_read(company):
    import json
    data=overview(company)
    previous=json.loads(frappe.defaults.get_user_default('pp_read_updates_v1') or '[]')
    ids=[row['id'] for row in data.get('notifications',[])]
    frappe.defaults.set_user_default('pp_read_updates_v1',json.dumps(list(dict.fromkeys(previous+ids))[-100:]))
    return dict(read=len(ids))


def _platform(company):
    from plus_point.tenancy import entitlement_status
    start = getdate(today()).replace(day=1)
    months = [str(add_months(start, offset))[:7] for offset in range(-5, 1)]
    invoices = frappe.get_list('Sales Invoice', filters={'company': company, 'docstatus': 1},
        fields=['posting_date', 'base_grand_total', 'outstanding_amount', 'conversion_rate','party_account_currency'], limit_page_length=0)
    payments = frappe.get_list('Payment Entry', filters={'company': company, 'docstatus': 1, 'party_type': 'Customer',
        'posting_date': ['between', [months[0]+'-01', today()]]},
        fields=['posting_date', 'payment_type', 'base_received_amount', 'base_paid_amount'], limit_page_length=0)
    billed, cash = defaultdict(Decimal), defaultdict(Decimal)
    balance = Decimal(0)
    from plus_point.billing import outstanding_base
    base_currency=frappe.db.get_value('Company',company,'default_currency')
    for row in invoices:
        balance += max(Decimal(0), outstanding_base(row,base_currency))
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
    conditions=[]
    def condition(level,title,message,label,path,action=None):
        if path.startswith('/desk/query-report/'):
            path += '?company='+quote(company,safe='')
        conditions.append(dict(level=level,title=title,message=message,label=label,path=path,action=action))
    signups=frappe.db.count('PP Signup Request',{'review_status':'Awaiting approval'}) if frappe.db.exists('DocType','PP Signup Request') else 0
    if signups:
        condition('warning','Demo signups await approval',f'{signups} signup request(s) submitted a demo payment. No money was collected. Review before approving.','Review signup requests','/desk/pp-signup-request?review_status=Awaiting%20approval')
    failed_activation=frappe.db.count('PP Signup Request',{'review_status':'Approved','activation_status':'Failed'})
    if failed_activation:
        condition('error','Company workspace setup needs attention',f'{failed_activation} approved workspace(s) could not finish setup. Open the request and retry; existing data is retained.','Review workspace setup','/desk/pp-signup-request?activation_status=Failed')
    if not customers:
        condition('empty','Add your first software customer','Register a customer and link its subscription.','Add customer','/desk/pp-tenant','new:PP Tenant')
    if counts['Suspended']+counts['Expired']:
        condition('error','Customer access needs attention','Expired or suspended accounts cannot accept business changes. Review the account and subscription.','Review customer access','/desk/pp-tenant')
    if any(row.status == 'Failed' for row in pending):
        condition('error','Customer support needs attention','A support action failed. Open the request result and verify the registered owner before trying again.','Review support requests','/desk/pp-support-request')
    elif pending:
        condition('warning','Account support is in progress','Queued requests need the background worker. View the result before creating another request.','Check support result','/desk/pp-support-request')
    if any(row['status']=='Trial' and row['valid_until'] and getdate(row['valid_until']) <= getdate(add_days(today(),7)) for row in customers):
        condition('warning','A customer trial ends soon','Review trials ending within seven days and agree the next subscription period.','Review subscriptions','/desk/subscription')
    if balance > 0:
        condition('warning','Software invoices remain unpaid','An issued invoice is not a payment. Check outstanding bills and record confirmed receipts.','Review unpaid invoices','/desk/query-report/Accounts%20Receivable')
    elif invoices:
        condition('success','No outstanding posted invoices','There is no positive outstanding balance on currently posted software invoices.','View financial results','/desk/query-report/Profit%20and%20Loss%20Statement')
    if not any(billed[month] or cash[month] for month in months):
        condition('empty','No posted software sales yet','Trial customers do not count as revenue. Create an invoice when the customer is ready to be billed.','Create software invoice','/desk/sales-invoice','new:Sales Invoice')
    return dict(customers=len(customers), active=counts['Active'], trials=counts['Trial'],
        conditions=conditions,
        restricted=counts['Suspended']+counts['Expired'], pending_support=len(pending),
        invoiced_month=str(money(billed[months[-1]])), receipts_month=str(money(cash[months[-1]])),
        client_balance=str(money(balance)), customers_preview=customers[:5],
        sales=[dict(month=month, invoiced=str(money(billed[month])), receipts=str(money(cash[month]))) for month in months])
