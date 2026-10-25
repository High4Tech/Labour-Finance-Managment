"""Partial planning drafts and bounded, idempotent event creation. No payroll posting."""
from contextlib import contextmanager
from hashlib import sha256
import json
import frappe
from frappe.utils import get_datetime, now_datetime, getdate

DT='PP Planning Draft'


def install():
    frappe.reload_doc('plus_point','doctype','pp_planning_draft')
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    create_custom_fields({'PP Contract Terms':[dict(fieldname='pp_daily_checkpoints',label='Daily billing checkpoints',fieldtype='Long Text',hidden=1,read_only=1)]})
    frappe.db.add_index(DT,['status','scheduled_for'],'pp_due_drafts')


def assert_scope(doc):
    from plus_point.operations import company
    if doc.company!=company().name:frappe.throw('This draft belongs to another company.',frappe.PermissionError)
    if doc.owner not in (None,frappe.session.user) and 'System Manager' not in frappe.get_roles():frappe.throw('This draft belongs to another user.',frappe.PermissionError)


def query(user=None):
    from plus_point.operations import company
    return '`tabPP Planning Draft`.company='+frappe.db.escape(company().name)+" AND `tabPP Planning Draft`.status!='Completed'"


def permission(doc,user=None,permission_type=None):
    try:assert_scope(doc);return True
    except frappe.PermissionError:return False


@contextmanager
def writing():
    previous=frappe.flags.get('pp_draft_write');frappe.flags.pp_draft_write=True
    try:yield
    finally:frappe.flags.pp_draft_write=previous


def checked(name,lock=False):
    from plus_point.setup_flow import require_customer
    require_customer()
    doc=frappe.get_doc(DT,name,for_update=lock);doc.check_permission('read');assert_scope(doc)
    return doc


def public(doc):
    return dict(name=doc.name,title=doc.title,kind=doc.kind,status=doc.status,revision=doc.revision,
                scheduled_for=doc.scheduled_for,agreement=doc.agreement,event=doc.event,last_error=doc.last_error,payload=frappe.parse_json(doc.payload or '{}'))


@frappe.whitelist()
def load(name):return public(checked(name))


@frappe.whitelist(methods=['POST'])
def save(kind,payload,name=None,client_key=None,revision=None):
    from plus_point.operations import company
    business=company();data=frappe.parse_json(payload)
    if kind not in ('Agreement','Event') or not isinstance(data,dict):frappe.throw('Choose an agreement or event draft.')
    content=json.dumps(data,ensure_ascii=False)
    if len(content.encode())>96000:frappe.throw('This draft is too large. Save the current rows before adding more.')
    if not name:
        if not client_key or len(client_key)>160:frappe.throw('A draft reference is required.')
        key=sha256((business.name+'|'+frappe.session.user+'|'+kind+'|'+client_key).encode()).hexdigest()
        frappe.db.get_value('Company',business.name,'name',for_update=True)
        name=frappe.db.get_value(DT,{'draft_key':key})
    doc=checked(name,True) if name else frappe.get_doc(dict(doctype=DT,company=business.name,kind=kind,draft_key=key,status='Draft'))
    if doc.kind!=kind or doc.status not in ('Draft','Failed'):frappe.throw('Open the current draft before editing it.')
    if not doc.is_new() and doc.payload==content:return public(doc)
    if revision is not None and int(revision)!=int(doc.revision or 0):frappe.throw('This draft changed in another window. Reopen it before editing.')
    title=(data.get('details') or {}).get('agreement_title') if kind=='Agreement' else data.get('event_name')
    doc.title=str(title or ('Untitled agreement' if kind=='Agreement' else 'Untitled event'))[:140]
    if kind=='Event' and data.get('contract_terms'):
        from plus_point.operations import terms_doc
        terms_doc(data['contract_terms']);doc.agreement=data['contract_terms']
    doc.payload=content;doc.revision=int(doc.revision or 0)+1;doc.last_error='';doc.status='Draft'
    with writing():doc.save()
    return public(doc)


@frappe.whitelist(methods=['POST'])
def finish(name,record):
    doc=checked(name,True)
    if doc.status=='Completed':return public(doc)
    from plus_point.operations import terms_doc
    from plus_point.events import plan_doc
    linked=terms_doc(record) if doc.kind=='Agreement' else plan_doc(record)
    if doc.kind=='Agreement':doc.agreement=linked.name
    else:doc.event=linked.name
    # Keep collaboration when a planning draft becomes the final agreement/event.
    for comment in frappe.get_all('Comment',filters={'reference_doctype':DT,'reference_name':doc.name,'comment_type':'Comment'},pluck='name'):
        frappe.db.set_value('Comment',comment,{'reference_doctype':linked.doctype,'reference_name':linked.name},update_modified=False)
    doc.status='Completed';doc.payload='{}'
    with writing():doc.save()
    return public(doc)


@frappe.whitelist(methods=['POST'])
def event_for_agreement(agreement):
    from plus_point.operations import terms_doc
    terms=terms_doc(agreement)
    if terms.status!='Active':frappe.throw('Complete and activate the agreement before creating its event.')
    frappe.db.get_value('PP Contract Terms',agreement,'name',for_update=True)
    key=sha256(('agreement-event|'+agreement).encode()).hexdigest()
    existing=frappe.db.get_value(DT,{'draft_key':key})
    if existing:return public(checked(existing))
    event=frappe.db.get_value('PP Event Plan',{'project':terms.project},'name')
    doc=frappe.get_doc(dict(doctype=DT,company=frappe.db.get_value('Project',terms.project,'company'),kind='Event',draft_key=key,
        title=terms.agreement_title,agreement=agreement,event=event,status='Completed' if event else 'Draft',revision=1,
        payload=json.dumps(dict(contract_terms=agreement,event_name=terms.agreement_title,notes=''))))
    with writing():doc.insert()
    return public(doc)


@frappe.whitelist(methods=['POST'])
def configure_event(name,values):
    from plus_point.operations import terms_doc,create_plan
    doc=checked(name,True);v=frappe._dict(frappe.parse_json(values) or {})
    if doc.kind!='Event' or doc.status=='Completed':frappe.throw('Open an unfinished event draft.')
    agreement=v.get('contract_terms') or doc.agreement or frappe.parse_json(doc.payload or '{}').get('contract_terms')
    terms=terms_doc(agreement)
    if terms.status!='Active':frappe.throw('Choose an active agreement for this event.')
    if not str(v.get('event_name') or '').strip():frappe.throw('Enter the event name.')
    if v.get('action') not in ('Draft','Now','Schedule'):frappe.throw('Choose Keep draft, Create now or Schedule creation.')
    doc.agreement=agreement;doc.title=str(v.event_name).strip()[:140];doc.scheduled_for=None;doc.last_error=''
    first=getdate(v.get('start_date') or terms.effective_start);last=getdate(v.get('end_date') or terms.effective_end)
    if first>last or first<getdate(terms.effective_start) or last>getdate(terms.effective_end):frappe.throw('Choose event dates within the agreement, with end on or after start.')
    doc.payload=json.dumps(dict(contract_terms=agreement,event_name=doc.title,notes=str(v.get('notes') or '')[:5000],start_date=str(first),end_date=str(last)))
    if v.action=='Now':
        event=create_plan(agreement,doc.title,v.get('notes'),str(first),str(last));doc.event=event['name'];doc.status='Completed';doc.payload='{}'
    elif v.action=='Schedule':
        if not v.get('scheduled_for') or get_datetime(v.scheduled_for)<=now_datetime():frappe.throw('Choose a future date and time for event creation.')
        if getdate(v.scheduled_for)>getdate(terms.effective_end):frappe.throw('Schedule creation on or before the agreement ends.')
        doc.scheduled_for=get_datetime(v.scheduled_for);doc.status='Scheduled'
    else:doc.status='Draft'
    doc.revision=int(doc.revision or 0)+1
    with writing():doc.save()
    return public(doc)


def run_scheduled():
    """Called once a minute; at most 25 due drafts per site per run."""
    if frappe.conf.get('pp_control_plane'):return
    from plus_point.tenancy import current_entitlement,entitlement_status
    entitlement=current_entitlement()
    if entitlement and entitlement_status(entitlement)!='Active':return
    names=frappe.get_all(DT,filters={'status':'Scheduled','scheduled_for':['<=',now_datetime()]},pluck='name',order_by='scheduled_for,name',limit_page_length=25)
    original=frappe.session.user
    for name in names:
        try:
            doc=frappe.get_doc(DT,name,for_update=True)
            if doc.status!='Scheduled' or get_datetime(doc.scheduled_for)>now_datetime():continue
            frappe.set_user(doc.owner)
            frappe.db.savepoint('pp_scheduled_event')
            try:
                from plus_point.operations import create_plan
                from plus_point.setup_flow import require_customer
                if not frappe.db.get_value('User',doc.owner,'enabled'):frappe.throw('The draft owner account is disabled. Ask an active company administrator to review this event.')
                require_customer();assert_scope(doc)
                data=frappe.parse_json(doc.payload);event=create_plan(doc.agreement,data['event_name'],data.get('notes'),data.get('start_date'),data.get('end_date'))
                doc.event=event['name'];doc.status='Completed';doc.payload='{}';doc.last_error=''
            except Exception as error:
                frappe.db.rollback(save_point='pp_scheduled_event');doc.status='Failed';doc.last_error=str(error)[:500]
            with writing():doc.save()
            if not frappe.flags.in_test:frappe.db.commit()
        finally:frappe.set_user(original)
