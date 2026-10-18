"""Local demo acquisition flow. No payments, passwords or tenant access are created."""
import hashlib
import secrets

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime, validate_email_address


def require_demo():
    if not frappe.conf.get('pp_control_plane') or not frappe.local.site.endswith('.localhost'):
        frappe.throw('Demo signup is available on the local High4Tech site only', frappe.PermissionError)


def plans():
    require_demo()
    rows=frappe.get_all('Subscription Plan', filters={'pp_public_plan':1,'price_determination':'Fixed Rate'},
        fields=['name','plan_name','cost','currency','billing_interval','billing_interval_count','pp_plan_summary'],order_by='cost asc')
    return [dict(name=r.name,title=r.plan_name,amount=str(r.cost),currency=r.currency,
        interval=f'{r.billing_interval_count} {r.billing_interval.lower()}',summary=r.pp_plan_summary or '') for r in rows if r.cost>0]


def public_state(doc):
    return dict(reference=doc.name,business=doc.business_name,plan=doc.plan,amount=str(doc.amount),currency=doc.currency,
        interval=doc.interval,status=doc.review_status,payment=doc.payment_status,demo=True)


def request_for_token(reference, token):
    require_demo()
    if not isinstance(token,str) or len(token)!=64 or not isinstance(reference,str) or len(reference)>140:
        frappe.throw('Invalid signup reference',frappe.PermissionError)
    try:
        doc=frappe.get_doc('PP Signup Request',reference,for_update=True)
    except frappe.DoesNotExistError:
        frappe.throw('Invalid signup reference',frappe.PermissionError)
    if not secrets.compare_digest(doc.token_hash or '',hashlib.sha256(token.encode()).hexdigest()):
        frappe.throw('Invalid signup reference',frappe.PermissionError)
    return doc


@frappe.whitelist(allow_guest=True,methods=['POST'])
@rate_limit(limit=5,seconds=60)
def register(contact_name,business_name,email,plan,website=''):
    require_demo()
    if website:
        frappe.throw('Unable to register')
    values={}
    for key,value in dict(contact_name=contact_name,business_name=business_name,email=email).items():
        if not isinstance(value,str) or not value.strip() or len(value)>140:
            frappe.throw('Enter a name, business and valid email (up to 140 characters each)')
        values[key]=value.strip()
    values['email']=validate_email_address(values['email'],throw=True).lower()
    selected=next((row for row in plans() if row['name']==plan),None)
    if not selected:
        frappe.throw('Choose a currently published plan')
    token=secrets.token_hex(32)
    doc=frappe.get_doc(dict(doctype='PP Signup Request',**values,plan=selected['name'],amount=selected['amount'],
        currency=selected['currency'],interval=selected['interval'],token_hash=hashlib.sha256(token.encode()).hexdigest()))
    doc.flags.public_signup=True
    doc.insert(ignore_permissions=True)
    return dict(**public_state(doc),token=token)


@frappe.whitelist(allow_guest=True,methods=['POST'])
@rate_limit(limit=30,seconds=60)
def status(reference,token):
    return public_state(request_for_token(reference,token))


@frappe.whitelist(allow_guest=True,methods=['POST'])
@rate_limit(limit=10,seconds=60)
def simulate_payment(reference,token):
    doc=request_for_token(reference,token)
    if doc.review_status=='Pending payment':
        doc.payment_status='Demo payment submitted';doc.review_status='Awaiting approval'
        doc.flags.public_signup=True;doc.save(ignore_permissions=True)
    return public_state(doc)


@frappe.whitelist(methods=['POST'])
def review(reference,decision):
    from plus_point.platform import require_platform
    require_platform();require_demo()
    if decision not in ('Approved','Rejected'):
        frappe.throw('Choose approve or reject')
    doc=frappe.get_doc('PP Signup Request',reference,for_update=True)
    if doc.review_status!='Awaiting approval' or doc.payment_status!='Demo payment submitted':
        frappe.throw('Only requests with a submitted demo payment can be reviewed')
    doc.review_status=decision;doc.reviewed_by=frappe.session.user;doc.reviewed_on=now_datetime()
    doc.save(ignore_permissions=True)
    return public_state(doc)


def page_context(context):
    context.no_cache=1
    if not frappe.conf.get('pp_control_plane'):
        if frappe.local.site.endswith('.localhost'):
            frappe.local.flags.redirect_location='http://platform.localhost:8000/plans'
            raise frappe.Redirect
        raise frappe.DoesNotExistError
    require_demo()
    context.plans=plans()
    context.no_breadcrumbs=1
    return context


def enable_local_demo_plan():
    """Operator-only; publish the existing labelled demo plan without changing its price."""
    from plus_point.platform import require_platform
    require_platform();require_demo()
    doc=frappe.get_doc('Subscription Plan','PLUS POINT Local Trial Plan')
    doc.pp_public_plan=1
    doc.pp_plan_summary='A sample monthly plan for exploring PLUS POINT. High4Tech reviews every demo signup.'
    doc.save()
    frappe.db.commit()
    return 'Existing sample plan published; no price, invoice or subscription changed'


def cleanup_browser_request(reference):
    """Operator-only cleanup for the exact generated signup browser fixture."""
    require_demo()
    if not frappe.conf.get('allow_tests'):
        raise RuntimeError('Tests must be enabled')
    doc=frappe.get_doc('PP Signup Request',reference)
    if doc.business_name!='QA Signup Browser' or not doc.email.endswith('@signup-test.example'):
        raise RuntimeError('Refusing to remove a non-test signup')
    frappe.delete_doc('PP Signup Request',reference,ignore_permissions=True)
    frappe.db.commit()
    return 'Exact browser signup fixture removed'

