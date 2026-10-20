"""Client profiles use native Customer, Contact and Address records."""
import frappe
from plus_point.setup_flow import linked,insert,require_customer
from plus_point.locations import address


def create(values):
    name=str(values.get('customer_name') or '').strip();person=str(values.get('contact_name') or '').strip()
    if not name:frappe.throw('Enter the client name')
    if not person:frappe.throw('Enter the client contact person')
    email=str(values.get('email') or '').strip();phone=str(values.get('phone') or '').strip()
    if not email and not phone:frappe.throw('Enter an email or phone number for the client contact')
    if email:email=frappe.utils.validate_email_address(email,throw=True)
    data=address(values)
    if len(name)>140 or len(person)>140 or len(phone)>40:frappe.throw('Check the client name and contact lengths')
    customer=insert('Customer',customer_name=name,customer_type=values.get('customer_type') or 'Company',customer_group='Commercial',territory='All Territories')
    contact=insert('Contact',first_name=person,links=[dict(link_doctype='Customer',link_name=customer.name)],
        email_ids=[dict(email_id=email,is_primary=1)] if email else [],phone_nos=[dict(phone=phone,is_primary_phone=1)] if phone else [])
    postal=insert('Address',address_title=name,address_type='Billing',address_line1=data['address_line1'],address_line2=data['address_line2'],
        city=data['city'],state=data['state'],country=data['country'],pincode=data['postal_code'],email_id=email,phone=phone,
        is_primary_address=1,links=[dict(link_doctype='Customer',link_name=customer.name)])
    customer.customer_primary_contact=contact.name;customer.customer_primary_address=postal.name;customer.save()
    return customer


@frappe.whitelist()
def details(customer):
    require_customer();doc=linked('Customer',customer)
    result=dict(name=doc.name,title=doc.customer_name,email='',phone='',contact_name='',address='')
    if doc.customer_primary_contact:
        c=linked('Contact',doc.customer_primary_contact)
        result.update(email=c.email_id or '',phone=c.phone or c.mobile_no or '',contact_name=c.full_name or c.first_name)
    if doc.customer_primary_address:
        a=linked('Address',doc.customer_primary_address)
        result['address']=', '.join(filter(None,[a.address_line1,a.city,a.state,a.country]))
    return result
