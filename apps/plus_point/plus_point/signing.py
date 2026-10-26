"""Expiring agreement links, immutable client-visible snapshots and explicit acceptance."""
import hashlib,secrets
from contextlib import contextmanager
import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import now_datetime,add_to_date,get_datetime,escape_html as e

@contextmanager
def operation():
    previous=frappe.flags.get('pp_signing_operation');frappe.flags.pp_signing_operation=True
    try:yield
    finally:frappe.flags.pp_signing_operation=previous

def snapshot(name):
    from plus_point.operations import agreement
    a=agreement(name);company=frappe.get_doc('Company',a['client_company']);rate=a['agreement_rate'];currency=a['agreement_currency'];venues={r.name:r.site_name for r in a['venues']}
    amount=lambda v:f'{float(v or 0)/rate:,.2f} {currency}'
    locations={r.name:', '.join(str(r.get(k) or '') for k in ('address_line1','city','country') if r.get(k)) for r in a['venues']}
    rows=''.join(f'<tr><td>{e(venues.get(r.site,r.site))}<br><small>{e(locations.get(r.site,""))}</small></td><td>{e(r.designation)}<br><small>{e(r.phase or "Event")}</small></td><td>{int(r.workers_required)}</td><td>{e(amount(r.client_rate)) if a["billing_model"]=="Daily" else "Included"}</td></tr>' for r in a['staffing'])
    milestones=''.join(f'<tr><td>{e(r.milestone_title)}</td><td>{e(str(r.due_date or ""))}</td><td>{e(amount(r.amount))}</td></tr>' for r in a['milestones'])
    checkpoints=''.join('<tr><td>'+e(r['title'])+'</td><td>'+e(r['from_date'])+' - '+e(r['to_date'])+'</td><td>'+e(r['due_date'])+'</td></tr>' for r in frappe.parse_json(a.get('pp_daily_checkpoints') or '[]'))
    conditions=''.join('<li>'+e(c)+'</li>' for c in frappe.parse_json(a.get('pp_conditions') or '[]'))
    resources=''
    requirements=frappe.parse_json(a.get('pp_transport_requirements') or '[]')
    resources+=''.join('<li>'+e(str(r['quantity']))+' × '+e(r['vehicle_type'])+' · '+e(r.get('site_name') or 'All sites')+'</li>' for r in requirements)
    contact_line=' · '.join(str(a['client'].get(k) or '') for k in ('email','phone') if a['client'].get(k))
    logo=f'<img alt="" src="{e(company.company_logo)}" style="max-width:160px;max-height:70px">' if company.company_logo and not company.company_logo.startswith('/private/') else ''
    return f'''<article class="agreement-document">{logo}<p>{e(company.company_name)} · {e(a.get('pp_reference') or '')}</p><h1>{e(a['agreement_title'])}</h1><p>Client: <strong>{e(a['client']['title'])}</strong></p><p>{e(str(a['effective_start']))} – {e(str(a['effective_end']))}</p><h2>Client details</h2><p>{e(a['client'].get('contact_name') or '')}<br>{e(contact_line)}<br>{e(', '.join(str(a['client'].get(k) or '') for k in ('address_line1','city','country') if a['client'].get(k)))}</p><h2>Agreed scope</h2><p>{e(frappe.utils.strip_html(a['scope'] or '')).replace(chr(10),'<br>')}</p>{'<h2>Conditions</h2><ol>'+conditions+'</ol>' if conditions else ''}<h2>Pricing</h2><p>{e(a['billing_model'])} billing{': '+e(amount(a['fixed_amount'])) if a['billing_model']=='Fixed' else ''}</p><table><thead><tr><th>Site</th><th>Crew category</th><th>Crew / day</th><th>Client pricing</th></tr></thead><tbody>{rows}</tbody></table>{'<h2>Payment milestones</h2><table><thead><tr><th>Milestone</th><th>Due</th><th>Amount</th></tr></thead><tbody>'+milestones+'</tbody></table>' if milestones else ''}{'<h2>Daily billing milestones</h2><p>Invoices use approved attendance only.</p><table><thead><tr><th scope="col">Milestone</th><th scope="col">Attendance period</th><th scope="col">Payment due</th></tr></thead><tbody>'+checkpoints+'</tbody></table>' if checkpoints else ''}{'<h2>Agreed vehicles</h2><ul>'+resources+'</ul>' if resources else ''}</article>'''

def digest(html):return hashlib.sha256(html.encode()).hexdigest()

@frappe.whitelist()
def status(name):
    from plus_point.operations import terms_doc
    terms_doc(name)
    rows=frappe.get_list('PP Agreement Share',filters={'contract_terms':name},fields=['name','status','expires','recipient','signed_by','signed_on'],order_by='creation desc',limit_page_length=10)
    return dict(requests=rows,email_configured=bool(frappe.db.exists('Email Account',{'enable_outgoing':1})))

@frappe.whitelist(methods=['POST'])
def create_link(name):
    from plus_point.operations import terms_doc
    doc=terms_doc(name,True);frappe.has_permission('PP Agreement Share','create',throw=True)
    frappe.db.get_value('PP Contract Terms',name,'name',for_update=True)
    html=snapshot(name);token=secrets.token_urlsafe(40)
    with operation():
        for pending in frappe.get_all('PP Agreement Share',filters={'contract_terms':name,'status':'Pending'},pluck='name'):
            old=frappe.get_doc('PP Agreement Share',pending);old.status='Revoked';old.save()
        share=frappe.get_doc(dict(doctype='PP Agreement Share',contract_terms=name,token_hash=digest(token),expires=add_to_date(now_datetime(),days=7),snapshot=html,digest=digest(html),status='Pending')).insert()
    from plus_point.clients import details
    customer=frappe.db.get_value('Project',doc.project,'customer');recipient=details(customer).get('email') or ''
    return dict(name=share.name,url=frappe.utils.get_url('/agree?token='+token),recipient=recipient,expires=str(share.expires))

@frappe.whitelist(methods=['POST'])
def send_link(name,share,token,recipient,cc="",pdf_file=None):
    from plus_point.operations import terms_doc
    terms_doc(name,True);doc=public_doc(token)
    if doc.name!=share or doc.contract_terms!=name or doc.status!='Pending':frappe.throw('Create a current signing link before sending.')
    from plus_point.agreement_documents import recipients
    to,copies=recipients(recipient,cc)
    if not frappe.db.exists('Email Account',{'enable_outgoing':1}):frappe.throw('Configure an outgoing Email Account first. You can copy the signing link instead.')
    url=frappe.utils.get_url('/agree?token='+token)
    attachments=[]
    if pdf_file:
        file=frappe.get_doc('File',pdf_file);file.check_permission('read')
        if file.attached_to_doctype!='Contract' or file.attached_to_name!=frappe.db.get_value('PP Contract Terms',name,'contract'):frappe.throw('Choose a document from this agreement.')
        attachments=[dict(fname=file.file_name,fcontent=file.get_content())]
    frappe.sendmail(recipients=to,cc=copies,attachments=attachments,subject='Agreement ready for review',message=f'<p>Please review and sign your agreement.</p><p><a href="{e(url)}">Review agreement</a></p>',reference_doctype='PP Contract Terms',reference_name=name)
    with operation():doc.recipient=recipient;doc.save()
    return dict(queued=True)

def public_doc(token,lock=False):
    if not isinstance(token,str) or not 35<=len(token)<=100:frappe.throw('This agreement link is invalid or expired.',frappe.PermissionError)
    name=frappe.db.get_value('PP Agreement Share',{'token_hash':digest(token)},'name')
    if not name:frappe.throw('This agreement link is invalid or expired.',frappe.PermissionError)
    doc=frappe.get_doc('PP Agreement Share',name,for_update=lock)
    if doc.status=='Revoked' or get_datetime(doc.expires)<now_datetime():frappe.throw('This agreement link is invalid or expired.',frappe.PermissionError)
    return doc

@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30,seconds=60)
def review(token):
    doc=public_doc(token)
    return dict(html=doc.snapshot,status=doc.status,signed_by=doc.signed_by,signed_on=doc.signed_on,reference=doc.name,digest=doc.digest)

@frappe.whitelist(allow_guest=True,methods=['POST'])
@rate_limit(limit=8,seconds=60)
def accept(token,signer,email,consent,signature=None):
    doc=public_doc(token,True)
    if doc.status!='Pending':frappe.throw('This agreement has already been signed.')
    signer=str(signer or '').strip()
    from plus_point.input_rules import check
    check('contact_name',signer)
    if len(signer)<2 or len(signer)>140 or str(consent).lower() not in ('1','true'):frappe.throw('Enter your full name and confirm agreement acceptance.')
    frappe.utils.validate_email_address(email,throw=True)
    if not email:frappe.throw('Enter your email address.')
    # The bearer token grants access to this exact frozen snapshot, never the company workspace.
    with operation():
        doc.status='Signed';doc.signed_by=signer;doc.signed_email=email;doc.signed_on=now_datetime()
        if signature:
            import base64,binascii
            if not isinstance(signature,str) or not signature.startswith('data:image/png;base64,') or len(signature)>300000:frappe.throw('Draw a valid signature or leave the drawing blank.')
            try:raw=base64.b64decode(signature.split(',',1)[1],validate=True)
            except (ValueError,binascii.Error):frappe.throw('Invalid signature image.')
            if not raw.startswith(b'\x89PNG\r\n\x1a\n'):frappe.throw('Invalid signature image.')
            from frappe.utils.file_manager import save_file
            doc.signature=save_file(doc.name+'.png',raw,'PP Agreement Share',doc.name,is_private=1).file_url
        doc.save(ignore_permissions=True)
        terms=frappe.get_doc('PP Contract Terms',doc.contract_terms);frappe.db.set_value('Contract',terms.contract,'is_signed',1)
        text=e(f'Agreement signed by {signer} ({email}). Snapshot: {doc.digest}.')
        terms.add_comment('Comment',text)
        recipients=frappe.get_all('Has Role',filters={'role':'System Manager','parenttype':'User'},pluck='parent')
        for user in recipients:
            if user!='Guest' and frappe.db.get_value('User',user,'enabled'):
                frappe.get_doc(dict(doctype='Notification Log',subject=f'Agreement signed: {terms.agreement_title}'[:140],email_content=text,for_user=user,type='Alert',document_type='PP Contract Terms',document_name=terms.name)).insert(ignore_permissions=True)
    return dict(signed=True,reference=doc.name)


def invalidate(name):
    if not frappe.db.exists('DocType','PP Agreement Share'):return
    with operation():
        for name in frappe.get_all('PP Agreement Share',filters={'contract_terms':name,'status':'Pending'},pluck='name'):
            doc=frappe.get_doc('PP Agreement Share',name);doc.status='Revoked';doc.save()

def milestone_changed(doc,method=None):
    invalidate(doc.contract_terms)


def cleanup_unsigned(doc,method=None):
    """Native agreement deletion releases only unsigned, permission-checked links."""
    for name in frappe.get_all('PP Agreement Share',filters={'contract_terms':doc.name},pluck='name'):
        share=frappe.get_doc('PP Agreement Share',name,for_update=True)
        if share.status=='Signed':frappe.throw('Signed agreement evidence cannot be deleted.')
        share.check_permission('delete')
        frappe.delete_doc('PP Agreement Share',name)
