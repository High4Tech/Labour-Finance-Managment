"""Stable human references and explicit agreement/display currency boundaries."""
from decimal import Decimal
import frappe
from copy import deepcopy
from frappe.model.naming import make_autoname
from plus_point.finance import money

REFERENCES={'PP Contract Terms':'AGR','PP Event Plan':'EVT','PP Site':'SITE','Project':'PRJ','Customer':'CLT','Employee':'WRK','PP Assignment':'ASG','PP Milestone':'MIL','PP Daily Register':'ATT','Vehicle':'VEH','Item':'ITEM','Warehouse':'WH','Sales Invoice':'INV','Payment Entry':'PAY','Purchase Invoice':'COST','PP Equipment Booking':'EQB','PP Vehicle Booking':'TRP','PP Wage Settlement':'WAGE'}

def before_insert(doc,method=None):
    if doc.doctype in REFERENCES and doc.meta.has_field('pp_reference'):
        doc.pp_reference=make_autoname(REFERENCES[doc.doctype]+'-.YYYY.-.#####',doc=doc)

def protect_reference(doc,method=None):
    old=doc.get_doc_before_save()
    if old and old.get('pp_reference') and doc.get('pp_reference')!=old.pp_reference:frappe.throw('Tracking IDs cannot be changed.')

def install():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    create_custom_fields({dt:[dict(fieldname='pp_reference',label='Tracking ID',fieldtype='Data',read_only=1,no_copy=1,search_index=1,in_standard_filter=1)] for dt in REFERENCES})
    create_custom_fields({'PP Contract Terms':[
        dict(fieldname='pp_agreement_currency',label='Agreement currency',fieldtype='Link',options='Currency'),
        dict(fieldname='pp_agreement_rate',label='Accounting currency per agreement unit',fieldtype='Float',precision=9)]})
    for dt,prefix in REFERENCES.items():
        for row in frappe.get_all(dt,fields=['name','creation'],filters={'pp_reference':['is','not set']},order_by='creation,name',limit_page_length=0):
            year=str(row.creation)[:4];frappe.db.set_value(dt,row.name,'pp_reference',make_autoname(prefix+'-'+year+'-.#####'),update_modified=False)
        meta=frappe.get_meta(dt);fields=[s.strip() for s in (meta.search_fields or '').split(',') if s.strip()]
        if 'pp_reference' not in fields:make_property_setter(dt,None,'search_fields',','.join(fields+['pp_reference']),'Data',validate_fields_for_doctype=False)

def rate_values(business,values,old=None):
    """Normalize only explicitly currency-tagged input. Old API callers use base units."""
    v=frappe._dict(deepcopy(frappe.parse_json(values) or {}))
    if not v.get('agreement_currency'):return v
    currency=v.agreement_currency
    frappe.get_doc('Currency',currency).check_permission('read')
    from plus_point.events import positive
    rate=Decimal(1) if currency==business.default_currency else positive(v.get('agreement_rate'),'Agreement exchange rate')
    if old and (old.get('pp_agreement_currency') or old.currency,Decimal(str(old.get('pp_agreement_rate') or 1)))!=(currency,rate):
        if any(frappe.db.exists(dt,{'contract_terms':old.name}) for dt in ['PP Assignment','PP Work Entry','PP Milestone']):frappe.throw('This agreement already has activity. Its saved currency and exchange rate are fixed; choose another invoice currency when billing.')
    if 'fixed_amount' in v:v.fixed_amount=float(money(Decimal(str(v.fixed_amount or 0))*rate))
    for row in v.get('staffing',[]):
        for key in ['wage_rate','client_rate']:row[key]=float(money(Decimal(str(row.get(key) or 0))*rate))
    for row in v.get('milestones',[]):row['amount']=float(money(Decimal(str(row.get('amount') or 0))*rate))
    v.pp_agreement_currency=currency;v.pp_agreement_rate=float(rate)
    return v

def agreement_units(data):
    data['agreement_currency']=data.get('pp_agreement_currency') or data['currency']
    data['agreement_rate']=data.get('pp_agreement_rate') or 1
    return data

@frappe.whitelist(methods=['POST'])
def display_currency(currency):
    from plus_point.setup_flow import require_customer
    from plus_point.exchange import DISPLAY_CURRENCIES
    from plus_point.operations import company
    require_customer();base=company().default_currency
    if currency not in set(DISPLAY_CURRENCIES)|{base}:frappe.throw('Choose an available display currency.')
    frappe.defaults.set_user_default('pp_display_currency',currency)
    return dict(currency=currency)
