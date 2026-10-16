"""Map approved contractor work to native ERPNext Sales Invoices and receivables."""
from decimal import Decimal
import frappe
from frappe.utils import getdate
from plus_point.finance import money


@frappe.whitelist(methods=['POST'])
def create_invoice(contract_terms, item_code, from_date=None, to_date=None):
    frappe.has_permission('Sales Invoice', 'create', throw=True)
    terms = frappe.get_doc('PP Contract Terms', contract_terms)
    terms.check_permission('read')
    frappe.db.get_value('PP Contract Terms', terms.name, 'name', for_update=True)
    if terms.status != 'Active':
        frappe.throw('Billing requires active terms')
    project = frappe.get_doc('Project', terms.project)
    project.check_permission('read')
    customer = frappe.db.get_value('Contract', terms.contract, 'party_name')
    doctype = 'PP Work Entry' if terms.billing_model == 'Daily' else 'PP Milestone'
    filters = dict(contract_terms=terms.name, status='Approved', sales_invoice=['is', 'not set'])
    date_field = 'work_date' if doctype == 'PP Work Entry' else 'due_date'
    if from_date and to_date and getdate(from_date) > getdate(to_date):
        frappe.throw('Start date must not be after end date')
    if from_date and to_date:
        filters[date_field] = ['between', [from_date, to_date]]
    elif from_date:
        filters[date_field] = ['>=', from_date]
    elif to_date:
        filters[date_field] = ['<=', to_date]
    amount_field = 'billable_amount' if doctype == 'PP Work Entry' else 'amount'
    sources = frappe.get_list(doctype, filters=filters, fields=['name', amount_field], limit_page_length=0, order_by='name')
    sources = [row for row in sources if money(row[amount_field]) > 0]
    if not sources:
        frappe.throw('No approved unbilled work or milestones in this period')
    invoice = frappe.get_doc(dict(doctype='Sales Invoice', customer=customer,
        company=project.company, project=project.name, currency=terms.currency,
        items=[dict(item_code=item_code, qty=1, rate=float(money(row[amount_field])),
            project=project.name, pp_source_type=doctype, pp_source_name=row.name)
            for row in sources]))
    invoice.insert()
    for source in sources:
        frappe.db.set_value(doctype, source.name, 'sales_invoice', invoice.name)
    return dict(name=invoice.name, sources=len(sources), status='Draft')


def validate_invoice(doc, method=None):
    seen = set()
    for row in doc.items:
        if not row.get('pp_source_type') and not row.get('pp_source_name'):
            continue
        if row.pp_source_type not in ('PP Work Entry', 'PP Milestone') or not row.pp_source_name:
            frappe.throw('Invalid PLUS POINT invoice source')
        key = (row.pp_source_type, row.pp_source_name)
        if key in seen:
            frappe.throw('An invoice cannot bill the same source twice')
        seen.add(key)
        source = frappe.get_doc(*key, for_update=True)
        source.check_permission('read')
        frappe.db.get_value('PP Contract Terms', source.contract_terms, 'name', for_update=True)
        if source.sales_invoice and source.sales_invoice != doc.name:
            frappe.throw('Work or milestone is already reserved by another invoice')
        if source.status not in ('Approved', 'Invoiced'):
            frappe.throw('Only approved sources may be invoiced')
        terms = frappe.get_doc('PP Contract Terms', source.contract_terms)
        project = frappe.get_doc('Project', terms.project)
        customer = frappe.db.get_value('Contract', terms.contract, 'party_name')
        expected = source.billable_amount if key[0] == 'PP Work Entry' else source.amount
        if (doc.project != project.name or row.project != project.name or doc.company != project.company
                or doc.currency != terms.currency or doc.customer != customer or doc.is_return):
            frappe.throw('Invoice must match the source customer, project, company and currency')
        if money(row.amount) != money(expected) or money(row.net_amount) != money(expected):
            frappe.throw('Invoice source amount must equal its approved value without discounts')
    if not doc.is_new():
        old = doc.get_doc_before_save()
        if old:
            previous = {(r.pp_source_type, r.pp_source_name) for r in old.items if r.get('pp_source_name')}
            if previous != seen:
                frappe.throw('Reserved invoice sources cannot be removed; delete the draft to release them')


def on_submit(doc, method=None):
    validate_invoice(doc)
    for row in doc.items:
        if row.get('pp_source_name'):
            frappe.db.set_value(row.pp_source_type, row.pp_source_name, 'sales_invoice', doc.name)
            if row.pp_source_type == 'PP Milestone':
                frappe.db.set_value('PP Milestone', row.pp_source_name, 'status', 'Invoiced')


def reserve_invoice(doc, method=None):
    for row in doc.items:
        if row.get('pp_source_name'):
            frappe.db.set_value(row.pp_source_type, row.pp_source_name, 'sales_invoice', doc.name)


def release_invoice(doc, method=None):
    for row in doc.items:
        if row.get('pp_source_name') and frappe.db.get_value(row.pp_source_type, row.pp_source_name, 'sales_invoice') == doc.name:
            frappe.db.set_value(row.pp_source_type, row.pp_source_name, 'sales_invoice', None)
            if row.pp_source_type == 'PP Milestone':
                frappe.db.set_value('PP Milestone', row.pp_source_name, 'status', 'Approved')
