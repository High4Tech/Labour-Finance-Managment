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
    from plus_point.locations import country_defaults
    currency=values.get('default_currency') or customer.default_currency or country_defaults(data['country'])['currency']
    linked('Currency',currency);frappe.db.set_value('Currency',currency,'enabled',1)
    customer.default_currency=currency
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
    result=dict(name=doc.name,title=doc.customer_name,customer_name=doc.customer_name,customer_type=doc.customer_type,default_currency=doc.default_currency or '',
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


# React product boundary. Customer/Contact/Address remain native records and
# their controllers/permissions still validate every write.
PROFILE_FIELDS = ('customer_name','customer_type','contact_name','email','phone',
    'country','default_currency','city','state','address_line1','address_line2','postal_code')


def profile_revision(doc):
    from hashlib import sha256
    versions = [str(doc.modified)]
    for dt, name in [('Contact',doc.customer_primary_contact),('Address',doc.customer_primary_address)]:
        if name:
            linked_doc = linked(dt,name)
            versions.append(str(linked_doc.modified))
    return sha256('|'.join(versions).encode()).hexdigest()


@frappe.whitelist()
def rows(search='',status='',page=1):
    from plus_point.operations import company
    company();frappe.has_permission('Customer','read',throw=True)
    if status not in ('','Active','Inactive'):frappe.throw('Choose All, Active or Inactive clients.')
    page=max(1,min(501,frappe.utils.cint(page)));filters={}
    if status:filters['disabled']=int(status=='Inactive')
    text=str(search or '').strip()[:140]
    found=frappe.get_list('Customer',filters=filters,or_filters={
        'customer_name':['like','%'+text+'%'],'name':['like','%'+text+'%']} if text else None,
        fields=['name','customer_name','customer_type','default_currency','disabled'],
        order_by='customer_name,name',limit_start=(page-1)*20,limit_page_length=21)
    return dict(rows=found[:20],page=page,more=len(found)>20,
        can_create=bool(frappe.has_permission('Customer','create')),
        can_delete=bool(frappe.has_permission('Customer','delete')))


@frappe.whitelist()
def profile(customer):
    from plus_point.operations import company
    business=company();doc=linked('Customer',customer)
    result=details(customer)
    result.update(disabled=bool(doc.disabled),revision=profile_revision(doc),
        can_edit=bool(doc.has_permission('write')),can_delete=bool(doc.has_permission('delete')))
    projects=frappe.get_list('Project',filters={'company':business.name,'customer':doc.name},
        pluck='name',limit_page_length=0)
    result['agreements']=frappe.get_list('PP Contract Terms',filters={'project':['in',projects or ['']],
        'event_basis':0},fields=['name','agreement_title','pp_reference','status','effective_start','effective_end'],
        order_by='modified desc',limit_page_length=20) if frappe.has_permission('PP Contract Terms','read') else []
    result['events']=frappe.get_list('PP Event Plan',filters={'company':business.name,'project':['in',projects or ['']]},
        fields=['name','event_name','pp_reference','planning_state','start_date','end_date'],
        order_by='modified desc',limit_page_length=20) if frappe.has_permission('PP Event Plan','read') else []
    return result


@frappe.whitelist()
def form(customer=None):
    from plus_point.operations import company
    business=company();doc=linked('Customer',customer) if customer else None
    frappe.has_permission('Customer','write' if doc else 'create',doc=doc,throw=True)
    return dict(values=details(customer) if doc else dict(customer_type='Company',country=business.country,
        default_currency=business.get('pp_invoice_currency') or business.default_currency),
        revision=profile_revision(doc) if doc else None,
        countries=frappe.get_list('Country',pluck='name',order_by='name',limit_page_length=0),
        currencies=frappe.get_list('Currency',pluck='name',order_by='name',limit_page_length=0))


@frappe.whitelist(methods=['POST'])
def save_profile(values,customer=None,revision=None):
    from plus_point.operations import company
    from plus_point.benefits import atomic

    @atomic
    def persist():
        company();data=frappe.parse_json(values)
        if not isinstance(data,dict) or set(data)-set(PROFILE_FIELDS):
            frappe.throw('Use the client profile fields to update this record.')
        if customer:
            frappe.db.get_value('Customer',customer,'modified',for_update=True)
            doc=linked('Customer',customer);doc.check_permission('write')
            # Lock the underlying profiles too: an accounting/native view may
            # update the contact/address without modifying Customer itself.
            for dt,name in [('Contact',doc.customer_primary_contact),('Address',doc.customer_primary_address)]:
                if name:frappe.db.get_value(dt,name,'modified',for_update=True)
            if not revision or revision!=profile_revision(doc):
                frappe.throw('This client changed elsewhere. Reload the profile before saving.',frappe.TimestampMismatchError)
        else:frappe.has_permission('Customer','create',throw=True)
        if data.get('customer_type') not in ('Company','Individual'):frappe.throw('Choose Company or Individual.')
        doc=save(data,customer)
        return dict(name=doc.name,revision=profile_revision(doc))
    return persist()
