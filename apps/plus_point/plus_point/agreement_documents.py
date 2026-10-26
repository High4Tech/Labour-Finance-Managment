"""Agreement documents and explicit creation-time sharing over native private Files."""
import hashlib,re
import frappe
from frappe.utils import escape_html as esc
from plus_point.operations import terms_doc


def recipients(recipient,cc=''):
    def parse(value):
        if not isinstance(value,str) or '\r' in value:frappe.throw('Enter email addresses separated by commas.')
        rows=[v.strip() for v in re.split(r'[,;\n]+',value) if v.strip()]
        if len(rows)>10:frappe.throw('Use at most ten CC email addresses.')
        for email in rows:
            if not re.fullmatch(r'[^@\s<>:,;]+@[^@\s<>:,;]+\.[^@\s<>:,;]+',email):frappe.throw('Enter valid email addresses without email headers.')
            frappe.utils.validate_email_address(email,throw=True)
        return list(dict.fromkeys(rows))
    to=parse(recipient);copies=parse(cc)
    if len(to)!=1:frappe.throw('Enter one recipient email address.')
    return to,[email for email in copies if email not in to]


def document_html(body,reference):
    return '''<!doctype html><html><head><meta charset="utf-8"><style>
    @page{size:A4;margin:18mm 16mm 20mm}body{font:10pt/1.5 DejaVu Sans,sans-serif;color:#183633}h1,h2,p,td,li{overflow-wrap:break-word;word-wrap:break-word}h1{font-size:21pt;line-height:1.2;margin:8mm 0 6mm}h2{font-size:12pt;color:#116f65;border-bottom:1px solid #cbdad6;padding-bottom:2mm;margin-top:7mm;page-break-after:avoid}p{margin:2mm 0}table{border-collapse:collapse;width:100%;font-size:9pt;margin:4mm 0}thead{display:table-header-group}th{background:#eaf3f0;text-align:left}th,td{padding:2.5mm;border-bottom:1px solid #d7e1dd;vertical-align:top}tr{page-break-inside:avoid}li{margin-bottom:2mm}.document-meta{font-size:9pt;color:#536b63}.acceptance{margin-top:10mm;padding:5mm;border:1px solid #cbdad6;page-break-inside:avoid}img{max-width:140px;max-height:60px}footer{font-size:8pt;color:#536b63;margin-top:8mm}</style></head><body>'''+body+'<footer>PLUS POINT · '+esc(reference)+'</footer></body></html>'


def pdf_content(html):
    from frappe.utils.pdf import get_pdf
    options={'page-size':'A4','margin-top':'18mm','margin-bottom':'18mm','margin-left':'16mm','margin-right':'16mm','disable-local-file-access':None}
    if frappe.local.site.endswith('.localhost'):
        from frappe.utils import scrub_urls,get_url
        html=scrub_urls(html).replace(get_url().rstrip('/'),'http://127.0.0.1:8000');options.update({'custom-header':[('Host',frappe.local.site+':8000')],'custom-header-propagation':None})
    return get_pdf(html,options=options)


def pdf_filename(title,identity):
    digest=hashlib.sha256(identity.encode() if isinstance(identity,str) else identity).hexdigest()[:12]
    return re.sub(r'[^\w .-]','_',title)[:150]+'-'+digest+'.pdf'


def find_pdf(doctype,name,filename):
    # Native File may append a collision suffix to a filename on disk.
    rows=frappe.get_list('File',filters={'attached_to_doctype':doctype,'attached_to_name':name,'is_private':1,'file_name':['like',filename[:-4]+'%']},fields=['name','file_name','file_url'],limit_page_length=20)
    return next((r for r in rows if re.fullmatch(re.escape(filename[:-4])+r'(?:[a-f0-9]{6})?\.pdf',r.file_name)),None)


def save_pdf(doctype,name,title,content,identity=None):
    from frappe.utils.file_manager import save_file
    filename=pdf_filename(title,identity if identity is not None else content)
    existing=find_pdf(doctype,name,filename)
    if existing:return existing
    file=save_file(filename,content,doctype,name,is_private=1)
    return dict(name=file.name,file_name=file.file_name,file_url=file.file_url)


def signed_body(doc):
    body=doc.snapshot
    if doc.status=='Signed':
        body+='<section class="acceptance"><h2>'+('Company-recorded client agreement (not a client signature)' if doc.get('approval_method')=='Company attested' else 'Client acceptance')+'</h2><p>'+('Recorded by ' if doc.get('approval_method')=='Company attested' else 'Signed by ')+esc(doc.signed_by)+' · '+esc(str(doc.signed_on))+'</p><p>Agreement version: '+esc(doc.digest)+'</p>'
        if doc.signature:
            import base64
            file=frappe.db.get_value('File',{'attached_to_doctype':'PP Agreement Share','attached_to_name':doc.name,'file_url':doc.signature},'name')
            if file:
                raw=frappe.get_doc('File',file).get_content();raw=raw.encode() if isinstance(raw,str) else raw
                body+='<img alt="Client signature" src="data:image/png;base64,'+base64.b64encode(raw).decode()+'">'
        body+='</section>'
    return body


@frappe.whitelist(methods=['POST'])
def agreement_pdf(name,share=None):
    terms=terms_doc(name)
    from plus_point.signing import snapshot
    body=snapshot(name)
    if share:
        doc=frappe.get_doc('PP Agreement Share',share);doc.check_permission('read')
        if doc.contract_terms!=name:frappe.throw('Choose a signing record for this agreement.')
        body=signed_body(doc)
    html=document_html(body,terms.pp_reference or name)
    title=(terms.pp_reference or name)+(' Signed agreement' if share and doc.status=='Signed' else ' Agreement');filename=pdf_filename(title,html)
    existing=find_pdf('Contract',terms.contract,filename)
    return existing or save_pdf('Contract',terms.contract,title,pdf_content(html),identity=html)


@frappe.whitelist(methods=['POST'])
def invoice_pdf(name):
    from plus_point.operations import invoice,invoice_pdf_content
    invoice(name);doc=frappe.get_doc('Sales Invoice',name)
    identity=doc.as_json()+str(frappe.db.get_value('Print Format','PLUS POINT Branded Invoice','modified') or '')
    existing=find_pdf('Sales Invoice',name,pdf_filename(name+' Invoice',identity))
    return existing or save_pdf('Sales Invoice',name,name+' Invoice',invoice_pdf_content(doc),identity=identity)


@frappe.whitelist()
def documents(name):
    terms=terms_doc(name)
    projects=[terms.project]+frappe.get_list('PP Contract Terms',filters={'governing_agreement':name,'event_basis':1},pluck='project',limit_page_length=0)
    invoices=frappe.get_list('Sales Invoice',filters={'project':['in',projects]},fields=['name','creation'],limit_page_length=500)
    result=frappe.get_list('File',filters={'attached_to_doctype':'Contract','attached_to_name':terms.contract},fields=['name','file_name','file_url','creation','is_private'],order_by='creation desc',limit_page_length=100)
    if invoices:
        invoice_files=frappe.get_list('File',filters={'attached_to_doctype':'Sales Invoice','attached_to_name':['in',[row.name for row in invoices]]},fields=['name','file_name','file_url','creation','is_private','attached_to_name'],order_by='creation desc',limit_page_length=200)
        result+=invoice_files
        printed={row.attached_to_name for row in invoice_files if re.fullmatch(re.escape(re.sub(r'[^\w .-]','_',row.attached_to_name+' Invoice')[:150])+r'-[a-f0-9]{12}(?:[a-f0-9]{6})?\.pdf',row.file_name)}
        for invoice in invoices:
            if invoice.name not in printed:result.append(frappe._dict(name='invoice:'+invoice.name,invoice=invoice.name,file_name=invoice.name+' Invoice.pdf',creation=invoice.creation,is_private=1))
    # Signed snapshots are documents already; render their PDF only when opened.
    for share in frappe.get_list('PP Agreement Share',filters={'contract_terms':name,'status':'Signed'},fields=['name','snapshot','digest','status','signed_by','signed_on','signature','approval_method'],order_by='signed_on desc',limit_page_length=10):
        title=(terms.pp_reference or name)+' Signed agreement'
        filename=pdf_filename(title,document_html(signed_body(share),terms.pp_reference or name))
        if not any(re.fullmatch(re.escape(filename[:-4])+r'(?:[a-f0-9]{6})?\.pdf',r.file_name) for r in result):
            result.append(frappe._dict(name='signed:'+share.name,file_name=title+'.pdf',share=share.name,agreement=name,creation=share.signed_on,is_private=1))
    return sorted(result,key=lambda r:str(r.creation),reverse=True)


@frappe.whitelist(methods=['POST'])
def finalize(name,send_email=0,recipient='',cc='',reviewed=None):
    terms=terms_doc(name,True)
    if frappe.utils.cint(send_email):
        recipients(recipient,cc)
        if not frappe.db.exists('Email Account',{'enable_outgoing':1}):frappe.throw('Set up outgoing email before selecting Send agreement by email. You can create the agreement and share its link instead.')
    from plus_point.signing import create_link,send_link
    share=create_link(name);pdf=agreement_pdf(name,share['name'])
    if frappe.utils.cint(send_email):send_link(name,share['name'],share['url'].split('token=',1)[1],recipient,cc=cc,pdf_file=pdf['name'])
    return dict(share=share,pdf=pdf,email_queued=bool(frappe.utils.cint(send_email)))


@frappe.whitelist(methods=['POST'])
def milestone_document(name):
    from plus_point.setup_flow import linked
    milestone=linked('PP Milestone',name);terms=terms_doc(milestone.contract_terms,True)
    frappe.db.get_value('PP Milestone',name,'name',for_update=True)
    milestone.reload()
    invoice=milestone.sales_invoice
    if not invoice and milestone.status!='Approved':frappe.throw('Approve this milestone before creating its invoice.')
    if not invoice:
        from plus_point.billing import create_invoice
        result=create_invoice(terms.name,terms.billing_item,source_names=[name]);invoice=result['name'] if isinstance(result,dict) else result.name
    return dict(invoice=invoice,pdf=invoice_pdf(invoice))


@frappe.whitelist()
def validate_delivery(reviewed=None,send_email=0,recipient='',cc=''):
    from plus_point.operations import company
    company()
    if frappe.utils.cint(send_email):
        recipients(recipient,cc)
        if not frappe.db.exists('Email Account',{'enable_outgoing':1}):frappe.throw('Set up outgoing email or turn off Send agreement by email and share the client link instead.')
    return dict(valid=True)


def private_pdf(name):
    file=frappe.get_doc('File',name);file.check_permission('read')
    if file.attached_to_doctype=='Contract':
        agreement=frappe.db.get_value('PP Contract Terms',{'contract':file.attached_to_name},'name')
        if not agreement:frappe.throw('Choose a document attached to an agreement.')
        terms_doc(agreement)
    elif file.attached_to_doctype=='Sales Invoice':
        from plus_point.operations import invoice
        invoice(file.attached_to_name)
    else:frappe.throw('Choose an agreement or invoice document.')
    if not file.is_private or not str(file.file_url).startswith('/private/files/') or not file.file_name.lower().endswith('.pdf'):frappe.throw('Choose a private PDF document.')
    return file


@frappe.whitelist(methods=['POST'])
def data(name):
    import base64
    file=private_pdf(name)
    content=file.get_content();content=content.encode() if isinstance(content,str) else content
    return dict(name=file.name,filename=file.file_name,mime='application/pdf',content=base64.b64encode(content).decode())
