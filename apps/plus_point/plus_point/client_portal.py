"""A limited client view using the existing expiring, revocable signing grants.

No guest access to Desk, worker identities, costs, notes, files or payment data.
The snapshot is frozen; only safe event progress is read live.
"""
import secrets
import frappe
from frappe.utils import add_to_date, now_datetime, get_datetime, getdate, today
from plus_point import signing


@frappe.whitelist(methods=['POST'])
def link(agreement=None,event=None):
    from plus_point.operations import terms_doc
    from plus_point.events import plan_doc
    plan=plan_doc(event,True) if event else None
    if plan:
        terms=terms_doc(plan.contract_terms,True)
        agreement=terms.get('governing_agreement') or terms.name
    terms=terms_doc(agreement,True)
    if plan:
        event_project=frappe.get_doc('Project',plan.project);agreement_project=frappe.get_doc('Project',terms.project)
        if (event_project.company,event_project.customer)!=(agreement_project.company,agreement_project.customer):
            frappe.throw('Choose an event for this client and company.',frappe.PermissionError)
    if terms.status not in ('Active','Closed'):frappe.throw('Create the agreement before sharing its client portal.')
    frappe.has_permission('PP Agreement Share','create',throw=True)
    # Serialize copy/create so two clicks return the same current link.
    frappe.db.get_value('PP Contract Terms',terms.name,'name',for_update=True)
    html=signing.snapshot(terms.name);fingerprint=signing.digest(html)
    matches=frappe.get_all('PP Agreement Share',filters={'contract_terms':terms.name,
        'portal_event':event or ['is','not set'],'status':['in',['Pending','Signed']],
        'expires':['>',now_datetime()],'digest':fingerprint},pluck='name',order_by='creation desc',limit_page_length=10)
    share=None;token=None
    for name in matches:
        candidate=frappe.get_doc('PP Agreement Share',name)
        if candidate.get('proposed_values'):continue
        token=candidate.get_password('access_token',raise_exception=False)
        if token:
            share=candidate;break
    if not share:
        token=secrets.token_urlsafe(40)
        with signing.operation():
            share=frappe.get_doc(dict(doctype='PP Agreement Share',contract_terms=terms.name,
                portal_event=event,access_token=token,token_hash=signing.digest(token),
                expires=add_to_date(now_datetime(),days=7),snapshot=html,digest=fingerprint,status='Pending')).insert()
    return dict(url=frappe.utils.get_url('/agree?token='+token),name=share.name,expires=str(share.expires))


def progress(share):
    """The bearer grant is bound to one agreement/client/company, optionally one event."""
    terms=frappe.get_doc('PP Contract Terms',share.contract_terms)
    project=frappe.get_doc('Project',terms.project)
    company,customer=project.company,project.customer
    ids=[terms.name]+frappe.get_all('PP Contract Terms',filters={'governing_agreement':terms.name,'event_basis':1},pluck='name')
    filters={'contract_terms':['in',ids],'company':company}
    if share.get('portal_event'):filters['name']=share.portal_event
    rows=frappe.get_all('PP Event Plan',filters=filters,fields=['name','event_name','project','start_date','end_date','planning_state','pp_reference'],order_by='start_date desc,name',limit_page_length=25)
    from plus_point.events import lifecycle
    result=[]
    for row in rows:
        context=frappe.db.get_value('Project',row.project,['company','customer','pp_archived','status'],as_dict=True)
        if not context or (context.company,context.customer)!=(company,customer):continue
        # Incomplete work stays internal. A client must not mistake a draft for a confirmed event.
        if row.planning_state=='Draft':continue
        doc=frappe.get_doc('PP Event Plan',row.name)
        phases=[]
        from plus_point.phases import normalize
        for phase in ('Setup','Event','Pack-down','Other'):
            staffing=[s for s in doc.staffing if phase in normalize(s.phase).split(', ')]
            if not staffing:continue
            start=min(getdate(s.start_date) for s in staffing);end=max(getdate(s.end_date) for s in staffing)
            phases.append(dict(title=phase,start=str(start),end=str(end),status='Completed' if end<getdate(today()) else 'Upcoming' if start>getdate(today()) else 'In progress'))
        planned=sum(int(s.workers_required)*(getdate(s.end_date)-getdate(s.start_date)).days+int(s.workers_required) for s in doc.staffing)
        assignments=frappe.get_all('PP Assignment',filters={'project':row.project},fields=['employee','start_date','end_date'])
        # Counts only, deliberately no employee names/rates or private staffing records.
        assigned=sum((min(getdate(a.end_date or row.end_date),getdate(row.end_date))-max(getdate(a.start_date),getdate(row.start_date))).days+1 for a in assignments if getdate(a.start_date)<=getdate(row.end_date) and getdate(a.end_date or row.end_date)>=getdate(row.start_date))
        result.append(dict(title=row.event_name,reference=row.pp_reference,start=str(row.start_date),end=str(row.end_date),
            status=lifecycle(row,context.pp_archived,context.status=='Cancelled'),phases=phases,
            required_worker_days=planned,assigned_worker_days=assigned))
    return result
