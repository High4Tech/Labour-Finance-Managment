"""Map approved contractor work to native ERPNext Sales Invoices and receivables."""
from decimal import Decimal
import frappe
from frappe.utils import getdate
from plus_point.finance import money
from plus_point.setup_flow import require_customer,linked


def default_currency(company,customer=None):
    return (frappe.db.get_value('Customer',customer,'default_currency') if customer else None) or frappe.db.get_value('Company',company,'pp_invoice_currency') or frappe.db.get_value('Company',company,'default_currency')


@frappe.whitelist()
def invoice_options(contract_terms):
    require_customer();terms=linked('PP Contract Terms',contract_terms);project=linked('Project',terms.project)
    customer=frappe.db.get_value('Contract',terms.contract,'party_name')
    return dict(currency=terms.get('pp_agreement_currency') or default_currency(project.company,customer),base_currency=terms.currency,company=project.company,exchange_rate=terms.get('pp_agreement_rate') if terms.get('pp_agreement_currency') else None)


@frappe.whitelist()
def quote(company,currency):
    require_customer();doc=linked('Company',company);linked('Currency',currency)
    if currency==doc.default_currency:return dict(rate='1',base_currency=doc.default_currency,currency=currency,as_of='')
    from plus_point.exchange import _snapshot,RateUnavailable
    try:
        data=_snapshot();base=Decimal(data['rates'].get(doc.default_currency,'0'));target=Decimal(data['rates'].get(currency,'0'))
        if not base.is_finite() or not target.is_finite() or base<=0 or target<=0:raise RateUnavailable()
    except RateUnavailable:frappe.throw('Current exchange rates are unavailable. Enter the agreed exchange rate before creating the invoice.')
    return dict(rate=str(base/target),base_currency=doc.default_currency,currency=currency,as_of=data['updated'])


def outstanding_base(invoice,base_currency):
    value=Decimal(str(invoice.outstanding_amount or 0))
    return money(value if invoice.get('party_account_currency')==base_currency else value*Decimal(str(invoice.conversion_rate or 1)))


def receivable_account(company,currency):
    """Native receivable ledgers have one currency; never relabel an existing ledger."""
    doc=frappe.get_doc('Company',company)
    base=frappe.get_doc('Account',doc.default_receivable_account)
    if base.account_currency==currency:return base.name
    frappe.db.get_value('Company',company,'name',for_update=True)
    title=f'Client receivables {currency}'
    name=frappe.db.get_value('Account',{'company':company,'account_name':title},'name')
    if name:
        account=frappe.get_doc('Account',name)
        if account.account_currency!=currency or account.account_type!='Receivable' or account.is_group or account.disabled:
            frappe.throw('The client currency account needs review in Accounts before invoicing.')
        return account.name
    return frappe.get_doc(dict(doctype='Account',account_name=title,company=company,parent_account=base.parent_account,
        account_currency=currency,account_type='Receivable',is_group=0)).insert().name


@frappe.whitelist(methods=['POST'])
def create_invoice(contract_terms, item_code=None, from_date=None, to_date=None, invoice_currency=None, exchange_rate=None, source_names=None):
    frappe.has_permission('Sales Invoice', 'create', throw=True)
    terms = frappe.get_doc('PP Contract Terms', contract_terms)
    terms.check_permission('read')
    frappe.db.get_value('PP Contract Terms', terms.name, 'name', for_update=True)
    if terms.status != 'Active':
        frappe.throw('Billing requires active terms')
    project = frappe.get_doc('Project', terms.project)
    project.check_permission('read')
    if not item_code:
        from plus_point.operations import service_item
        item_code=terms.billing_item or service_item()
    customer = frappe.db.get_value('Contract', terms.contract, 'party_name')
    currency=invoice_currency or terms.get('pp_agreement_currency') or default_currency(project.company,customer)
    linked('Currency',currency);frappe.db.set_value('Currency',currency,'enabled',1)
    try:rate=Decimal(str(exchange_rate)) if exchange_rate not in (None,'') else Decimal(str(terms.get('pp_agreement_rate'))) if currency==terms.get('pp_agreement_currency') and terms.get('pp_agreement_rate') else Decimal(quote(project.company,currency)['rate'])
    except (ValueError,ArithmeticError):frappe.throw('Enter a positive exchange rate.')
    if not rate.is_finite() or rate<=0:frappe.throw('Enter a positive exchange rate.')
    if currency==terms.currency:rate=Decimal(1)
    doctype = 'PP Work Entry' if terms.billing_model == 'Daily' else 'PP Milestone'
    filters = dict(contract_terms=terms.name, status='Approved', sales_invoice=['is', 'not set'])
    if source_names is not None:
        names=frappe.parse_json(source_names)
        if not isinstance(names,list) or not names or any(not isinstance(n,str) for n in names):frappe.throw('Choose valid approved invoice sources.')
        filters['name']=['in',names]
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
    sources = frappe.get_list(doctype, filters=filters, fields=['name', amount_field]+(['milestone_title'] if doctype=='PP Milestone' else ['employee','work_date']), limit_page_length=0, order_by='name')
    sources = [row for row in sources if money(row[amount_field]) > 0]
    if not sources:
        frappe.throw('No approved unbilled work or milestones in this period')
    invoice = frappe.get_doc(dict(doctype='Sales Invoice', customer=customer,
        company=project.company, project=project.name, currency=currency,conversion_rate=float(rate),debit_to=receivable_account(project.company,currency),
        items=[dict(item_code=item_code,description=frappe.utils.escape_html(project.project_name+' — '+(row.milestone_title if doctype=='PP Milestone' else (frappe.db.get_value('Employee',row.employee,'employee_name') or row.employee)+' / '+str(row.work_date))),qty=1, rate=float(money(Decimal(str(row[amount_field]))/rate)),
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
        expected = (source.get('pp_invoice_amount_snapshot') or source.billable_amount) if key[0] == 'PP Work Entry' else source.amount
        if (doc.project != project.name or row.project != project.name or doc.company != project.company
                or doc.customer != customer or doc.is_return):
            frappe.throw('Invoice must match the source customer, project and company')
        rate=Decimal(str(doc.conversion_rate or 0))
        if not rate.is_finite() or rate<=0 or (doc.currency==terms.currency and rate!=1):frappe.throw('Enter a valid invoice exchange rate.')
        converted=money(Decimal(str(expected))/rate)
        if money(row.amount) != converted or money(row.net_amount) != converted:
            frappe.throw('Invoice source amount must equal its approved value converted at the invoice exchange rate, without discounts')
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
            if row.pp_source_type=='PP Work Entry':frappe.db.set_value('PP Work Entry',row.pp_source_name,'pp_invoice_amount_snapshot',0)
            if row.pp_source_type == 'PP Milestone':
                frappe.db.set_value('PP Milestone', row.pp_source_name, 'status', 'Approved')
