"""Client profiles use native Customer, Contact and Address records."""
import frappe
from plus_point.setup_flow import linked,insert,require_customer
from plus_point.locations import address


def create(values):
    return save(values)


def save(values,customer=None):
    name=str(values.get('customer_name') or '').strip();person=str(values.get('contact_name') or '').strip()
    if not name:frappe.throw('Enter the client name')
    if not person:frappe.throw('Enter the client contact person')
    email=str(values.get('email') or '').strip();phone=str(values.get('phone') or '').strip()
    if not email and not phone:frappe.throw('Enter an email or phone number for the client contact')
    if email:email=frappe.utils.validate_email_address(email,throw=True)
    data=address(values)
    if len(name)>140 or len(person)>140 or len(phone)>40:frappe.throw('Check the client name and contact lengths')
    customer=linked('Customer',customer) if customer else frappe.new_doc('Customer')
    customer.update(dict(customer_name=name,customer_type=values.get('customer_type') or 'Company',customer_group=customer.customer_group or 'Commercial',territory=customer.territory or 'All Territories'))
    customer.save()
    def profile(doctype,previous):
        doc=linked(doctype,previous) if previous else frappe.new_doc(doctype)
        # A primary contact/address shared by another client must not be overwritten.
        if previous and any(r.link_doctype=='Customer' and r.link_name!=customer.name for r in doc.links):doc=frappe.new_doc(doctype)
        if doc.is_new():doc.append('links',dict(link_doctype='Customer',link_name=customer.name))
        doc.check_permission('create' if doc.is_new() else 'write')
        return doc
    contact=profile('Contact',customer.customer_primary_contact)
    contact.update(dict(first_name=person,middle_name='',last_name=''))
    contact.set('email_ids',[r.as_dict() for r in contact.email_ids if not r.is_primary and r.email_id!=email])
    if email:contact.append('email_ids',dict(email_id=email,is_primary=1))
    contact.set('phone_nos',[r.as_dict() for r in contact.phone_nos if not r.is_primary_phone and r.phone!=phone])
    if phone:contact.append('phone_nos',dict(phone=phone,is_primary_phone=1))
    contact.save()
    postal=profile('Address',customer.customer_primary_address)
    postal.update(dict(address_title=name,address_type='Billing',address_line1=data['address_line1'],address_line2=data['address_line2'],
        city=data['city'],state=data['state'],country=data['country'],pincode=data['postal_code'],email_id=email,phone=phone,
        is_primary_address=1))
    postal.save()
    customer.customer_primary_contact=contact.name;customer.customer_primary_address=postal.name;customer.save()
    return customer


@frappe.whitelist()
def details(customer):
    require_customer();doc=linked('Customer',customer)
    result=dict(name=doc.name,title=doc.customer_name,customer_name=doc.customer_name,customer_type=doc.customer_type,
        email='',phone='',contact_name='',address='',country='',city='',state='',address_line1='',address_line2='',postal_code='')
    if doc.customer_primary_contact:
        c=linked('Contact',doc.customer_primary_contact)
        result.update(email=c.email_id or '',phone=c.phone or c.mobile_no or '',contact_name=c.full_name or c.first_name)
    if doc.customer_primary_address:
        a=linked('Address',doc.customer_primary_address)
        result['address']=', '.join(filter(None,[a.address_line1,a.city,a.state,a.country]))
        result.update({k:a.get(k) or '' for k in ('country','city','state','address_line1','address_line2')})
        result['postal_code']=a.pincode or ''
    return result
