"""Resolve spreadsheet labels without modifying the uploaded data or bypassing permissions."""
import re
import frappe
from plus_point.setup_flow import linked


LABELS = {'Customer':'customer_name', 'Supplier':'supplier_name', 'Project':'project_name',
          'Employee':'employee_name', 'Item':'item_name', 'Warehouse':'warehouse_name',
          'Account':'account_name', 'PP Site':'site_name'}
EARLIER = {'Customer':'clients', 'Employee':'employees', 'Item':'inventory_items',
           'Warehouse':'warehouses', 'PP Site':'event_sites', 'Project':'events',
           'Sales Invoice':'invoices', 'PP Work Entry':'work', 'PP Milestone':'milestones'}


def find(doctype, value, company, field=None, optional=False, filters=None):
    """Exact IDs win; labels must identify one visible record in the chosen company."""
    value = str(value or '').strip()
    filters = dict(filters or {})
    if doctype in ('Employee','Project','Warehouse','Account','Vehicle'):
        filters['company'] = company
    if doctype == 'PP Site':
        projects = frappe.get_list('Project', filters={'company':company}, pluck='name', limit_page_length=0)
        if 'project' not in filters:filters['project'] = ['in', projects or ['']]
    if value.startswith('import:'):
        from plus_point.imports import record_key
        kind = EARLIER.get(doctype)
        receipt = frappe.db.get_value('PP Import Record', record_key(company,kind,value[7:]),
            ['document_type','document_name'], as_dict=True) if kind else None
        if not receipt:
            frappe.throw(f'{field or doctype}: import ID {value[7:]} is missing. Import the {kind or doctype} template first, then review this file again.')
        doc = linked(receipt.document_type, receipt.document_name)
        if doctype == 'Project' and doc.doctype == 'PP Event Plan':
            value = doc.project
        elif doc.doctype != doctype:
            frappe.throw(f'{field or doctype}: this import ID refers to a different record type')
        else:
            value = doc.name
    if value and frappe.db.exists(doctype,value):
        doc = linked(doctype,value)
        # An exact ID from a different company must never fall back to a label.
        if doc.get('company') and doctype in ('Employee','Project','Warehouse','Account','Vehicle') and doc.company != company:
            frappe.throw(f'{field or doctype}: {doctype} must belong to the selected company')
        if doctype == 'PP Site':linked('Project',doc.project,company)
        return doc.name
    label = LABELS.get(doctype)
    matches = frappe.get_list(doctype, filters=dict(filters, **{label:value}),
        pluck='name', limit_page_length=2) if value and label else []
    if len(matches)>1:
        frappe.throw(f'{field or doctype}: more than one {doctype} matches “{value}”. Use its ID from Download reference IDs.')
    if matches:
        doc=linked(doctype,matches[0])
        if doctype=='PP Site':linked('Project',doc.project,company)
        return matches[0]
    if optional and not value.startswith('import:'):return None
    next_step = f'Import {EARLIER[doctype]} first, or ' if doctype in EARLIER else ''
    frappe.throw(f'{field or doctype}: no matching {doctype} for “{value}”. {next_step}choose an existing ID from Download reference IDs. Names must match one record exactly.')


CLIENT_FIELDS = ['contact_name','email','phone','country','address_line1','address_line2','city','state','postal_code','default_currency']


def choice(value, field, options, aliases=None, default=None):
    """CSV labels are human input; retain strict meaning without strict casing."""
    def key(text):return re.sub(r'[\s_-]+',' ',str(text or '').strip().casefold())
    choices={key(option):option for option in options}
    choices.update({key(label):canonical for label,canonical in (aliases or {}).items()})
    if not str(value or '').strip() and default is not None:return default
    result=choices.get(key(value))
    if result is None:
        frappe.throw(f'{field}: “{value or "(blank)"}” is not supported. Use '+ ' or '.join(options)+'. Capitalization does not matter.')
    return result


def customer_type(value, default='Company'):
    return choice(value,'customer_type',('Company','Individual'),
        {'business':'Company','corporate':'Company','organization':'Company','organisation':'Company',
         'person':'Individual','personal':'Individual'},default)


def client_values(row, prefix=''):
    return dict(customer_name=row.get('customer_name') or row.get('customer'),
        customer_type=customer_type(row.get('customer_type')),
        **{key:row.get(prefix+key,'') for key in CLIENT_FIELDS})


def validate_client(values):
    """Optional complete contact/address profile; a legacy name-only file stays usable."""
    from plus_point.input_rules import check
    from plus_point.locations import address
    if not values.get('customer_name'):frappe.throw('Enter customer_name for the new client')
    if len(values['customer_name'])>140:frappe.throw('Client name must be 140 characters or fewer')
    if values.get('customer_type') not in ('Company','Individual'):frappe.throw('customer_type must be Company or Individual')
    full = any(values.get(key) for key in CLIENT_FIELDS if key != 'default_currency')
    if full:
        if not values.get('contact_name'):frappe.throw('Enter contact_name for the client contact profile')
        if len(values['contact_name'])>140:frappe.throw('Client contact name must be 140 characters or fewer')
        if not values.get('email') and not values.get('phone'):frappe.throw('Enter client email or phone')
        check('contact_name',values['contact_name']);check('phone',values.get('phone'))
        if values.get('email'):frappe.utils.validate_email_address(values['email'],throw=True)
        address(values)
    if values.get('default_currency'):linked('Currency',values['default_currency'])
    return full


def normalize(kind, company, original):
    row = dict(original)
    notes = []
    def ref(key, doctype, **options):
        before = row.get(key,'')
        row[key] = find(doctype,before,company,key,**options)
        if before != row[key]:notes.append(f'{key}: {before} → {row[key]}')
    def select(key, options, aliases=None, default=None):
        before=row.get(key,'')
        row[key]=choice(before,key,options,aliases,default)
        if before!=row[key]:notes.append(f'{key}: {before or "(blank)"} → {row[key]}')
    if kind in ('employees','event_sites','vehicles','inventory_items'):
        select('status',('Active','Inactive'))
    if kind=='employees' and row.get('gender'):
        select('gender',frappe.get_list('Gender',pluck='name',limit_page_length=0))
    if kind=='vehicles':
        select('fuel_type',('Petrol','Diesel','Natural Gas','Electric'))
        select('cargo_uom',('units','kg','m³'),{'m3':'m³','cubic metres':'m³','cubic meters':'m³'})
    if kind=='invoices' and row.get('source_type'):
        select('source_type',('PP Work Entry','PP Milestone'))
    if kind=='events':
        select('billing_model',('Daily','Fixed'),{'per_worker':'Daily','per worker day':'Daily','fixed price':'Fixed'})
        if row['billing_model']=='Fixed':
            from plus_point.events import positive
            if positive(row.get('client_rate'),'Client daily rate',allow_zero=True):
                row['client_rate']='0'
                notes.append('Fixed-price event: client_rate is unused and will be saved as 0. The fixed_amount is the client contract total; crew wages stay separate.')
    if kind == 'employees':return row, notes
    if kind == 'clients':
        value = row.get('customer') or row.get('customer_name')
        row['customer'] = find('Customer',value,company,'customer',optional=True) or ''
        before=row.get('customer_type','')
        default=linked('Customer',row['customer']).customer_type if row['customer'] else 'Company'
        row['customer_type']=customer_type(before,default)
        if before!=row['customer_type']:notes.append(f'customer_type: {before or "(blank)"} → {row["customer_type"]}')
        if row['customer'] and value!=row['customer']:notes.append(f'Client: {value} → {row["customer"]}')
    elif kind == 'event_sites':
        ref('project','Project')
        value = row.get('site') or row.get('site_name')
        row['site'] = find('PP Site',value,company,'site',optional=not bool(row.get('site')),
            filters={'project':row['project']}) or ''
        if row['site'] and linked('PP Site',row['site']).project != row['project']:
            frappe.throw('site must belong to the selected event project')
    elif kind == 'warehouses':
        row['_warehouse'] = find('Warehouse',row.get('warehouse_name'),company,'warehouse_name',optional=True) or ''
    elif kind == 'stock_balances':
        ref('item_code','Item',filters={'is_stock_item':1});ref('warehouse','Warehouse')
    elif kind == 'events':
        value = row.get('customer') or row.get('customer_name')
        if not value:frappe.throw('Enter customer: the client name or an existing Customer ID')
        existing = find('Customer',value,company,'customer',optional=True)
        if existing:
            row['customer'] = existing
            if value!=existing:notes.append(f'Client: {value} → {existing}')
        else:
            row['customer_name'] = row.get('customer_name') or value
            before=row.get('customer_type','')
            row['customer_type']=customer_type(before)
            if before and before!=row['customer_type']:notes.append(f'customer_type: {before} → {row["customer_type"]}')
            values = client_values(row,'client_')
            full = validate_client(values)
            frappe.has_permission('Customer','create',throw=True)
            if full:
                for doctype in ('Contact','Address'):frappe.has_permission(doctype,'create',throw=True)
            row['_new_client'] = values
            notes.append('Create client: '+values['customer_name']+(' with contact and address' if full else ' (basic profile; add contact and address later)'))
    elif kind == 'work':ref('assignment','PP Assignment')
    elif kind == 'milestones':ref('contract_terms','PP Contract Terms')
    elif kind == 'receipts':
        ref('invoice','Sales Invoice');ref('bank_account','Account',filters={'is_group':0,'account_type':['in',['Bank','Cash']]})
    elif kind in ('worker_payments','expenses','invoices'):
        ref('project','Project')
        if kind == 'worker_payments':
            ref('employee','Employee');ref('bank_account','Account',filters={'is_group':0,'account_type':['in',['Bank','Cash']]})
        else:
            ref('supplier' if kind=='expenses' else 'customer','Supplier' if kind=='expenses' else 'Customer')
            ref('item_code','Item',filters={'is_stock_item':0,'disabled':0})
            if kind=='invoices' and row.get('source_type') in ('PP Work Entry','PP Milestone') and row.get('source_name'):
                ref('source_name',row['source_type'])
    return row, notes
