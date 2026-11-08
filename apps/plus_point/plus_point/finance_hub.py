"""Finance navigation and permission-scoped loan summaries; no cached money totals."""
from decimal import Decimal
import frappe
from plus_point.finance import money
from plus_point.setup_flow import require_customer, linked


def company_scope(company=None):
    require_customer()
    from plus_point.event_setup import companies
    allowed = [row.name for row in companies()]
    company = company or (allowed[0] if allowed else None)
    if not company or company not in allowed:
        frappe.throw('Choose a company you can access.', frappe.PermissionError)
    return linked('Company', company)


@frappe.whitelist()
def summary(company=None):
    business = company_scope(company)
    if not frappe.has_permission('PP Worker Loan', 'read'):
        return dict(enabled=False)
    # Database aggregates respect native permissions and never load all loans
    # or call the per-worker payroll calculation for a section landing page.
    totals = frappe.get_list('PP Worker Loan', filters={'company': business.name, 'docstatus': ['<', 2]},
        fields=['docstatus', {'SUM': 'amount', 'as': 'total'}], group_by='docstatus',
        order_by=None, limit_page_length=3)
    amounts = {row.docstatus: money(row.total) for row in totals}
    rows = frappe.get_list('PP Loan Recovery', filters={'company': business.name, 'docstatus': 1},
        fields=[{'SUM': 'amount', 'as': 'total'}], order_by=None, limit_page_length=1)
    recovered = money((rows[0].total or 0) if rows else 0)
    advanced = amounts.get(1, Decimal(0))
    return dict(enabled=True, currency=business.default_currency,
        advanced=str(advanced), recovered=str(recovered),
        outstanding=str(max(Decimal(0), advanced-recovered)), drafts=str(amounts.get(0, Decimal(0))))


@frappe.whitelist()
def loan_states(names):
    business = company_scope()
    names = frappe.parse_json(names)
    if not isinstance(names, list) or len(names) > 200 or any(not isinstance(n, str) for n in names):
        frappe.throw('Choose at most 200 loans at a time.')
    if not names:
        return []
    rows = frappe.get_list('PP Worker Loan', filters={'company': business.name, 'name': ['in', names]},
        fields=['name', 'employee', 'amount', 'docstatus', 'currency', 'loan_date', 'deduction_percent'], limit_page_length=200)
    repayments = frappe.get_list('PP Loan Recovery', filters={'company': business.name, 'loan': ['in', [r.name for r in rows]], 'docstatus': 1},
        fields=['loan', {'SUM': 'amount', 'as': 'total'}], group_by='loan', order_by=None, limit_page_length=200) if rows else []
    paid = {r.loan: money(r.total) for r in repayments}
    employees = frappe.get_list('Employee', filters={'company': business.name, 'name': ['in', list({r.employee for r in rows})]},
        fields=['name', 'employee_name', 'image'], limit_page_length=200) if rows else []
    workers = {r.name: r for r in employees}
    for row in rows:
        row.recovered = str(paid.get(row.name, Decimal(0)))
        remaining = max(Decimal(0), money(row.amount)-money(row.recovered)) if row.docstatus == 1 else Decimal(0)
        row.outstanding = str(remaining)
        row.loan_status = 'Cancelled' if row.docstatus == 2 else 'Draft · unpaid' if row.docstatus == 0 else 'Repaid' if remaining == 0 else 'Active'
        worker = workers.get(row.employee)
        row.worker_name = worker.employee_name if worker else row.employee
        row.image = worker.image if worker else ''
    return rows


@frappe.whitelist()
def loan_detail(name, month=None):
    business = company_scope()
    loan = linked('PP Worker Loan', name, business.name)
    worker = linked('Employee', loan.employee, business.name)
    from plus_point.benefits import balances
    state = balances(worker.name, month)
    row = next((r for r in state['loans'] if r.name == name), None)
    return dict(worker=dict(name=worker.name, company=worker.company, employee_name=worker.employee_name,
            image=worker.image, pp_loan_deduction_percent=worker.get('pp_loan_deduction_percent')),
        currency=business.default_currency, benefits=state, loan=row,
        recoveries=frappe.get_list('PP Loan Recovery', filters={'loan': name, 'company': business.name},
            fields=['name','month','amount','docstatus','journal_entry'], order_by='month desc, creation desc', limit_page_length=100))

@frappe.whitelist(methods=['POST'])
def list_records(doctype, search=None, start=0, project=None):
    """Read accounting records using native list and company permissions."""
    from frappe.utils import cint

    fields = {
        'Payment Entry': ['payment_type', 'party_name', 'party', 'paid_amount', 'paid_from_account_currency'],
        'Sales Invoice': ['customer_name', 'grand_total', 'currency'],
        'Purchase Invoice': ['supplier_name', 'grand_total', 'currency'],
        'Expense Claim': ['employee_name', 'total_claimed_amount', 'company.default_currency as currency'],
    }
    if frappe.conf.get('pp_control_plane') or doctype not in fields:
        frappe.throw('This finance list is unavailable.', frappe.PermissionError)
    business = company_scope()
    search = str(search or '').strip()[:140]
    filters = {'company': business.name}
    scope = None
    if project:
        work = linked('Project', project, business.name)
        # Reimbursements carry their project on the expense lines. Native list
        # permissions still apply to the parent document and joined child rows.
        filters['expenses.project' if doctype == 'Expense Claim' else 'project'] = work.name
        scope = dict(name=work.name, title=work.project_name)
    if search:
        filters['name'] = ['like', f'%{search}%']
    rows = frappe.get_list(
        doctype,
        fields=['name', 'docstatus', 'posting_date', *fields[doctype]],
        filters=filters,
        order_by='posting_date desc, name desc',
        limit_start=max(0, cint(start)),
        limit_page_length=21,
    )
    return {'rows': rows[:20], 'has_more': len(rows) > 20, 'project': scope}
