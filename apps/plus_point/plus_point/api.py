"""Authenticated operational reports backed by existing Frappe REST/API security."""
from decimal import Decimal

import frappe
from plus_point.finance import money


def _manager_only():
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Only System Manager can see financial summaries", frappe.PermissionError)


@frappe.whitelist()
def project_summary(project):
    """Approved daily work or approved fixed milestones; excludes unposted invoices/other costs."""
    _manager_only()
    if not frappe.db.exists("Project", project):
        frappe.throw("Project does not exist")
    frappe.get_doc("Project", project).check_permission("read")
    terms = frappe.get_list("PP Contract Terms", filters={"project":project}, fields=["name", "billing_model", "fixed_amount"], limit_page_length=0)
    result = {"project": project, "earned_revenue": "0.00", "labour_cost": "0.00", "gross_contribution_before_other_costs": "0.00", "contracts": []}
    total_revenue = Decimal(0)
    total_wages = Decimal(0)
    for term in terms:
        entries = frappe.get_list("PP Work Entry",filters={"contract_terms":term.name,"status":"Approved"},fields=["wage_amount","billable_amount"], limit_page_length=0)
        wages = sum((money(row.wage_amount) for row in entries),Decimal(0))
        if term.billing_model == "Daily":
            revenue = sum((money(row.billable_amount) for row in entries),Decimal(0))
        else:
            milestones = frappe.get_list("PP Milestone", filters={"contract_terms":term.name,"status":["in",["Approved","Invoiced"]]},fields=["amount"], limit_page_length=0)
            revenue = sum((money(row.amount) for row in milestones),Decimal(0))
        result["contracts"].append({"contract_terms":term.name,"billing_model":term.billing_model,"earned_revenue":str(money(revenue)),"labour_cost":str(money(wages))})
        total_revenue += revenue
        total_wages += wages
    result["earned_revenue"] = str(money(total_revenue))
    result["labour_cost"] = str(money(total_wages))
    result["gross_contribution_before_other_costs"] = str(money(total_revenue-total_wages))
    project_doc = frappe.get_doc('Project', project)
    invoices = frappe.get_list('Sales Invoice', filters=dict(project=project, company=project_doc.company, docstatus=1),
        fields=['name', 'currency','party_account_currency', 'base_net_total', 'base_grand_total', 'outstanding_amount', 'conversion_rate'], limit_page_length=0)
    settlements = frappe.get_list('PP Wage Settlement', filters=dict(project=project, docstatus=1), fields=['amount'], limit_page_length=0)
    paid = sum((money(row.amount) for row in settlements), Decimal(0))
    currency = frappe.db.get_value('Company', project_doc.company, 'default_currency')
    payments = frappe.get_list('Payment Entry', filters=dict(company=project_doc.company, docstatus=1,
        party_type='Customer',payment_type=['in',['Receive','Pay']]),
        fields=['name', 'payment_type','source_exchange_rate','target_exchange_rate'], limit_page_length=0)
    payment_sign = {row.name: (1 if row.payment_type == 'Receive' else -1) for row in payments}
    payment_rate = {row.name:Decimal(str(row.source_exchange_rate if row.payment_type=='Receive' else row.target_exchange_rate)) for row in payments}
    invoice_names = [row.name for row in invoices]
    references = frappe.get_all('Payment Entry Reference', filters=dict(parent=['in', list(payment_sign)],
        reference_doctype='Sales Invoice', reference_name=['in', invoice_names]),
        fields=['parent', 'allocated_amount'], limit_page_length=0) if payment_sign and invoice_names else []
    cash = sum((money(Decimal(str(row.allocated_amount))*payment_rate[row.parent]) * payment_sign[row.parent] for row in references), Decimal(0))
    # Native project purchase and expense-claim totals exclude this operational wage ledger.
    from plus_point.budget import costs
    tracked_costs = costs(project)
    other_costs = tracked_costs['purchases'] + tracked_costs['claims']
    from plus_point.billing import outstanding_base
    result.update(
        currency=frappe.db.get_value('Company', project_doc.company, 'default_currency'),
        fixed_contract_value=str(money(sum((money(t.fixed_amount) for t in terms), Decimal(0)))),
        invoiced_net=str(money(sum((money(i.base_net_total) for i in invoices), Decimal(0)))),
        invoiced_gross=str(money(sum((money(i.base_grand_total) for i in invoices), Decimal(0)))),
        cash_collected_gross=str(money(cash)),
        cash_scope='Submitted native Payment Entry allocations converted at their party-account exchange rate, net of refunds; excludes unallocated receipts',
        settled_against_invoices_gross=str(money(sum((money(i.base_grand_total) - outstanding_base(i,currency) for i in invoices), Decimal(0)))),
        client_outstanding_gross=str(money(sum((outstanding_base(i,currency) for i in invoices), Decimal(0)))),
        wages_paid=str(money(paid)), wages_outstanding=str(money(total_wages - paid)),
        other_project_costs=str(money(other_costs)),
        operational_profit=str(money(total_revenue - total_wages - other_costs)),
        cost_scope='Posted net project purchase items and sanctioned expense lines; excludes taxes, overhead and unallocated costs',
    )
    return result


@frappe.whitelist(methods=["POST"])
def prepare_daily_register(site, work_date):
    """Create a Draft native Frappe Desk register from dated active site assignments.

    Does not create or approve attendance; users review and Submit explicitly.
    """
    _manager_only()
    frappe.has_permission("PP Daily Register", "create", throw=True)
    from frappe.utils import getdate

    day = getdate(work_date)
    site_doc = frappe.get_doc("PP Site", site)
    site_doc.check_permission("read")
    if not site_doc.is_active:
        frappe.throw("Cannot create register for an inactive site")
    assignments = frappe.get_list(
        "PP Assignment",
        filters={"site": site, "start_date": ["<=", day]},
        fields=["name", "employee", "end_date"],
        order_by="employee asc",
        limit_page_length=0,
    )
    active = [x for x in assignments if not x.end_date or getdate(x.end_date) >= day]
    if not active:
        frappe.throw("No active workers are assigned to this site")
    register = frappe.get_doc({
        "doctype": "PP Daily Register",
        "site": site,
        "work_date": str(day),
        "project": site_doc.project,
        "entries": [
            {"assignment": x.name, "employee": x.employee, "units": "1"}
            for x in active
        ],
    })
    register.insert()
    return {"name": register.name, "site": site, "work_date": str(day), "workers": len(active)}


@frappe.whitelist()
def worker_statement(employee, from_date=None, to_date=None, project=None):
    """Approved earnings/billed contribution, not wages paid or client receipts.

    Uses existing site database permissions; access is restricted to System Managers.
    """
    _manager_only()
    if not frappe.db.exists("Employee", employee):
        frappe.throw("Employee does not exist")
    frappe.get_doc("Employee", employee).check_permission("read")
    if from_date and to_date:
        from frappe.utils import getdate
        if getdate(from_date) > getdate(to_date):
            frappe.throw("Start date must not be after end date")
    filters = {"employee": employee, "status": "Approved"}
    if project:
        filters["project"] = project
    if from_date:
        filters["work_date"] = [">=", from_date]
    if to_date:
        if from_date:
            filters["work_date"] = ["between", [from_date, to_date]]
        else:
            filters["work_date"] = ["<=", to_date]
    rows = frappe.get_list(
        "PP Work Entry", filters=filters,
        fields=["name", "work_date", "project", "site", "units", "wage_amount", "billable_amount"],
        order_by="work_date asc, name asc", limit_page_length=0,
    )
    wages = sum((money(row.wage_amount) for row in rows), Decimal(0))
    billables = sum((money(row.billable_amount) for row in rows), Decimal(0))
    # Payments are lifetime/project totals; period earnings must not be presented as a period balance.
    payment_filters = dict(employee=employee, docstatus=1)
    if project:
        payment_filters['project'] = project
    payments = frappe.get_list('PP Wage Settlement', filters=payment_filters, fields=['amount'], limit_page_length=0)
    paid = sum((money(row.amount) for row in payments), Decimal(0))
    return {
        "employee": employee,
        "approved_entries": len(rows),
        "worked_days": str(sum((Decimal(str(row.units)) for row in rows), Decimal(0))),
        "wages_earned": str(money(wages)),
        "wages_paid_all_dates": str(money(paid)),
        "direct_client_billable": str(money(billables)),
        "note": "Fixed-contract worker revenue is not directly billable. Wages paid are submitted wage settlements across all dates, not a balance for the selected earnings period.",
        "entries": [{
            "name": row.name, "work_date": str(row.work_date),
            "project": row.project, "site": row.site,
            "units": str(row.units), "wage_amount": str(money(row.wage_amount)),
            "billable_amount": str(money(row.billable_amount)),
        } for row in rows],
    }
