"""Company-scoped event editing, branded invoices and browser PDF transport."""
import base64
import frappe
from plus_point.setup_flow import linked
from plus_point.operations import company,terms_doc


@frappe.whitelist(methods=['POST'])
def save_venue(plan,values):
    from plus_point.events import plan_doc
    from plus_point.operations import add_requirement,ensure_event_role
    doc=plan_doc(plan,True);terms_doc(doc.contract_terms)
    v=frappe._dict(frappe.parse_json(values) or {})
    frappe.db.savepoint('pp_venue')
    try:
        site=v.get('site')
        if site:
            if linked('PP Site',site).project!=doc.project:frappe.throw('Choose a venue in this event.')
        else:
            from plus_point.locations import address
            location=address(v)
            if not str(v.get('site_name') or '').strip():frappe.throw('Enter the venue name.')
            site=frappe.get_doc(dict(doctype='PP Site',project=doc.project,site_name=v.site_name,is_active=1,**location)).insert().name
        ensure_event_role(v.designation)
        add_requirement(doc.name,dict(site=site,designation=v.designation,phase=v.get('phase') or 'Event',
            start_date=v.get('start_date') or doc.start_date,end_date=v.get('end_date') or doc.end_date,
            workers_required=v.workers_required,wage_rate=v.wage_rate,client_rate=v.get('client_rate') or 0))
        return dict(site=site)
    except Exception:
        frappe.db.rollback(save_point='pp_venue');raise


@frappe.whitelist(methods=['POST'])
def add_worker(plan,values):
    from plus_point.events import plan_doc
    from plus_point.operations import ensure_event_role
    doc=plan_doc(plan,True);terms_doc(doc.contract_terms);v=frappe._dict(frappe.parse_json(values) or {})
    ensure_event_role(v.designation)
    worker=frappe.get_doc(dict(doctype='Employee',company=doc.company,status='Active',create_user_automatically=0,
        **{k:v.get(k) for k in ('first_name','middle_name','last_name','gender','date_of_birth','date_of_joining','cell_number','personal_email','designation')})).insert()
    return dict(name=worker.name,worker=worker.employee_name)


def install():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({
        'PP Work Entry':[dict(fieldname='pp_invoice_amount_snapshot',label='Original invoiced amount',fieldtype='Currency',read_only=1,hidden=1)],
        'Sales Invoice':[dict(fieldname='pp_attendance_correction',label='Attendance correction',fieldtype='Link',options='PP Work Entry',read_only=1)],
        'Company':[dict(fieldname='pp_invoice_email',label='Invoice contact email',fieldtype='Data',options='Email'),
            dict(fieldname='pp_invoice_phone',label='Invoice contact phone',fieldtype='Data'),
            dict(fieldname='pp_invoice_address',label='Invoice address',fieldtype='Small Text')]
    })
    from pathlib import Path
    html=Path(__file__).with_name('templates').joinpath('branded_invoice.html').read_text()
    name='PLUS POINT Branded Invoice'
    doc=frappe.get_doc('Print Format',name) if frappe.db.exists('Print Format',name) else frappe.new_doc('Print Format')
    doc.update(dict(name=name,doc_type='Sales Invoice',module='PLUS POINT',custom_format=1,print_format_type='Jinja',html=html,disabled=0))
    doc.save()


@frappe.whitelist()
def branding():
    doc=company()
    return dict(name=doc.name,title=doc.company_name,logo=doc.company_logo or '',
        email=doc.get('pp_invoice_email') or '',phone=doc.get('pp_invoice_phone') or '',
        address=doc.get('pp_invoice_address') or '',tax_id=doc.tax_id or '')


@frappe.whitelist(methods=['POST'])
def save_branding(values):
    doc=company();doc.check_permission('write');v=frappe._dict(frappe.parse_json(values) or {})
    if v.get('email'):frappe.utils.validate_email_address(v.email,throw=True)
    if 'logo' in v and v.logo:
        if not str(v.logo).lower().endswith(('.png','.jpg','.jpeg','.webp')):frappe.throw('Use a PNG, JPEG or WebP company logo.')
        if not frappe.db.exists('File',{'file_url':v.logo,'attached_to_doctype':'Company','attached_to_name':doc.name}):frappe.throw('Upload a logo attached to your company.')
    for key,target in [('email','pp_invoice_email'),('phone','pp_invoice_phone'),('address','pp_invoice_address'),('tax_id','tax_id'),('logo','company_logo')]:
        if key in v:doc.set(target,v[key])
    doc.save();return branding()


@frappe.whitelist()
def invoice_preview(name):
    from plus_point.operations import invoice
    invoice(name);doc=linked('Sales Invoice',name);doc.check_permission('print')
    return dict(html=frappe.get_print('Sales Invoice',name,print_format='PLUS POINT Branded Invoice',doc=doc))


@frappe.whitelist(methods=['POST'])
def pdf_data(name):
    from plus_point.operations import invoice,invoice_pdf_content
    invoice(name);doc=linked('Sales Invoice',name)
    return dict(filename=name+'.pdf',content=base64.b64encode(invoice_pdf_content(doc)).decode(),mime='application/pdf')
