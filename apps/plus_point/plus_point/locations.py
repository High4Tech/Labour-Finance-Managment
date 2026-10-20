"""Structured addresses and optional map coordinates, using local country data."""
import math
import frappe
from plus_point.setup_flow import linked,require_customer


@frappe.whitelist()
def country_defaults(country):
    require_customer();linked('Country',country)
    from frappe.geo.country_info import get_country_info
    info=get_country_info(country)
    code=info.get('currency')
    if not code or not frappe.db.exists('Currency',code):frappe.throw('No default currency is configured for this country. Contact High4Tech to configure it.')
    return dict(country=country,currency=code,currency_name=info.get('currency_name'),code=info.get('code'))


def currency_locked(company):
    if not company:return False
    if frappe.db.exists('GL Entry',{'company':company}) or frappe.db.exists('Stock Ledger Entry',{'company':company}):return True
    projects=frappe.get_all('Project',filters={'company':company},pluck='name')
    if projects and frappe.db.exists('PP Contract Terms',{'project':['in',projects]}):return True
    return frappe.get_doc('Company',company).check_if_transactions_exist()


def set_company_country(doc,country):
    defaults=country_defaults(country)
    if currency_locked(doc.name):
        if country!=doc.country:frappe.throw('Country and base currency are fixed after agreements or accounting entries. Event venues can use other countries.')
        return
    old=doc.default_currency;new=defaults['currency']
    if old==new and country==doc.country:return
    frappe.db.set_value('Currency',new,'enabled',1)
    if old!=new:
        # Native Account validation permits a currency change only before GL.
        # Change only accounts in the previous base currency; preserve any
        # deliberately configured foreign-currency accounts.
        for name in frappe.get_all('Account',filters={'company':doc.name,'is_group':0},pluck='name'):
            account=frappe.get_doc('Account',name)
            if not account.account_currency or account.account_currency==old:
                account.account_currency=new;account.save()
        frappe.clear_cache(doctype='Account')
    doc.country=country;doc.default_currency=new;doc.save()


def address(values,required=True):
    result={key:str(values.get(key) or '').strip() for key in ('address_line1','address_line2','city','state','country','postal_code')}
    if required:
        for key,label in [('country','Country'),('city','City'),('address_line1','Street address')]:
            if not result[key]:frappe.throw(f'Enter the {label.lower()} before continuing')
    for key,value in result.items():
        if len(value)>240:frappe.throw('Address fields must be 240 characters or fewer')
    if result['country']:linked('Country',result['country'])
    return result


def coordinates(values):
    lat=values.get('latitude');lon=values.get('longitude')
    if lat in (None,'') and lon in (None,''):return {}
    try:
        lat=float(lat);lon=float(lon)
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90<=lat<=90 or not -180<=lon<=180:raise ValueError()
    except (TypeError,ValueError):frappe.throw('Choose a valid map point or clear both coordinates')
    return dict(latitude=lat,longitude=lon)


def site_values(values,required=True):
    data=address(values,required)
    data.update(coordinates(values))
    data['address']='\n'.join(data[k] for k in ('address_line1','address_line2','city','state','postal_code','country') if data.get(k))
    return data
