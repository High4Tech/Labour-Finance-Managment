"""Spending limits for the contractor cost ledger; never a client billing cap."""
from collections import defaultdict
from decimal import Decimal

import frappe
from frappe.utils import escape_html, get_link_to_form

from plus_point.finance import as_decimal, daily_amounts, money

SUPPORTED = ('PP Work Entry', 'PP Daily Register', 'Purchase Invoice', 'Expense Claim')


def lock_project(project):
    # Every cost-increasing writer takes this same row lock before reading totals.
    # Draft work also uses it so a later approval keeps a consistent lock order.
    return frappe.get_doc('Project', project, for_update=True)


def costs(project, exclude_type=None, exclude_name=None):
    def total(query, values):
        return as_decimal(frappe.db.sql(query, values)[0][0] or 0)
    wages = total("""select sum(wage_amount) from `tabPP Work Entry`
        where project=%s and status='Approved' and name!=%s""",
        (project, exclude_name if exclude_type == 'PP Work Entry' else ''))
    purchases = total("""select sum(i.base_net_amount) from `tabPurchase Invoice Item` i
        join `tabPurchase Invoice` p on p.name=i.parent
        where p.docstatus=1 and coalesce(nullif(i.project,''),p.project)=%s and p.name!=%s""",
        (project, exclude_name if exclude_type == 'Purchase Invoice' else ''))
    claims = total("""select sum(i.base_sanctioned_amount) from `tabExpense Claim Detail` i
        join `tabExpense Claim` p on p.name=i.parent
        where p.docstatus=1 and p.approval_status='Approved'
        and coalesce(nullif(i.project,''),p.project)=%s and p.name!=%s""",
        (project, exclude_name if exclude_type == 'Expense Claim' else ''))
    return dict(wages=wages, purchases=purchases, claims=claims, total=wages+purchases+claims)


def costs_many(projects):
    """One aggregate per ledger for a permission-checked dashboard project set."""
    values={name:dict(wages=Decimal(0),purchases=Decimal(0),claims=Decimal(0),total=Decimal(0)) for name in projects}
    if not values:
        return values
    queries={
        'wages':"""select project,sum(wage_amount) amount from `tabPP Work Entry`
            where status='Approved' and project in %(projects)s group by project""",
        'purchases':"""select coalesce(nullif(i.project,''),p.project) project,sum(i.base_net_amount) amount
            from `tabPurchase Invoice Item` i join `tabPurchase Invoice` p on p.name=i.parent
            where p.docstatus=1 and coalesce(nullif(i.project,''),p.project) in %(projects)s group by project""",
        'claims':"""select coalesce(nullif(i.project,''),p.project) project,sum(i.base_sanctioned_amount) amount
            from `tabExpense Claim Detail` i join `tabExpense Claim` p on p.name=i.parent
            where p.docstatus=1 and p.approval_status='Approved'
            and coalesce(nullif(i.project,''),p.project) in %(projects)s group by project""",
    }
    for key,query in queries.items():
        for row in frappe.db.sql(query,{'projects':list(values)},as_dict=True):
            values[row.project][key]=as_decimal(row.amount or 0)
    for row in values.values():
        row['total']=row['wages']+row['purchases']+row['claims']
    return values


def status(project, proposed=None, exclude_type=None, exclude_name=None, locked=None, totals=None):
    doc = locked or frappe.get_doc('Project', project)
    current = totals if totals is not None else costs(project)
    projected = money(costs(project, exclude_type, exclude_name)['total'] + as_decimal(proposed)
                      if proposed is not None else current['total'])
    limit = money(doc.estimated_costing or 0)
    enabled = bool(doc.get('pp_enforce_spending_budget'))
    percent = projected / limit * 100 if limit > 0 else Decimal(0)
    level = ('empty' if not enabled else 'error' if projected > limit else
             'warning' if percent >= 80 else 'success')
    return dict(project=project, title=doc.project_name, company=doc.company, currency=frappe.db.get_value('Company', doc.company, 'default_currency'),
        enabled=enabled, limit=str(limit), used=str(money(current['total'])), projected=str(money(projected)),
        remaining=str(money(limit-projected)), percent=float(percent), level=level,
        blocked=enabled and projected > limit and projected > money(current['total']),
        wages=str(current['wages']), purchases=str(current['purchases']), claims=str(current['claims']))


def validate_project(doc, method=None):
    if frappe.conf.get('pp_control_plane') or frappe.flags.in_migrate:
        return
    limit = money(doc.estimated_costing or 0)
    if limit < 0:
        frappe.throw('Spending budget cannot be negative')
    if doc.get('pp_enforce_spending_budget') and limit <= 0:
        frappe.throw('Enter a positive spending budget before enabling the spending stop')
    old = doc.get_doc_before_save()
    changed = ((bool(doc.get('pp_enforce_spending_budget')) != bool(old.get('pp_enforce_spending_budget'))
                or money(old.estimated_costing or 0) != limit) if old else bool(doc.get('pp_enforce_spending_budget')))
    if changed and 'System Manager' not in frappe.get_roles():
        frappe.throw('A business administrator must approve spending-budget changes', frappe.PermissionError)
    if old:
        lock_project(doc.name)


def proposals(doc):
    values = defaultdict(Decimal)
    if doc.doctype == 'PP Work Entry':
        assignment = frappe.get_doc('PP Assignment', doc.assignment)
        values[assignment.project] += daily_amounts(assignment.wage_rate, 0, doc.units)[0]
    elif doc.doctype == 'PP Daily Register':
        for row in doc.entries or []:
            assignment = frappe.get_doc('PP Assignment', row.assignment)
            values[assignment.project] += daily_amounts(assignment.wage_rate, 0, row.units)[0]
    elif doc.doctype == 'Purchase Invoice':
        for row in doc.items or []:
            project = row.project or doc.project
            if project:
                values[project] += as_decimal(row.base_net_amount or 0)
    elif doc.doctype == 'Expense Claim' and doc.approval_status == 'Approved':
        for row in doc.expenses or []:
            project = row.project or doc.project
            if project:
                values[project] += as_decimal(row.base_sanctioned_amount or 0)
    return values


def evaluate(doc, locking=False):
    values = proposals(doc)
    # Include old projects when a posted expense is reassigned; decreases remain
    # possible even when another project's existing costs are over budget.
    old = doc.get_doc_before_save()
    if old and old.docstatus == 1 and doc.doctype in ('Purchase Invoice', 'Expense Claim'):
        for project in proposals(old):
            values.setdefault(project, Decimal(0))
    result = []
    for project in sorted(values):
        project_doc = lock_project(project) if locking else frappe.get_doc('Project', project)
        if doc.get('company') and project_doc.company != doc.company:
            frappe.throw('Expense project must belong to the document company')
        result.append(status(project, values[project], doc.doctype, doc.name or '', locked=project_doc))
    return result


def enforce(doc, method=None):
    if frappe.conf.get('pp_control_plane') or frappe.flags.in_migrate:
        return
    if doc.doctype == 'PP Work Entry' and doc.status != 'Approved':
        return
    for state in evaluate(doc, locking=True):
        if state['blocked']:
            link = get_link_to_form('Project', state['project'], 'Review spending budget')
            frappe.throw(f"This action would take {escape_html(state['title'])} spending to "
                f"{state['projected']} {escape_html(state['currency'])}, above its {state['limit']} budget. "
                f"Nothing was approved or submitted. Reduce the proposed cost or ask your administrator to review the budget. {link}",
                title='Spending budget exceeded')


@frappe.whitelist(methods=['POST'])
def preview(document):
    if frappe.conf.get('pp_control_plane'):
        frappe.throw('Spending checks belong on a customer site', frappe.PermissionError)
    from plus_point.api import _manager_only
    _manager_only()
    values = frappe.parse_json(document) if isinstance(document, str) else document
    if values.get('doctype') not in SUPPORTED:
        frappe.throw('Unsupported spending action')
    doc = frappe.get_doc(values)
    if not doc.is_new() and frappe.db.exists(doc.doctype, doc.name):
        frappe.get_doc(doc.doctype, doc.name).check_permission('write')
    else:
        frappe.has_permission(doc.doctype, 'create', throw=True)
    for project in proposals(doc):
        frappe.get_doc('Project', project).check_permission('read')
    return evaluate(doc)


@frappe.whitelist()
def project_status(project):
    from plus_point.api import _manager_only
    _manager_only()
    if frappe.conf.get('pp_control_plane'):
        frappe.throw('Spending checks belong on a customer site', frappe.PermissionError)
    frappe.get_doc('Project', project).check_permission('read')
    return status(project)
