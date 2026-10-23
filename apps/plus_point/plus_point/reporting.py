"""Contractor-specific views in Frappe's native reporting and export interface."""
from collections import defaultdict
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import escape_html, getdate, today

from plus_point.api import _manager_only, project_summary
from plus_point.finance import money


def _scope(filters):
    _manager_only()
    if frappe.conf.get('pp_control_plane'):
        frappe.throw(_('Contractor reports belong on a customer site'), frappe.PermissionError)
    filters = frappe._dict(filters or {})
    if not filters.company:
        frappe.throw(_('Select your company'))
    frappe.get_doc('Company', filters.company).check_permission('read')
    project_filters = {'company': filters.company}
    if not filters.get('include_archived'):project_filters['pp_archived']=0
    if filters.project:
        project = frappe.get_doc('Project', filters.project)
        project.check_permission('read')
        if project.company != filters.company:
            frappe.throw(_('The project must belong to your selected company'))
        project_filters['name'] = filters.project
    if filters.customer:
        frappe.get_doc('Customer', filters.customer).check_permission('read')
        project_filters['customer'] = filters.customer
    if filters.status:
        if filters.status not in ('Open', 'Completed', 'Cancelled'):
            frappe.throw(_('Invalid project status'))
        project_filters['status'] = filters.status
    projects = frappe.get_list('Project', filters=project_filters,
        fields=['name', 'project_name', 'customer', 'status', 'is_active'],
        order_by='project_name asc', limit_page_length=0)
    currency = frappe.db.get_value('Company', filters.company, 'default_currency')
    return filters, projects, currency


def _column(key, label, kind='Currency', options=None, width=165):
    column = dict(fieldname=key, label=_(label), fieldtype=kind, width=width)
    if kind == 'Currency':
        column['options'] = 'currency'
    elif options:
        column['options'] = options
    return column


def _card(label, value, currency=None, indicator='Blue'):
    return dict(label=_(label), value=value, indicator=indicator,
                datatype='Currency' if currency else 'Float', currency=currency)


def _note(summary, detail):
    return (f'<p>{escape_html(_(summary))}</p><details class="pp-report-notes">'
            f'<summary>{escape_html(_("How these figures are calculated"))}</summary>'
            f'<p>{escape_html(_(detail))}</p></details>')


def project_finances(filters=None):
    filters, projects, currency = _scope(filters)
    if filters.view and filters.view not in ('Financial results', 'Deployment overview'):
        frappe.throw(_('Invalid report view'))
    names = [row.name for row in projects]
    terms = frappe.get_list('PP Contract Terms', filters={'project': ['in', names]},
        fields=['name', 'project', 'contract', 'status', 'effective_start', 'effective_end'],
        limit_page_length=0) if names else []
    contractor_projects = {row.project for row in terms}
    projects = [row for row in projects if row.name in contractor_projects]
    names = [row.name for row in projects]
    terms_by_project = defaultdict(list)
    for row in terms:
        terms_by_project[row.project].append(row)
    base_columns = [_column('project', 'Project', 'Link', 'Project', 210),
                    _column('customer', 'Client company', 'Link', 'Customer', 190),
                    _column('status', 'Project status', 'Data', width=120)]
    if filters.view == 'Deployment overview':
        return _deployment(filters, projects, terms_by_project, base_columns)
    rows = []
    for project in projects:
        summary = project_summary(project.name)
        rows.append(dict(summary, customer=project.customer, status=project.status))
    own=frappe.db.get_value('PP Contract Terms',{'project':filters.project},['pp_agreement_currency','pp_agreement_rate'],as_dict=True) if filters.project else None
    target=(own.pp_agreement_currency or currency) if own else filters.get('display_currency') or frappe.defaults.get_user_default('pp_display_currency')
    if target and target!=currency:
        from plus_point.billing import quote
        rate=Decimal(str(own.pp_agreement_rate)) if own and own.pp_agreement_rate else Decimal(str(quote(filters.company,target)['rate']))
        for row in rows:
            for key in ('fixed_contract_value','earned_revenue','labour_cost','wages_paid','wages_outstanding','invoiced_gross','cash_collected_gross','client_outstanding_gross','other_project_costs','operational_profit','gross_contribution_before_other_costs','invoiced_net','settled_against_invoices_gross'):
                row[key]=str(money(Decimal(str(row[key]))/rate))
            row['currency']=target
        currency=target
    columns = base_columns + [_column(key, label) for key, label in [
        ('fixed_contract_value', 'Fixed contract value'), ('earned_revenue', 'Revenue earned'),
        ('labour_cost', 'Wages earned'), ('wages_paid', 'Wages paid'),
        ('wages_outstanding', 'Wages outstanding'), ('invoiced_gross', 'Invoiced incl. taxes'),
        ('cash_collected_gross', 'Client cash received'), ('client_outstanding_gross', 'Client invoice balance'),
        ('other_project_costs', 'Other project costs'), ('operational_profit', 'Operational contribution'),
    ]] + [_column('currency', 'Currency', 'Link', 'Currency', 90)]
    total = lambda key: sum((money(row[key]) for row in rows), Decimal(0))
    summary = [_card('Revenue earned', total('earned_revenue'), currency),
               _card('Client cash received', total('cash_collected_gross'), currency),
               _card('Wages outstanding', total('wages_outstanding'), currency),
               _card('Operational contribution', total('operational_profit'), currency)]
    message = _note('Lifetime project totals. Contract value, earned revenue, invoices and cash received are separate. '
                    'Operational contribution excludes taxes, overhead and unallocated costs.',
                'Includes completed projects unless filtered. Fixed contract value is not earned revenue. '
                'Fixed revenue comes from approved milestones; it is not attributed to individual workers. '
                'Cash includes allocated customer Payment Entries converted to company currency, net of refunds; excludes unallocated receipts. '
                'Other costs use submitted net purchase items and sanctioned expense lines assigned to the project, excluding taxes, overhead and unallocated costs. '
                'Do not enter the same worker wages again as project expenses. Operational contribution is not statutory net profit. '
                'Use Deployment overview for site and workforce counts; dated worker activity is in Worker Statement.')
    return columns, rows, message, None, summary


def _deployment(filters, projects, terms_by_project, columns):
    names = [row.name for row in projects]
    day = getdate(today())
    sites = frappe.get_list('PP Site', filters={'project': ['in', names], 'is_active': 1},
        fields=['name', 'project'], limit_page_length=0) if names else []
    site_names = {row.name for row in sites}
    assignments = frappe.get_list('PP Assignment', filters={'project': ['in', names]},
        fields=['employee', 'site', 'project', 'contract_terms', 'start_date', 'end_date'],
        limit_page_length=0) if names else []
    employees = frappe.get_list('Employee', filters={'company': filters.company, 'status': 'Active'},
        pluck='name', limit_page_length=0)
    active_workers = set(employees)
    work = frappe.get_list('PP Work Entry', filters={'project': ['in', names], 'status': 'Approved'},
        fields=['project', 'units'], limit_page_length=0) if names else []
    active_contracts, deployed = set(), set()
    rows = []
    for project in projects:
        active_terms = {term.name for term in terms_by_project[project.name]
            if term.status == 'Active' and getdate(term.effective_start) <= day
            and (not term.effective_end or getdate(term.effective_end) >= day)}
        active_contracts.update(term.contract for term in terms_by_project[project.name] if term.name in active_terms)
        allocated = [row for row in assignments if row.project == project.name]
        current = {row.employee for row in allocated if row.employee in active_workers and row.site in site_names
            and row.contract_terms in active_terms and getdate(row.start_date) <= day
            and (not row.end_date or getdate(row.end_date) >= day)
            and project.status == 'Open' and project.is_active == 'Yes'}
        deployed.update(current)
        rows.append(dict(project=project.name, customer=project.customer, status=project.status,
            active_contracts=len({term.contract for term in terms_by_project[project.name] if term.name in active_terms}),
            active_sites=sum(1 for site in sites if site.project == project.name),
            assigned_workers=len({row.employee for row in allocated}), deployed_today=len(current),
            worked_days=sum((Decimal(str(row.units)) for row in work if row.project == project.name), Decimal(0))))
    columns += [_column(key, label, 'Float', width=160) for key, label in [
        ('active_contracts', 'Active billing contracts'), ('active_sites', 'Active sites'),
        ('assigned_workers', 'Workers assigned (all dates)'), ('deployed_today', 'Deployed today'),
        ('worked_days', 'Approved workforce days')]]
    summary = [_card('Client companies', len({row.customer for row in projects if row.customer})),
               _card('Active billing contracts', len(active_contracts)),
               _card('Active sites', len(sites)), _card('Deployed today', len(deployed)),
               _card('Active workers in your company', len(employees))]
    return columns, rows, _note('Assignment-based deployment today, not confirmed attendance.',
        'Only projects with PLUS POINT billing terms are included. Deployed today means an active, dated assignment '
        'on an active site and active terms in an open project, not confirmed attendance. Counts deduplicate workers and contracts across projects. '
        'Active workers in your company is company-wide; other figures follow the client/project filters.'), None, summary


def worker_statement_report(filters=None):
    filters, projects, currency = _scope(filters)
    if not filters.employee:
        frappe.throw(_('Select a worker'))
    frappe.get_doc('Employee', filters.employee).check_permission('read')
    start = getdate(filters.from_date) if filters.from_date else None
    end = getdate(filters.to_date) if filters.to_date else None
    if start and end and start > end:
        frappe.throw(_('Start date must not be after end date'))
    names = [project.name for project in projects]
    project_clients = {project.name: project.customer for project in projects}
    if filters.view and filters.view not in ('Work and payments', 'Assignment history'):
        frappe.throw(_('Invalid report view'))
    if filters.view == 'Assignment history':
        return _assignment_history(filters, names, project_clients, currency, start, end)
    frappe.has_permission('Payment Entry', 'read', throw=True)
    entries = frappe.get_list('PP Work Entry', filters={'employee': filters.employee, 'project': ['in', names], 'status': 'Approved'},
        fields=['name', 'work_date', 'project', 'site', 'units', 'wage_rate', 'wage_amount', 'billable_amount'],
        limit_page_length=0) if names else []
    settlements = frappe.get_list('PP Wage Settlement', filters={'employee': filters.employee, 'project': ['in', names], 'docstatus': 1},
        fields=['name', 'project', 'payment_entry', 'amount'], limit_page_length=0) if names else []
    payment_names = [row.payment_entry for row in settlements]
    payments = frappe.get_list('Payment Entry', filters={'name': ['in', payment_names], 'docstatus': 1, 'company': filters.company},
        fields=['name', 'posting_date'], limit_page_length=0) if payment_names else []
    dates = {row.name: row.posting_date for row in payments}
    if len(dates) != len(set(payment_names)):
        frappe.throw(_('Some linked employee payments are unavailable. Request access before viewing this statement.'), frappe.PermissionError)
    ledger = [dict(date=row.work_date, kind='Work', work_entry=row.name, project=row.project, site=row.site,
                   units=row.units, wage_rate=row.wage_rate, wages_earned=money(row.wage_amount), wages_paid=Decimal(0),
                   direct_client_earnings=money(row.billable_amount)) for row in entries]
    ledger += [dict(date=dates[row.payment_entry], kind='Payment', settlement=row.name, payment_entry=row.payment_entry,
                    project=row.project, wages_earned=Decimal(0), wages_paid=money(row.amount)) for row in settlements]
    recoveries=frappe.get_list('PP Loan Recovery',filters={'employee':filters.employee,'project':['in',names],'docstatus':1},fields=['name','project','amount','journal_entry'],limit_page_length=0) if names and frappe.db.exists('DocType','PP Loan Recovery') else []
    ledger += [dict(date=frappe.db.get_value('Journal Entry',r.journal_entry,'posting_date'),kind='Loan recovery',loan_recovery_record=r.name,journal_entry=r.journal_entry,project=r.project,wages_earned=Decimal(0),wages_paid=Decimal(0),loan_recovery=money(r.amount)) for r in recoveries]
    ledger.sort(key=lambda row: (getdate(row['date']), row['kind'] != 'Work', row.get('work_entry') or row.get('settlement') or row.get('loan_recovery_record')))
    opening = sum((row['wages_earned'] - row['wages_paid'] - row.get('loan_recovery',Decimal(0)) for row in ledger if start and getdate(row['date']) < start), Decimal(0))
    balance, rows = opening, []
    for row in ledger:
        day = getdate(row['date'])
        if (start and day < start) or (end and day > end):
            continue
        balance += row['wages_earned'] - row['wages_paid'] - row.get('loan_recovery',Decimal(0))
        rows.append(dict(row, balance=money(balance), currency=currency, customer=project_clients[row['project']]))
    columns = [_column('date', 'Date', 'Date', width=110), _column('kind', 'Record', 'Data', width=95),
        _column('customer', 'Client company', 'Link', 'Customer', 170), _column('project', 'Project', 'Link', 'Project', 180),
        _column('site', 'Work site', 'Link', 'PP Site', 160), _column('units', 'Days worked', 'Float', width=115),
        _column('wage_rate', 'Daily wage'), _column('wages_earned', 'Wages earned'), _column('wages_paid', 'Wages paid'),
        _column('loan_recovery','Loan recovered'), _column('loan_recovery_record','Loan recovery','Link','PP Loan Recovery',160), _column('journal_entry','Recovery journal','Link','Journal Entry',170), _column('balance', 'Wage balance'), _column('direct_client_earnings', 'Daily client earnings'),
        _column('work_entry', 'Work entry', 'Link', 'PP Work Entry', 190),
        _column('payment_entry', 'Payment', 'Link', 'Payment Entry', 190),
        _column('settlement', 'Wage settlement', 'Link', 'PP Wage Settlement', 190),
        _column('currency', 'Currency', 'Link', 'Currency', 90)]
    summary = [_card('Opening wage balance', money(opening), currency),
        _card('Days worked', sum((Decimal(str(row.get('units') or 0)) for row in rows), Decimal(0))),
        _card('Wages earned in period', sum((row['wages_earned'] for row in rows), Decimal(0)), currency),
        _card('Wages paid in period', sum((row['wages_paid'] for row in rows), Decimal(0)), currency),
        _card('Closing wage balance', money(balance), currency)]
    message = _note('Approved work and settled payments, with opening and closing wage balances. Recorded loan recoveries reduce the wage balance; unpaid drafts and unallocated payments are excluded.',
        'Approved work and submitted wage settlements only. Payment dates come from the native employee Payment Entry. '
        'Unallocated payments and advances are excluded. Opening balance includes earlier records in the selected company/client/project scope. '
        'Daily client earnings are zero for fixed contracts; fixed milestone revenue is not allocated to individual workers. '
        'Use Assignment history to see deployments and agreed rates, including dates with no attendance.')
    return columns, rows, message, None, summary


def _assignment_history(filters, names, clients, currency, start, end):
    assignments = frappe.get_list('PP Assignment', filters={'employee': filters.employee, 'project': ['in', names]},
        fields=['name', 'project', 'site', 'contract_terms', 'start_date', 'end_date', 'wage_rate', 'client_rate'],
        order_by='start_date asc, name asc', limit_page_length=0) if names else []
    rows = [dict(row, customer=clients[row.project], currency=currency) for row in assignments
        if (not end or getdate(row.start_date) <= end) and (not start or not row.end_date or getdate(row.end_date) >= start)]
    columns = [_column('name', 'Assignment', 'Link', 'PP Assignment', 160),
        _column('customer', 'Client company', 'Link', 'Customer', 170), _column('project', 'Project', 'Link', 'Project', 180),
        _column('site', 'Work site', 'Link', 'PP Site', 160), _column('start_date', 'From', 'Date', width=110),
        _column('end_date', 'Through', 'Date', width=110), _column('wage_rate', 'Daily wage'),
        _column('client_rate', 'Daily client rate'), _column('contract_terms', 'Billing terms', 'Link', 'PP Contract Terms', 160),
        _column('currency', 'Currency', 'Link', 'Currency', 90)]
    return columns, rows, _note('Dated allocations and agreed rates, including assignments with no attendance.',
        'Assignments overlapping the selected dates, including allocations with no work entries. '
        'These are agreed rates, not proof of attendance or payment. Close an old assignment before starting a new rate at the same site.'), None, []
