"""Agreement-led operations. Composed screens retain native records and audit history."""
from collections import defaultdict
from decimal import Decimal
import json
import re
import frappe
from frappe.utils import getdate, today, add_days
from plus_point.setup_flow import require_customer, linked
from plus_point.finance import money
from plus_point.benefits import atomic

EVENT_ROLES = ('Event manager', 'Site supervisor', 'Crew leader', 'Event crew', 'Stagehand',
    'Electrician', 'Lighting technician', 'Sound technician', 'AV technician', 'Rigger',
    'Carpenter', 'Decorator', 'Usher', 'Security staff', 'Cleaner', 'Driver', 'Warehouse crew')


def event_roles():
    """Event choices do not inherit unrelated ERP demonstration designations."""
    custom=frappe.parse_json(frappe.defaults.get_global_default('pp_event_roles') or '[]')
    return sorted(set(EVENT_ROLES) | set(custom), key=str.casefold)


def install_event_defaults():
    """Native event roles are local reference data, not worker accounts."""
    frappe.set_user('Administrator')
    from plus_point.install import ensure_event_archive_field
    ensure_event_archive_field()
    for title in EVENT_ROLES:ensure_event_role(title)
    frappe.db.commit()
    return dict(categories=len(EVENT_ROLES))


def ensure_event_role(title):
    if not frappe.db.exists('Designation',title):
        if title not in event_roles():frappe.throw('Choose an event crew category, or add a new category first.')
        frappe.get_doc(dict(doctype='Designation',designation_name=title)).insert()


def service_item():
    """Create the application's native non-stock service when it is first needed."""
    code='PP-EVENT-SERVICE'
    frappe.db.get_value('DocType','Item','name',for_update=True)
    if frappe.db.exists('Item',code):
        item=linked('Item',code)
        if item.disabled or item.is_stock_item:frappe.throw('The Event services item must be enabled and non-stock before billing.')
        return item.name
    group=frappe.db.get_value('Item Group',{'name':'Services','is_group':0},'name') or frappe.db.get_value('Item Group',{'is_group':0},'name')
    unit=frappe.db.get_value('UOM',{'name':'Nos'},'name') or frappe.db.get_value('UOM',{},'name')
    return frappe.get_doc(dict(doctype='Item',item_code=code,item_name='Event services',
        item_group=group,stock_uom=unit,is_stock_item=0)).insert().name


@frappe.whitelist(methods=['POST'])
def prepare_billing(contract_terms):
    terms=terms_doc(contract_terms,True)
    if not terms.billing_item:
        terms.billing_item=service_item();terms.save()
    from plus_point.billing import invoice_options
    return dict(invoice_options(terms.name),item=terms.billing_item,
        service_name=frappe.db.get_value('Item',terms.billing_item,'item_name'))


def company():
    require_customer()
    from plus_point.event_setup import companies
    rows=companies()
    if not rows:frappe.throw('Complete your business setup first.')
    return linked('Company',rows[0].name)


def terms_doc(name,write=False):
    business=company();doc=linked('PP Contract Terms',name)
    linked('Project',doc.project,business.name)
    doc.check_permission('write' if write else 'read')
    return doc


@frappe.whitelist()
def catalogue():
    business=company()
    projects={r.name:r for r in frappe.get_list('Project',filters={'company':business.name,'pp_archived':0},fields=['name','project_name','customer','status'],limit_page_length=0)}
    terms=frappe.get_list('PP Contract Terms',filters={'project':['in',list(projects) or ['']],'event_basis':0},fields=['name','project','contract','billing_model','status','fixed_amount','effective_start','effective_end','agreement_title','pp_reference','validity_mode','resource_mode'],order_by='modified desc',limit_page_length=0)
    clients={r.name:r.customer_name for r in frappe.get_list('Customer',filters={'disabled':0},fields=['name','customer_name'],order_by='customer_name,name',limit_page_length=0)}
    for row in terms:row.update(title=row.agreement_title or projects[row.project].project_name,customer=projects[row.project].customer,client=clients.get(projects[row.project].customer,''))
    plans=frappe.get_list('PP Event Plan',filters={'company':business.name,'project':['in',list(projects) or ['']]},fields=['name','event_name','contract_terms','project','start_date','end_date','crew_allocated','pp_reference'],order_by='start_date desc,event_name',limit_page_length=0)
    return dict(currency=business.default_currency,invoice_currency=business.pp_invoice_currency or business.default_currency,country=business.country,agreements=terms,plans=plans,
        clients=[dict(name=k,title=v) for k,v in clients.items()],
        designations=event_roles(),
        items=frappe.get_list('Item',filters={'is_stock_item':0,'disabled':0},fields=['name','item_name'],order_by='item_name,name',limit_page_length=0))


def validate_agreement(doc):
    from plus_point.agreement_lifecycle import apply_status
    from plus_point.agreement_events import validate_terms
    validate_terms(doc)
    apply_status(doc)
    from plus_point.daily_billing import validate as validate_checkpoints
    validate_checkpoints(doc)
    if not doc.get('staffing'):return
    project=linked('Project',doc.project)
    from plus_point.events import span,positive
    seen=set()
    for row in doc.staffing:
        from plus_point.phases import normalize
        row.phase=normalize(row.phase)
        site=linked('PP Site',row.site);linked('Designation',row.designation)
        if site.project!=project.name:frappe.throw('Agreement venues must belong to this event.')
        span(row.start_date,row.end_date)
        if getdate(row.start_date)<getdate(doc.effective_start) or doc.effective_end and getdate(row.end_date)>getdate(doc.effective_end):frappe.throw('Staffing dates must fall within the agreement dates.')
        row.workers_required=int(positive(row.workers_required,'Workers per day',whole=True))
        if row.workers_required>500:frappe.throw('Use at most 500 workers per role/site/day.')
        positive(row.wage_rate,'Daily wage',allow_zero=True);positive(row.client_rate,'Client rate',allow_zero=doc.billing_model=='Fixed')
        if doc.billing_model=='Fixed' and money(row.client_rate):frappe.throw('Fixed agreements use milestones rather than worker-day client charges.')
        key=(row.site,row.designation)
        for previous in doc.staffing:
            if previous==row:break
            if (previous.site,previous.designation)==key and getdate(previous.start_date)<=getdate(row.end_date) and getdate(previous.end_date)>=getdate(row.start_date):frappe.throw('Combine overlapping requirements for the same venue and role.')
        seen.add(key)
    from plus_point.people import validate_capacity
    if doc.get('resource_mode') in (None,'','Fixed quantities'):validate_capacity(doc)
    if doc.get('auto_invoice') and not doc.get('billing_item'):frappe.throw('Choose a billing service item for automatic milestone invoices.')


@frappe.whitelist(methods=['POST'])
def save_agreement(values,name=None):
    business=company();values=frappe._dict(frappe.parse_json(values) or {})
    if name:
        from plus_point.agreement_updates import guard
        guard(terms_doc(name))
    if values.get('validity_mode')=='Ongoing':values.effective_end=None
    if values.get('scope') is not None and not frappe.utils.strip_html(values.scope).strip():values.scope=''
    if values.get('effective_start') and getdate(values.effective_start)<getdate(today()):
        changed=not name or getdate(terms_doc(name).effective_start)!=getdate(values.effective_start)
        if changed and str(values.get('allow_past_dates') or '').lower() not in ('1','true'):
            frappe.throw('Upcoming work must start today or later. Enable Allow dates in the past in Agreement details only when entering historical work.')
    from plus_point.workflows import rate_values
    values=rate_values(business,values,terms_doc(name) if name else None)
    frappe.db.savepoint('pp_agreement_save')
    try:
        if name:
            doc=terms_doc(name,True);project=linked('Project',doc.project);contract=linked('Contract',doc.contract)
            from plus_point.budget import lock_project
            lock_project(project.name)
            customer=project.customer
            if values.get('customer') and values.customer!=customer:frappe.throw('The client of an existing agreement cannot change.')
        else:
            if values.get('customer'):customer=linked('Customer',values.customer).name
            else:
                from plus_point.clients import create
                customer=create(values.get('client') or {}).name
            title=str(values.get('agreement_title') or '').strip()
            if not title:frappe.throw('Enter an agreement name.')
            project=frappe.get_doc(dict(doctype='Project',project_name=title,company=business.name,customer=customer,
                expected_start_date=values.effective_start,expected_end_date=values.effective_end)).insert()
            contract=frappe.new_doc('Contract');contract.update(dict(party_type='Customer',party_name=customer,
                start_date=values.effective_start,end_date=values.effective_end,contract_terms=values.get('scope') or title));contract.flags.ignore_mandatory=not bool(values.effective_end);contract.insert()
            doc=frappe.new_doc('PP Contract Terms');doc.update(dict(project=project.name,contract=contract.name,currency=business.default_currency))
        if values.get('client') and (name or values.get('customer')):
            from plus_point.clients import save
            save(values.client,customer)
        previous_currency=doc.get('pp_agreement_currency') or doc.currency
        previous_rate=Decimal(str(doc.get('pp_agreement_rate') or 1))
        currency_changed=bool(name and values.get('pp_agreement_currency') and values.pp_agreement_currency!=previous_currency)
        if currency_changed and (frappe.db.exists('PP Milestone',{'contract_terms':name,'status':['in',['Approved','Invoiced']]}) or frappe.db.exists('Sales Invoice',{'project':project.name,'docstatus':['!=',2]})):
            frappe.throw('This agreement already has approved milestones or invoices. Create a new agreement to use a different currency and preserve its financial history.')
        for key in ('agreement_title','billing_model','effective_start','effective_end','fixed_amount','billing_item','auto_invoice','status','pp_agreement_currency','pp_agreement_rate','pp_future_crew_count','pp_conditions','pp_daily_checkpoints','validity_mode','resource_mode','rate_card','recurrence_note'):
            if key in values:doc.set(key,values[key])
        if 'pp_conditions' in values:
            conditions=frappe.parse_json(values.pp_conditions or '[]')
            if not isinstance(conditions,list) or len(conditions)>100 or any(not isinstance(c,str) or len(c)>5000 for c in conditions):frappe.throw('Use at most 100 text conditions of 5,000 characters each.')
            if conditions and not doc.meta.has_field('pp_conditions'):frappe.throw('This company app update is incomplete. Ask support to install agreement conditions, then save again. Your changes have not been saved.')
            doc.pp_conditions=frappe.as_json([c.strip() for c in conditions if c.strip()])
        if not doc.get('event_basis'):
            contract.start_date=getdate(doc.effective_start);contract.end_date=getdate(doc.effective_end) if doc.effective_end else None
            contract.flags.ignore_mandatory=not bool(doc.effective_end)
            contract.save()
        from plus_point.daily_billing import validate as validate_checkpoints,rebase
        rebase(doc)
        validate_checkpoints(doc)
        if not doc.billing_item:doc.billing_item=service_item()
        if values.get('scope') is not None:
            contract.check_permission('write');contract.contract_terms=values.scope or (f'Draft: {doc.agreement_title}' if doc.status=='Draft' else values.scope);contract.flags.ignore_mandatory=not bool(doc.effective_end);contract.save()
        if 'staffing' in values:
            if 'sites' in values and (not isinstance(values.sites,list) or len(values.sites)>12 or any(not isinstance(v,str) or len(v)>140 for v in values.sites)):frappe.throw('Use at most 12 named sites in an agreement.')
            locations={r.site_name:r.name for r in frappe.get_list('PP Site',filters={'project':project.name},fields=['name','site_name'],limit_page_length=0)}
            client_country=(values.get('client') or {}).get('country') or frappe.db.get_value('Address',frappe.db.get_value('Customer',customer,'customer_primary_address'),'country') or business.country
            for title in values.get('sites',[]):
                title=str(title).strip()
                if not title:frappe.throw('Enter each site name.')
                if title not in locations:
                    venue=frappe.get_doc(dict(doctype='PP Site',project=project.name,site_name=title,is_active=1,country=client_country)).insert();locations[title]=venue.name
            details=values.get('site_details') or {}
            if not isinstance(details,dict) or len(details)>12:frappe.throw('Use location details for at most 12 sites.')
            for title,metadata in details.items():
                if title not in locations or not isinstance(metadata,dict):continue
                venue=linked('PP Site',locations[title]);venue.check_permission('write')
                for key in ('city','address_line1'):
                    if key in metadata:
                        if not isinstance(metadata[key],str) or len(metadata[key])>200:frappe.throw('Keep site location details within 200 characters.')
                        venue.set(key,metadata[key])
                venue.save()
            rows=[]
            for raw in values.staffing:
                raw=frappe._dict(raw);site=raw.get('site')
                if not raw.get('country'):raw.country=frappe.db.get_value('PP Site',site,'country') if site else client_country
                if raw.get('designation'):ensure_event_role(raw.designation)
                if site:
                    venue=linked('PP Site',site)
                    if venue.project!=project.name:frappe.throw('Choose a venue in this agreement.')
                else:
                    title=str(raw.get('site_name') or '').strip()
                    if not title:frappe.throw('Enter each venue name.')
                    site=locations.get(title)
                    if not site:
                        venue=frappe.get_doc(dict(doctype='PP Site',project=project.name,site_name=title,is_active=1,
                            **{key:raw.get(key) for key in ('country','state','city','address_line1','address_line2','postal_code','latitude','longitude')})).insert()
                        site=locations[title]=venue.name
                if any(raw.get(key) for key in ('country','city','address_line1')):
                    venue=linked('PP Site',site);venue.check_permission('write')
                    for key in ('country','city','address_line1','state','address_line2','postal_code'):
                        if raw.get(key) is not None:venue.set(key,raw[key])
                    venue.save()
                rows.append(dict(site=site,**{key:raw.get(key) for key in ('designation','start_date','end_date','workers_required','wage_rate','client_rate','phase')}))
            if not rows and doc.status!='Draft' and doc.get('resource_mode') not in ('Rate card','Per event'):frappe.throw('Add at least one venue and worker category.')
            doc.set('staffing',rows)
        if 'transport_requirements' in values:
            from plus_point.resources import transport_requirements
            site_names=frappe.get_list('PP Site',filters={'project':project.name},pluck='site_name',limit_page_length=0)
            transport=transport_requirements(values.transport_requirements,doc.effective_start,doc.effective_end,site_names)
            if transport and not doc.meta.has_field('pp_transport_requirements'):frappe.throw('Vehicle requirements are not installed on this site yet.')
            doc.pp_transport_requirements=frappe.as_json(transport)
        if doc.status=='Draft' and name and frappe.db.exists('PP Assignment',{'contract_terms':name}):frappe.throw('This agreement already has worker assignments. Keep it Active, or close completed work instead of changing it to Draft.')
        doc.save()
        if name and doc.billing_model=='Fixed':
            from plus_point.planning import cost_warning
            warning=cost_warning(doc,[])
            if warning and not frappe.utils.cint(values.get('confirm_over_budget')):frappe.throw(warning)
        if currency_changed:
            # Planned milestone prices keep their entered numeric amounts when
            # a draft agreement changes currency. Approved history is protected.
            factor=Decimal(str(doc.pp_agreement_rate))/previous_rate
            for row in frappe.get_list('PP Milestone',filters={'contract_terms':name,'status':'Planned'},fields=['name'],limit_page_length=0):
                milestone=linked('PP Milestone',row.name);milestone.amount=money(Decimal(str(milestone.amount))*factor);milestone.save()
        if name and not frappe.flags.get('pp_agreement_revision'):
            from plus_point.signing import invalidate
            invalidate(doc.name)
        plan_name=frappe.db.get_value('PP Event Plan',{'project':project.name},'name')
        if plan_name and 'staffing' in values and not frappe.flags.get('pp_agreement_revision'):
            plan=frappe.get_doc('PP Event Plan',plan_name)
            keys=('site','designation','start_date','end_date','phase')
            signature=lambda r:tuple(str(r.get(k) or '') for k in keys)
            previous=doc.get_doc_before_save();baseline={signature(r) for r in previous.staffing} if previous else set()
            extras=[{k:r.get(k) for k in keys+('workers_required','wage_rate','client_rate')} for r in plan.staffing if signature(r) not in baseline]
            rows=[{k:r.get(k) for k in keys+('workers_required','wage_rate','client_rate')} for r in doc.staffing]
            # Keep removed but deployed positions as explicit event extras. Existing
            # attendance and worker pay agreements never disappear with a client edit.
            for old in previous.staffing if previous else []:
                if signature(old) not in {signature(r) for r in doc.staffing} and frappe.db.exists('PP Assignment',{'contract_terms':doc.name,'site':old.site}):
                    extras.append({k:old.get(k) for k in keys+('workers_required','wage_rate','client_rate')})
            known={signature(r) for r in rows}
            for row in extras:
                if signature(row) not in known:rows.append(row);known.add(signature(row))
            # Fixed client prices do not define payroll. Zero-wage requirements
            # inherit an existing plan payroll rate until a worker is assigned.
            for row in rows:
                existing=next((r for r in plan.staffing if signature(r)==signature(row)),None)
                row['wage_rate']=existing.wage_rate if existing else 0
                if doc.billing_model=='Fixed':row['client_rate']=0
            plan.set('staffing',rows)
            plan.start_date=min(getdate(r['start_date']) for r in rows);plan.end_date=max(getdate(r['end_date']) for r in rows)
            plan.wage_rate=rows[0]['wage_rate'];plan.client_rate=rows[0]['client_rate']
            plan.save()
            for allocation in frappe.get_list('PP Assignment',filters={'contract_terms':doc.name},fields=['name','site','employee'],limit_page_length=0):
                if frappe.db.exists('PP Work Entry',{'assignment':allocation.name}):continue
                # Only unused allocations adopt revised rates; a work entry is an
                # immutable payroll snapshot, even before approval.
                assignment=linked('PP Assignment',allocation.name)
                role=frappe.db.get_value('Employee',allocation.employee,'designation')
                match=next((r for r in doc.staffing if r.site==allocation.site and r.designation==role and getdate(r.start_date)<=getdate(assignment.start_date) and getdate(r.end_date)>=getdate(assignment.end_date or r.end_date)),None)
                if doc.billing_model=='Fixed':assignment.client_rate=0
                elif match:assignment.client_rate=match.client_rate
                assignment.pp_cost_override=frappe.utils.cint(values.get('confirm_over_budget'))
                assignment.save()
        if 'sites' in values:
            retained=set(values.sites)|{frappe.db.get_value('PP Site',r.site,'site_name') for r in doc.staffing}
            for venue in frappe.get_list('PP Site',filters={'project':project.name},fields=['name','site_name'],limit_page_length=0):
                if venue.site_name in retained:continue
                if any(frappe.db.exists(dt,{'site':venue.name}) for dt in ['PP Assignment','PP Work Entry','PP Daily Register','PP Vehicle Booking','PP Equipment Booking']):continue
                frappe.delete_doc('PP Site',venue.name)
        for row in values.get('milestones',[]):
            if str(row.get('milestone_title') or '').strip():save_milestone(doc.name,row)
        if values.get('require_payment_plan') and doc.status!='Draft':require_payments(doc)
        return dict(name=doc.name,project=project.name)
    except Exception:
        frappe.db.rollback(save_point='pp_agreement_save');raise


@frappe.whitelist()
def agreement(name):
    doc=terms_doc(name);project=linked('Project',doc.project);contract=linked('Contract',doc.contract)
    from plus_point.clients import details
    scope=contract.contract_terms
    if doc.get('commercial_snapshot'):scope=frappe.parse_json(doc.commercial_snapshot).get('scope') or scope
    if doc.status=='Draft' and scope==f'Draft: {doc.agreement_title}':scope=''
    result=doc.as_dict();result.update(archived=bool(project.get('pp_archived')),has_allocations=bool(frappe.db.exists('PP Assignment',{'contract_terms':name})),client_company=project.company,scope=scope,customer=project.customer,client=details(project.customer),is_signed=contract.get('is_signed'),
        files=frappe.get_list('File',filters={'attached_to_doctype':'Contract','attached_to_name':contract.name},fields=['name','file_name','file_url'],limit_page_length=0),
        venues=frappe.get_list('PP Site',filters={'project':project.name},fields=['name','site_name','country','city','address_line1'],order_by='site_name',limit_page_length=0),
        milestones=frappe.get_list('PP Milestone',filters={'contract_terms':name},fields=['name','milestone_title','due_date','amount','status','sales_invoice'],order_by='due_date,name',limit_page_length=0))
    if doc.get('event_basis') and doc.get('governing_agreement'):
        parent=terms_doc(doc.governing_agreement);result['validity_start']=parent.effective_start;result['validity_end']=parent.effective_end
    result['updates']=frappe.get_list('PP Agreement Share',filters={'contract_terms':name,'proposed_values':['is','set']},fields=['name','status','change_summary','approval_method'],order_by='creation desc',limit_page_length=10)
    from plus_point.workflows import agreement_units
    return agreement_units(result)


@frappe.whitelist(methods=['POST'])
def create_plan(contract_terms,event_name,notes=None,start_date=None,end_date=None,new_occurrence=0):
    if frappe.utils.cint(new_occurrence):
        from plus_point.agreement_events import create_event
        return create_event(agreement=contract_terms,event_name=event_name,notes=notes,start_date=start_date,end_date=end_date)
    doc=terms_doc(contract_terms)
    if doc.status!='Active':frappe.throw('Activate this agreement before planning the event.')
    from plus_point.budget import lock_project
    lock_project(doc.project)
    existing=frappe.db.get_value('PP Event Plan',{'project':doc.project},'name')
    if existing:return dict(name=existing,existing=True)
    if not doc.staffing:frappe.throw('Add venue and worker-category requirements in the agreement first.')
    if not str(event_name or '').strip():frappe.throw('Enter the event name.')
    rows=[{key:r.get(key) for key in ('site','phase','start_date','end_date','workers_required','designation','wage_rate','client_rate')} for r in doc.staffing]
    if start_date or end_date:
        first=getdate(start_date or doc.effective_start);last=getdate(end_date or doc.effective_end)
        if first>last or first<getdate(doc.effective_start) or last>getdate(doc.effective_end):frappe.throw('Choose event dates within the agreement, with end on or after start.')
        rows=[dict(r,start_date=max(getdate(r['start_date']),first),end_date=min(getdate(r['end_date']),last)) for r in rows if getdate(r['start_date'])<=last and getdate(r['end_date'])>=first]
        if not rows:frappe.throw('No crew requirements fall within these event dates. Choose dates covered by the agreement.')
    starts=[getdate(r['start_date']) for r in rows];ends=[getdate(r['end_date']) for r in rows]
    for kind in ('PP Vehicle Booking','PP Equipment Booking'):
        for reservation in frappe.get_list(kind,filters={'project':doc.project,'status':'Planned'},fields=['start_date','end_date'],limit_page_length=0):
            starts.append(getdate(reservation.start_date));ends.append(getdate(reservation.end_date))
    plan=frappe.get_doc(dict(doctype='PP Event Plan',event_name=event_name,project=doc.project,company=company().name,
        contract_terms=doc.name,start_date=min(starts),end_date=max(ends),
        wage_rate=rows[0]['wage_rate'],client_rate=rows[0]['client_rate'],staffing=rows,notes=notes or '')).insert()
    return dict(name=plan.name,existing=False)


@frappe.whitelist()
def plan(name):
    from plus_point.events import plan_doc,timeline,crew_proposal
    doc=plan_doc(name)
    if not doc.contract_terms:return dict(doc.as_dict(),unlinked=True)
    terms_doc(doc.contract_terms)
    result=doc.as_dict();result.update(timeline=timeline(name),agreement=agreement(doc.contract_terms))
    from plus_point.agreement_events import governing
    result.update(governing_agreement=governing(frappe.get_doc('PP Contract Terms',doc.contract_terms)),standalone=bool(result['agreement'].get('event_basis') and not result['agreement'].get('governing_agreement')))
    if result['governing_agreement']:result['governing_title']=frappe.db.get_value('PP Contract Terms',result['governing_agreement'],'agreement_title')
    source=payment_source(terms_doc(doc.contract_terms))
    result.update(payment_plan_defined=payment_defined(source),payment_terms_owner=source.name,event_payment_terms=source.name==doc.contract_terms and bool(result['agreement'].get('event_basis')))
    workers={r.name:r for r in frappe.get_list('Employee',filters={'company':doc.company},fields=['name','employee_name','designation','image'],limit_page_length=0)}
    allocations=frappe.get_list('PP Assignment',filters={'project':doc.project},fields=['name','employee','site','start_date','end_date','wage_rate','client_rate','pp_pay_basis','pp_pay_amount'],order_by='start_date,employee',limit_page_length=0)
    used=set(frappe.get_list('PP Work Entry',filters={'project':doc.project},pluck='assignment',limit_page_length=0))
    for row in allocations:
        person=workers.get(row.employee);row.update(worker=person.employee_name if person else row.employee,designation=person.designation if person else '',image=person.image if person else '',has_attendance=row.name in used)
    project=linked('Project',doc.project)
    result['allocations']=allocations;result['coverage']=coverage(doc)
    result['files']=frappe.get_list('File',filters={'attached_to_doctype':'PP Event Plan','attached_to_name':doc.name},fields=['name','file_name','file_url'],limit_page_length=100)
    result.update(archived=bool(project.get('pp_archived')),budget=project.estimated_costing,enforce_budget=project.pp_enforce_spending_budget)
    from plus_point.events import lifecycle
    result['event_status']=lifecycle(doc,result['archived'],project.status=='Cancelled')
    result['reservations']=[]
    for kind,label in [('PP Vehicle Booking','vehicle'),('PP Equipment Booking','item')]:
        for row in frappe.get_list(kind,filters={'project':doc.project,'status':'Planned'},fields=['name',label,'site','start_date','end_date'],limit_page_length=0):
            result['reservations'].append(dict(name=row.name,title=row[label],site=frappe.db.get_value('PP Site',row.site,'site_name'),start=str(row.start_date),end=str(row.end_date)))
    return result


def payment_source(terms):
    parent=terms_doc(terms.governing_agreement) if terms.get('governing_agreement') else None
    return parent if parent and parent.effective_end else terms


def payment_defined(terms):
    return bool(frappe.parse_json(terms.get('pp_daily_checkpoints') or '[]')) if terms.billing_model=='Daily' else bool(frappe.db.exists('PP Milestone',{'contract_terms':terms.name}))


def require_payments(terms):
    # Ongoing master agreements set dated payment schedules on each occurrence.
    if not terms.effective_end:return
    source=payment_source(terms)
    defined=payment_defined(source)
    if not defined:
        frappe.local.response['field_errors']={'payment_schedule':'Define a payment milestone or choose Pay after completion.'}
        frappe.throw('Define a payment milestone in the commercial terms before completing this record. You can choose Pay after completion.')


@frappe.whitelist(methods=['POST'])
@atomic
def save_project(name,values):
    from plus_point.events import plan_doc
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    data=frappe._dict(frappe.parse_json(values) or {})
    first=getdate(data.get('start_date') or doc.start_date);last=getdate(data.get('end_date') or doc.end_date)
    if (first,last)!=(getdate(doc.start_date),getdate(doc.end_date)):
        from plus_point.events import span
        span(first,last)
        for assignment in frappe.get_list('PP Assignment',filters={'project':doc.project},fields=['start_date','end_date'],limit_page_length=0):
            if getdate(assignment.start_date)<first or not assignment.end_date or getdate(assignment.end_date)>last:
                frappe.throw('Adjust the assigned workers’ dates before shortening the event period. Existing attendance and wages will be preserved.')
        for row in doc.staffing:
            if (getdate(row.start_date),getdate(row.end_date))==(getdate(doc.start_date),getdate(doc.end_date)):
                row.start_date=first;row.end_date=last
            else:
                if getdate(row.end_date)<first or getdate(row.start_date)>last:frappe.throw('Move or remove crew requirements outside the new event period first.')
                row.start_date=max(first,getdate(row.start_date));row.end_date=min(last,getdate(row.end_date))
        from plus_point.events import reservation_bounds
        # Full-event reservations follow its new period; partial reservations keep
        # their deliberately chosen dates. Any conflict rolls this entire edit back.
        with reservation_bounds(doc.project,first,last):
            for doctype in ('PP Equipment Booking','PP Vehicle Booking'):
                for booking_name in frappe.get_list(doctype,filters={'project':doc.project,'status':'Planned'},pluck='name',limit_page_length=0):
                    booking=linked(doctype,booking_name);booking.check_permission('write')
                    if (getdate(booking.start_date),getdate(booking.end_date))==(getdate(doc.start_date),getdate(doc.end_date)):
                        booking.start_date=first;booking.end_date=last;booking.save()
                    elif getdate(booking.start_date)<first or getdate(booking.end_date)>last:
                        frappe.throw('Move or cancel partial resource bookings outside the new event period first. No event or booking dates were changed.')
    project=linked('Project',doc.project);project.check_permission('write')
    if 'budget' in data:project.estimated_costing=data.budget
    if 'enforce_budget' in data:project.pp_enforce_spending_budget=frappe.utils.cint(data.enforce_budget)
    project.save()
    for key in ('event_name','start_date','end_date','notes'):
        if key in data:doc.set(key,data[key])
    terms=terms_doc(doc.contract_terms,True)
    if terms.get('event_basis'):
        if terms.governing_agreement:
            parent=terms_doc(terms.governing_agreement)
            if first<getdate(parent.effective_start) or parent.effective_end and last>getdate(parent.effective_end):frappe.throw('Event dates must remain within the governing agreement.')
        terms.effective_start=first;terms.effective_end=last
        for row in terms.staffing:row.start_date=first;row.end_date=last
        from plus_point.daily_billing import rebase
        rebase(terms)
        terms.save()
    if frappe.utils.cint(data.get('complete')):
        from plus_point.events import complete_plan
        if data.get('require_payment_plan'):require_payments(terms)
        complete_plan(doc)
    doc.save();return dict(name=doc.name)


def coverage(doc):
    """Compare actual allocations to the agreed category/day baseline, including extras."""
    terms=terms_doc(doc.contract_terms)
    baseline=terms.staffing or doc.staffing
    assignments=frappe.get_list('PP Assignment',filters={'project':doc.project},fields=['employee','site','start_date','end_date'],limit_page_length=0)
    roles={r.name:r.designation for r in frappe.get_list('Employee',filters={'company':doc.company},fields=['name','designation'],limit_page_length=0)}
    sites={r.name:r.site_name for r in frappe.get_list('PP Site',filters={'project':doc.project},fields=['name','site_name'],limit_page_length=0)}
    rows=[]
    from plus_point.events import span
    from plus_point.benefits import leave_map
    leaves=leave_map([r.employee for r in assignments],doc.start_date,doc.end_date)
    for day in span(doc.start_date,doc.end_date):
        required=defaultdict(int);actual=defaultdict(int);planned=defaultdict(int)
        for r in baseline:
            if getdate(r.start_date)<=getdate(day)<=getdate(r.end_date):required[(r.site,r.get('designation') or '')]+=int(r.workers_required)
        for r in doc.staffing:
            if getdate(r.start_date)<=getdate(day)<=getdate(r.end_date):planned[(r.site,r.get('designation') or '')]+=int(r.workers_required)
        for r in assignments:
            if getdate(r.start_date)<=getdate(day)<=getdate(r.end_date or doc.end_date):
                key=(r.site,roles.get(r.employee) or '')
                if (r.site,'') in required:key=(r.site,'')
                actual[key]+=float(max(Decimal(0),1-leaves.get((r.employee,day),Decimal(0))))
        for key in sorted(set(required)|set(actual)|set(planned)):
            wanted=required[key];count=actual[key];target=planned[key]
            rows.append(dict(date=day,site=key[0],venue=sites.get(key[0],key[0]),designation=key[1] or 'All crew',required=wanted,planned=target,assigned=count,planned_extra=max(0,target-wanted),extra=max(0,count-wanted),missing=max(0,target-count)))
    return rows


def auto_settings(doc,requirements,payments):
    keys={r.name for r in doc.staffing}
    if requirements is not None:
        requirements=frappe.parse_json(requirements)
        if not isinstance(requirements,list) or not requirements or len(requirements)>100 or any(not isinstance(k,str) or k not in keys for k in requirements) or len(set(requirements))!=len(requirements):
            frappe.throw('Choose existing crew roles from this event only.')
    payments=frappe.parse_json(payments) if payments is not None else {}
    if not isinstance(payments,dict) or len(payments)>100 or any(k not in (requirements or keys) or not isinstance(v,dict) for k,v in payments.items()):frappe.throw('Review pay settings for the selected event roles.')
    if payments and set(payments)!=set(requirements or keys):frappe.throw('Choose pay settings for every selected role.')
    for value in payments.values():
        if value.get('basis') not in ('Daily','Monthly'):frappe.throw('Choose Daily or Monthly pay for each role.')
        if value['basis']=='Monthly' and value.get('amount') not in (None,''):frappe.throw('Monthly pay uses each worker’s profile salary.')
        if value.get('amount') not in (None,''):
            from plus_point.events import positive
            positive(value['amount'],'Daily rate')
    return requirements,payments


def auto_snapshot(proposal):
    return [dict((k,r.get(k)) for k in ('requirement','employee','start_date','end_date','pp_pay_basis','pp_pay_amount','client_rate')) for r in proposal['assignments']]


def auto_pay_overrides(proposal,rates):
    """Overrides are allowed only for daily workers in the server-selected proposal."""
    rates=frappe.parse_json(rates) if rates is not None else {}
    if not isinstance(rates,dict) or len(rates)>1000:frappe.throw('Review the selected worker rates.')
    rows={row['employee']:row for row in proposal['assignments']}
    if any(key not in rows or rows[key]['pp_pay_basis']!='Daily' for key in rates):frappe.throw('Edit daily rates only for the workers in this selection.')
    from plus_point.events import positive
    for key,value in rates.items():
        amount=float(positive(value,'Daily rate'))
        rows[key].update(pp_pay_amount=amount,wage_rate=amount)


@frappe.whitelist()
def auto_assign_preview(name,requirements=None,payments=None,rates=None):
    from plus_point.events import plan_doc,crew_proposal
    from plus_point.planning import cost_warning
    doc=plan_doc(name);terms=terms_doc(doc.contract_terms)
    requirements,payments=auto_settings(doc,requirements,payments)
    doc.selected_crew='';proposal=crew_proposal(doc,requirements=requirements,payments=payments)
    snapshot=auto_snapshot(proposal);auto_pay_overrides(proposal,rates)
    return dict(**proposal,snapshot=snapshot,warning=cost_warning(terms,proposal['assignments']))


@frappe.whitelist(methods=['POST'])
def auto_assign(name,confirm_over_budget=0,requirements=None,payments=None,expected=None,rates=None):
    from plus_point.events import plan_doc,crew_proposal,validate_plan
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    from plus_point.budget import lock_project
    lock_project(doc.project)
    frappe.db.get_value('PP Event Plan',name,'name',for_update=True);doc.reload()
    # Select only matching available categories; existing allocations count as cover.
    requirements,payments=auto_settings(doc,requirements,payments)
    doc.selected_crew='';proposal=crew_proposal(doc,lock=True,requirements=requirements,payments=payments)
    if expected is not None and frappe.parse_json(expected)!=auto_snapshot(proposal):frappe.throw('Crew availability or profile pay changed. Review the selection again before assigning.')
    auto_pay_overrides(proposal,rates)
    frappe.db.savepoint('pp_auto_staff')
    try:
        from plus_point.planning import cost_warning
        warning=cost_warning(terms_doc(doc.contract_terms),proposal['assignments'])
        if warning and not frappe.utils.cint(confirm_over_budget):frappe.throw(warning)
        added=[]
        for row in proposal['assignments']:
            assignment=frappe.get_doc(dict(doctype='PP Assignment',employee=row['employee'],project=doc.project,site=row['site'],contract_terms=doc.contract_terms,
                start_date=row['start_date'],end_date=row['end_date'],wage_rate=row['wage_rate'],client_rate=row['client_rate'],pp_event_plan=name,
                pp_pay_basis=row.get('pp_pay_basis'),pp_pay_amount=row.get('pp_pay_amount'),
                pp_cost_override=frappe.utils.cint(confirm_over_budget))).insert()
            added.append(assignment.name)
        frappe.db.set_value('PP Event Plan',name,'crew_allocated',int(all(not row['missing'] for row in coverage(doc))))
        return dict(created=len(added),assignments=added,shortages=proposal['shortages'])
    except Exception:
        frappe.db.rollback(save_point='pp_auto_staff');raise


@frappe.whitelist(methods=['POST'])
def undo_auto_assign(name,assignments):
    """Release only the named new allocations, never recorded work or other events."""
    from plus_point.events import plan_doc
    from plus_point.budget import lock_project
    doc=plan_doc(name,True);terms_doc(doc.contract_terms);lock_project(doc.project)
    names=list(dict.fromkeys(frappe.parse_json(assignments) or []))
    if not names or len(names)>1000:frappe.throw('Choose the assignments from this auto-selection.')
    frappe.db.savepoint('pp_undo_auto_staff')
    try:
        records=[]
        for assignment in sorted(names):
            row=frappe.get_doc('PP Assignment',assignment,for_update=True);row.check_permission('delete')
            if row.project!=doc.project or row.pp_event_plan!=doc.name:frappe.throw('Only assignments in this event can be released.')
            frappe.db.get_value('Employee',row.employee,'name',for_update=True)
            if frappe.db.exists('PP Work Entry',{'assignment':row.name}):
                frappe.throw('Attendance already references this worker. Review that record before releasing the assignment.')
            records.append(row)
        # The native on_trash hook removes blank auto-rosters and rejects marked
        # or submitted attendance. The savepoint keeps bulk undo all-or-nothing.
        for row in records:frappe.delete_doc('PP Assignment',row.name)
        frappe.db.set_value('PP Event Plan',name,'crew_allocated',int(all(not row['missing'] for row in coverage(doc))))
        return dict(released=len(records))
    except Exception:
        frappe.db.rollback(save_point='pp_undo_auto_staff');raise


@frappe.whitelist()
def available_crew(name,requirement):
    from plus_point.events import plan_doc
    from plus_point.crew import available
    doc=plan_doc(name);terms_doc(doc.contract_terms)
    row=next((r for r in doc.staffing if r.name==requirement),None)
    if not row:frappe.throw('Reload the site requirements.')
    result=available(doc.company,row.start_date,row.end_date)
    assigned={r.employee:r.name for r in frappe.get_list('PP Assignment',filters={
        'project':doc.project,'site':row.site,'start_date':['<=',row.end_date]},
        fields=['name','employee','end_date'],limit_page_length=0)
        if not r.end_date or getdate(r.end_date)>=getdate(row.start_date)}
    people={r.name:r for r in frappe.get_list('Employee',filters={'company':doc.company},fields=['name','designation','pp_salary_basis','pp_salary_amount','pp_daily_rate','pp_monthly_rate'],limit_page_length=0)}
    from plus_point.planning import worker_rates
    for r in result['rows']:
        person=people[r['name']];r.update(pay_rates=worker_rates(person),pay_basis=person.get('pp_salary_basis') or 'Daily')
        role=person.designation or '';eligible=not row.designation or not role or role==row.designation
        r.update(designation=role,assigned=r['name'] in assigned,assignment=assigned.get(r['name']),eligible=eligible)
        if not eligible and not r['assigned']:r.update(available=False,reason=f'Category: {role}. This position needs {row.designation}.')
    return result


@frappe.whitelist(methods=['POST'])
def assign_crew(name,requirement,employees,payments=None,confirm_over_budget=0):
    from plus_point.events import plan_doc
    from plus_point.crew import assign,selection
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    row=next((r for r in doc.staffing if r.name==requirement),None)
    if not row:frappe.throw('Reload the site requirements.')
    names=selection(frappe.parse_json(employees))
    frappe.db.savepoint('pp_manual_crew')
    try:
        from plus_point.budget import lock_project
        lock_project(doc.project)
        doc.reload();row=next((r for r in doc.staffing if r.name==requirement),None)
        if not row:frappe.throw('The crew requirement changed. Reload the event before assigning workers.')
        for employee in names:
            worker=linked('Employee',employee,doc.company)
            if row.designation and worker.designation and worker.designation!=row.designation:frappe.throw('Select workers in the required category.')
            if row.designation and not worker.designation:
                worker.designation=row.designation;worker.save()
        from plus_point.budget import lock_project
        lock_project(doc.project)
        existing={r.employee for r in frappe.get_list('PP Assignment',filters={'project':doc.project,'site':row.site,
            'start_date':['<=',row.end_date]},fields=['employee','end_date'],limit_page_length=0)
            if not r.end_date or getdate(r.end_date)>=getdate(row.start_date)}
        names=[n for n in names if n not in existing]
        from plus_point.planning import pay_preview
        preview=pay_preview(name,requirement,names,payments) if names else dict(rows=[],warning='')
        if preview['warning'] and not frappe.utils.cint(confirm_over_budget):frappe.throw(preview['warning'])
        result=dict(created=0,assignments=[])
        for proposal in preview['rows']:
            added=assign(doc.project,row.site,doc.contract_terms,row.start_date,row.end_date,proposal['wage_rate'],row.client_rate or doc.client_rate,[proposal['employee']],
                pay_basis=proposal['pp_pay_basis'],pay_amount=proposal['pp_pay_amount'],confirm_over_budget=confirm_over_budget);result['created']+=added['created'];result['assignments']+=added.get('assignments',[])
        for assignment in result.get('assignments',[]):frappe.db.set_value('PP Assignment',assignment,'pp_event_plan',name)
        frappe.db.set_value('PP Event Plan',name,'crew_allocated',int(all(not r['missing'] for r in coverage(doc))))
        return result
    except Exception:
        frappe.db.rollback(save_point='pp_manual_crew');raise


@frappe.whitelist(methods=['POST'])
def add_requirement(name,values):
    from plus_point.events import plan_doc
    doc=plan_doc(name,True);terms=terms_doc(doc.contract_terms)
    raw=frappe._dict(frappe.parse_json(values) or {})
    if terms.get('event_basis') and terms.billing_model=='Daily':
        agreed={r['designation']:money(r['client_rate']) for r in frappe.parse_json(terms.rate_card or '[]')}
        agreed.update({r.designation:money(r.client_rate) for r in terms.staffing})
        if raw.get('client_rate') is None:raw.client_rate=agreed.get(raw.designation,0)
        if money(raw.client_rate)!=agreed.get(raw.designation):
            terms.commercial_status='Pending';terms.commercial_source='Additional or changed client rate requires confirmation.';terms.save()
    doc.append('staffing',{key:raw.get(key) for key in ('site','designation','start_date','end_date','workers_required','wage_rate','client_rate','phase')})
    doc.save();return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def update_headcount(name,requirement,workers_required):
    from plus_point.events import plan_doc
    doc=plan_doc(name,True);terms_doc(doc.contract_terms)
    row=next((r for r in doc.staffing if r.name==requirement),None)
    if not row:frappe.throw('Reload the event requirements.')
    row.workers_required=workers_required;doc.save()
    # Changing a target never silently allocates/releases a person or changes a rate.
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def bulk_requirements(name,requirements,values):
    from plus_point.events import plan_doc
    from plus_point.budget import lock_project
    doc=plan_doc(name,True);terms_doc(doc.contract_terms);lock_project(doc.project)
    frappe.db.get_value('PP Event Plan',name,'name',for_update=True);doc.reload()
    keys=frappe.parse_json(requirements);values=frappe.parse_json(values)
    if not isinstance(keys,list) or not keys or len(keys)>100 or len(set(keys))!=len(keys) or any(key not in {r.name for r in doc.staffing} for key in keys):frappe.throw('Select crew requirements from this event only.')
    if not isinstance(values,dict) or not values or set(values)-{'workers_required','phase','start_date','end_date'}:frappe.throw('Choose crew quantities, phases or dates to change.')
    for row in doc.staffing:
        if row.name in keys:row.update(values)
    doc.save();return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def move_worker(assignment,effective_date,target_plan=None,site=None,end_date=None,confirm_over_budget=0):
    """End the old commitment before a new one; never rewrite attendance or rates."""
    business=company();old=linked('PP Assignment',assignment);old.check_permission('write');linked('Project',old.project,business.name)
    target=linked('PP Event Plan',target_plan) if target_plan else None
    from plus_point.budget import lock_project
    for name in sorted({old.project}|({target.project} if target else set())):lock_project(name)
    old=frappe.get_doc('PP Assignment',assignment,for_update=True)
    frappe.db.get_value('Employee',old.employee,'name',for_update=True)
    first=getdate(effective_date)
    if first<getdate(today()):frappe.throw('Use today or a future date for transfers. Past attendance stays unchanged.')
    if first<getdate(old.start_date) or old.end_date and first>getdate(old.end_date):frappe.throw('Choose a date within the current allocation.')
    if frappe.db.exists('PP Work Entry',{'assignment':old.name,'work_date':['>=',first]}):frappe.throw('Attendance already exists on or after this date. Choose a date after the last recorded work.')
    frappe.db.savepoint('pp_move_worker')
    try:
        lines=frappe.get_all('PP Register Line',filters={'assignment':old.name},fields=['name','parent','attendance_status','work_entry'])
        for row in lines:
            register=linked('PP Daily Register',row.parent)
            if getdate(register.work_date)<first:continue
            register.check_permission('write')
            if register.docstatus or row.work_entry or row.attendance_status!='Not marked':frappe.throw('Clear unapproved marks after the transfer date before moving this worker.')
            register.remove(next(r for r in register.entries if r.name==row.name));register.save()
        if first==getdate(old.start_date):frappe.delete_doc('PP Assignment',old.name)
        else:old.end_date=add_days(first,-1);old.save()
        if old.get('pp_event_plan'):frappe.db.set_value('PP Event Plan',old.pp_event_plan,'crew_allocated',0)
        if target:
            linked('Project',target.project,business.name);terms=terms_doc(target.contract_terms)
            role=frappe.db.get_value('Employee',old.employee,'designation')
            last=getdate(end_date or target.end_date)
            matching=[r for r in target.staffing if r.site==site and (not r.designation or r.designation==role) and getdate(r.start_date)<=first and getdate(r.end_date)>=last]
            if not matching:frappe.throw('The destination needs a matching worker category and dates. Add the category to the plan first.')
            row=matching[0]
            from plus_point.crew import validate_selected
            validate_selected([old.employee],business.name,first,last,lock=True)
            new=frappe.get_doc(dict(doctype='PP Assignment',employee=old.employee,site=site,project=target.project,contract_terms=terms.name,
                start_date=first,end_date=last,wage_rate=old.wage_rate,pp_pay_basis=old.get('pp_pay_basis'),pp_pay_amount=old.get('pp_pay_amount'),
                pp_cost_override=frappe.utils.cint(confirm_over_budget),client_rate=(row.client_rate or target.client_rate) if terms.billing_model=='Daily' else 0,pp_event_plan=target.name)).insert()
            return dict(name=new.name,transferred=True)
        return dict(transferred=False,released=True)
    except Exception:
        frappe.db.rollback(save_point='pp_move_worker');raise


@frappe.whitelist(methods=['POST'])
def save_milestone(contract_terms,values,name=None):
    terms=terms_doc(contract_terms,True);values=frappe._dict(frappe.parse_json(values) or {})
    doc=linked('PP Milestone',name) if name else frappe.new_doc('PP Milestone')
    if name and doc.contract_terms!=terms.name:frappe.throw('Choose a milestone in this agreement.')
    doc.update(dict(contract_terms=terms.name,**{k:values.get(k) for k in ('milestone_title','due_date','amount','status')}));doc.save()
    return dict(name=doc.name,sales_invoice=frappe.db.get_value('PP Milestone',doc.name,'sales_invoice'))


@frappe.whitelist(methods=['POST'])
def bulk_milestones(contract_terms,names,values):
    terms=terms_doc(contract_terms,True);frappe.db.get_value('PP Contract Terms',terms.name,'name',for_update=True)
    names=frappe.parse_json(names);values=frappe.parse_json(values)
    if not isinstance(names,list) or not names or len(names)>100 or len(set(names))!=len(names):frappe.throw('Select up to 100 milestones.')
    if not isinstance(values,dict) or not values or set(values)-{'due_date','amount','status'}:frappe.throw('Choose payment due, amount or status to change.')
    docs=[]
    for name in sorted(names):
        doc=linked('PP Milestone',name);doc.check_permission('write')
        if doc.contract_terms!=terms.name or doc.sales_invoice:frappe.throw('Select uninvoiced milestones in this agreement only.')
        docs.append(doc)
    total=sum((money(values.get('amount',row.amount)) for row in frappe.get_all('PP Milestone',filters={'contract_terms':terms.name},fields=['name','amount']) if row.name in names),money(0))
    total+=sum((money(row.amount) for row in frappe.get_all('PP Milestone',filters={'contract_terms':terms.name},fields=['name','amount']) if row.name not in names),money(0))
    if total>money(terms.fixed_amount):frappe.throw('Milestone amounts cannot exceed the fixed contract value.')
    frappe.db.savepoint('pp_bulk_milestones')
    try:
        for doc in docs:save_milestone(terms.name,dict(milestone_title=doc.milestone_title,due_date=doc.due_date,amount=doc.amount,status=doc.status)|values,doc.name)
    except Exception:
        frappe.db.rollback(save_point='pp_bulk_milestones');raise
    return dict(updated=len(docs))


def milestone_invoice(doc,method=None):
    if doc.status!='Approved' or doc.sales_invoice or frappe.flags.in_migrate:return
    terms=frappe.get_doc('PP Contract Terms',doc.contract_terms)
    if not terms.get('auto_invoice'):return
    if not terms.billing_item:
        terms.billing_item=service_item();frappe.db.set_value('PP Contract Terms',terms.name,'billing_item',terms.billing_item)
    from plus_point.billing import create_invoice
    create_invoice(terms.name,terms.billing_item,source_names=[doc.name])


@frappe.whitelist()
def billing(contract_terms):
    terms=terms_doc(contract_terms)
    from plus_point.api import project_summary
    ids=[terms.name]+frappe.get_list('PP Contract Terms',filters={'governing_agreement':terms.name,'event_basis':1},pluck='name',limit_page_length=200)
    projects={terms.project}|set(frappe.get_list('PP Contract Terms',filters={'name':['in',ids]},pluck='project',limit_page_length=200))
    summaries=[project_summary(p) for p in sorted(projects)];totals=dict(summaries[0])
    for key,value in list(totals.items()):
        if isinstance(value,str):
            try:totals[key]=str(sum((money(r[key]) for r in summaries),money(0)))
            except (ValueError,ArithmeticError):pass
    totals['fixed_contract_value']=str(money(terms.fixed_amount))
    source_type='PP Milestone' if terms.billing_model=='Fixed' else 'PP Work Entry'
    return dict(agreement=agreement(terms.name),totals=totals,
        unbilled_count=frappe.db.count(source_type,{'contract_terms':['in',ids],'status':'Approved','sales_invoice':['is','not set'],('amount' if source_type=='PP Milestone' else 'billable_amount'):['>',0]}),
        invoices=frappe.get_list('Sales Invoice',filters={'project':['in',list(projects)]},fields=['name','posting_date','due_date','grand_total','outstanding_amount','currency','docstatus','status'],order_by='posting_date desc,name desc',limit_page_length=200))



@frappe.whitelist(methods=['POST'])
def extra_invoice(contract_terms,item_code,description,amount,invoice_currency=None,exchange_rate=None):
    terms=terms_doc(contract_terms)
    from plus_point.agreement_events import assert_confirmed
    assert_confirmed(terms)
    project=linked('Project',terms.project)
    from plus_point.events import positive
    positive(amount,'Invoice amount');linked('Item',item_code)
    if not str(description or '').strip():frappe.throw('Describe the extra charge.')
    currency=invoice_currency or terms.currency;linked('Currency',currency)
    from plus_point.billing import receivable_account,quote
    rate=Decimal(1) if currency==terms.currency else positive(exchange_rate or (terms.get('pp_agreement_rate') if currency==terms.get('pp_agreement_currency') else quote(project.company,currency)['rate']),'Exchange rate')
    doc=frappe.get_doc(dict(doctype='Sales Invoice',company=project.company,project=project.name,customer=project.customer,
        currency=currency,conversion_rate=float(rate),debit_to=receivable_account(project.company,currency),items=[dict(item_code=item_code,description=description,qty=1,rate=amount,project=project.name)])).insert()
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def update_invoice(name,values):
    business=company();doc=linked('Sales Invoice',name);linked('Project',doc.project,business.name);doc.check_permission('write')
    if doc.docstatus:frappe.throw('Only draft invoices can be edited. Posted invoices retain their history.')
    data=frappe._dict(frappe.parse_json(values) or {})
    currency=data.get('currency') or doc.currency
    linked('Currency',currency)
    from plus_point.events import positive
    base=frappe.db.get_value('Company',doc.company,'default_currency')
    rate=Decimal(1) if currency==base else positive(data.get('exchange_rate') or doc.conversion_rate,'Exchange rate')
    old_rate=Decimal(str(doc.conversion_rate))
    if currency!=doc.currency or rate!=old_rate:
        from plus_point.billing import receivable_account
        doc.debit_to=receivable_account(doc.company,currency)
        doc.currency=currency;doc.conversion_rate=float(rate)
        for row in doc.items:
            if row.get('pp_source_name'):
                source=linked(row.pp_source_type,row.pp_source_name)
                amount=source.amount if row.pp_source_type=='PP Milestone' else source.billable_amount
                row.rate=float(money(Decimal(str(amount))/rate))
            else:row.rate=float(money(Decimal(str(row.rate))*old_rate/rate))
    if data.get('due_date'):doc.due_date=data.due_date
    if 'remarks' in data:doc.remarks=data.remarks
    items={r.name:r for r in doc.items}
    for row in data.get('items',[]):
        if row.get('name') not in items:frappe.throw('Reload the invoice before editing its items.')
        item=items[row['name']]
        if 'description' in row:item.description=row['description']
        if not item.get('pp_source_name'):
            if 'rate' in row:
                from plus_point.events import positive
                positive(row['rate'],'Rate');item.rate=row['rate']
    doc.save();return dict(name=doc.name)


@frappe.whitelist()
def invoice(name):
    business=company();doc=linked('Sales Invoice',name);linked('Project',doc.project,business.name)
    return dict(name=doc.name,project=doc.project,docstatus=doc.docstatus,due_date=doc.due_date,remarks=doc.remarks,currency=doc.currency,exchange_rate=doc.conversion_rate,
        items=[dict(name=r.name,description=r.description,rate=r.rate,qty=r.qty,amount=r.amount,locked=bool(r.get('pp_source_name'))) for r in doc.items])


@frappe.whitelist(methods=['POST'])
def post_invoice(name):
    invoice(name);doc=linked('Sales Invoice',name);doc.submit();return dict(name=doc.name)


@frappe.whitelist()
def email_options(name):
    invoice(name);doc=linked('Sales Invoice',name)
    from plus_point.clients import details
    recipient=details(doc.customer)['email']
    return dict(recipient=recipient,configured=bool(frappe.db.exists('Email Account',{'enable_outgoing':1})))


def invoice_pdf_content(doc):
    doc.check_permission('print')
    from frappe.utils.pdf import get_pdf
    html=frappe.get_print('Sales Invoice',doc.name,print_format='PLUS POINT Branded Invoice',doc=doc)
    options={}
    # Chromium resolves *.localhost on Windows; wkhtmltopdf inside Linux does not.
    # Rebase this local render only, retaining the tenant Host for public assets.
    # Native private-image inlining and file-access protections remain in force.
    if frappe.local.site.endswith('.localhost'):
        from frappe.utils import scrub_urls,get_url
        html=scrub_urls(html).replace(get_url().rstrip('/'),'http://127.0.0.1:8000')
        options={'custom-header':[('Host',frappe.local.site+':8000')],'custom-header-propagation':None}
    return get_pdf(html,options=options)


@frappe.whitelist()
def download_invoice(name):
    invoice(name);doc=linked('Sales Invoice',name)
    from plus_point.agreement_documents import invoice_pdf
    stored=invoice_pdf(name);content=frappe.get_doc('File',stored['name']).get_content()
    if isinstance(content,str):content=content.encode()
    frappe.local.response.update(filename=re.sub(r'[^A-Za-z0-9_.-]','_',name)+'.pdf',filecontent=content,type='pdf',http_status_code=200)
    from frappe.utils.response import build_response
    response=build_response('pdf')
    response.headers.set('Content-Disposition','attachment',filename=frappe.local.response.filename)
    return response


@frappe.whitelist(methods=['POST'])
def email_invoice(name,recipient,subject,body):
    options=email_options(name)
    if not options['configured']:frappe.throw('Connect an outgoing email account before sending invoices.')
    recipient=frappe.utils.validate_email_address(recipient,throw=True)
    if not recipient:frappe.throw('Enter the client email address.')
    if not str(subject or '').strip() or len(subject)>140:frappe.throw('Enter an email subject of up to 140 characters.')
    doc=linked('Sales Invoice',name);doc.check_permission('read')
    from plus_point.agreement_documents import invoice_pdf
    stored=invoice_pdf(name);file=frappe.get_doc('File',stored['name'])
    frappe.sendmail(recipients=[recipient],subject=subject,message=frappe.utils.escape_html(body or '').replace('\n','<br>'),
        attachments=[dict(fname=file.file_name,fcontent=file.get_content())],
        reference_doctype='Sales Invoice',reference_name=name)
    return dict(queued=True)


@frappe.whitelist(methods=['POST'])
def set_photo(employee,file_url=None):
    business=company();worker=linked('Employee',employee,business.name);worker.check_permission('write')
    if file_url:
        files=frappe.get_list('File',filters={'file_url':file_url,'attached_to_doctype':'Employee','attached_to_name':employee},fields=['name','file_name'],limit_page_length=1)
        if not files or files[0].file_name.rsplit('.',1)[-1].lower() not in ('png','jpg','jpeg','webp','gif'):frappe.throw('Upload a PNG, JPG, WebP or GIF attached to this worker profile.')
    worker.image=file_url or '';worker.save();return dict(image=worker.image)


@frappe.whitelist()
def worker_states():
    business=company();day=getdate(today());result={}
    projects=frappe.get_list('Project',filters={'company':business.name},pluck='name',limit_page_length=0)
    for row in frappe.get_list('PP Assignment',filters={'project':['in',projects or ['']]},fields=['employee','start_date','end_date'],limit_page_length=0):
        if row.end_date and getdate(row.end_date)<day:continue
        state='Assigned' if getdate(row.start_date)<=day else 'Scheduled'
        if result.get(row.employee)!='Assigned':result[row.employee]=state
    return result


@frappe.whitelist()
def worker_filter(state):
    business=company()
    if state not in ('Available','Assigned','Scheduled','Inactive'):frappe.throw('Choose a worker availability status.')
    workers=frappe.get_list('Employee',filters={'company':business.name},fields=['name','status'],limit_page_length=0)
    # Booking dates, including future bookings, drive availability; not a hidden
    # default employee filter or the list's current page of results.
    projects=frappe.get_list('Project',filters={'company':business.name},pluck='name',limit_page_length=0)
    day=getdate(today());states={}
    for row in frappe.get_list('PP Assignment',filters={'project':['in',projects or ['']]},fields=['employee','start_date','end_date'],limit_page_length=0):
        if row.end_date and getdate(row.end_date)<day:continue
        value='Assigned' if getdate(row.start_date)<=day else 'Scheduled'
        if states.get(row.employee)!='Assigned':states[row.employee]=value
    return [w.name for w in workers if ('Inactive' if w.status!='Active' else states.get(w.name,'Available'))==state]


@frappe.whitelist(methods=['POST'])
def create_category(title):
    company();title=str(title or '').strip()
    if not title or len(title)>100:frappe.throw('Enter a worker category of up to 100 characters.')
    if not frappe.db.exists('Designation',title):frappe.get_doc(dict(doctype='Designation',designation_name=title)).insert()
    frappe.defaults.set_global_default('pp_event_roles',json.dumps(sorted(set(event_roles())|{title})))
    return dict(name=title)


def activity_doc(doctype,name):
    if doctype=='PP Planning Draft':
        from plus_point.drafts import checked
        return checked(name)
    if doctype=='PP Contract Terms':return terms_doc(name)
    if doctype=='PP Event Plan':
        from plus_point.events import plan_doc
        doc=plan_doc(name)
        if doc.contract_terms:terms_doc(doc.contract_terms)
        return doc
    frappe.throw('Choose an agreement, draft or event for comments.')


@frappe.whitelist()
def activity(doctype,name):
    doc=activity_doc(doctype,name)
    return dict(comments=frappe.get_list('Comment',filters={'reference_doctype':doctype,'reference_name':name,'comment_type':'Comment'},fields=['name','content','comment_by','creation'],order_by='creation desc',limit_page_length=50),
        versions=frappe.get_list('Version',filters={'ref_doctype':doctype,'docname':name},fields=['name','owner','creation'],order_by='creation desc',limit_page_length=20),
        created=doc.creation,modified=doc.modified,owner=doc.owner,modified_by=doc.modified_by)


@frappe.whitelist(methods=['POST'])
def add_comment(doctype,name,content):
    doc=activity_doc(doctype,name);doc.check_permission('write')
    text=str(content or '').strip()
    if not text or len(text)>5000:frappe.throw('Write a comment of up to 5,000 characters.')
    doc.add_comment('Comment','<p>'+frappe.utils.escape_html(text).replace('\n','<br>')+'</p>')
    return dict(saved=True)
