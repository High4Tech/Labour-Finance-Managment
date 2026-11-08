"""React accounting forms; native ERPNext documents remain the authority.

Only the company app's supported fields are exposed. Other accounting fields
stay on the original document and remain available in the authorized native view.
"""
import frappe
from frappe.utils import nowdate
from plus_point.benefits import atomic
from plus_point.finance_hub import company_scope


FIELDS = {
    'Payment Entry': ['payment_type', 'posting_date', 'party_type', 'party', 'mode_of_payment',
        'paid_from', 'paid_to', 'paid_amount', 'received_amount', 'source_exchange_rate',
        'target_exchange_rate', 'reference_no', 'reference_date', 'cost_center', 'project', 'remarks'],
    'Sales Invoice': ['customer', 'posting_date', 'due_date', 'project', 'currency',
        'conversion_rate', 'items', 'remarks'],
    'Purchase Invoice': ['supplier', 'posting_date', 'due_date', 'bill_no', 'bill_date',
        'project', 'currency', 'conversion_rate', 'items', 'remarks'],
    'Expense Claim': ['employee', 'posting_date', 'expense_approver', 'approval_status',
        'payable_account', 'cost_center', 'expenses', 'remark'],
}
CHILDREN = {
    'items': ['item_code', 'description', 'qty', 'uom', 'rate', 'expense_account', 'cost_center', 'project'],
    'expenses': ['expense_date', 'expense_type', 'description', 'amount', 'sanctioned_amount',
        'default_account', 'cost_center', 'project'],
}


def context(doctype, name=None):
    if doctype not in FIELDS:
        frappe.throw('This accounting form is unavailable.', frappe.PermissionError)
    business = company_scope()
    if name:
        doc = frappe.get_doc(doctype, name)
        doc.check_permission('read')
        if doc.company != business.name:
            frappe.throw('This record belongs to another company.', frappe.PermissionError)
    else:
        frappe.has_permission(doctype, 'create', throw=True)
        doc = frappe.new_doc(doctype)
        doc.company = business.name
        doc.posting_date = nowdate()
        if doctype in ('Sales Invoice', 'Purchase Invoice'):
            doc.currency = business.default_currency
            doc.conversion_rate = 1
    return business, doc


def schema(doctype, names, parent=None):
    meta = frappe.get_meta(doctype)
    readable = set(meta.get_permitted_fieldnames(parenttype=parent))
    writable = set(meta.get_permitted_fieldnames(parenttype=parent, permission_type='write'))
    read_levels = set(meta.get_permlevel_access(permission_type='read', parenttype=parent))
    write_levels = set(meta.get_permlevel_access(permission_type='write', parenttype=parent))
    for table in meta.get_table_fields():
        if table.permlevel in read_levels:
            readable.add(table.fieldname)
        if table.permlevel in write_levels:
            writable.add(table.fieldname)
    result = []
    for name in names:
        field = meta.get_field(name)
        if not field or name not in readable:
            continue
        row = dict(key=name, label=field.label, type=field.fieldtype, required=bool(field.reqd),
            options=field.options, readonly=bool(field.read_only or name not in writable))
        if doctype == 'Payment Entry' and name == 'party_type':
            row.update(type='Select', options='\nCustomer\nSupplier\nEmployee')
        if field.fieldtype == 'Table':
            row['fields'] = schema(field.options, CHILDREN.get(name, []), doctype)
        result.append(row)
    return result


@frappe.whitelist()
def detail(doctype, name=None, defaults=None):
    business, doc = context(doctype, name)
    doc = frappe.get_doc(doc.as_dict())
    original = doc.as_json()
    fields = schema(doctype, FIELDS[doctype])
    advanced = []
    if defaults and not doc.docstatus and doc.has_permission('write' if name else 'create'):
        initial = frappe.parse_json(defaults)
        if not isinstance(initial, dict):
            frappe.throw('Review the initial accounting details.')
        if initial.get('company') and initial['company'] != business.name:
            frappe.throw('Choose the company for this accounting draft.', frappe.PermissionError)
        for key in (() if name else ('references', 'taxes', 'deductions', 'is_return', 'is_pos')):
            if initial.get(key):
                advanced.append(key.replace('_', ' '))
        editable = {}
        for field in fields:
            if field['readonly'] or field['key'] not in initial:
                continue
            value = initial[field['key']]
            if field['type'] == 'Table' and isinstance(value, list):
                if any(not isinstance(row, dict) for row in value):
                    frappe.throw('Review the initial accounting lines.')
                value = [dict(**({'name': row['name']} if name and row.get('name') else {}), **{f['key']: row.get(f['key']) for f in field['fields'] if not f['readonly']})
                    for row in value]
            editable[field['key']] = value
        apply_values(doc, editable)
    # Filter a copy, never mutate the cached/source document for presentation.
    safe = frappe.get_doc(doc.as_dict())
    safe.apply_fieldlevel_read_permissions()
    values = {}
    for field in fields:
        value = safe.get(field['key'])
        if field['type'] == 'Table':
            value = [dict(name=row.name, **{f['key']: row.get(f['key']) for f in field['fields']})
                for row in value or []]
        values[field['key']] = value
    totals = {key: doc.get(key) for key in ['grand_total', 'outstanding_amount', 'paid_amount',
        'received_amount', 'total_claimed_amount', 'total_sanctioned_amount',
        'paid_from_account_currency', 'paid_to_account_currency'] if doc.meta.has_field(key)}
    return dict(name=doc.name if name else None, doctype=doctype, company=business.name,
        currency=doc.get('currency') or business.default_currency, modified=str(doc.modified or ''),
        docstatus=doc.docstatus or 0, fields=fields, values=values, totals=totals,
        can_write=bool(doc.has_permission('write') if name else frappe.has_permission(doctype, 'create')),
        can_submit=bool(name and original == doc.as_json() and doc.has_permission('submit')), advanced=advanced)


def apply_values(doc, values):
    fields = {field['key']: field for field in schema(doc.doctype, FIELDS[doc.doctype])}
    if not isinstance(values, dict) or len(values) > 30:
        frappe.throw('Review the accounting form values.')
    for key, value in values.items():
        field = fields.get(key)
        if not field or field['readonly']:
            frappe.throw('This accounting field cannot be changed: ' + str(key), frappe.PermissionError)
        if field['type'] != 'Table':
            if isinstance(value, (dict, list)):
                frappe.throw('Enter one value for ' + field['label'] + '.')
            doc.set(key, value)
            continue
        if not isinstance(value, list) or len(value) > 200:
            frappe.throw('Use at most 200 lines in one document.')
        previous = {row.name: row for row in doc.get(key) or []}
        rows = []
        allowed = {f['key'] for f in field['fields'] if not f['readonly']}
        for item in value:
            if not isinstance(item, dict) or set(item) - allowed - {'name'}:
                frappe.throw('Review the fields in this accounting line.')
            name = item.get('name')
            if name and name not in previous:
                frappe.throw('This accounting line no longer belongs to the document. Reload it.')
            row = previous[name] if name else frappe.new_doc(doc.meta.get_field(key).options)
            row.update({k: v for k, v in item.items() if k in allowed})
            rows.append(row)
        doc.set(key, rows)


@frappe.whitelist(methods=['POST'])
@atomic
def save(doctype, values, name=None, modified=None):
    _, doc = context(doctype, name)
    doc.check_permission('write' if name else 'create')
    if doc.docstatus:
        frappe.throw('Posted or cancelled records cannot be edited. Use authorized accounting controls.')
    if name and str(doc.modified) != str(modified or ''):
        frappe.throw('Someone changed this record. Reload it before saving your changes.')
    apply_values(doc, frappe.parse_json(values))
    if doctype in ('Sales Invoice', 'Purchase Invoice'):
        doc.run_method('set_missing_values')
        doc.run_method('set_missing_item_details')
    # save/insert runs native link, mandatory, account, currency and permissions checks.
    doc.save()
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
@atomic
def submit(doctype, name, modified):
    _, doc = context(doctype, name)
    doc.check_permission('submit')
    if str(doc.modified) != str(modified):
        frappe.throw('This record changed. Reload and review it before posting.')
    if doc.docstatus != 0:
        frappe.throw('Only a draft can be submitted.')
    doc.submit()
    return dict(name=doc.name)


@frappe.whitelist()
def choices(doctype, field, text=None, parentfield=None, party_type=None):
    business = company_scope()
    if doctype not in FIELDS or not (frappe.has_permission(doctype, 'read') or frappe.has_permission(doctype, 'create')):
        frappe.throw('This accounting form is unavailable.', frappe.PermissionError)
    fields = schema(doctype, FIELDS[doctype])
    if parentfield:
        fields = next((f.get('fields', []) for f in fields if f['key'] == parentfield), [])
    definition = next((f for f in fields if f['key'] == field), None)
    if not definition or definition['type'] not in ('Link', 'Dynamic Link'):
        frappe.throw('This field has no searchable choices.')
    target = definition['options']
    if definition['type'] == 'Dynamic Link':
        if field != 'party' or party_type not in ('Customer', 'Supplier', 'Employee'):
            frappe.throw('Choose Customer, Supplier or Employee as the party type.')
        target = party_type
    filters = {}
    meta = frappe.get_meta(target)
    if meta.has_field('company'):
        filters['company'] = business.name
    if target == 'Account':
        filters.update(is_group=0, disabled=0)
    text = str(text or '').strip()[:140]
    title = meta.title_field if meta.title_field and meta.has_field(meta.title_field) else 'name'
    rows = frappe.get_list(target, fields=list(dict.fromkeys(['name', title])), filters=filters,
        or_filters={'name': ['like', '%' + text + '%'], title: ['like', '%' + text + '%']} if text else None,
        order_by=title + ' asc', limit_page_length=20, reference_doctype=doctype)
    return [dict(value=row.name, label=row.get(title) or row.name) for row in rows]


@frappe.whitelist()
def payment_accounts(party_type, party, payment_type, posting_date):
    business, _ = context('Payment Entry')
    if party_type not in ('Customer', 'Supplier', 'Employee') or payment_type not in ('Receive', 'Pay'):
        frappe.throw('Choose the payment direction and party type.')
    if party_type == 'Employee':
        from plus_point.setup_flow import linked
        linked('Employee', party, business.name)
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_party_details
    details = get_party_details(business.name, party_type, party, posting_date)
    return dict(account=details['party_account'], currency=details['party_account_currency'])


@frappe.whitelist()
def payment_currencies(paid_from=None, paid_to=None):
    business = company_scope()
    if not (frappe.has_permission('Payment Entry', 'read') or frappe.has_permission('Payment Entry', 'create')):
        frappe.throw('This accounting form is unavailable.', frappe.PermissionError)
    result = {}
    for key, name in [('source', paid_from), ('target', paid_to)]:
        if not name:
            continue
        rows = frappe.get_list('Account', filters={'name': name, 'company': business.name, 'is_group': 0},
            fields=['account_currency'], reference_doctype='Payment Entry', limit_page_length=1)
        if not rows:
            frappe.throw('Choose an accessible account in this company.', frappe.PermissionError)
        result[key] = rows[0].account_currency or business.default_currency
    return result


@frappe.whitelist(methods=['POST'])
def print_data(doctype, name):
    """Preview native printing without inserting a File or changing the document."""
    import base64
    _, doc = context(doctype, name)
    doc.check_permission('print')
    content = frappe.get_print(doctype, name, as_pdf=True)
    return dict(filename=frappe.scrub(doctype) + '-' + str(doc.name).replace('/', '-') + '.pdf',
        mime='application/pdf', content=base64.b64encode(content).decode())
